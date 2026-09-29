# api_backend/backend_app/routes/nurse_shifts/nurse_shift_endpoint.py
import logging
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .schemas import NurseShiftCreate, NurseShiftOut, ActiveNurseOut
from ...database import SessionLocal
from controller.nurse_shift_controller import NurseShiftController
from repositories.nurse_shift_repo import NurseShiftRepository
from repositories.user_repo import UserRepository
from repositories.audit_repo import AuditRepository
from models.nurse_shift import SHIFT_TYPES
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nurse-shifts", tags=["Planning infirmiers"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_nurse_shift_controller(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NurseShiftController:
    repo = NurseShiftRepository(db)
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    return NurseShiftController(repo=repo, user_repo=user_repo, current_user=current_user, audit_repo=audit_repo)


def _user_name(user) -> str:
    if not user:
        return "Inconnu"
    return getattr(user, "full_name", None) or getattr(user, "username", None) or "Inconnu"


def _to_out(shift) -> NurseShiftOut:
    return NurseShiftOut(
        id=shift.id,
        shift_date=shift.shift_date,
        shift_type=shift.shift_type,
        nurse_id=shift.nurse_id,
        nurse_name=_user_name(getattr(shift, "nurse", None)),
        created_by=shift.created_by,
        created_by_name=_user_name(getattr(shift, "created_by_user", None)),
        created_at=shift.created_at,
    )


@router.post(
    "/",
    response_model=NurseShiftOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def create_shift(data: NurseShiftCreate, ctrl: NurseShiftController = Depends(get_nurse_shift_controller)):
    if data.shift_type not in SHIFT_TYPES:
        raise HTTPException(status_code=422, detail="Créneau invalide.")
    try:
        shift = ctrl.assign_shift(data.shift_date, data.shift_type, data.nurse_id)
        return _to_out(shift)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        if "introuvable" in str(ve):
            raise HTTPException(status_code=404, detail=str(ve))
        raise HTTPException(status_code=409, detail=str(ve))
    except IntegrityError:
        logger.exception("Conflit base de donnees a l'affectation")
        raise HTTPException(status_code=409, detail="Cet infirmier est déjà affecté à ce créneau.")


@router.delete(
    "/{shift_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def delete_shift(shift_id: int, ctrl: NurseShiftController = Depends(get_nurse_shift_controller)):
    try:
        ctrl.remove_shift(shift_id)
        return None
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get(
    "/",
    response_model=list[NurseShiftOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_shifts(
    start: date = Query(...),
    end: date = Query(...),
    ctrl: NurseShiftController = Depends(get_nurse_shift_controller),
):
    return [_to_out(s) for s in ctrl.list_shifts(start, end)]


@router.get(
    "/nurses",
    response_model=list[ActiveNurseOut],
    dependencies=[Depends(role_required("medecin", "nurse"))],
)
def list_nurses(ctrl: NurseShiftController = Depends(get_nurse_shift_controller)):
    return [
        ActiveNurseOut(user_id=u.user_id, full_name=u.full_name, is_head_nurse=bool(u.is_head_nurse))
        for u in ctrl.list_active_nurses()
    ]
