from pydantic import BaseModel, EmailStr, Field




# ---------- User Schemas ----------

class UserSchema(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str

class SignupSchema(BaseModel):
    user: UserSchema


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


# ---------- Shipment Schemas ----------

class ShipmentSchema(BaseModel):
    shipment_number: str
    route_details: str
    device: str
    po_number: str
    goods_type: str
    status: str = "pending"


# ---------- Device Schemas ----------

class DeviceSchema(BaseModel):
    Battery_Level: float
    Device_ID: int
    First_Sensor_temperature: float
    Route_From: str
    Route_To: str