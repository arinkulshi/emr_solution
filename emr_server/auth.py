import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import httpx
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

# Medplum configuration
MEDPLUM_BASE_URL = os.getenv("MEDPLUM_BASE_URL", "https://api.medplum.com")
MEDPLUM_CLIENT_ID = os.getenv("MEDPLUM_CLIENT_ID")
MEDPLUM_CLIENT_SECRET = os.getenv("MEDPLUM_CLIENT_SECRET")

# In-memory token store for our server's OAuth2
token_store = {}

security = HTTPBearer()


class MedplumAuth:
    """Handles authentication with Medplum FHIR server"""
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
    
    async def get_access_token(self) -> str:
        """Get valid access token for Medplum, refresh if needed"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        # Request new token from Medplum using Basic Auth
        import base64
        credentials = f"{MEDPLUM_CLIENT_ID}:{MEDPLUM_CLIENT_SECRET}"
        basic_auth = base64.b64encode(credentials.encode()).decode()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.medplum.com/oauth2/token",
                headers={
                    "Authorization": f"Basic {basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data="grant_type=client_credentials"
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to authenticate with Medplum: {response.text}"
                )
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            # Set expiry with 5 minute buffer
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
            
            return self.access_token


# Global Medplum auth instance
medplum_auth = MedplumAuth()


def create_access_token() -> str:
    """Create a new access token for clients accessing our server"""
    token = secrets.token_urlsafe(32)
    token_store[token] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }
    return token


def validate_token(token: str) -> bool:
    """Validate if token exists and is not expired"""
    if token not in token_store:
        return False
    
    token_data = token_store[token]
    if datetime.now() > token_data["expires_at"]:
        del token_store[token]
        return False
    
    return True


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """FastAPI dependency to verify bearer token"""
    token = credentials.credentials
    
    if not validate_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


async def get_medplum_token() -> str:
    """Dependency to get valid Medplum access token"""
    return await medplum_auth.get_access_token()