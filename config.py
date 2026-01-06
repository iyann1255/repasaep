import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()

if not API_ID or not API_HASH:
    raise SystemExit("API_ID / API_HASH belum diset di .env")
