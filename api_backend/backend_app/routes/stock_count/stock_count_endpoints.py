# api_backend/backend_app/routes/stock_count/stock_count_endpoints.py
"""Routeur /stock-counts : comptage physique du stock de la pharmacie (a l'aveugle).

Garde de role PAR ROUTE : ecriture COUNTERS (StockController seul), lecture READERS
(StockController, admin, promoteur), frequence SETTINGS_WRITERS (admin seul). Tout autre role : 403.
Erreurs du controleur : StockCountNotFoundError -> 404, StockCountConflictError -> 409,
PermissionError -> 403, ValueError -> 422.
Chemins fixes (/status, /settings, /requests) declares AVANT /{count_id}.
"""
from contextlib import contextmanager
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.stock_count_controller import (
    MAX_LIMIT, StockCountConflictError, StockCountController, StockCountNotFoundError,
    get_stock_count_controller,
)

from .stock_count_schemas import INT32_MAX, SettingsBody, StartBody, SubmitBody

router = APIRouter(prefix="/stock-counts", tags=["Comptage du stock"])

# comptage reserve au StockController (un admin ne peut pas approuver sa propre demande)
COUNTERS = ("StockController",)
READERS = ("StockController", "admin", "promoteur")
SETTINGS_WRITERS = ("admin",)

CountId = Path(ge=1, le=INT32_MAX)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_controller(current_user: Any = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> StockCountController:
    return get_stock_count_controller(db, current_user)


@contextmanager
def _errors():
    try:
        yield
    except StockCountNotFoundError as e:  # sous-classe de ValueError : avant ValueError
        raise HTTPException(status_code=404, detail=str(e))
    except StockCountConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required(*COUNTERS))])
def start_count(payload: StartBody, ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.start(payload.scope)


@router.get("/status", dependencies=[Depends(role_required(*READERS))])
def count_status(ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.status()


@router.get("/settings", dependencies=[Depends(role_required(*READERS))])
def get_settings(ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.get_settings()


@router.put("/settings", dependencies=[Depends(role_required(*SETTINGS_WRITERS))])
def set_settings(payload: SettingsBody, ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.set_interval(payload.interval_days)


@router.get("", dependencies=[Depends(role_required(*READERS))])
def list_counts(date_from: Optional[str] = Query(None, max_length=10),
                date_to: Optional[str] = Query(None, max_length=10),
                status_: Optional[str] = Query(None, alias="status", max_length=20),
                limit: int = Query(50, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0, le=INT32_MAX),
                mine: bool = Query(False),
                ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.list({"date_from": date_from, "date_to": date_to, "status": status_,
                          "limit": limit, "offset": offset, "mine": mine})


@router.get("/requests", dependencies=[Depends(role_required(*READERS))])
def my_requests(ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.my_requests()


@router.get("/{count_id}", dependencies=[Depends(role_required(*READERS))])
def get_count(count_id: int = CountId, ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.get(count_id)


@router.post("/{count_id}/submit", dependencies=[Depends(role_required(*COUNTERS))])
def submit_count(payload: SubmitBody, count_id: int = CountId,
                 ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.submit(count_id, [l.model_dump() for l in payload.lines], payload.client_now)


@router.post("/{count_id}/abandon", dependencies=[Depends(role_required(*COUNTERS))])
def abandon_count(count_id: int = CountId, ctrl: StockCountController = Depends(get_controller)):
    with _errors():
        return ctrl.abandon(count_id)
