# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv # Import load_dotenv
import os

# Import the APIRouter instances from your updated routes.py
from backend.routes import auth_router, shipment_router, device_router, admin_router

load_dotenv() # Load environment variables early

app = FastAPI(
    title="SCM Xpert Lite API",
    description="API for Supply Chain Management Xpert Lite application.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust this for production to specific origins
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True # Needed for setting cookies
)

# Include the routers with prefixes
app.include_router(auth_router, prefix="/auth")
app.include_router(shipment_router, prefix="/shipments")
app.include_router(device_router, prefix="/device")
app.include_router(admin_router, prefix="/admin")


# Mount static files for the frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def root():
    # Redirect to the login page of the frontend
    return RedirectResponse("/frontend/login.html")



from backend.database import users_collection
from fastapi import HTTPException, status
from datetime import datetime

@app.get("/users")
async def get_all_public_users_data():
    """
    WARNING: This endpoint exposes all user data (excluding passwords)
    without any authentication or authorization.
    DO NOT USE IN PRODUCTION. This is for testing data retrieval without dependencies.
    """
    try:
        # Fetch all users, excluding the sensitive password field
        users = list(users_collection.find({}, {"password": 0}))

        for user in users:
            user["_id"] = str(user["_id"]) # Convert ObjectId to string
            if "created_at" in user and isinstance(user["created_at"], datetime):
                user["created_at"] = user["created_at"].isoformat() # Convert datetime to ISO format

        return {"users": users}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve public user data: {str(e)}"
        )