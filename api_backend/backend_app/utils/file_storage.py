# api_backend/backend_app/utils/file_storage.py

import os
import shutil
from datetime import datetime
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

# 2. Configuration Local (Développement)
# Dossier où seront stockés les fichiers si Supabase n'est pas activé
LOCAL_UPLOAD_DIR = "static/uploads/toxico_consents"
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)


async def save_consent_file(file: UploadFile, patient_code: str) -> str:
    """
    Sauvegarde le fichier de consentement.
    - Si Supabase est configuré -> Upload Cloud et retourne l'URL publique (https://...)
    - Sinon -> Sauvegarde locale et retourne le chemin relatif (/static/...)
    """
    if not file or not file.filename:
        return ""

    # Nettoyage du nom de fichier
    # On garde l'extension (.pdf, .jpg)
    filename_str = str(file.filename) # Force string pour splitext
    extension = os.path.splitext(filename_str)[1].lower()
    
    if extension not in ['.pdf', '.jpg', '.jpeg', '.png']:
        # Fallback de sécurité si pas d'extension
        extension = ".pdf"

    # Création d'un nom unique : CODE_TIMESTAMP.ext
    timestamp = int(datetime.now().timestamp())
    safe_filename = f"{patient_code}_{timestamp}{extension}"

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

    # --- STRATÉGIE B : LOCAL (DISQUE) ---
    try:
        print(f"💾 [STORAGE] Sauvegarde locale : {safe_filename}")
        
        file_path = os.path.join(LOCAL_UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # On retourne le chemin relatif pour l'API
        # Ex: /static/uploads/toxico_consents/PAT123_17888.pdf
        # On utilise des forward slashs pour être compatible web
        return f"/static/uploads/toxico_consents/{safe_filename}"
        
    except Exception as e:
        print(f"❌ [STORAGE] Erreur fatale sauvegarde locale: {str(e)}")
        # En dev, on lève l'erreur pour comprendre
        # En prod, on pourrait retourner "" pour ne pas bloquer l'admission
        raise ValueError(f"Impossible de sauvegarder le fichier: {str(e)}")