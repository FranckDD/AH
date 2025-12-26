# api_backend/app/routes/consultations/consultations_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List, Any, Optional

from app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.cs_controller import ConsultationSpirituelController
from repositories.cs_repo import ConsultationSpirituelRepository
from app.routes.auth.auth_endpoints import get_current_user,role_required
from app.exceptions import translate_integrity_error

from .mapping import normalize_consultation_data
from ..cs.schemas_cs import   ConsultationCreate,ConsultationUpdate,ConsultationResponse

logger = logging.getLogger(__name__)

#router = APIRouter( prefix="/consultations",    tags=["Consultations"],    dependencies=[Depends(get_current_user)],)
router = APIRouter(
    prefix="/cs",
    tags=["Consultation spirituelle"],
    dependencies=[Depends(role_required("secretaire", "admin"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_consultation_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsultationSpirituelController:
    """
    Construit le controller de consultation en réutilisant AuthController pour
    récupérer les repos liés (ex: patient_repo) afin de respecter la
    séparation repo/controller présente dans le projet.
    """
    auth_ctrl = AuthController(db_session=db)
    # patient controller utile au controller de consultations (injection)
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)
    cs_repo = ConsultationSpirituelRepository(session=db)
    return ConsultationSpirituelController(repo=cs_repo, patient_controller=patient_ctrl, current_user=current_user)


def _safe_validate_consultation(raw: Any) -> ConsultationResponse:
    """
    Normalise & valide une consultation pour éviter ResponseValidationError.
    - normalise (dates, tableaux, etc) via normalize_consultation_data
    - tente model_validate (pydantic v2)
    - si ValidationError, applique heuristique pour nuller certains champs et retenter
    """
    data = normalize_consultation_data(raw)
    try:
        return ConsultationResponse.model_validate(data)
    except ValidationError as ve:
        errors = ve.errors()
        to_null = set()
        for e in errors:
            loc = e.get("loc", ())
            if not loc:
                continue
            # heuristique : si problème sur fields optionnels list/array ou created_by_name => nuller
            if "presc_generic" in loc or "presc_med_spirituel" in loc or "created_by_name" in loc:
                to_null.add(loc[-1])
        if to_null:
            for k in to_null:
                data[k] = None
            try:
                return ConsultationResponse.model_validate(data)
            except ValidationError:
                logger.exception("Failed to auto-correct consultation data after nulling fields: %s", to_null)
                raise HTTPException(status_code=500, detail="Erreur interne : données consultation invalides")
        logger.exception("Unrecoverable response validation error for consultation: %s -- errors: %s", data, errors)
        raise HTTPException(status_code=500, detail="Erreur interne : données consultation invalides")


@router.get("/", response_model=List[ConsultationResponse])
def list_consultations(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    search: Optional[str] = Query(None),
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    """
    Retourne la liste des consultations (simple pagination côté endpoint).
    Si besoin, tu peux déplacer la pagination côté repo.
    """
    all_raw = cs_ctrl.list_consultations()
    # Optional: implémentation simple de pagination en mémoire
    start = (page - 1) * per_page
    end = start + per_page
    page_items = all_raw[start:end]
    validated = [ _safe_validate_consultation(item) for item in page_items ]
    return validated


@router.get("/patient/{patient_id}", response_model=List[ConsultationResponse])
def list_for_patient(
    patient_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    raws = cs_ctrl.list_for_patient(patient_id)
    return [ _safe_validate_consultation(r) for r in raws ]


@router.get("/last/{patient_id}", response_model=Optional[ConsultationResponse])
def get_last_for_patient(
    patient_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    last = cs_ctrl.get_last_for_patient(patient_id)
    if not last:
        return None
    return _safe_validate_consultation(last)


@router.get("/{cs_id}", response_model=ConsultationResponse)
def get_consultation(
    cs_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        cs = cs_ctrl.get_consultation(cs_id)
        return _safe_validate_consultation(cs)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def create_consultation(
    data: ConsultationCreate,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        cs = cs_ctrl.create_consultation(data.model_dump())
        # cs devrait être l'objet ORM retourné par le repo
        return _safe_validate_consultation(cs)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating consultation: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création de la consultation")


@router.put("/{cs_id}", response_model=ConsultationResponse)
def update_consultation(
    cs_id: int,
    data: ConsultationUpdate,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    try:
        updated = cs_ctrl.update_consultation(cs_id, data.model_dump(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Consultation non trouvée après mise à jour")
        return _safe_validate_consultation(updated)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except IntegrityError as ie:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            cs_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating consultation: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour de la consultation")


@router.delete("/{cs_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consultation(
    cs_id: int,
    cs_ctrl: ConsultationSpirituelController = Depends(get_consultation_controller),
):
    cs = cs_ctrl.delete_consultation(cs_id)
    if not cs:
        raise HTTPException(status_code=404, detail="Consultation non trouvée")
    return None
