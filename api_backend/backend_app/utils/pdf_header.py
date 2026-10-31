# api_backend/backend_app/utils/pdf_header.py
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


# Dossiers d'envoi des logos (miroir de controller/config_controller.py : UPLOAD_DIR, TICKET_LOGO_UPLOAD_DIR ; un
# test verifie l'egalite) et dossier racine servi par /static (api_backend/main.py : StaticFiles(directory="static")).
UPLOAD_DIR = "static/uploads/logos"
TICKET_LOGO_UPLOAD_DIR = "static/uploads/ticket_logos"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_DIR = Path(__file__).resolve().parents[2]
_CONTAINER_ROOT = Path("/app")


def _asset_bases() -> list:
    """Dossiers de base essayes dans l'ordre : dossier de lancement, racine du depot, api_backend/, conteneur."""
    return [Path.cwd(), _REPO_ROOT, _API_DIR, _CONTAINER_ROOT]


def resolve_local_asset_path(url: Optional[str]) -> Optional[Path]:
    """Resout un champ *_url (relatif type /static/... ou absolu legacy) en
    chemin fichier local reel. Retourne None si le champ est vide ou si le
    fichier n'existe pas sur disque - jamais d'exception, un logo manquant
    ne doit jamais faire echouer la generation d'un document.

    Le chemin ne depend plus du dossier de lancement de l'API : il est cherche dans l'ordre relativement au dossier
    courant, a la racine du depot, a api_backend/ puis a /app (conteneur) ; en dernier recours le nom du fichier
    est cherche dans les dossiers d'envoi configures (UPLOAD_DIR, TICKET_LOGO_UPLOAD_DIR) de chaque base."""
    if not url:
        return None
    try:
        relative_path = urlparse(str(url)).path
        parts = [p for p in relative_path.replace("\\", "/").split("/") if p]
        if not parts or ".." in parts:
            return None
        rel = Path(*parts)
        bases = _asset_bases()
        for base in bases:
            candidate = (base / rel)
            if candidate.is_file():
                return candidate.resolve()
        for base in bases:
            for upload_dir in (UPLOAD_DIR, TICKET_LOGO_UPLOAD_DIR):
                candidate = base / upload_dir / rel.name
                if candidate.is_file():
                    return candidate.resolve()
    except (OSError, ValueError):
        return None
    return None


_LOGO_MAX_PX = 400


def light_logo(logo_uri: Optional[str]) -> Optional[str]:
    """URI d'une version reduite du logo (largeur ou hauteur <= 400 px, cache dans le dossier temporaire).
    Un logo de plusieurs Mo rendait chaque document tres lent et le PDF enorme (le logo est copie dans chaque
    page). En cas de doute (fichier illisible, deja petit) l'URI d'origine est conservee."""
    if logo_uri and str(logo_uri).startswith("/"):
        # chemin /static/... du champ logo_url : meme resolution que get_pdf_header_context
        found = resolve_local_asset_path(logo_uri)
        logo_uri = found.as_uri() if found else logo_uri
    if not logo_uri or not str(logo_uri).startswith("file:"):
        return logo_uri
    try:
        import hashlib
        import tempfile
        from urllib.parse import unquote
        from urllib.request import url2pathname
        from PIL import Image

        src = Path(url2pathname(unquote(urlparse(logo_uri).path)))
        if not src.is_file():
            src = resolve_local_asset_path(src.name and f"/{UPLOAD_DIR}/{src.name}") or src
        stat = src.stat()
        key = hashlib.sha1(f"{src}|{stat.st_mtime_ns}|{stat.st_size}|{_LOGO_MAX_PX}".encode()).hexdigest()
        target = Path(tempfile.gettempdir()) / "ah2_pdf_logo_cache" / f"{key}.png"
        if target.exists():
            return target.as_uri()
        with Image.open(src) as img:
            if max(img.size) <= _LOGO_MAX_PX and stat.st_size < 200_000:
                return logo_uri
            img.load()
            small = img.copy()
        small.thumbnail((_LOGO_MAX_PX, _LOGO_MAX_PX), Image.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(f".{os.getpid()}.tmp")
        small.save(tmp, format="PNG", optimize=True)
        os.replace(tmp, target)
        return target.as_uri()
    except Exception:
        return logo_uri


def get_pdf_header_context(config_ctrl: Any) -> Dict[str, Any]:
    """
    Resout une seule fois les infos d'etablissement (nom, adresse, logo)
    pour tout generateur PDF de ce projet - source unique, evite la
    derive deja constatee (facture caisse ignorait completement
    OrganizationConfig avant ce chantier, nom/logo codes en dur).

    logo_url est normalement un chemin relatif servi par /static (ex.
    "/static/uploads/logos/xxx.png") - controller/config_controller.py
    l'enregistre ainsi a l'upload. Mais une valeur deja en base peut etre
    une URL absolue (ex. cree avant cette convention, ou re-soumise telle
    quelle depuis un apercu front qui l'affichait complete) - urlparse()
    extrait le chemin dans les deux cas, jamais une URL absolue ne peut
    etre passee telle quelle a WeasyPrint (illisible via base_url si elle
    commence par "/"). On resout donc ici directement le fichier local
    sur disque (meme convention que UPLOAD_DIR dans config_controller.py,
    relative au CWD du process), motif deja valide par
    controller/lab_controller.py.
    """
    structure = config_ctrl.get_structure_info()
    local_logo = resolve_local_asset_path(structure.logo_url) if structure else None
    original = local_logo.as_uri() if local_logo else None
    # Les PDF embarquent une version reduite (<= 400 px) du logo : un logo de plusieurs Mo alourdissait chaque
    # document. L'original reste disponible (logo_path_original) ; les ecrans web lisent logo_url, pas ce contexte.
    return {"structure": structure, "logo_path": light_logo(original), "logo_path_original": original}


def get_ticket_header_context(config_ctrl: Any) -> Dict[str, Any]:
    """Meme resolution que get_pdf_header_context, mais pour le logo
    monochrome dedie au ticket thermique (ticket_logo_url) - fichier
    distinct du logo couleur, deja optimise pour un rendu bitmap ESC/POS.
    ticket_logo_path est un chemin plat (pas un file:// URI comme
    logo_path) : python-escpos.printer.image() attend un chemin fichier
    normal ou une image PIL, jamais une URI."""
    structure = config_ctrl.get_structure_info()
    ticket_logo_url = getattr(structure, "ticket_logo_url", None) if structure else None
    local_logo = resolve_local_asset_path(ticket_logo_url)
    return {"structure": structure, "ticket_logo_path": str(local_logo) if local_logo else None}
