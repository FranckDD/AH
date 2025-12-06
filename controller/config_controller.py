import os
import shutil
from fastapi import UploadFile
from repositories.config_repo import ConfigRepository
from models.organization_config import OrganizationConfig

# Configuration du dossier d'upload
UPLOAD_DIR = "static/uploads/logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ConfigController:
    def __init__(self, repo: ConfigRepository):
        self.repo = repo

    def get_structure_info(self) -> OrganizationConfig:
        config = self.repo.get_config()
        if not config:
            # Retourne un objet vide par défaut pour éviter les erreurs front
            return OrganizationConfig() 
        return config

    def update_structure_info(
        self, 
        data_dict: dict, 
        logo_file: UploadFile = None, # type: ignore
        base_url: str = "" # Pour construire l'URL complète
    ) -> OrganizationConfig:
        
        # 1. Gestion de l'upload du logo si présent
        if logo_file:
            # Nettoyage du nom de fichier
            filename = f"logo_{logo_file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # Sauvegarde physique
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(logo_file.file, buffer)
            
            # Mise à jour de l'URL dans les données (URL accessible via navigateur)
            # Assure-toi que FastAPI sert le dossier "static"
            # Exemple: http://localhost:8000/static/uploads/logos/mon_logo.png
            data_dict["logo_url"] = f"{base_url}/static/uploads/logos/{filename}"

        # 2. Sauvegarde en base via le repo
        return self.repo.save_config(data_dict)