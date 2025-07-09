# backend/database.py
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "supplychain")

client = MongoClient("mongodb+srv://leelakrishnar24:V5gDHCh8umpNBNZE@cluster0.mqnmljn.mongodb.net/")
db = client[DB_NAME]

# Use environment variables for collection names
USERS_COLLECTION_NAME = os.getenv("USERS_COLLECTION", "users")
SHIPMENTS_COLLECTION_NAME = os.getenv("SHIPMENTS_COLLECTION", "shipments")
SENSOR_READINGS_COLLECTION_NAME = os.getenv("SENSOR_READINGS_COLLECTION", "sensor_readings")

users_collection = db[USERS_COLLECTION_NAME]
shipments_collection = db[SHIPMENTS_COLLECTION_NAME]
sensors_collection = db[SENSOR_READINGS_COLLECTION_NAME] # Renamed for clarity from 'sensors'

# Create indexes (good practice from your reference code)
users_collection.create_index("email", unique=True)
shipments_collection.create_index("shipment_number")
sensors_collection.create_index("timestamp") # Assuming 'timestamp' field in sensor_readings