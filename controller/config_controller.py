import io
import os
import shutil
import uuid
from fastapi import UploadFile
from PIL import Image
from repositories.config_repo import ConfigRepository
from models.organization_config import OrganizationConfig

UPLOAD_DIR = "static/uploads/logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 Mo


def _generate_safe_filename(original_filename: str) -> str:
    """Genere un nom de fichier aleatoire a partir d'une extension validee.
    Le nom fourni par le client n'est jamais reutilise tel quel (SEC-03)."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension de fichier non autorisee : {ext or '(aucune)'}")
    return f"{uuid.uuid4().hex}.{ext}"


def _validate_image_content(file_obj) -> None:
    """Verifie que le contenu est reellement une image, pas seulement l'extension."""
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        position = None
    try:
        Image.open(file_obj).verify()
    except Exception as e:
        raise ValueError(f"Le fichier envoye n'est pas une image valide : {e}")
    finally:
        if position is not None:
            file_obj.seek(position)


class ConfigController:
    def __init__(self, repo: ConfigRepository):
        self.repo = repo

    def get_structure_info(self) -> OrganizationConfig:
        config = self.repo.get_config()
        if not config:
            return OrganizationConfig()
        return config

    def update_structure_info(
        self,
        data_dict: dict,
        logo_file: UploadFile = None,  # type: ignore
        base_url: str = ""
    ) -> OrganizationConfig:

        if logo_file:
            raw_bytes = logo_file.file.read()
            if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
                raise ValueError("Le fichier depasse la taille maximale autorisee (5 Mo)")

            buffer = io.BytesIO(raw_bytes)
            _validate_image_content(buffer)

            filename = _generate_safe_filename(logo_file.filename or "")
            file_path = os.path.join(UPLOAD_DIR, filename)

            buffer.seek(0)
            with open(file_path, "wb") as out:
                shutil.copyfileobj(buffer, out)

            data_dict["logo_url"] = f"{base_url}/static/uploads/logos/{filename}"

        return self.repo.save_config(data_dict)
