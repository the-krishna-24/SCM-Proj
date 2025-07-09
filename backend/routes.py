# backend/routes.py
import os
from datetime import datetime
from typing import Optional
from functools import wraps

from fastapi import APIRouter, HTTPException, Depends, Form, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv

# Assuming these are correctly imported from your backend.database
from backend.database import users_collection, shipments_collection, sensors_collection as sensors # Corrected to 'sensors'
# Assuming these are correctly imported from your backend.auth.hash and .jwt_handler
from backend.auth.hash import hash_password, verify_password
from backend.auth.jwt_handler import sign_jwt, decode_jwt # Using sign_jwt and decode_jwt
# Assuming these are correctly imported from your backend.utils.dependencies and .auth.recaptcha
from backend.utils.dependencies import get_current_user, oauth2_scheme # get_current_user already defined
from backend.auth.recaptcha import verify_recaptcha


load_dotenv()

# --- Helper function for admin check ---
def admin_required(func):
    """Decorator to restrict access to admin users only."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = kwargs.get("current_user")
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins only"
            )
        # Ensure 'current_user' is passed to the wrapped function if it expects it
        if "current_user" not in kwargs:
             kwargs["current_user"] = current_user
        return await func(*args, **kwargs)
    return wrapper

# --- Routers ---
# These routers should define paths *relative* to the prefixes set in main.py
auth_router = APIRouter( tags=["Auth"])
shipment_router = APIRouter(tags=["Shipments"])
device_router = APIRouter( tags=["Device Data"])
# admin_router has its own dependency for get_current_user
admin_router = APIRouter( tags=["Admin Tools"], dependencies=[Depends(get_current_user)])


# --- Auth Endpoints (will be under /auth in main.py) ---
@auth_router.post("/signup")
async def signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    
):
    # Input validation
    if not all([name, email, password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All fields are required"
        )
    if "@" not in email or "." not in email.split("@")[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Check for existing email
    if users_collection.find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Determine role
    role = "admin" if email.endswith("@admin.com") else "user" # Example: assign admin role for specific emails
    user_data = {
        "name": name,
        "email": email,
        "password": hash_password(password),
        "role": role,
        "created_at": datetime.utcnow()
    }

    result = users_collection.insert_one(user_data)
    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "User created successfully"}
    )

@auth_router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    
):
    user = users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Generate token
    token = sign_jwt(user["email"], user["role"], user["name"])
    response = JSONResponse({
        "access_token": token["access_token"],
        "token_type": "bearer",
        "user": {
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    })
    # Set HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=token["access_token"],
        httponly=True,
        secure=os.getenv("ENVIRONMENT") == "production",
        samesite="lax"
    )
    return response

@auth_router.post("/token")
async def login_for_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return sign_jwt(user["email"], user["role"], user["name"])

@auth_router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

@auth_router.post("/logout") # Changed to POST as logout often changes state (removes cookie)
async def logout():
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Logged out successfully"}
    )
    response.delete_cookie("access_token")
    return response


# --- Shipment Endpoints (will be under /shipments in main.py) ---
@shipment_router.get("/all")
async def get_all_shipments(current_user: dict = Depends(get_current_user)): # Added dependency for protection
    shipments = list(shipments_collection.find({}))
    for shipment in shipments:
        shipment["_id"] = str(shipment["_id"])
        # Convert datetime to ISO format for JSON serialization
        if "created_at" in shipment and isinstance(shipment["created_at"], datetime):
            shipment["created_at"] = shipment["created_at"].isoformat()
    return {"shipments": shipments}

@shipment_router.post("/create") # Renamed from create_shipment for consistency
async def create_shipment(
    current_user: dict = Depends(get_current_user),
    shipment_number: str = Form(...),
    route_details: str = Form(...),
    device: str = Form(...),
    goods_type: str = Form(...),
    delivery_date: str = Form(...),
    batch_id: str = Form(...),
    po_number: Optional[str] = Form(None),
    ndc_number: Optional[str] = Form(None),
    serial_number: Optional[str] = Form(None),
    container_number: Optional[str] = Form(None),
    delivery_number: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    if not all([shipment_number, route_details, device, goods_type, delivery_date, batch_id]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields"
        )

    shipment_data = {
        "shipment_number": shipment_number,
        "route_details": route_details,
        "device": device,
        "goods_type": goods_type,
        "delivery_date": delivery_date,
        "batch_id": batch_id,
        "created_by": current_user["sub"], # 'sub' typically holds the email in JWT
        "created_at": datetime.utcnow(),
        "status": "pending"
    }

    # Add optional fields if provided
    optional_fields = {
        "po_number": po_number,
        "ndc_number": ndc_number,
        "serial_number": serial_number,
        "container_number": container_number,
        "delivery_number": delivery_number,
        "description": description
    }
    for field, value in optional_fields.items():
        if value is not None:
            shipment_data[field] = value

    result = shipments_collection.insert_one(shipment_data)
    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shipment"
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Shipment created successfully"}
    )

@shipment_router.get("/{shipment_id}")
async def get_shipment_by_id(
    shipment_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        obj_id = ObjectId(shipment_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shipment ID format"
        )

    # Fetch shipment, ensuring it belongs to the current user (or if user is admin)
    query = {"_id": obj_id}
    if current_user.get("role") != "admin": # Admins can see all, users only their own
        query["created_by"] = current_user["sub"]

    shipment = shipments_collection.find_one(query)

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found"
        )

    shipment["_id"] = str(shipment["_id"])
    if "created_at" in shipment and isinstance(shipment["created_at"], datetime):
        shipment["created_at"] = shipment["created_at"].isoformat()

    return shipment

@shipment_router.get("/search") # Renamed from search_shipments for consistency
async def search_shipments(current_user: dict = Depends(get_current_user)):
    # This endpoint currently just lists shipments created by the current user
    # If you want actual search, you'd need to add query parameters (e.g., shipment_number, status)
    shipments = list(shipments_collection.find(
        {"created_by": current_user["sub"]},
        {"_id": 1, "shipment_number": 1, "route_details": 1, "status": 1, "created_at": 1}
    ))

    for s in shipments:
        s["_id"] = str(s["_id"])
        if isinstance(s.get("created_at"), datetime):
            s["created_at"] = s["created_at"].isoformat()

    return {"shipments": shipments}

# --- Device Data Endpoints (Admin Only, will be under /device in main.py) ---
@device_router.get("/data")
@admin_required # Applying the decorator for admin-only access
async def get_device_data(
    current_user: dict = Depends(get_current_user), # Dependency still needed to get user role
    limit: int = 20
):
    data = list(sensors.find() # Corrected to use 'sensors' collection
                             .sort("timestamp", -1) # Assuming 'timestamp' field
                             .limit(limit))

    for item in data:
        item["_id"] = str(item["_id"])
        if "timestamp" in item and isinstance(item["timestamp"], datetime):
            item["timestamp"] = item["timestamp"].isoformat()

    return {"data": data}


# --- Admin Endpoints (will be under /admin in main.py) ---
# Admin router has get_current_user dependency at router level
@admin_router.get("/tools")
@admin_required # Applying the decorator for admin-only access
async def admin_tools(current_user: dict = Depends(get_current_user)):
    # The decorator handles the role check
    return {"message": "Admin tools available"}

@admin_router.get("/users")
@admin_required
async def get_users(
    current_user: dict = Depends(get_current_user),
    email: Optional[str] = None
):
    query = {}
    if email:
        query["email"] = {"$regex": email, "$options": "i"} # Case-insensitive search

    users = list(users_collection.find(query, {"password": 0})) # Exclude password from results
    for user in users:
        user["_id"] = str(user["_id"])
        if "created_at" in user and isinstance(user["created_at"], datetime):
            user["created_at"] = user["created_at"].isoformat()

    return {"users": users}

@admin_router.post("/users/{email}/role")
@admin_required
async def change_user_role(
    email: str,
    role_data: dict, # Expects {"role": "admin" or "user"}
    current_user: dict = Depends(get_current_user)
):
    new_role = role_data.get("role")
    if new_role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified. Must be 'admin' or 'user'."
        )

    result = users_collection.update_one(
        {"email": email},
        {"$set": {"role": new_role}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or role already set to this value."
        )

    return {"message": "User role updated successfully"}

@admin_router.delete("/users/{email}")
@admin_required
async def delete_user(
    email: str,
    current_user: dict = Depends(get_current_user)
):
    result = users_collection.delete_one({"email": email})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "User deleted successfully"}