# api_backend/backend_app/utils/pdf_header.py
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def resolve_local_asset_path(url: Optional[str]) -> Optional[Path]:
    """Resout un champ *_url (relatif type /static/... ou absolu legacy) en
    chemin fichier local reel. Retourne None si le champ est vide ou si le
    fichier n'existe pas sur disque - jamais d'exception, un logo manquant
    ne doit jamais faire echouer la generation d'un document."""
    if not url:
        return None
    relative_path = urlparse(url).path
    local_path = Path(relative_path.lstrip("/")).resolve()
    return local_path if local_path.is_file() else None


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
    return {"structure": structure, "logo_path": local_logo.as_uri() if local_logo else None}


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
