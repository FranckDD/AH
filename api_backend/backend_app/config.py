# app/config.py (version finale)
import os
from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print("Aucun .env – Fallbacks pour client.")

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))
AH2_API_BASE = os.getenv('AH2_API_BASE')

IS_CLIENT = os.getenv("IS_CLIENT", "false").lower() == "true"

if not IS_CLIENT:
    # Backend strict
    if DATABASE_URL is None:
        raise RuntimeError("DATABASE_URL must be defined in environment variables.")
    if JWT_SECRET is None:
        raise RuntimeError("JWT_SECRET must be defined in environment variables.")
    if JWT_ALGORITHM is None:
        raise RuntimeError("JWT_ALGORITHM must be defined in environment variables.")
    if AH2_API_BASE is None:
        raise RuntimeError("AH2_API_BASE must be defined in environment variables.")
else:
    # Client fallback (no .env needed)
    AH2_API_BASE = AH2_API_BASE or "https://web-production-d587.up.railway.app"
    print(f"[CONFIG CLIENT] AH2_API_BASE : {AH2_API_BASE}")
    # JWT/DB unused in client – skip

print("Loaded JWT_SECRET length:", len(JWT_SECRET) if JWT_SECRET else "None")