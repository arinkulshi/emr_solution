from datetime import datetime
from typing import Optional


def format_date_for_hl7(date_str: str) -> str:
    """
    Convert MM/DD/YYYY to YYYYMMDD for HL7
    
    Args:
        date_str: Date in MM/DD/YYYY format
        
    Returns:
        Date in YYYYMMDD format
    """
    parts = date_str.split('/')
    if len(parts) != 3:
        raise ValueError(f"Invalid date format. Expected MM/DD/YYYY, got {date_str}")
    
    month, day, year = parts
    return f"{year}{month.zfill(2)}{day.zfill(2)}"


def generate_hl7_adt_message(
    mrn: Optional[str],
    last_name: str,
    first_name: str,
    dob: str,  # MM/DD/YYYY format
    gender: str,  # "Male" or "Female"
    insurance_name: Optional[str] = None,
    member_id: Optional[str] = None,
    plan: Optional[str] = None,
    group_number: Optional[str] = None
) -> str:
    """
    Generate HL7 ADT^A04 message from patient data
    
    HL7 Delimiters: | ^ ~ \\ &
    - | = field separator
    - ^ = component separator
    - ~ = repetition separator
    - \\ = escape character
    - & = subcomponent separator
    
    Args:
        mrn: Medical Record Number (optional, will be auto-generated if not provided)
        last_name: Patient's last name
        first_name: Patient's first name
        dob: Date of birth in MM/DD/YYYY format
        gender: Patient gender ("Male" or "Female")
        insurance_name: Insurance company name (optional)
        member_id: Insurance member ID (optional)
        plan: Insurance plan name (optional)
        group_number: Insurance group number (optional)
        
    Returns:
        HL7 message string with segments separated by CR (\\r)
    """
    # Generate message timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Generate MRN if not provided
    if not mrn:
        mrn = f"MRN{timestamp}"
    
    # Generate unique message ID
    msg_id = f"MSG{timestamp}"
    
    # MSH - Message Header segment
    msh = f"MSH|^~\\&|INTEGRATION|CLINIC|EMR|HOSPITAL|{timestamp}||ADT^A04|{msg_id}|P|2.5"
    
    # PID - Patient Identification segment
    # Convert date format
    hl7_dob = format_date_for_hl7(dob)
    
    # Convert gender
    hl7_gender = "M" if gender.upper() in ["MALE", "M"] else "F"
    
    # PID format: PID|SetID|PatientID|PatientIdentifierList|AlternatePatientID|PatientName|...
    pid = f"PID|1||{mrn}^^^MRN||{last_name}^{first_name}||{hl7_dob}|{hl7_gender}"
    
    # Start with required segments
    segments = [msh, pid]
    
    # IN1 - Insurance segment (optional)
    if insurance_name and member_id:
        # IN1 format: IN1|SetID|InsurancePlanID|InsuranceCompanyID|InsuranceCompanyName|...
        in1_parts = [
            "IN1",
            "1",  # Set ID
            member_id or "",  # Insurance Plan ID
            "",  # Insurance Company ID (empty)
            insurance_name or "",  # Insurance Company Name
            "",  # Insurance Company Address
            "",  # Insurance Company Contact Person
            "",  # Insurance Company Phone Number
            "",  # Group Number field (IN1-8)
        ]
        
        # Add group number at position 8 if provided
        if group_number:
            in1_parts.append(group_number)
        else:
            in1_parts.append("")
        
        # Add plan at position 9 if provided
        if plan:
            in1_parts.append(plan)
        
        in1 = "|".join(in1_parts)
        segments.append(in1)
    
    # Join segments with CR (carriage return) - HL7 standard
    return "\r".join(segments)


def parse_hl7_message_info(hl7_message: str) -> dict:
    """
    Parse basic info from HL7 message for debugging
    
    Args:
        hl7_message: HL7 message string
        
    Returns:
        Dictionary with parsed message info
    """
    segments = hl7_message.split('\r')
    
    info = {
        "segment_count": len(segments),
        "segments": []
    }
    
    for segment in segments:
        if segment:
            segment_type = segment[:3]
            info["segments"].append(segment_type)
    
    return info