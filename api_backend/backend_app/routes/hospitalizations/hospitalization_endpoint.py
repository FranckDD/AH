import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
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
from repositories.notification_repo import NotificationRepository
from repositories.user_repo import UserRepository
from models.hospitalization import CLINICAL_STATUSES, DISCHARGE_DISPOSITIONS
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hospitalizations",
    tags=["Hospitalisations"],
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
    notification_repo = NotificationRepository(db)
    user_repo = UserRepository(db)
    return HospitalizationController(
        repo=repo,
        current_user=current_user,
        audit_repo=audit_repo,
        notification_repo=notification_repo,
        user_repo=user_repo,
    )


def _user_name(user) -> Optional[str]:
    if not user:
        return None
    return getattr(user, "full_name", None) or getattr(user, "username", None)


def _status_update_to_out(update) -> HospitalizationStatusUpdateOut:
    return HospitalizationStatusUpdateOut(
        id=update.id,
        status=update.status,
        note=update.note,
        created_by=update.created_by,
        created_by_name=_user_name(getattr(update, "created_by_user", None)),
        created_at=update.created_at,
    )


def _to_out(hosp) -> HospitalizationOut:
    return HospitalizationOut(
        id=hosp.id,
        patient_id=hosp.patient_id,
        admitted_at=hosp.admitted_at,
        admitted_by=hosp.admitted_by,
        admitted_by_name=_user_name(getattr(hosp, "admitted_by_user", None)),
        admission_reason=hosp.admission_reason,
        discharged_at=hosp.discharged_at,
        discharge_disposition=hosp.discharge_disposition,
        discharge_note=hosp.discharge_note,
        discharged_by=hosp.discharged_by,
        discharged_by_name=_user_name(getattr(hosp, "discharged_by_user", None)),
        patient_first_name=getattr(hosp.patient, "first_name", None) if hosp.patient else None,
        patient_last_name=getattr(hosp.patient, "last_name", None) if hosp.patient else None,
        # Deja trie newest-first (Hospitalization.status_updates,
        # order_by=desc(created_at), voir models/hospitalization.py) - le
        # frontend affiche cette liste telle quelle, jamais juste [0].
        status_updates=[_status_update_to_out(u) for u in (hosp.status_updates or [])],
    )


@router.post(
    "/",
    response_model=HospitalizationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def admit(data: HospitalizationAdmit, ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    try:
        hosp = ctrl.admit(data.patient_id, data.admission_reason)
        return _to_out(hosp)
    except ValueError as ve:
        if "introuvable" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=409, detail=str(ve))
    except IntegrityError:
        logger.exception("Conflit base de donnees a l'admission")
        raise HTTPException(status_code=409, detail="Ce patient est déjà hospitalisé (séjour en cours).")


@router.post(
    "/{hospitalization_id}/status",
    response_model=HospitalizationStatusUpdateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def add_status_update(
    hospitalization_id: int,
    data: HospitalizationStatusCreate,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    if data.status not in CLINICAL_STATUSES:
        raise HTTPException(status_code=422, detail="Statut clinique invalide.")
    try:
        update = ctrl.add_status_update(hospitalization_id, data.status, data.note)
        return _status_update_to_out(update)
    except ValueError as ve:
        if "Aucune hospitalisation trouvée" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=400, detail=str(ve))


@router.post(
    "/{hospitalization_id}/discharge",
    response_model=HospitalizationOut,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def discharge(
    hospitalization_id: int,
    data: HospitalizationDischarge,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    if data.discharge_disposition not in DISCHARGE_DISPOSITIONS:
        raise HTTPException(status_code=422, detail="Type de sortie invalide.")
    try:
        hosp = ctrl.discharge(hospitalization_id, data.discharge_disposition, data.discharge_note)
        return _to_out(hosp)
    except ValueError as ve:
        if "Aucune hospitalisation trouvée" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=400, detail=str(ve))


@router.get(
    "/current",
    response_model=list[HospitalizationOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_current(ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return [_to_out(h) for h in ctrl.list_current()]


@router.get(
    "/patient/{patient_id}",
    response_model=list[HospitalizationOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def get_history_for_patient(patient_id: int, ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return [_to_out(h) for h in ctrl.get_history_for_patient(patient_id)]


@router.get(
    "/{hospitalization_id}/discharge-letter",
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def download_discharge_letter(
    hospitalization_id: int,
    ctrl: HospitalizationController = Depends(get_hospitalization_controller),
):
    try:
        pdf_bytes = ctrl.generate_discharge_letter_pdf(hospitalization_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=lettre_sortie_{hospitalization_id}.pdf"},
        )
    except ValueError as ve:
        if "Aucune hospitalisation trouvée" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        logger.exception("Erreur lors de la génération de la lettre de sortie")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la génération du PDF")


@router.get(
    "/kpi/count_current",
    response_model=HospitalizationCountOut,
    dependencies=[Depends(role_required("medecin", "nurse", "admin", "promoteur"))],
)
def count_current(ctrl: HospitalizationController = Depends(get_hospitalization_controller)):
    return HospitalizationCountOut(count=ctrl.count_current())
