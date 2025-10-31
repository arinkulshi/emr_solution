from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from integration_service.patient_service import router as patient_router

# Create FastAPI application
app = FastAPI(
    title="Integration Service",
    description="Integration service that syncs patient data with EMR Server",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc)
        }
    )


# Include routers
app.include_router(patient_router)


# Root endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Integration Service is running",
        "version": "1.0.0",
        "endpoints": {
            "patient": "/patient/",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Integration Service"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("Integration Service starting up...")
    print("Patient service available at /patient/")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("Integration Service shutting down...")