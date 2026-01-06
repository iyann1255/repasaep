import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()

MONGO_URL = os.getenv("MONGO_URL", "").strip()
MONGO_DB = os.getenv("MONGO_DB", "chatrep").strip()

if not API_ID or not API_HASH:
    raise SystemExit("API_ID / API_HASH belum diset di .env")

if not MONGO_URL:
    raise SystemExit("MONGO_URL belum diset di .env")
