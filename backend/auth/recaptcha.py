# backend/auth/recaptcha.py
import requests, os
from dotenv import load_dotenv

load_dotenv()
RECAPTCHA_SECRET = os.getenv("GOOGLE_RECAPTCHA_SECRET") # Changed to match .env variable

def verify_recaptcha(token: str):
    if not RECAPTCHA_SECRET:
        # You can log here if needed, but per request, keeping it minimal
        return False
    try:
        r = requests.post("https://www.google.com/recaptcha/api/siteverify", data={
            "secret": RECAPTCHA_SECRET,
            "response": token
        }, timeout=5) # Added timeout for robustness
        r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return r.json().get("success", False)
    except requests.exceptions.RequestException:
        # Handle request-specific errors more gracefully if needed,
        # but for minimal logging, just return False.
        return False