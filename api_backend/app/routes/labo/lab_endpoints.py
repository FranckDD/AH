# app/routes/lab/lab_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
from typing import Any, List

from app.database import SessionLocal
from app.routes.auth.auth_endpoints import get_current_user,role_required
from repositories.lab_repo import LabRepository
from controller.lab_controller import LabController
from labo.labo_schemas import LabResultCreate, LabResultOut

logger = logging.getLogger(__name__)

#router = APIRouter(prefix="/lab", tags=["lab"])  # ne pas répéter get_current_user ici, on l'ajoute par dépendance sur les endpoints
router = APIRouter(
    prefix="/labo",
    tags=["labo"],
    dependencies=[Depends(role_required("laborantin"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_lab_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> LabController:
    repo = LabRepository(db)
    return LabController(repo=repo, current_user=current_user)

def _safe_return_lab_result(lr) -> LabResultOut:
    """
    Retourne un LabResultOut validé. Utiliser model_validate si ton schema
    a model_config = {'from_attributes': True}.
    """
    # Si tu prefères, fais des conversions manuelles pour éviter la validation complexe
    return LabResultOut.model_validate(lr)  # requires from_attributes = True

@router.post("/results", response_model=LabResultOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(get_current_user)])
def create_lab_result(
    payload: LabResultCreate,
    ctrl: LabController = Depends(get_lab_controller),
):
    """
    Create lab result (atomic: result + details). Payload.details doit être une list
    de Pydantic models (LabResultDetailCreate par ex.).
    """
    try:
        # pydantic v2: use model_dump(); v1: use dict()
        details_list: List[dict] = [d.model_dump() for d in payload.details]

        # create_result(patient_id, examen_id, details)
        out = ctrl.create_result(payload.patient_id, payload.examen_id, details_list)

        # out should contain 'result_id' (comme dans ton controller)
        result_id = out.get("result_id")
        if result_id is None:
            raise HTTPException(status_code=500, detail="Création échouée: pas d'identifiant retourné")

        # fetch full result to return
        lr = ctrl.repo.get_full_lab_result(result_id)
        if not lr:
            raise HTTPException(status_code=500, detail="Impossible de récupérer le résultat créé")

        return _safe_return_lab_result(lr)

    except IntegrityError as ie:
        # rollback safe
        try:
            ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise HTTPException(status_code=400, detail=str(ie.orig) if hasattr(ie, "orig") else str(ie))

    except SQLAlchemyError as se:
        try:
            ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQL error creating lab result: %s", se)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création du résultat de labo")

    except Exception as e:
        # rollback to be safe
        try:
            ctrl.repo.session.rollback()
        except Exception:
            pass
        logger.exception("Unexpected error creating lab result")
        raise HTTPException(status_code=500, detail=str(e))
