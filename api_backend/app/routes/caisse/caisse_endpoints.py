from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
import logging
from datetime import date, datetime

from app.database import SessionLocal
from controller.auth_controller import AuthController
from controller.patient_controller import PatientController
from controller.caisse_controller import CaisseController
from repositories.caisse_repo import CaisseRepository
from app.routes.auth.auth_endpoints import get_current_user, role_required
from app.exceptions import translate_integrity_error
from .mapping import normalize_caisse_data  # facultatif si tu utilises Pydantic

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/caisse",
    tags=["Caisse"],
    dependencies=[Depends(role_required("secretaire", "admin"))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_caisse_controller(current_user=Depends(get_current_user), db: Session = Depends(get_db)) -> CaisseController:
    auth_ctrl = AuthController(db_session=db)
    patient_ctrl = PatientController(repo=auth_ctrl.patient_repo, current_user=current_user)
    caisse_repo = CaisseRepository(session=db)
    return CaisseController(repo=caisse_repo, current_user=current_user)


@router.get("/", response_model=List[Any])
def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    raws = caisse_ctrl.list_transactions()
    start = (page - 1) * per_page
    end = start + per_page
    page_items = raws[start:end]
    return [normalize_caisse_data(x) for x in page_items]


@router.get("/{transaction_id}", response_model=Any)
def get_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        tx = caisse_ctrl.get_transaction(transaction_id)
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/patient/{patient_id}", response_model=List[Any])
def list_for_patient(patient_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    items = caisse_ctrl.list_for_patient(patient_id)
    return [normalize_caisse_data(x) for x in items]


@router.get("/daily_total", response_model=float)
def daily_total(for_date: date = Query(...), caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    return caisse_ctrl.get_daily_total(for_date)


@router.get("/total", response_model=float)
def total_transactions(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    return caisse_ctrl.get_total_transactions(date_from=date_from, date_to=date_to)


@router.post("/", response_model=Any, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: dict = Body(...),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        tx = caisse_ctrl.create_transaction(data)
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try:
            caisse_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            caisse_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError creating transaction: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la création de la transaction")


@router.put("/{transaction_id}", response_model=Any)
def update_transaction(
    transaction_id: int,
    data: dict = Body(...),
    caisse_ctrl: CaisseController = Depends(get_caisse_controller),
):
    try:
        tx = caisse_ctrl.update_transaction(transaction_id, data)
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction non trouvée après mise à jour")
        return normalize_caisse_data(tx)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except IntegrityError as ie:
        try:
            caisse_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after IntegrityError")
        raise translate_integrity_error(ie)
    except SQLAlchemyError as e:
        try:
            caisse_ctrl.repo.session.rollback()
        except Exception:
            logger.exception("Rollback failed after SQLAlchemyError")
        logger.exception("SQLAlchemyError updating transaction: %s", e)
        raise HTTPException(status_code=500, detail="Erreur serveur lors de la mise à jour de la transaction")


@router.post("/{transaction_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        caisse_ctrl.cancel_transaction(transaction_id)
        return {"detail": "Annulé"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, caisse_ctrl: CaisseController = Depends(get_caisse_controller)):
    try:
        caisse_ctrl.delete_transaction(transaction_id)
        return None
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
