# backend/utils/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
# Make sure you import decode_jwt (not decode_token)


import sys
import os

# Add root project directory to sys.path manually
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.auth.jwt_handler import decode_jwt


# The tokenUrl must match the full path where your /token endpoint is accessible
# Given your main.py includes auth_router with prefix="/auth"
# and your auth_router has @auth_router.post("/token"), the path is /auth/token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_jwt(token)
    if "error" in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=payload["error"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload