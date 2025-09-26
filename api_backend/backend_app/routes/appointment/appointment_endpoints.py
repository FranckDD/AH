# view_pyqt6/.../appointment_endpoints.py (modifié)
import logging
from typing import List, Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
from datetime import date, datetime

from backend_app.database import SessionLocal
from backend_app.exceptions import translate_integrity_error  # si tu l'as
from .appointment_schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentListResponse
from controller.appointment_controller import AppointmentController
from controller.auth_controller import AuthController
from repositories.appointment_repo import AppointmentRepository
from backend_app.routes.auth.auth_endpoints import get_current_user  # dépendance auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["Appointments"], dependencies=[Depends(get_current_user)])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_appointment_controller(current_user=Depends(get_current_user),
                               db=Depends(get_db)) -> AppointmentController:
    # Adaptation robuste pour récupérer/instancier patient_controller
    auth_ctrl = AuthController(db_session=db)
    repo = AppointmentRepository(db)

    patient_ctrl = getattr(auth_ctrl, "patient_controller", None)
    if not patient_ctrl:
        try:
            from controller.patient_controller import PatientController
            patient_repo = getattr(auth_ctrl, "patient_repo", None)
            if patient_repo is None:
                from repositories.patient_repo import PatientRepository
                patient_repo = PatientRepository(db)
            patient_ctrl = PatientController(repo=patient_repo, current_user=current_user)
        except Exception:
            logger.exception("Impossible de créer le PatientController pour les appointments")
            raise

    return AppointmentController(repo=repo, patient_controller=patient_ctrl, current_user=current_user)


# -----------------------
# Robust date normalization util
# -----------------------
from fastapi import HTTPException as FastAPIHTTPException
from datetime import datetime as _dt
from datetime import date as _date
from datetime import time as _time

def _to_date(value):
    """
    Normalize a value into a datetime.date or None.
    Accepts:
      - None
      - datetime.date
      - datetime.datetime -> returns .date()
      - ISO date string 'YYYY-MM-DD'
      - ISO datetime 'YYYY-MM-DDTHH:MM:SS' or 'YYYY-MM-DD HH:MM:SS'
    Raises HTTPException(400) on invalid format.
    """
    if value is None:
        return None
    # already a date (but not datetime)
    if isinstance(value, _date) and not isinstance(value, _dt):
        return value
    # datetime -> date
    if isinstance(value, _dt):
        return value.date()
    # string parsing
    if isinstance(value, str):
        s = value.strip()
        # try date first (YYYY-MM-DD)
        try:
            # date.fromisoformat accepts 'YYYY-MM-DD'
            return _date.fromisoformat(s)
        except Exception:
            pass
        # try ISO datetime
        try:
            dt = _dt.fromisoformat(s)
            return dt.date()
        except Exception:
            pass
        # try common "YYYY-MM-DD HH:MM:SS"
        try:
            dt = _dt.strptime(s, "%Y-%m-%d %H:%M:%S")
            return dt.date()
        except Exception:
            # not valid
            raise FastAPIHTTPException(status_code=400, detail=f"Date invalide: '{value}' (attendu YYYY-MM-DD ou ISO datetime)")
    raise FastAPIHTTPException(status_code=400, detail=f"Type date non supporté: {type(value)}")


# -----------------------
# Helper: validate/normalize appointment items
# -----------------------
def _safe_validate_appointment(raw: Any) -> AppointmentResponse:
    """
    Valide un objet 'raw' (ORM instance ou dict) en AppointmentResponse.
    Convertit patient/doctor ORM -> dict si nécessaire.
    """
    def sa_obj_to_dict(obj):
        if obj is None:
            return None
        if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
            try:
                return obj.to_dict()
            except Exception:
                pass
        table = getattr(obj, "__table__", None)
        if table is not None:
            data = {}
            for col in table.columns:
                try:
                    data[col.name] = getattr(obj, col.name, None)
                except Exception:
                    data[col.name] = None
            return data
        try:
            return {k: v for k, v in getattr(obj, "__dict__", {}).items() if not k.startswith("_")}
        except Exception:
            return None

    data = {}
    try:
        if isinstance(raw, dict):
            data = raw.copy()
        elif hasattr(raw, "__dict__"):
            data = {k: v for k, v in raw.__dict__.items() if not k.startswith("_")}
        else:
            data = raw
    except Exception:
        data = raw

    try:
        if "patient" in data and not isinstance(data.get("patient"), dict):
            data["patient"] = sa_obj_to_dict(data.get("patient"))
        if "doctor" in data and not isinstance(data.get("doctor"), dict):
            data["doctor"] = sa_obj_to_dict(data.get("doctor"))

        appt_date = data.get("appointment_date")
        if isinstance(appt_date, datetime):
            data["appointment_date"] = appt_date.date()
        appt_time = data.get("appointment_time")
        if isinstance(appt_time, datetime):
            data["appointment_time"] = appt_time.time()
    except Exception:
        logger.exception("Erreur lors de la normalisation des champs patient/doctor/date/time pour un RDV")

    try:
        # utilise pydantic validation/from_attributes
        return AppointmentResponse.model_validate(data)
    except ValidationError as ve:
        logger.exception("Unrecoverable appointment response validation error: %s", ve.errors())
        raise HTTPException(status_code=500, detail="Erreur interne : données RDV invalides")


# -----------------------
# LIST (paged) - renvoie toujours {data, total, page, per_page}
# -----------------------
@router.get("/", response_model=AppointmentListResponse)
def list_appointments(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    doctor_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None),
    appt_ctrl: AppointmentController = Depends(get_appointment_controller),
):
    """
    Return paginated appointments with embedded patient & doctor in each item.
    Accepts controller responses in several shapes.
    """
    try:
        # normalize string dates to date objects if provided
        df = _to_date(date_from) if date_from is not None else None
        dt = _to_date(date_to) if date_to is not None else None

        res = appt_ctrl.list_appointments(page=page, per_page=per_page,
                                          date_from=df, date_to=dt,
                                          doctor_id=doctor_id, patient_id=patient_id)

        # Normaliser le payload retourné par le controller / gateway
        items = []
        total = None

        if isinstance(res, dict):
            # préférer 'data' puis 'items' puis 'results'
            if isinstance(res.get("data"), list):
                items = res.get("data", [])
            elif isinstance(res.get("items"), list):
                items = res.get("items", [])
            elif isinstance(res.get("results"), list):
                items = res.get("results", [])
            else:
                # fallback: maybe controller returned {'data': None, ...} or other shapes
                # essayer d'extraire toute liste présente
                for k in ("rows", "payload", "results", "items", "data"):
                    v = res.get(k)
                    if isinstance(v, list):
                        items = v
                        break
            total = res.get("total") if res.get("total") is not None else res.get("count")
        elif isinstance(res, list):
            items = res
            total = len(items)
        elif res is None:
            items = []
            total = 0
        else:
            # unexpected type -> attempt to treat as single item
            items = [res]
            total = 1

        # validate/serialize each item to AppointmentResponse
        validated = []
        for appt in items:
            try:
                validated.append(_safe_validate_appointment(appt))
            except Exception:
                # skip invalid items but log
                logger.exception("Erreur lors de la validation d'un RDV dans list_appointments")

        # ensure ints for page/per_page/total
        try:
            page_int = int(page)
        except Exception:
            page_int = 1
        try:
            per_page_int = int(per_page)
        except Exception:
            per_page_int = len(validated) or 0
        try:
            total_int = int(total) if total is not None else len(validated)
        except Exception:
            total_int = len(validated)

        return {"data": validated, "total": total_int, "page": page_int, "per_page": per_page_int}

    except SQLAlchemyError:
        logger.exception("Erreur DB list_appointments")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des rendez-vous")


# ---- Nouveaux endpoints exposant les méthodes du controller / KPI / by-day / upcoming ----

@router.get("/by-day/{target_date}", response_model=List[AppointmentResponse])
def appointments_by_day(target_date: str, appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        target_date = _to_date(target_date)
        raw = appt_ctrl.get_by_day(target_date)
        return [_safe_validate_appointment(r) for r in (raw or [])]
    except SQLAlchemyError:
        logger.exception("Erreur DB appointments_by_day")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des RDV du jour")


@router.get("/kpi/count_by_day")
def kpi_count_by_day(target_date: str = Query(...), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        target_date = _to_date(target_date)
        cnt = appt_ctrl.count_by_day(target_date)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB kpi_count_by_day")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI")


@router.get("/specialties", response_model=List[str])
def list_specialties(appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        specs = appt_ctrl.get_all_specialties()
        return specs
    except SQLAlchemyError:
        logger.exception("Erreur DB list_specialties")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des spécialités")


@router.get("/upcoming", response_model=List[AppointmentResponse])
def get_upcoming_appointments(
    doctor_id: Optional[int] = Query(None),
    limit: int = Query(5, ge=1, le=100),
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        raw = appt_ctrl.upcoming_appointments(doctor_id if doctor_id else None, limit=limit)
        validated = [ _safe_validate_appointment(r) for r in (raw or []) ]
        return validated
    except SQLAlchemyError:
        logger.exception("Erreur DB upcoming_appointments")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des prochains RDV")


@router.get("/upcoming_today", response_model=List[AppointmentResponse])
def get_upcoming_today(doctor_id: Optional[int] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        raw = appt_ctrl.upcoming_today(doctor_id)
        validated = [ _safe_validate_appointment(r) for r in (raw or []) ]
        return validated
    except SQLAlchemyError:
        logger.exception("Erreur DB upcoming_today")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des RDV du jour")


@router.get("/kpi/weekly/{year}")
def kpi_weekly_appointments(year: int, doctor_id: Optional[int] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        data = appt_ctrl.weekly_appointments(doctor_id if doctor_id else None, year)
        return data
    except SQLAlchemyError:
        logger.exception("Erreur DB weekly_appointments")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI hebdomadaire")


@router.get("/kpi/count_by_status")
def kpi_count_by_status(doctor_id: Optional[int] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        s = _to_date(start) if start is not None else None
        e = _to_date(end) if end is not None else None
        data = appt_ctrl.count_by_status(doctor_id, s, e)
        return data
    except SQLAlchemyError:
        logger.exception("Erreur DB count_by_status")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI status")


@router.get("/kpi/total")
def kpi_total_appointments(doctor_id: Optional[int] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        s = _to_date(start) if start is not None else None
        e = _to_date(end) if end is not None else None
        total = appt_ctrl.total_appointments(doctor_id, s, e)
        return {"total": total}
    except SQLAlchemyError:
        logger.exception("Erreur DB total_appointments")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI total")


@router.get("/kpi/time_series")
def kpi_time_series(doctor_id: Optional[int] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        s = _to_date(start) if start is not None else None
        e = _to_date(end) if end is not None else None
        series = appt_ctrl.appointments_time_series(doctor_id, s, e)
        return series
    except SQLAlchemyError:
        logger.exception("Erreur DB appointments_time_series")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI time series")


@router.get("/kpi/distinct_patients")
def kpi_distinct_patients(doctor_id: Optional[int] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        s = _to_date(start) if start is not None else None
        e = _to_date(end) if end is not None else None
        cnt = appt_ctrl.distinct_patients_count(doctor_id, s, e)
        return {"distinct_patients": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB distinct_patients_count")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI patients distincts")


@router.get("/kpi/monthly_breakdown")
def kpi_monthly_breakdown(year: Optional[int] = Query(None), doctor_id: Optional[int] = Query(None), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        data = appt_ctrl.monthly_breakdown(year=year, doctor_id=doctor_id)
        return data
    except SQLAlchemyError:
        logger.exception("Erreur DB monthly_breakdown")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul KPI mensuel")


# Doctor-filtered schedules
@router.get("/doctor/day", response_model=List[AppointmentResponse])
def doctor_day_schedule(doctor_id: Optional[int] = Query(None), target_date: str = Query(...), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        td = _to_date(target_date)
        raw = appt_ctrl.get_by_day_doctor(doctor_id, td)
        return [ _safe_validate_appointment(r) for r in (raw or []) ]
    except SQLAlchemyError:
        logger.exception("Erreur DB get_by_day_doctor")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des RDV du médecin pour le jour donné")


@router.get("/doctor/week", response_model=List[AppointmentResponse])
def doctor_week_schedule(doctor_id: Optional[int] = Query(None), start_date: str = Query(...), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        sd = _to_date(start_date)
        raw = appt_ctrl.get_by_week_doctor(doctor_id, sd)
        return [ _safe_validate_appointment(r) for r in (raw or []) ]
    except SQLAlchemyError:
        logger.exception("Erreur DB get_by_week_doctor")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des RDV du médecin pour la semaine donnée")


@router.get("/doctor/month", response_model=List[AppointmentResponse])
def doctor_month_schedule(doctor_id: Optional[int] = Query(None), year: int = Query(...), month: int = Query(..., ge=1, le=12), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        raw = appt_ctrl.get_by_month_doctor(doctor_id, year, month)
        return [ _safe_validate_appointment(r) for r in (raw or []) ]
    except SQLAlchemyError:
        logger.exception("Erreur DB get_by_month_doctor")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la lecture des RDV du médecin pour le mois donné")


@router.get("/doctor/search_by_patient", response_model=List[AppointmentResponse])
def doctor_search_by_patient(doctor_id: Optional[int] = Query(None), patient_id: int = Query(...), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        raw = appt_ctrl.search_by_patient_doctor(doctor_id, patient_id)
        return [ _safe_validate_appointment(r) for r in (raw or []) ]
    except SQLAlchemyError:
        logger.exception("Erreur DB search_by_patient_doctor")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la recherche RDV par patient pour le médecin")


@router.get("/count_consultations")
def count_consultations(period: str = Query("day", regex="^(day|week)$"), appt_ctrl: AppointmentController = Depends(get_appointment_controller)):
    try:
        cnt = appt_ctrl.count_consultations(period=period)
        return {"count": cnt}
    except SQLAlchemyError:
        logger.exception("Erreur DB count_consultations")
        raise HTTPException(status_code=500, detail="Erreur serveur lors du calcul du nombre de consultations")


# -----------------------
# CRUD endpoints (placed AFTER static routes to avoid path collisions)
# -----------------------

@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        created = appt_ctrl.book_appointment(payload.model_dump())
        # controller.book_appointment peut retourner dict ou ORM
        if isinstance(created, dict):
            created_id = created.get("appointment_id") or created.get("id")
        else:
            created_id = getattr(created, "id", None)
        if not created_id:
            raise HTTPException(status_code=500, detail="RDV créé mais impossible à lire")
        appt_fresh = appt_ctrl.repo.get_by_id(int(created_id))
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


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    appt = appt_ctrl.repo.get_by_id(appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")
    return _safe_validate_appointment(appt)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        data = payload.model_dump(exclude_unset=True)
        # controller.modify_appointment expects (id, appointment_data: dict)
        updated = appt_ctrl.modify_appointment(appointment_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="RDV introuvable")
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


# ---- Actions accept/cancel/complete ----
@router.post("/{appointment_id}/accept", response_model=AppointmentResponse)
def accept_appointment_endpoint(
    appointment_id: int = Path(..., ge=1),
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        # Si le controller a une méthode dédiée, l'utiliser
        if hasattr(appt_ctrl, "modify_appointment"):
            appt = appt_ctrl.modify_appointment(appointment_id, status="pending")
        else:
            # fallback: use cancel/complete/modify patterns
            raise HTTPException(status_code=405, detail="Méthode accept non supportée côté serveur")
        if not appt:
            raise HTTPException(status_code=404, detail="RDV introuvable")
        fresh = appt_ctrl.repo.get_by_id(appointment_id)
        return _safe_validate_appointment(fresh)
    except SQLAlchemyError:
        logger.exception("Erreur DB accept_appointment")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de l'acceptation du RDV")


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment_endpoint(
    appointment_id: int = Path(..., ge=1),
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        # Prefer dedicated method cancel_appointment
        if hasattr(appt_ctrl, "cancel_appointment"):
            appt = appt_ctrl.cancel_appointment(appointment_id)
        else:
            appt = appt_ctrl.modify_appointment(appointment_id, status="cancelled")
        if not appt:
            raise HTTPException(status_code=404, detail="RDV introuvable")
        fresh = appt_ctrl.repo.get_by_id(appointment_id)
        return _safe_validate_appointment(fresh)
    except SQLAlchemyError:
        logger.exception("Erreur DB cancel_appointment")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de l'annulation du RDV")


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment_endpoint(
    appointment_id: int = Path(..., ge=1),
    appt_ctrl: AppointmentController = Depends(get_appointment_controller)
):
    try:
        if hasattr(appt_ctrl, "complete_appointment"):
            appt = appt_ctrl.complete_appointment(appointment_id)
        else:
            appt = appt_ctrl.modify_appointment(appointment_id, status="completed")
        if not appt:
            raise HTTPException(status_code=404, detail="RDV introuvable")
        fresh = appt_ctrl.repo.get_by_id(appointment_id)
        return _safe_validate_appointment(fresh)
    except SQLAlchemyError:
        logger.exception("Erreur DB complete_appointment")
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la complétion du RDV")
