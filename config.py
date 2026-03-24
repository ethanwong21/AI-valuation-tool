from dotenv import load_dotenv
import os

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
SEC_USER_EMAIL = os.getenv("SEC_USER_EMAIL")

if not FRED_API_KEY:
    raise ValueError("Missing FRED_API_KEY in .env")

if not SEC_USER_EMAIL:
    raise ValueError("Missing SEC_USER_EMAIL in .env")