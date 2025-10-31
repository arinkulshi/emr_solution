import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

EMR_SERVER_URL = os.getenv("EMR_SERVER_URL", "http://localhost:8000")

router = APIRouter(prefix="/patient", tags=["Patient Service"])


# Pydantic models for request validation
class InsuranceInfo(BaseModel):
    name: str
    memberID: str
    plan: str
    groupNumber: str


class PatientData(BaseModel):
    mrn: Optional[str] = None
    lastName: str
    firstName: str
    dob: str  # Format: MM/DD/YYYY
    gender: str  # "Male" or "Female"
    insurance: Optional[InsuranceInfo] = None


class IntegrationServiceAuth:
    """Handle authentication with EMR Server"""
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
    
    async def get_access_token(self) -> str:
        """Get valid access token from EMR Server"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        # Request new token from EMR Server
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{EMR_SERVER_URL}/auth/token")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to authenticate with EMR Server"
                )
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            # Token expires in 24 hours, refresh 1 hour before
            self.token_expiry = datetime.now() + timedelta(seconds=82800)
            
            return self.access_token


# Global auth instance
emr_auth = IntegrationServiceAuth()


async def check_patient_exists(mrn: str, token: str) -> Optional[dict]:
    """Check if patient exists in EMR by MRN"""
    if not mrn:
        return None
    
    url = f"{EMR_SERVER_URL}/fhir/Patient"
    params = {"identifier": mrn}
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            return None
        
        bundle = response.json()
        
        # Check if we found any patients and verify MRN matches
        if bundle.get("total", 0) > 0 and bundle.get("entry"):
            for entry in bundle.get("entry", []):
                patient = entry.get("resource", {})
                identifiers = patient.get("identifier", [])
                for identifier in identifiers:
                    if identifier.get("value") == mrn:
                        return patient
        
        return None


async def send_hl7_to_emr(hl7_message: str, token: str) -> dict:
    """Send HL7 message to EMR Server"""
    url = f"{EMR_SERVER_URL}/hl7/inbound"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, content=hl7_message, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to send HL7 to EMR: {response.text}"
            )
        
        return response.json()


def format_date_for_hl7(date_str: str) -> str:
    """Convert MM/DD/YYYY to YYYYMMDD for HL7"""
    try:
        # Parse MM/DD/YYYY
        parts = date_str.split('/')
        if len(parts) != 3:
            raise ValueError("Invalid date format")
        
        month, day, year = parts
        # Return YYYYMMDD
        return f"{year}{month.zfill(2)}{day.zfill(2)}"
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Expected MM/DD/YYYY, got {date_str}"
        )


def generate_hl7_message(patient_data: PatientData) -> str:
    """Generate HL7 ADT^A04 message from patient data"""
    from datetime import datetime
    
    # Generate message timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Generate unique message ID
    msg_id = f"MSG{timestamp}"
    
    # MSH segment
    msh = f"MSH|^~\\&|INTEGRATION|CLINIC|EMR|HOSPITAL|{timestamp}||ADT^A04|{msg_id}|P|2.5"
    
    # PID segment
    mrn = patient_data.mrn if patient_data.mrn else f"MRN{timestamp}"
    last_name = patient_data.lastName
    first_name = patient_data.firstName
    dob = format_date_for_hl7(patient_data.dob)
    gender = "M" if patient_data.gender.upper() in ["MALE", "M"] else "F"
    
    pid = f"PID|1||{mrn}^^^MRN||{last_name}^{first_name}||{dob}|{gender}"
    
    # IN1 segment (if insurance provided)
    segments = [msh, pid]
    
    if patient_data.insurance:
        ins = patient_data.insurance
        in1 = f"IN1|1|{ins.memberID}||{ins.name}|||||{ins.groupNumber}|{ins.plan}"
        segments.append(in1)
    
    # Join segments with CR (carriage return)
    return "\r".join(segments)


@router.post("/")
async def create_or_update_patient(patient_data: PatientData):
    """
    Create or update patient in EMR
    
    Process:
    1. Get access token from EMR Server
    2. Check if patient exists (by MRN)
    3. If not exists, generate HL7 message and send to EMR
    4. Return result summary
    """
    # Get authentication token
    try:
        token = await emr_auth.get_access_token()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate: {str(e)}"
        )
    
    # Check if patient exists
    existing_patient = None
    if patient_data.mrn:
        existing_patient = await check_patient_exists(patient_data.mrn, token)
    
    if existing_patient:
        return {
            "status": "patient_exists",
            "message": "Patient already exists in EMR",
            "patient_id": existing_patient.get("id"),
            "mrn": patient_data.mrn
        }
    
    # Generate HL7 message
    try:
        hl7_message = generate_hl7_message(patient_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate HL7 message: {str(e)}"
        )
    
    # Send HL7 to EMR
    try:
        emr_response = await send_hl7_to_emr(hl7_message, token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send to EMR: {str(e)}"
        )
    
    # Check if EMR found existing patient or created new one
    patient_action = emr_response.get("summary", {}).get("patient", {}).get("action")
    
    if patient_action == "found":
        # EMR found existing patient - return error to prevent confusion
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Patient with MRN {patient_data.mrn} already exists in EMR"
        )
    
    return {
        "status": "patient_created",
        "message": "Patient successfully created in EMR",
        "emr_response": emr_response,
        "hl7_message": hl7_message
    }


@router.get("/health")
async def patient_service_health():
    """Health check for patient service"""
    return {"status": "Patient service is healthy"}