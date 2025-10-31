import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from .auth import verify_token, get_medplum_token
import os

MEDPLUM_BASE_URL = os.getenv("MEDPLUM_BASE_URL", "https://api.medplum.com/fhir/R4")

router = APIRouter(prefix="/fhir", tags=["FHIR Proxy"])


async def proxy_fhir_get(resource_type: str, query_params: str, medplum_token: str):
    """Proxy GET request to Medplum FHIR API"""
    url = f"{MEDPLUM_BASE_URL}/{resource_type}"
    if query_params:
        url += f"?{query_params}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {medplum_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Medplum API error: {response.text}"
            )
        
        return response.json()


@router.get("/Patient")
async def get_patients(
    request: Request,
    token: str = Depends(verify_token),
    medplum_token: str = Depends(get_medplum_token)
):
    """Search for patients"""
    query_params = str(request.query_params)
    return await proxy_fhir_get("Patient", query_params, medplum_token)


@router.get("/Patient/{patient_id}")
async def get_patient_by_id(
    patient_id: str,
    token: str = Depends(verify_token),
    medplum_token: str = Depends(get_medplum_token)
):
    """Get a specific patient by ID"""
    url = f"{MEDPLUM_BASE_URL}/Patient/{patient_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {medplum_token}"}
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Patient not found")
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Medplum API error: {response.text}"
            )
        
        return response.json()


@router.get("/Coverage")
async def get_coverages(
    request: Request,
    token: str = Depends(verify_token),
    medplum_token: str = Depends(get_medplum_token)
):
    """Search for coverage resources"""
    query_params = str(request.query_params)
    return await proxy_fhir_get("Coverage", query_params, medplum_token)


@router.get("/Coverage/{coverage_id}")
async def get_coverage_by_id(
    coverage_id: str,
    token: str = Depends(verify_token),
    medplum_token: str = Depends(get_medplum_token)
):
    """Get a specific coverage by ID"""
    url = f"{MEDPLUM_BASE_URL}/Coverage/{coverage_id}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {medplum_token}"}
        )
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Coverage not found")
        elif response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Medplum API error: {response.text}"
            )
        
        return response.json()


# Reject all modification methods
@router.post("/{resource_type}")
@router.put("/{resource_type}/{resource_id}")
@router.patch("/{resource_type}/{resource_id}")
@router.delete("/{resource_type}/{resource_id}")
async def reject_modifications():
    """Reject all POST, PUT, PATCH, DELETE requests"""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Modification operations are not allowed. This is a read-only FHIR endpoint."
    )