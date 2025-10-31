import hl7
from typing import Dict, Optional, List
from datetime import datetime


def parse_hl7_message(hl7_message: str) -> hl7.Message:
    """Parse HL7 message string into hl7.Message object"""
    # Normalize line separators: CRLF or LF -> CR (HL7 standard)
    hl7_message = hl7_message.replace('\r\n', '\r').replace('\n', '\r')
    return hl7.parse(hl7_message)


def parse_hl7_date(date_str: str) -> Optional[str]:
    """Convert HL7 date format (YYYYMMDD) to FHIR date format (YYYY-MM-DD)"""
    if not date_str or len(date_str) < 8:
        return None
    
    try:
        # HL7 format: YYYYMMDD or YYYYMMDDHHMMSS
        year = date_str[0:4]
        month = date_str[4:6]
        day = date_str[6:8]
        return f"{year}-{month}-{day}"
    except:
        return None


def parse_hl7_name(name_field) -> Dict:
    """Parse HL7 XPN (Extended Person Name) field into FHIR name structure"""
    # HL7 name format: LastName^FirstName^MiddleName^Suffix^Prefix
    name_parts = str(name_field).split('^')
    
    fhir_name = {
        "use": "official",
        "family": name_parts[0] if len(name_parts) > 0 else "",
        "given": []
    }
    
    if len(name_parts) > 1 and name_parts[1]:
        fhir_name["given"].append(name_parts[1])
    
    if len(name_parts) > 2 and name_parts[2]:
        fhir_name["given"].append(name_parts[2])
    
    return fhir_name


def pid_to_fhir_patient(pid_segment) -> Dict:
    """Convert HL7 PID segment to FHIR Patient resource"""
    
    # Extract fields from PID segment
    # PID-3: Patient Identifier List (MRN)
    # PID-5: Patient Name
    # PID-7: Date of Birth
    # PID-8: Administrative Sex
    
    patient = {
        "resourceType": "Patient",
        "identifier": [],
        "name": [],
        "gender": "unknown",
        "birthDate": None
    }
    
    # PID-3: Patient Identifier (MRN)
    if len(pid_segment) > 3 and pid_segment[3]:
        mrn = str(pid_segment[3]).split('^')[0]  # Get ID from first component
        patient["identifier"].append({
            "use": "usual",
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                    "code": "MR",
                    "display": "Medical Record Number"
                }]
            },
            "value": mrn
        })
    
    # PID-5: Patient Name
    if len(pid_segment) > 5 and pid_segment[5]:
        patient["name"].append(parse_hl7_name(pid_segment[5]))
    
    # PID-7: Date of Birth
    if len(pid_segment) > 7 and pid_segment[7]:
        dob = parse_hl7_date(str(pid_segment[7]))
        if dob:
            patient["birthDate"] = dob
    
    # PID-8: Administrative Sex
    if len(pid_segment) > 8 and pid_segment[8]:
        gender_map = {
            "M": "male",
            "F": "female",
            "O": "other",
            "U": "unknown"
        }
        gender_code = str(pid_segment[8]).upper()
        patient["gender"] = gender_map.get(gender_code, "unknown")
    
    return patient


def in1_to_fhir_coverage(in1_segment, patient_reference: str) -> Dict:
    """Convert HL7 IN1 segment to FHIR Coverage resource"""
    
    # Extract fields from IN1 segment
    # IN1-2: Insurance Plan ID (Member ID)
    # IN1-3: Insurance Company ID
    # IN1-4: Insurance Company Name
    # IN1-8: Group Number
    # IN1-9: Group Name (Plan)
    
    coverage = {
        "resourceType": "Coverage",
        "status": "active",
        "beneficiary": {
            "reference": patient_reference
        },
        "payor": []
    }
    
    # IN1-2: Member ID
    if len(in1_segment) > 2 and in1_segment[2]:
        member_id = str(in1_segment[2]).split('^')[0]
        coverage["subscriberId"] = member_id
    
    # IN1-4: Insurance Company Name
    if len(in1_segment) > 4 and in1_segment[4]:
        insurance_name = str(in1_segment[4])
        coverage["payor"].append({
            "display": insurance_name
        })
    
    # IN1-8: Group Number
    if len(in1_segment) > 8 and in1_segment[8]:
        group_number = str(in1_segment[8]).strip()
        if group_number:  # Only add if not empty
            if "class" not in coverage:
                coverage["class"] = []
            coverage["class"].append({
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                        "code": "group",
                        "display": "Group"
                    }]
                },
                "value": group_number
            })
    
    # IN1-9: Group Name / Plan
    if len(in1_segment) > 9 and in1_segment[9]:
        plan_name = str(in1_segment[9]).strip()
        if plan_name:  # Only add if not empty
            if "class" not in coverage:
                coverage["class"] = []
            coverage["class"].append({
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                        "code": "plan",
                        "display": "Plan"
                    }]
                },
                "value": plan_name,
                "name": plan_name
            })
    
    return coverage


def convert_hl7_to_fhir(hl7_message: str) -> Dict[str, any]:
    """
    Convert HL7 ADT message to FHIR resources
    
    Returns:
        Dictionary with 'patient' and optionally 'coverage' FHIR resources
    """
    message = parse_hl7_message(hl7_message)
    
    result = {
        "patient": None,
        "coverage": None
    }
    
    # Find PID segment
    pid_segment = None
    in1_segment = None
    
    for segment in message:
        segment_type = str(segment[0])
        
        if segment_type == "PID":
            pid_segment = segment
        elif segment_type == "IN1":
            in1_segment = segment
    
    # Convert PID to Patient
    if pid_segment:
        result["patient"] = pid_to_fhir_patient(pid_segment)
        
        # Convert IN1 to Coverage if present
        if in1_segment:
            # We need a patient reference - use temporary ID
            patient_id = result["patient"]["identifier"][0]["value"] if result["patient"]["identifier"] else "temp"
            result["coverage"] = in1_to_fhir_coverage(in1_segment, f"Patient/{patient_id}")
    
    return result