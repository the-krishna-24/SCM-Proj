# backend/auth/jwt_handler.py
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
SECRET = os.getenv("SECRET_KEY", "Vs3CetW9L1zSBVe1U9tXjWNSF-NWsrOjrN__Um27v-E")
ALG = os.getenv("ALGORITHM", "HS256")

# Renamed to sign_jwt and modified to accept role and name
def sign_jwt(email: str, role: str, name: str) -> dict:
    payload = {
        "sub": email,
        "role": role,
        "name": name,
        "exp": datetime.utcnow() + timedelta(minutes=30) # Token expires in 30 minutes
    }
    encoded_jwt = jwt.encode(payload, SECRET, algorithm=ALG)
    return {"access_token": encoded_jwt}

# Renamed to decode_jwt and handles errors more gracefully  
def decode_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, SECRET, algorithms=[ALG])
        # Check if token is expired
        if decoded_token.get("exp") and datetime.fromtimestamp(decoded_token["exp"]) < datetime.utcnow():
            return {"error": "Token has expired"}
        return decoded_token
    except JWTError:
        return {"error": "Invalid token"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}