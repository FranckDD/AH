# app/config.py (version finale)
import os
from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    print("Aucun .env, fallbacks pour client.")

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))
AH2_API_BASE = os.getenv('AH2_API_BASE')

IS_CLIENT = os.getenv("IS_CLIENT", "false").lower() == "true"
IS_PROD = os.getenv("IS_PROD", "false").lower() == "true"

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

DEFAULT_DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    # `npm run preview` (build de production, necessaire pour tester le
    # service worker/PWA) sert par defaut sur ce port.
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def parse_cors_origins(raw, is_prod=None):
    """Origines CORS autorisees. Vide/None -> liste de developpement.

    Sinon liste separee par des virgules (espaces et items vides ignores).
    "*" est refuse en production.
    """
    if is_prod is None:
        is_prod = IS_PROD
    if raw is None or not raw.strip():
        return list(DEFAULT_DEV_CORS_ORIGINS)
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        return list(DEFAULT_DEV_CORS_ORIGINS)
    if "*" in origins and is_prod:
        raise ValueError("CORS_ORIGINS ne doit pas contenir '*' en production.")
    return origins


print("Loaded JWT_SECRET length:", len(JWT_SECRET) if JWT_SECRET else "None")