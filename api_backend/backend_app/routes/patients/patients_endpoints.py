from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from typing import List, Any, Optional
from datetime import date

from .mapping import normalize_patient_data
from api_backend.backend_app.exceptions import translate_integrity_error
from .patients_schemas import PatientCreate, PatientUpdate, PatientResponse
from api_backend.backend_app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

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
    data = normalize_patient_data(raw)
    try:
        return PatientResponse.model_validate(data)
    except ValidationError as ve:
        errors = ve.errors()
        to_null = set()
        for e in errors:
            loc = e.get("loc", ())
            if not loc:
                continue
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
        logger.exception("Unrecoverable response validation error for patient: %s -- errors: %s", data, errors)
        raise HTTPException(status_code=500, detail="Erreur interne : données patient invalides")


# --- existing CRUD endpoints (list/get/post/put/delete) ---
@router.get("/", response_model=List[PatientResponse])
def list_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    patients_raw = patient_ctrl.list_patients(page=page, per_page=per_page, search=search)
    validated = []
    for p in patients_raw:
        validated.append(_safe_validate_patient(p))
    return validated



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


# --- Nouveaux endpoints exposant les méthodes KPI ---

@router.get("/spiritual", response_model=List[PatientResponse])
def list_spiritual_patients(patient_ctrl: PatientController = Depends(get_patient_controller)):
    try:
        raws = patient_ctrl.list_spiritual_patients()
        return [ _safe_validate_patient(p) for p in raws ]
    except SQLAlchemyError:
        logger.exception("Erreur DB list_spiritual_patients")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des patients spirituels")

@router.get("/find_by_code", response_model=PatientResponse)
def find_by_code(code: str = Query(...), patient_ctrl: PatientController = Depends(get_patient_controller)):
    try:
        p = patient_ctrl.find_by_code(code)
        if not p:
            raise HTTPException(status_code=404, detail="Patient non trouvé par code")
        return _safe_validate_patient(p)
    except SQLAlchemyError:
        logger.exception("Erreur DB find_by_code")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la recherche par code")
@router.get("/find", response_model=PatientResponse)
def find_patient(q: str = Query(...), patient_ctrl: PatientController = Depends(get_patient_controller)):
    try:
        p = patient_ctrl.find_patient(q)
        if not p:
            raise HTTPException(status_code=404, detail="Patient non trouvé")
        return _safe_validate_patient(p)
    except SQLAlchemyError:
        logger.exception("Erreur DB find_patient")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la recherche du patient")
    
    # dans le même router (par ex. app/routes/patients.py)

@router.get("/find_presc", response_model=PatientResponse)
def find_by_patient_presc(q: str = Query(...), patient_ctrl: PatientController = Depends(get_patient_controller)):
    """
    Endpoint utilisé par le module Prescription pour lookup patient par code ou id.
    Query param 'q' peut être un id (digits) ou un code_patient (string).
    """
    try:
        p = patient_ctrl.find_by_patient_presc(q)
        if not p:
            raise HTTPException(status_code=404, detail="Patient non trouvé pour prescription")
        return _safe_validate_patient(p)
    except SQLAlchemyError:
        logger.exception("Erreur DB find_by_patient_presc")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la recherche du patient")

    
    

@router.get("/by_doctor", response_model=List[PatientResponse])
def patients_followed_by_doctor(
    doctor_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        raws = patient_ctrl.patients_followed_by_doctor(doctor_id, page=page, per_page=per_page)
        return [ _safe_validate_patient(p) for p in raws ]
    except SQLAlchemyError:
        logger.exception("Erreur DB patients_followed_by_doctor")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des patients suivis par le médecin")

@router.get("/by_consultation_type")
def patients_by_consultation_type(
    doctor_id: Optional[int] = Query(None),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        data = patient_ctrl.patients_by_consultation_type(doctor_id, start=start, end=end)
        return data
    except SQLAlchemyError:
        logger.exception("Erreur DB patients_by_consultation_type")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture par type de consultation")

@router.get("/for_day", response_model=List[PatientResponse])
def patients_for_day(target_date: date = Query(...), doctor_id: Optional[int] = Query(None), patient_ctrl: PatientController = Depends(get_patient_controller)):
    try:
        raws = patient_ctrl.patients_for_day(target_date, doctor_id)
        return [ _safe_validate_patient(p) for p in raws ]
    except SQLAlchemyError:
        logger.exception("Erreur DB patients_for_day")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des patients pour le jour donné")

@router.get("/count_registered")
def count_registered(period: str = Query("day", regex="^(day|week)$"), patient_ctrl: PatientController = Depends(get_patient_controller)):
    try:
        cnt = patient_ctrl.count_registered(period=period)
        return {"count": cnt}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except SQLAlchemyError:
        logger.exception("Erreur DB count_registered")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du comptage des enregistrements")
    

@router.get("/find_for_appointment", response_model=PatientResponse)
def find_for_appointment(code: str = Query(...), patient_ctrl: PatientController = Depends(get_patient_controller)):
    p = patient_ctrl.find_by_code(code)
    if not p:
        raise HTTPException(status_code=404, detail="Patient non trouvé")
    return _safe_validate_patient(p)
  

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
        pid, code = patient_ctrl.create_patient(data.model_dump())
        patient = patient_ctrl.repo.get_by_id(pid)
        if not patient:
            raise HTTPException(status_code=500, detail="Patient créé mais impossible à lire")
        return _safe_validate_patient(patient)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

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
        logger.exception("SQLAlchemyError creating patient: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création du patient")
    
@router.get("/for_days", response_model=List[PatientResponse])
def new_patients_for_day(
    target_date: date = Query(..., description="Date pour laquelle récupérer les nouveaux patients (YYYY-MM-DD)"),
    doctor_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=2000),
    patient_ctrl: PatientController = Depends(get_patient_controller)
):
    try:
        raws = patient_ctrl.patients_for_day(target_date=target_date, doctor_id=doctor_id, page=page, per_page=per_page)
        # Si patient_ctrl renvoie des dicts sérialisés (comme ci-dessus), on peut renvoyer directement.
        # Si le endpoint doit renvoyer des PatientResponse Pydantic, on doit valider/normaliser :
        validated = []
        for p in raws:
            if isinstance(p, dict):
                # si p contient birth_date as date, PatientResponse doit supporter it
                validated.append(PatientResponse.model_validate(p))
            else:
                # ORM instance -> Pydantic from_attributes
                validated.append(PatientResponse.model_validate(p))
        return validated
    except RuntimeError as re:
        # e.g. colonne created_at introuvable
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.exception("Erreur DB patients_for_day: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des nouveaux patients")

