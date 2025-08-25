# app/routes/appointments/appointments_endpoints.py
import logging
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
from datetime import date, datetime

from app.database import SessionLocal
from app.exceptions import translate_integrity_error  # si tu l'as comme pour patients
from .appointment_schemas import   AppointmentCreate, AppointmentUpdate, AppointmentResponse
from controller.appointment_controller import AppointmentController
from controller.auth_controller import AuthController
from repositories.appointment_repo import AppointmentRepository
from app.routes.auth.auth_endpoints import get_current_user  # dépendance auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["Appointments"], dependencies=[Depends(get_current_user)])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_appointment_controller(current_user=Depends(get_current_user),
                               db: Session = Depends(get_db)) -> AppointmentController:
    # adapte selon la signature de ton AuthController / repo de patients si nécessaire
    auth_ctrl = AuthController(db_session=db)
    repo = AppointmentRepository(db)
    return AppointmentController(repo=repo, patient_controller=auth_ctrl.patient_controller, current_user=current_user)

def _safe_validate_appointment(raw: Any) -> AppointmentResponse:
    """
    Normalise & valide un objet appointment (ORM object ou dict) pour éviter ResponseValidationError.
    Strategy: try model_validate; if fails, try small auto-corrections (ex: convertir datetimes -> date/time)
    """
    # si c'est un ORM object et model_config.from_attributes=True, Pydantic gère l'accès aux attributs
    try:
        return AppointmentResponse.model_validate(raw)
    except ValidationError as ve:
        # attempt light fixes if possible
        data = {}
        # try to extract attributes into dict to attempt conversion
        try:
            # raw may be ORM instance -> rely on pydantic from_attributes not dict
            # fallback to __dict__ for some cases
            if hasattr(raw, "__dict__"):
                data = {k: v for k, v in raw.__dict__.items() if not k.startswith("_")}
            elif isinstance(raw, dict):
                data = raw.copy()
        except Exception:
            data = {}

        # quick conversions heuristics: if appointment_date is datetime -> make date, if time is datetime -> time
        appt_date = data.get("appointment_date")
        if isinstance(appt_date, datetime):
            data["appointment_date"] = appt_date.date()
        appt_time = data.get("appointment_time")
        if isinstance(appt_time, datetime):
            data["appointment_time"] = appt_time.time()

        try:
            return AppointmentResponse.model_validate(data)
        except ValidationError:
            logger.exception("Unrecoverable appointment response validation error: %s", ve.errors())
            raise HTTPException(status_code=500, detail="Erreur interne : données RDV invalides")

@router.get("/", response_model=List[AppointmentResponse])
def list_appointments(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    doctor_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    appt_ctrl: AppointmentController = Depends(get_appointment_controller),
):
    """
    Liste des RDV. Si date_from/date_to fournis, filtre par intervalle.
    Sinon renvoie tout (avec pagination côté repo si implémenté).
    """
    try:
        results = []
        if date_from and date_to:
            results = appt_ctrl.repo.find_by_date_range(date_from, date_to)
        elif patient_id:
            results = appt_ctrl.search_by_patient(patient_id)
        elif doctor_id:
            results = appt_ctrl.search_by_doctor(doctor_id)
        else:
            results = appt_ctrl.repo.list_all()

        validated = [ _safe_validate_appointment(r) for r in results ]
        return validated
    except SQLAlchemyError:
        logger.exception("Erreur DB list_appointments")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des rendez-vous")

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    appt = appt_ctrl.repo.get_by_id(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")
    return _safe_validate_appointment(appt)

@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        # controller.book_appointment attends un dict (tu l'as codé ainsi)
        appt = appt_ctrl.book_appointment(payload.model_dump())
        # relire depuis le repo pour avoir tous champs (created_at, relations)
        appt_fresh = appt_ctrl.repo.get_by_id(appt.id)
        if not appt_fresh:
            raise HTTPException(status_code=500, detail="RDV créé mais impossible à lire")
        return _safe_validate_appointment(appt_fresh)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except IntegrityError as ie:
        try:
            appt_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError (appointments)")
        raise translate_integrity_error(ie)

    except SQLAlchemyError as e:
        try:
            appt_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError (appointments)")
        logger.exception("SQLAlchemyError creating appointment: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création du RDV")

@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        data = payload.model_dump(exclude_unset=True)
        updated = appt_ctrl.modify_appointment(appointment_id, **data)
        if not updated:
            raise HTTPException(status_code=404, detail="RDV introuvable")
        # repo.update doit déjà commit et retourner l'objet
        appt_fresh = appt_ctrl.repo.get_by_id(appointment_id)
        return _safe_validate_appointment(appt_fresh)

    except IntegrityError as ie:
        try:
            appt_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError (appointments update)")
        raise translate_integrity_error(ie)

    except SQLAlchemyError as e:
        try:
            appt_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError (appointments update)")
        logger.exception("SQLAlchemyError updating appointment: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour du RDV")

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    appt = appt_ctrl.repo.get_by_id(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="RDV introuvable")
    try:
        appt_ctrl.repo.delete(appt)
    except SQLAlchemyError:
        logger.exception("Erreur lors de la suppression RDV")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la suppression du RDV")
