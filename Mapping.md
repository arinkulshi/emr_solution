# HL7 to FHIR Mapping Documentation

This document explains how HL7 v2 segments map to FHIR R4 resources in this implementation.

## Overview

The system converts HL7 ADT^A04 messages (Patient Registration) into FHIR resources:
- **PID segment** → **FHIR Patient resource**
- **IN1 segment** → **FHIR Coverage resource**

## HL7 Message Structure

### Sample HL7 Message
```
MSH|^~\&|INTEGRATION|CLINIC|EMR|HOSPITAL|20231031120000||ADT^A04|MSG00001|P|2.5
PID|1||MRN123456^^^MRN||Smith^John^A||19801215|M
IN1|1|PPO123|BC001|BlueCross BlueShield|||||GRP456789|Gold Plan PPO
```

### HL7 Delimiters
- `|` = Field separator
- `^` = Component separator
- `~` = Repetition separator
- `\` = Escape character
- `&` = Subcomponent separator

## MSH Segment (Message Header)

**Purpose:** Message metadata and routing information

| Field | HL7 Position | Description | Example |
|-------|--------------|-------------|---------|
| Sending Application | MSH-3 | Source system | INTEGRATION |
| Sending Facility | MSH-4 | Source facility | CLINIC |
| Receiving Application | MSH-5 | Destination system | EMR |
| Receiving Facility | MSH-6 | Destination facility | HOSPITAL |
| Message Timestamp | MSH-7 | When message was created | 20231031120000 |
| Message Type | MSH-9 | ADT^A04 (Patient Registration) | ADT^A04 |
| Message Control ID | MSH-10 | Unique message ID | MSG00001 |
| Processing ID | MSH-11 | P=Production, T=Test | P |
| Version | MSH-12 | HL7 version | 2.5 |

**FHIR Mapping:** MSH is used for message validation but not directly mapped to FHIR resources.

## PID Segment → FHIR Patient Resource

**Purpose:** Patient demographic information

### Field Mappings

| HL7 Field | Position | Description | FHIR Element | Notes |
|-----------|----------|-------------|--------------|-------|
| Set ID | PID-1 | Sequence number | N/A | Not mapped |
| Patient ID | PID-2 | External ID | N/A | Deprecated in v2.5 |
| **Patient Identifier List** | **PID-3** | **MRN/Patient ID** | **Patient.identifier** | **Primary identifier** |
| Alternate Patient ID | PID-4 | Alternate ID | N/A | Not mapped |
| **Patient Name** | **PID-5** | **Name** | **Patient.name** | **Last^First^Middle** |
| Mother's Maiden Name | PID-6 | Mother's name | N/A | Not mapped |
| **Date of Birth** | **PID-7** | **Birth date** | **Patient.birthDate** | **YYYYMMDD format** |
| **Administrative Sex** | **PID-8** | **Gender** | **Patient.gender** | **M/F/O/U** |

### Detailed Mappings

#### PID-3: Patient Identifier → Patient.identifier

**HL7 Format:** `MRN123456^^^MRN`

**FHIR Mapping:**
```json
{
  "identifier": [{
    "use": "usual",
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
        "code": "MR",
        "display": "Medical Record Number"
      }]
    },
    "value": "MRN123456"
  }]
}
```

**Transformation:**
1. Extract ID from first component (before first `^`)
2. Assign identifier type as "MR" (Medical Record Number)
3. Set use as "usual"

#### PID-5: Patient Name → Patient.name

**HL7 Format:** `Smith^John^A` (Last^First^Middle)

**FHIR Mapping:**
```json
{
  "name": [{
    "use": "official",
    "family": "Smith",
    "given": ["John", "A"]
  }]
}
```

**Transformation:**
1. Split by `^` delimiter
2. First component → family name
3. Second component → first given name
4. Third component → second given name (middle)

#### PID-7: Date of Birth → Patient.birthDate

**HL7 Format:** `19801215` (YYYYMMDD)

**FHIR Mapping:**
```json
{
  "birthDate": "1980-12-15"
}
```

**Transformation:**
1. Extract year (positions 0-4): "1980"
2. Extract month (positions 4-6): "12"
3. Extract day (positions 6-8): "15"
4. Format as YYYY-MM-DD

#### PID-8: Administrative Sex → Patient.gender

**HL7 Format:** Single character code

| HL7 Code | FHIR Value |
|----------|------------|
| M | male |
| F | female |
| O | other |
| U | unknown |

**FHIR Mapping:**
```json
{
  "gender": "male"
}
```

### Complete Patient Example

**HL7:**
```
PID|1||MRN123456^^^MRN||Smith^John^A||19801215|M
```

**FHIR:**
```json
{
  "resourceType": "Patient",
  "identifier": [{
    "use": "usual",
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
        "code": "MR",
        "display": "Medical Record Number"
      }]
    },
    "value": "MRN123456"
  }],
  "name": [{
    "use": "official",
    "family": "Smith",
    "given": ["John", "A"]
  }],
  "gender": "male",
  "birthDate": "1980-12-15"
}
```

## IN1 Segment → FHIR Coverage Resource

**Purpose:** Insurance/coverage information

### Field Mappings

| HL7 Field | Position | Description | FHIR Element | Notes |
|-----------|----------|-------------|--------------|-------|
| Set ID | IN1-1 | Sequence number | N/A | Not mapped |
| **Insurance Plan ID** | **IN1-2** | **Member ID** | **Coverage.subscriberId** | **Primary member ID** |
| Insurance Company ID | IN1-3 | Company ID code | N/A | Not mapped |
| **Insurance Company Name** | **IN1-4** | **Payor name** | **Coverage.payor.display** | **Insurance company** |
| Insurance Company Address | IN1-5 | Address | N/A | Not mapped |
| Insurance Company Contact | IN1-6 | Contact person | N/A | Not mapped |
| Insurance Company Phone | IN1-7 | Phone number | N/A | Not mapped |
| **Group Number** | **IN1-8** | **Group ID** | **Coverage.class (group)** | **Group identifier** |
| **Group Name** | **IN1-9** | **Plan name** | **Coverage.class (plan)** | **Plan name** |

### Detailed Mappings

#### IN1-2: Insurance Plan ID → Coverage.subscriberId

**HL7 Format:** `PPO123`

**FHIR Mapping:**
```json
{
  "subscriberId": "PPO123"
}
```

#### IN1-4: Insurance Company Name → Coverage.payor

**HL7 Format:** `BlueCross BlueShield`

**FHIR Mapping:**
```json
{
  "payor": [{
    "display": "BlueCross BlueShield"
  }]
}
```

#### IN1-8: Group Number → Coverage.class (group)

**HL7 Format:** `GRP456789`

**FHIR Mapping:**
```json
{
  "class": [{
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
        "code": "group",
        "display": "Group"
      }]
    },
    "value": "GRP456789"
  }]
}
```

#### IN1-9: Group Name/Plan → Coverage.class (plan)

**HL7 Format:** `Gold Plan PPO`

**FHIR Mapping:**
```json
{
  "class": [{
    "type": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
        "code": "plan",
        "display": "Plan"
      }]
    },
    "value": "Gold Plan PPO",
    "name": "Gold Plan PPO"
  }]
}
```

### Complete Coverage Example

**HL7:**
```
IN1|1|PPO123|BC001|BlueCross BlueShield|||||GRP456789|Gold Plan PPO
```

**FHIR:**
```json
{
  "resourceType": "Coverage",
  "status": "active",
  "subscriberId": "PPO123",
  "beneficiary": {
    "reference": "Patient/MRN123456"
  },
  "payor": [{
    "display": "BlueCross BlueShield"
  }],
  "class": [
    {
      "type": {
        "coding": [{
          "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
          "code": "group",
          "display": "Group"
        }]
      },
      "value": "GRP456789"
    },
    {
      "type": {
        "coding": [{
          "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
          "code": "plan",
          "display": "Plan"
        }]
      },
      "value": "Gold Plan PPO",
      "name": "Gold Plan PPO"
    }
  ]
}
```

## Reverse Mapping: JSON → HL7

The integration service accepts simplified JSON and converts it to HL7:

### Input JSON Format
```json
{
  "mrn": "MRN123456",
  "lastName": "Smith",
  "firstName": "John",
  "dob": "12/31/1990",
  "gender": "Male",
  "insurance": {
    "name": "BlueCross BlueShield",
    "memberID": "PPO123",
    "plan": "Gold Plan PPO",
    "groupNumber": "GRP456789"
  }
}
```

### Transformation Rules

| JSON Field | HL7 Segment | HL7 Field | Transformation |
|------------|-------------|-----------|----------------|
| mrn | PID | PID-3 | Add `^^^MRN` suffix |
| lastName | PID | PID-5.1 | First component of name |
| firstName | PID | PID-5.2 | Second component of name |
| dob | PID | PID-7 | MM/DD/YYYY → YYYYMMDD |
| gender | PID | PID-8 | "Male"→"M", "Female"→"F" |
| insurance.memberID | IN1 | IN1-2 | Direct mapping |
| insurance.name | IN1 | IN1-4 | Direct mapping |
| insurance.groupNumber | IN1 | IN1-8 | Direct mapping |
| insurance.plan | IN1 | IN1-9 | Direct mapping |

### Generated HL7 Output
```
MSH|^~\&|INTEGRATION|CLINIC|EMR|HOSPITAL|20231031120000||ADT^A04|MSG00001|P|2.5
PID|1||MRN123456^^^MRN||Smith^John||19901231|M
IN1|1|PPO123||BlueCross BlueShield|||||GRP456789|Gold Plan PPO
```

## Error Handling

### Missing Required Fields

| Missing Field | Behavior |
|--------------|----------|
| PID segment | Reject message - "No patient information found" |
| PID-5 (Name) | Create patient with empty name array |
| PID-7 (DOB) | Set birthDate to null |
| PID-8 (Gender) | Default to "unknown" |
| IN1 segment | Skip coverage creation (optional) |

### Invalid Data

| Invalid Data | Behavior |
|-------------|----------|
| Invalid date format | Return 400 error with details |
| Invalid gender code | Map to "unknown" |
| Empty string values | Skip field or use empty string |
| Special characters | Escape according to HL7 rules |

## Standards Compliance

- **HL7 v2.5** specification for message structure
- **FHIR R4** for resource definitions
- **ISO 8601** date format for FHIR (YYYY-MM-DD)
- **HL7 v2** date format (YYYYMMDD)

## References

- HL7 v2.5 Specification: http://www.hl7.org/implement/standards/product_brief.cfm?product_id=144
- FHIR R4 Patient: https://www.hl7.org/fhir/patient.html
- FHIR R4 Coverage: https://www.hl7.org/fhir/coverage.html
- HL7 v2 to FHIR Mapping: https://build.fhir.org/ig/HL7/v2-to-fhir/