from fastapi import FastAPI
from fastapi.responses import JSONResponse
from emr_server.fhir_proxy import router as fhir_router
from emr_server.hl7_endpoint import router as hl7_router  # ADD THIS
from emr_server.auth import create_access_token

app = FastAPI(title="EMR Server")

# Include routers
app.include_router(fhir_router)
app.include_router(hl7_router)  # ADD THIS

@app.get("/")
async def root():
    return {"message": "EMR Server is running"}

@app.post("/auth/token")
async def get_token():
    """Issue a new access token for clients"""
    token = create_access_token()
    return {"access_token": token, "token_type": "bearer"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}