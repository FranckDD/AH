# api_backend/backend_app/utils/file_storage.py

import os
import re
import shutil
import uuid
from typing import Optional, Union, Dict
from fastapi import UploadFile


create_client = None 
Client = None # type: ignore 
HAS_SUPABASE = False
# Tentative d'import de Supabase (si installé)
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = None # type: ignore

# --- CONFIGURATION ---

# 1. Configuration Supabase (Production)
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET_NAME", "toxico-consents")

# Initialisation du client Supabase
supabase: Optional[Client] = None # type: ignore

if HAS_SUPABASE and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ [STORAGE] Client Supabase initialisé.")
    except Exception as e:
        print(f"⚠️ [STORAGE] Erreur init Supabase: {e}")

# 2. Configuration Local
# Les consentements sont des donnees medicales : ils vivent HORS du montage /static (public, sans login)
# et ne sont servis que par GET /toxico/dossiers/{id}/consent. Dossier configurable (futur volume Docker).
DEFAULT_CONSENT_STORAGE_DIR = os.path.join("storage", "toxico_consents")
CONSENT_MAX_BYTES = 5 * 1024 * 1024
LEGACY_CONSENT_DIR = "static/uploads/toxico_consents"
LEGACY_CONSENT_URL_PREFIX = "/static/uploads/toxico_consents/"
# Identifiant stocke en base : 32 hex aleatoires + extension. Rien d'autre n'est jamais servi localement.
CONSENT_ID_RE = re.compile(r"^[0-9a-f]{32}\.(pdf|jpg|png)$")


def consent_storage_dir() -> str:
    return os.getenv("CONSENT_STORAGE_DIR") or DEFAULT_CONSENT_STORAGE_DIR


def consent_path(file_id: str) -> Optional[str]:
    """Chemin disque d'un identifiant de consentement, ou None si l'identifiant n'est pas conforme."""
    if not file_id or not CONSENT_ID_RE.match(str(file_id)):
        return None
    return os.path.join(consent_storage_dir(), str(file_id))


def detect_consent_extension(head: bytes) -> Optional[str]:
    """Type reel d'apres les premiers octets (le nom envoye par le client n'est pas fiable)."""
    if head.startswith(b"%PDF-"):
        return ".pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    return None


def new_consent_id(extension: str) -> str:
    return f"{uuid.uuid4().hex}{extension}"


async def save_consent_file(file: UploadFile, patient_code: str = '') -> str:
    """
    Sauvegarde le fichier de consentement.
    - Si Supabase est configuré -> Upload Cloud et retourne l'URL publique (https://...)
    - Sinon -> Sauvegarde locale hors /static et retourne l'identifiant (uuid.ext)
    """
    if not file or not file.filename:
        return ""

    # Type reel d'apres le contenu (l'extension du nom client n'est pas fiable)
    head = await file.read(16)
    await file.seek(0)
    extension = detect_consent_extension(head)
    if not extension:
        raise ValueError("Type de fichier non autorise (PDF, JPEG ou PNG attendu)")
    safe_filename = new_consent_id(extension)

    # --- STRATÉGIE A : SUPABASE (CLOUD) ---
    if supabase:
        try:
            print(f"☁️ [STORAGE] Upload vers Supabase : {safe_filename}")
            
            # Lecture du fichier en mémoire
            file_content = await file.read()
            
            # Upload
            # 'upsert=True' écrase si le nom existe déjà (peu probable avec le timestamp)
            # file_options attend un dict ou None, pas de typage strict ici pour la lib
            res = supabase.storage.from_(SUPABASE_BUCKET).upload(
                path=safe_filename,
                file=file_content,
                file_options={"content-type": file.content_type, "upsert": "true"} # type: ignore
            )
            
            # Récupération de l'URL Publique
            public_url_response = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(safe_filename)
            
            # Selon la version de la lib, get_public_url retourne soit un str soit un dict
            # On s'assure d'avoir la string
            final_url = ""
            if isinstance(public_url_response, str):
                final_url = public_url_response
            elif isinstance(public_url_response, dict):
                 final_url = public_url_response.get('publicUrl', "")
            # Pour les objets Pydantic ou autres retours de la lib
            elif hasattr(public_url_response, 'publicUrl'): 
                 final_url = getattr(public_url_response, 'publicUrl')
            else:
                 final_url = str(public_url_response) # Fallback
            
            return final_url

        except Exception as e:
            print(f"❌ [STORAGE] Erreur Supabase: {str(e)}")
            print("⚠️ [STORAGE] Bascule vers le stockage local de secours.")
            # Si Supabase échoue, on continue vers le code local ci-dessous (Fallback)
            # On doit remettre le curseur de lecture du fichier à 0 car on l'a lu ci-dessus
            await file.seek(0)

    # --- STRATÉGIE B : LOCAL (DISQUE, hors /static) ---
    try:
        target_dir = consent_storage_dir()
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, safe_filename), "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # On stocke seulement l'identifiant ; l'API construit l'URL authentifiee a la lecture.
        return safe_filename
    except Exception as e:
        raise ValueError(f"Impossible de sauvegarder le fichier: {str(e)}")
