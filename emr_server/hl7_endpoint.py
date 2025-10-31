import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from .auth import verify_token, get_medplum_token
from .hl7_converter import convert_hl7_to_fhir
import os

MEDPLUM_BASE_URL = os.getenv("MEDPLUM_BASE_URL", "https://api.medplum.com/fhir/R4")

router = APIRouter(prefix="/hl7", tags=["HL7"])


async def search_patient_by_mrn(mrn: str, medplum_token: str) -> dict:
    """Search for existing patient by MRN identifier"""
    url = f"{MEDPLUM_BASE_URL}/Patient"
    
    async with httpx.AsyncClient() as client:
        # Get ALL patients and search through them
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {medplum_token}"}
        )
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get("entry"):
                # Check every patient for matching MRN
                for entry in bundle.get("entry", []):
                    patient = entry.get("resource", {})
                    identifiers = patient.get("identifier", [])
                    for identifier in identifiers:
                        # Match on value only
                        if identifier.get("value") == mrn:
                            print(f"Found existing patient with MRN {mrn}: {patient.get('id')}")
                            return patient
        
        print(f"No existing patient found with MRN {mrn}")
        return None


async def create_fhir_resource(resource: dict, medplum_token: str) -> dict:
    """Create a FHIR resource in Medplum"""
    resource_type = resource["resourceType"]
    url = f"{MEDPLUM_BASE_URL}/{resource_type}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=resource,
            headers={
                "Authorization": f"Bearer {medplum_token}",
                "Content-Type": "application/fhir+json"
            }
        )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create {resource_type}: {response.text}"
            )
        
        return response.json()


@router.post("/inbound")
async def receive_hl7_message(
    request: Request,
    token: str = Depends(verify_token),
    medplum_token: str = Depends(get_medplum_token)
):
    """
    Receive HL7 v2 ADT messages and convert them to FHIR resources
    
    Expects plain text HL7 message in request body
    """
    # Get raw HL7 message from request body
    hl7_message = await request.body()
    hl7_message = hl7_message.decode('utf-8')
    
    if not hl7_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty HL7 message"
        )
    
    # Convert HL7 to FHIR
    try:
        fhir_resources = convert_hl7_to_fhir(hl7_message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse HL7 message: {str(e)}"
        )
    
    if not fhir_resources.get("patient"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No patient information found in HL7 message"
        )
    
    summary = {
        "patient": {"action": None, "id": None},
        "coverage": {"action": None, "id": None}
    }
    
    # Check if patient exists by MRN
    patient_resource = fhir_resources["patient"]
    mrn = None
    if patient_resource.get("identifier"):
        mrn = patient_resource["identifier"][0]["value"]
    
    existing_patient = None
    if mrn:
        existing_patient = await search_patient_by_mrn(mrn, medplum_token)
    
    # Create or use existing patient
    if existing_patient:
        summary["patient"]["action"] = "found"
        summary["patient"]["id"] = existing_patient["id"]
        patient_id = existing_patient["id"]
    else:
        # Create new patient
        created_patient = await create_fhir_resource(patient_resource, medplum_token)
        summary["patient"]["action"] = "created"
        summary["patient"]["id"] = created_patient["id"]
        patient_id = created_patient["id"]
    
    # Handle coverage if present
    if fhir_resources.get("coverage"):
        coverage_resource = fhir_resources["coverage"]
        # Update beneficiary reference with actual patient ID
        coverage_resource["beneficiary"]["reference"] = f"Patient/{patient_id}"
        
        # Create coverage
        created_coverage = await create_fhir_resource(coverage_resource, medplum_token)
        summary["coverage"]["action"] = "created"
        summary["coverage"]["id"] = created_coverage["id"]
    
    return {
        "message": "HL7 message processed successfully",
        "summary": summary
    }


@router.get("/health")
async def hl7_health():
    """Health check endpoint for HL7 service"""
    return {"status": "HL7 endpoint is healthy"}