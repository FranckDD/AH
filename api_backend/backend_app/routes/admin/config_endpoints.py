from typing import Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from api_backend.backend_app.database import SessionLocal
from controller.config_controller import ConfigController
from repositories.config_repo import ConfigRepository
from models.organization_config import OrganizationConfig
from api_backend.backend_app.routes.auth.auth_endpoints import role_required

router = APIRouter(
    prefix="/config",
    tags=["System Configuration"]
)

# Dependency Injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_config_controller(db: Session = Depends(get_db)):
    repo = ConfigRepository(session=db)
    return ConfigController(repo=repo)

# --- NORMALISATION ---
def normalize_config_data(config: OrganizationConfig):
    if not config:
        return {}
    return {
        "id": config.id,
        "name": config.name,
        "slogan": config.slogan,
        "logo_url": config.logo_url,
        "address": config.address,
        "city": config.city,
        "po_box": config.po_box,
        "phone": config.phone,
        "phone2": config.phone2,
        "email": config.email,
        "website": config.website,
        "niu": config.niu,
        "rccm": config.rccm,
        "legal_info": config.legal_info
    }

# --- ROUTES ---

@router.get("/structure", response_model=Any)
def get_structure_info(
    ctrl: ConfigController = Depends(get_config_controller)
):
    """
    Récupère les informations de la structure.
    """
    config = ctrl.get_structure_info()
    return normalize_config_data(config)

@router.post("/structure", response_model=Any, dependencies=[Depends(role_required("admin"))])
async def update_structure_info(
    request: Request,
    # On utilise Form() pour chaque champ car c'est du multipart/form-data
    name: str = Form(...),
    slogan: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    po_box: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    phone2: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    niu: Optional[str] = Form(None),
    rccm: Optional[str] = Form(None),
    legal_info: Optional[str] = Form(None),
    
    # Le fichier est optionnel (on peut update juste le texte)
    logo: Optional[UploadFile] = File(None),
    
    ctrl: ConfigController = Depends(get_config_controller)
):
    """
    Met à jour les infos et upload le logo si fourni.
    """
    # Construction du dictionnaire de données
    data = {
        "name": name,
        "slogan": slogan,
        "address": address,
        "city": city,
        "po_box": po_box,
        "phone": phone,
        "phone2": phone2,
        "email": email,
        "website": website,
        "niu": niu,
        "rccm": rccm,
        "legal_info": legal_info
    }
    
    # Pour construire l'URL absolue du logo (ex: http://localhost:8000)
    base_url = str(request.base_url).rstrip("/")
    
    updated_config = ctrl.update_structure_info(
        data_dict=data, 
        logo_file=logo,  # type: ignore
        base_url=base_url
    )
    
    return normalize_config_data(updated_config)