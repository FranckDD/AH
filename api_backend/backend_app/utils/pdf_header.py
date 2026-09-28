# api_backend/backend_app/utils/pdf_header.py
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse


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

    logo_path = None
    if structure and structure.logo_url:
        relative_path = urlparse(structure.logo_url).path
        local_logo = Path(relative_path.lstrip("/")).resolve()
        if local_logo.is_file():
            logo_path = local_logo.as_uri()

    return {"structure": structure, "logo_path": logo_path}
