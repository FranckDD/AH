import io
import os
import secrets
import shutil
import uuid
from fastapi import UploadFile
from PIL import Image
from repositories.config_repo import ConfigRepository
from models.organization_config import OrganizationConfig

UPLOAD_DIR = "static/uploads/logos"
TICKET_LOGO_UPLOAD_DIR = "static/uploads/ticket_logos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TICKET_LOGO_UPLOAD_DIR, exist_ok=True)

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

    def _save_uploaded_image(self, image_file: UploadFile, upload_dir: str) -> str:
        """Valide et sauvegarde une image uploadee, retourne son chemin
        relatif servi par /static. Factorise entre le logo couleur (factures
        PDF) et le logo monochrome (ticket thermique) - meme validation,
        seul le repertoire de destination change."""
        raw_bytes = image_file.file.read()
        if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("Le fichier depasse la taille maximale autorisee (5 Mo)")

        buffer = io.BytesIO(raw_bytes)
        _validate_image_content(buffer)

        filename = _generate_safe_filename(image_file.filename or "")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        buffer.seek(0)
        with open(file_path, "wb") as out:
            shutil.copyfileobj(buffer, out)

        return f"/{upload_dir}/{filename}"

    def update_structure_info(
        self,
        data_dict: dict,
        logo_file: UploadFile = None,  # type: ignore
        ticket_logo_file: UploadFile = None,  # type: ignore
    ) -> OrganizationConfig:
        if logo_file:
            data_dict["logo_url"] = self._save_uploaded_image(logo_file, UPLOAD_DIR)
        if ticket_logo_file:
            data_dict["ticket_logo_url"] = self._save_uploaded_image(ticket_logo_file, TICKET_LOGO_UPLOAD_DIR)
        return self.repo.save_config(data_dict)

    def get_ticket_print_token(self) -> str | None:
        config = self.get_structure_info()
        return getattr(config, "ticket_print_token", None)

    def generate_ticket_print_token(self) -> str:
        """Genere un nouveau jeton partage (32 octets urlsafe -> 43
        caracteres) requis par le service pont local pour accepter une
        demande d'impression - empeche un site tiers ouvert dans un autre
        onglet du meme navigateur d'imprimer silencieusement sur
        http://localhost:PORT."""
        token = secrets.token_urlsafe(32)
        if self.repo:
            self.repo.save_config({"ticket_print_token": token})
        return token
