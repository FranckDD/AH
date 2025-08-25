# api_backend/app/routes/patients/patients_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List, Any

from .mapping import normalize_patient_data
from app.exceptions import translate_integrity_error
from .patients_schemas import PatientCreate, PatientUpdate, PatientResponse
from app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

#router = APIRouter(prefix="/patients", tags=["Patients"], dependencies=[Depends(get_current_user)] )
router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
    dependencies=[Depends(role_required("medecin", "nurse"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_patient_controller(current_user=Depends(get_current_user),
                           db: Session = Depends(get_db)) -> PatientController:
    auth_ctrl = AuthController(db_session=db)
    return PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)

def _safe_validate_patient(raw: Any) -> PatientResponse:
    """
    Tente de normaliser & valider un enregistrement patient pour éviter ResponseValidationError.
    Stratégie:
     - normalise (gender, phone),
     - parse_obj,
     - si ValidationError concerne gender/contact_phone, on remplace par None et retente.
     - sinon, on lève HTTP 500 (données corrompues).
    """
    data = normalize_patient_data(raw)
    try:
        return PatientResponse.model_validate(data)  # pydantic v2 usage (validate)
    except ValidationError as ve:
        # inspect errors pour tenter des corrections auto
        errors = ve.errors()
        # collect fields to nuller
        to_null = set()
        for e in errors:
            loc = e.get("loc", ())
            if not loc:
                continue
            # message-based heuristic: si erreur liée a gender/contact_phone => nuller
            if "gender" in loc or "contact_phone" in loc:
                to_null.add(loc[-1])
        if to_null:
            for k in to_null:
                data[k] = None
            try:
                return PatientResponse.model_validate(data)
            except ValidationError:
                logger.exception("Failed to auto-correct patient data after nulling fields: %s", to_null)
                raise HTTPException(status_code=500, detail="Erreur interne : données patient invalides")
        # si non récupérable
        logger.exception("Unrecoverable response validation error for patient: %s -- errors: %s", data, errors)
        raise HTTPException(status_code=500, detail="Erreur interne : données patient invalides")

@router.get("/", response_model=List[PatientResponse])
def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    # récupère liste (objets ORM ou dicts selon ton repo)
    patients_raw = patient_ctrl.list_patients(page=page, per_page=per_page, search=search)
    validated = []
    for p in patients_raw:
        validated.append(_safe_validate_patient(p))
    # FastAPI acceptera des Pydantic models en sortie
    return validated

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    p = patient_ctrl.get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    return _safe_validate_patient(p)

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    data: PatientCreate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        pid, code = patient_ctrl.create_patient(data.model_dump())  # pydantic v2 -> model_dump()
        patient = patient_ctrl.repo.get_by_id(pid)
        if not patient:
            raise HTTPException(status_code=500, detail="Patient créé mais impossible à lire")
        return _safe_validate_patient(patient)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except IntegrityError as ie:
        # rollback (sécurisé)
        try:
            patient_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)

    except SQLAlchemyError as e:
        try:
            patient_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating patient: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création du patient")


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        patient_ctrl.update_patient(patient_id, data.model_dump(exclude_unset=True))
        patient = patient_ctrl.repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient non trouvé après mise à jour")
        return _safe_validate_patient(patient)

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

    except IntegrityError as ie:
        try:
            patient_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)

    except SQLAlchemyError as e:
        try:
            patient_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating patient: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour du patient")

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    success = patient_ctrl.delete_patient(patient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
