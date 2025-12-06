# Fichier: api_backend/backend_app/routes/audit/audit_endpoint.py

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from repositories.audit_repo import AuditRepository
from controller.audit_controller import AuditController

# 🟢 CORRECTION IMPORT : On importe les modèles de LISTE
from .audit_schemas import AuditAccessListResponse, AuditUserActionListResponse

# Configuration du router
router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
    dependencies=[Depends(role_required("admin", "manager"))]
)

# Dépendance DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dépendance Controller
def get_audit_controller(db: Session = Depends(get_db)) -> AuditController:
    repo = AuditRepository(db)
    return AuditController(repo)

# --- ENDPOINTS ---

@router.get("/access", response_model=AuditAccessListResponse)
def list_access_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    action_type: Optional[str] = Query(None, description="LOGIN, LOGOUT, LOGIN_FAILED"),
    ctrl: AuditController = Depends(get_audit_controller)
):
    """
    Liste l'historique des connexions et accès système.
    """
    try:
        return ctrl.list_access_logs(
            page=page,
            per_page=per_page,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            action_type=action_type
        )
    except Exception as e:
        print(f"[ERREUR AUDIT ACCESS] {str(e)}") 
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des logs d'accès.")

@router.get("/actions", response_model=AuditUserActionListResponse)
def list_action_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    resource_type: Optional[str] = Query(None, description="Ex: Patient, Prescription, User"),
    ctrl: AuditController = Depends(get_audit_controller)
):
    """
    Liste l'historique des actions métier (Création, Modification, Suppression).
    """
    try:
        return ctrl.list_action_logs(
            page=page,
            per_page=per_page,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            resource_type=resource_type
        )
    except Exception as e:
        print(f"[ERREUR AUDIT ACTIONS] {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des logs d'actions.")