# EMR Integration System

Complete EMR integration system with two main components:
1. **EMR Server** - Wraps Medplum FHIR API and provides HL7 integration
2. **Integration Service** - Client application that syncs patient data with EMR

## Architecture

```
┌─────────────────────┐
│ Integration Service │
│   (Port 8001)       │
└──────────┬──────────┘
           │ JSON API
           │
           ▼
┌─────────────────────┐
│    EMR Server       │
│   (Port 8000)       │
└──────────┬──────────┘
           │ HL7/FHIR
           │
           ▼
┌─────────────────────┐
│   Medplum FHIR      │
│   (Cloud)           │
└─────────────────────┘
```

## Prerequisites

- Python 3.11 or 3.12 (not 3.13 - compatibility issues)
- Medplum account and client credentials
- Git (for repository management)

## Setup Instructions

### 1. Clone/Setup Project

```powershell
cd C:\Users\akuls\emr_solution
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If you get execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Medplum Configuration
MEDPLUM_BASE_URL=https://api.medplum.com/fhir/R4
MEDPLUM_CLIENT_ID=your_client_id_here
MEDPLUM_CLIENT_SECRET=your_client_secret_here

# EMR Server URL
EMR_SERVER_URL=http://localhost:8000
```

**To get Medplum credentials:**
1. Go to https://app.medplum.com
2. Register and create a project
3. Create a ClientApplication
4. Copy the Client ID and Secret to your `.env` file

### 5. Verify Setup

```powershell
python -c "import fastapi, httpx, hl7; print('All packages installed!')"
```

## Running the Services

### Terminal 1 - EMR Server

```powershell
cd C:\Users\akuls\emr_solution
.\venv\Scripts\Activate.ps1
uvicorn emr_server.main:app --reload --port 8000
```

You should see:
```
EMR Server starting up...
FHIR Proxy endpoints available at /fhir/*
HL7 Inbound endpoint available at /hl7/inbound
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2 - Integration Service

```powershell
cd C:\Users\akuls\emr_solution
.\venv\Scripts\Activate.ps1
uvicorn integration_service.main:app --reload --port 8001
```

You should see:
```
Integration Service starting up...
Patient service available at /patient/
INFO:     Uvicorn running on http://127.0.0.1:8001
```

## Testing the System

### 1. Test EMR Server Health

```powershell
curl http://localhost:8000/health
```

Expected: `{"status":"healthy","service":"EMR Server"}`

### 2. Test Integration Service Health

```powershell
curl http://localhost:8001/health
```

Expected: `{"status":"healthy","service":"Integration Service"}`

### 3. Create a Patient via Integration Service

```powershell
$patientData = @{
    mrn = "TEST123"
    lastName = "Smith"
    firstName = "John"
    dob = "12/31/1990"
    gender = "Male"
    insurance = @{
        name = "Blue Cross"
        memberID = "BC123456"
        plan = "Gold PPO"
        groupNumber = "GRP789"
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8001/patient/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $patientData
```

Expected response:
```json
{
  "status": "patient_created",
  "message": "Patient successfully created in EMR",
  "emr_response": {
    "message": "HL7 message processed successfully",
    "summary": {
      "patient": {"action": "created", "id": "..."},
      "coverage": {"action": "created", "id": "..."}
    }
  }
}
```

### 4. Test Idempotency (Send Same Patient Again)

Run the same command again - should get:
```json
{
  "status": "patient_exists",
  "message": "Patient already exists in EMR",
  "patient_id": "...",
  "mrn": "TEST123"
}
```

### 5. Verify in EMR Server

```powershell
# Get token
$token = (curl -X POST http://localhost:8000/auth/token | ConvertFrom-Json).access_token

# Query patient
curl -H "Authorization: Bearer $token" "http://localhost:8000/fhir/Patient?identifier=TEST123"
```

## API Documentation

### EMR Server (Port 8000)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/token` | Get access token | No |
| GET | `/fhir/Patient` | Search patients | Yes |
| GET | `/fhir/Patient/{id}` | Get patient by ID | Yes |
| GET | `/fhir/Coverage` | Search coverage | Yes |
| POST | `/hl7/inbound` | Receive HL7 messages | Yes |

### Integration Service (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/patient/` | Create/update patient |
| GET | `/health` | Health check |

## Project Structure

```
emr_solution/
├── .env                          # Environment variables
├── requirements.txt              # Python dependencies
│
├── emr_server/                   # EMR Server (Deliverable 1)
│   ├── __init__.py
│   ├── main.py                   # FastAPI app
│   ├── auth.py                   # OAuth2 authentication
│   ├── fhir_proxy.py            # Read-only FHIR proxy
│   ├── hl7_converter.py         # HL7 to FHIR conversion
│   └── hl7_endpoint.py          # HL7 inbound endpoint
│
└── integration_service/          # Integration Service (Deliverable 2)
    ├── __init__.py
    ├── main.py                   # FastAPI app
    ├── patient_service.py        # Patient creation logic
    └── hl7_generator.py          # JSON to HL7 conversion
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'integration_service'"
- Make sure you're running uvicorn from the project root directory
- Check that `__init__.py` exists in both service directories

### "Failed to authenticate with Medplum"
- Verify your Medplum credentials in `.env`
- Check that MEDPLUM_CLIENT_ID and MEDPLUM_CLIENT_SECRET are correct

### "Connection refused" errors
- Ensure both services are running
- Check that ports 8000 and 8001 are not in use by other applications

### Import errors
- Activate virtual environment: `.\venv\Scripts\Activate.ps1`
- Reinstall dependencies: `pip install -r requirements.txt`

## LLM Usage Disclosure

This project was built with assistance from Claude (Anthropic) for:
- Project scaffolding and structure
- Code generation for FastAPI endpoints
- HL7 and FHIR data mapping logic
- Error handling patterns

## License

This is a technical challenge submission.