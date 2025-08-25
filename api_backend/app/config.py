# app/config.py
import os
from dotenv import load_dotenv, find_dotenv

# Trouve et charge le .env le plus proche du projet
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    # optionnel : log si aucun .env trouvé (utile en dev)
    print("Aucun .env trouvé par find_dotenv(), vérifie l'emplacement du fichier .env")

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))

# vérifications explicites (raise aide si mal configuré)
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL must be defined in environment variables.")
if JWT_SECRET is None:
    raise RuntimeError("JWT_SECRET must be defined in environment variables.")
if JWT_ALGORITHM is None:
    raise RuntimeError("JWT_ALGORITHM must be defined in environment variables.")

# Debug temporaire (EN DEV seulement) — affiche la longueur pour éviter d'imprimer la clé brute
print("Loaded JWT_SECRET length:", len(JWT_SECRET) if JWT_SECRET is not None else "None")
