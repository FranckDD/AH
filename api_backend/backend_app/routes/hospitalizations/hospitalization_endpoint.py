import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .schemas import (
    HospitalizationAdmit,
    HospitalizationStatusCreate,
    HospitalizationDischarge,
    HospitalizationOut,
    HospitalizationStatusUpdateOut,
    HospitalizationCountOut,
)
from ...database import SessionLocal
from controller.hospitalization_controller import HospitalizationController
from repositories.hospitalization_repo import HospitalizationRepository
from repositories.audit_repo import AuditRepository
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hospitalizations",
    tags=["Hospitalisations"],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_hospitalization_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HospitalizationController:
    repo = HospitalizationRepository(db)
    audit_repo = AuditRepository(db)
    return HospitalizationController(repo=repo, current_user=current_user, audit_repo=audit_repo)


def _to_out(hosp) -> HospitalizationOut:
    return HospitalizationOut(
        id=hosp.id,
        patient_id=hosp.patient_id,
        admitted_at=hosp.admitted_at,
        admitted_by=hosp.admitted_by,
        admission_reason=hosp.admission_reason,
        discharged_at=hosp.discharged_at,
        discharge_disposition=hosp.discharge_disposition,
        discharge_note=hosp.discharge_note,
        discharged_by=hosp.discharged_by,
        patient_first_name=getattr(hosp.patient, "first_name", None) if hosp.patient else None,
        patient_last_name=getattr(hosp.patient, "last_name", None) if hosp.patient else None,
        status_updates=[HospitalizationStatusUpdateOut.model_validate(u) for u in (hosp.status_updates or [])],
    )


@router.post("/", response_model=HospitalizationOut, status_code=status.HTTP_201_CREATED)
def admit(data: HospitalizationAdmit, ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    try:
        hosp = ctrl.admit(data.patient_id, data.admission_reason)
        return _to_out(hosp)
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except IntegrityError:
        logger.exception("Conflit base de donnees a l'admission")
        raise HTTPException(status_code=409, detail="Ce patient est déjà hospitalisé (séjour en cours).")


@router.post("/{hospitalization_id}/status", response_model=HospitalizationStatusUpdateOut, status_code=status.HTTP_201_CREATED)
def add_status_update(
    hospitalization_id: int,
    data: HospitalizationStatusCreate,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    if data.status not in ("AMELIORATION", "STABLE", "AGGRAVATION"):
        raise HTTPException(status_code=422, detail="Statut clinique invalide.")
    try:
        update = ctrl.add_status_update(hospitalization_id, data.status, data.note)
        return HospitalizationStatusUpdateOut.model_validate(update)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/{hospitalization_id}/discharge", response_model=HospitalizationOut)
def discharge(
    hospitalization_id: int,
    data: HospitalizationDischarge,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    if data.discharge_disposition not in ("GUERI", "TRANSFERE", "SORTIE_CONTRE_AVIS_MEDICAL", "DECES"):
        raise HTTPException(status_code=422, detail="Type de sortie invalide.")
    try:
        hosp = ctrl.discharge(hospitalization_id, data.discharge_disposition, data.discharge_note)
        return _to_out(hosp)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/current", response_model=list[HospitalizationOut])
def list_current(ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return [_to_out(h) for h in ctrl.list_current()]


@router.get("/patient/{patient_id}", response_model=list[HospitalizationOut])
def get_history_for_patient(patient_id: int, ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return [_to_out(h) for h in ctrl.get_history_for_patient(patient_id)]


@router.get(
    "/kpi/count_current",
    response_model=HospitalizationCountOut,
    dependencies=[Depends(role_required("medecin", "nurse", "admin", "promoteur"))],
)
def count_current(ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return HospitalizationCountOut(count=ctrl.count_current())
