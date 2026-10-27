# api_backend/backend_app/utils/product_photos.py
"""Photos des produits de la pharmacie : fichiers sur disque, hors /static, jamais publics.

Servies uniquement par GET /pharmacy/{id}/photo (authentifie). Dossier configurable
(futur volume Docker) via PRODUCT_PHOTO_DIR.
"""
import io
import os
import re
import threading
import uuid
import warnings
from typing import Optional

from PIL import Image, ImageFile, ImageOps

DEFAULT_PHOTO_DIR = os.path.join("storage", "product_photos")
PHOTO_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
PHOTO_MAX_SIDE = 480
PHOTO_MAX_BYTES = 100 * 1024
PHOTO_MAX_PIXELS = 40_000_000
_DECODE_LOCK = threading.Lock()  # etat global de Pillow/warnings + borne la memoire de decodage
PHOTO_ID_RE = re.compile(r"^[0-9a-f]{32}\.jpg$")


class PhotoError(ValueError):
    """Photo refusee ; .status_code vaut 400 (contenu) ou 413 (taille)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def photo_dir() -> str:
    return os.getenv("PRODUCT_PHOTO_DIR") or DEFAULT_PHOTO_DIR


def photo_file_path(photo_id: Optional[str]) -> Optional[str]:
    """Chemin disque d'un identifiant de photo, ou None si l'identifiant n'est pas conforme."""
    if not photo_id or not PHOTO_ID_RE.match(str(photo_id)):
        return None
    return os.path.join(photo_dir(), str(photo_id))


def shrink_to_jpeg(raw: bytes) -> bytes:
    """Image quelconque -> JPEG dont le plus grand cote vaut au plus 480 px et le poids au plus 100 Ko."""
    if len(raw) > PHOTO_MAX_UPLOAD_BYTES:
        raise PhotoError("Image too large (5 MB maximum).", 413)
    with _DECODE_LOCK:
        # Une autre bibliotheque de l'appli active LOAD_TRUNCATED_IMAGES (global) : on exige une image complete.
        previous_truncated = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                img = Image.open(io.BytesIO(raw))
                width, height = img.size  # lu dans l'en-tete, avant tout decodage
                if width * height > PHOTO_MAX_PIXELS:
                    raise PhotoError("Image dimensions are too large.", 400)
                img.seek(0)  # formats animes : premiere image seulement
                img.load()
                img = ImageOps.exif_transpose(img)
        except PhotoError:
            raise
        except Exception:  # dont DecompressionBombError/Warning
            raise PhotoError("The file is not a valid image.", 400)
        finally:
            ImageFile.LOAD_TRUNCATED_IMAGES = previous_truncated
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    else:
        img = img.convert("RGB")
    img.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE), Image.LANCZOS)
    while True:
        for quality in (85, 75, 65, 55, 45, 35, 25):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if buf.tell() <= PHOTO_MAX_BYTES:
                return buf.getvalue()
        # Tres rare (image tres detaillee) : on reduit encore les dimensions.
        w, h = img.size
        if max(w, h) <= 64:
            raise PhotoError("Image cannot be reduced enough.", 400)
        img = img.resize((max(1, int(w * 0.8)), max(1, int(h * 0.8))), Image.LANCZOS)


def write_photo(jpeg_bytes: bytes) -> str:
    """Ecrit le fichier sous un nom uuid et retourne l'identifiant stocke en base."""
    os.makedirs(photo_dir(), exist_ok=True)
    photo_id = f"{uuid.uuid4().hex}.jpg"
    with open(os.path.join(photo_dir(), photo_id), "wb") as out:
        out.write(jpeg_bytes)
    return photo_id


def remove_photo(photo_id: Optional[str]) -> None:
    path = photo_file_path(photo_id)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
