# api_backend/backend_app/routes/stock/stock_endpoints.py
"""Routeur /stock : lots, receptions, avaries, demandes d'ajustement, historique.

Garde de role PAR ROUTE (pas de garde globale). Erreurs du controleur :
StockNotFoundError -> 404, ValueError -> 422, PermissionError -> 403, StockConflictError -> 409.
P4 : Assistant force a mine_only sur receptions/avaries ; secretaire force a mine_only
sur les demandes d'ajustement ; admin et StockController voient tout.
"""
from contextlib import contextmanager
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.stock_controller import StockController, StockLineError
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_repo import StockConflictError, StockNotFoundError, StockRepository
from .stock_schemas import (
    AdjustmentCreate, AdjustmentReject, IncidentCreate, LotCreate, LotDeliver,
    ReceiptCreate, ReceiptLinesUpdate, RejectBody,
)

router = APIRouter(prefix="/stock", tags=["Stock"])

CREATORS = ("Assistant", "admin")
READERS = ("Assistant", "admin", "StockController")
CHECKERS = ("StockController", "admin")
_SEE_ALL = {"admin", "stockcontroller"}  # codes canoniques (user.roles)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_stock_controller(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StockController:
    # Les TROIS depots sont reellement injectes (notifications comprises).
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), current_user)


@contextmanager
def _errors():
    try:
        yield
    except StockLineError as e:  # sous-classe de ValueError : avant ValueError
        raise HTTPException(status_code=422, detail=e.to_detail())
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StockConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


def _roles(user) -> set:
    return {r.strip().lower() for r in getattr(user, "roles", []) or [] if r}


def _sees_all(user) -> bool:
    return bool(_roles(user) & _SEE_ALL)


# ---------------- lots ----------------
@router.post("/lots", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required(*CREATORS))])
def create_lot(payload: LotCreate, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.create_lot(payload.model_dump())


@router.get("/lots", dependencies=[Depends(role_required(*READERS))])
def list_lots(status: Optional[str] = Query(None, max_length=20),
              ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.list_lots(status)


@router.post("/lots/{lot_id}/deliver", dependencies=[Depends(role_required(*CREATORS))])
def deliver_lot(lot_id: int, payload: Optional[LotDeliver] = None,
                ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.mark_lot_delivered(lot_id, payload.delivery_date if payload else None)


@router.post("/lots/{lot_id}/cancel", dependencies=[Depends(role_required(*CREATORS))])
def cancel_lot(lot_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.cancel_lot(lot_id)


# ---------------- receptions ----------------
@router.post("/receipts", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required(*CREATORS))])
def create_receipt(payload: ReceiptCreate, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        data = payload.model_dump()
        data["lines"] = [l.model_dump(exclude_unset=True) for l in payload.lines]
        return ctrl.create_receipt(data)


@router.get("/receipts", dependencies=[Depends(role_required(*READERS))])
def list_receipts(status: Optional[str] = Query(None, max_length=20), mine_only: bool = False,
                  current_user: Any = Depends(get_current_user),
                  ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.list_receipts(status, mine_only or not _sees_all(current_user))


@router.get("/receipts/{receipt_id}", dependencies=[Depends(role_required(*READERS))])
def get_receipt(receipt_id: int, current_user: Any = Depends(get_current_user),
                ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        r = ctrl.get_receipt(receipt_id)
    if not _sees_all(current_user) and r["created_by"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez consulter que vos propres réceptions.")
    return r


@router.put("/receipts/{receipt_id}/lines", dependencies=[Depends(role_required(*CHECKERS))])
def update_receipt_lines(receipt_id: int, payload: ReceiptLinesUpdate,
                         ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.update_receipt_lines(receipt_id, [l.model_dump(exclude_none=True) for l in payload.lines])


@router.post("/receipts/{receipt_id}/validate", dependencies=[Depends(role_required(*CHECKERS))])
def validate_receipt(receipt_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.validate_receipt(receipt_id)


@router.post("/receipts/{receipt_id}/reject", dependencies=[Depends(role_required(*CHECKERS))])
def reject_receipt(receipt_id: int, payload: RejectBody, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.reject_receipt(receipt_id, payload.reason)


@router.post("/receipts/{receipt_id}/cancel", dependencies=[Depends(role_required(*CREATORS))])
def cancel_receipt(receipt_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.cancel_receipt(receipt_id)


# ---------------- avaries ----------------
@router.post("/incidents", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required(*CREATORS))])
def create_incident(payload: IncidentCreate, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.create_incident(payload.model_dump())


@router.get("/incidents", dependencies=[Depends(role_required(*READERS))])
def list_incidents(status: Optional[str] = Query(None, max_length=20), mine_only: bool = False,
                   current_user: Any = Depends(get_current_user),
                   ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.list_incidents(status, mine_only or not _sees_all(current_user))


@router.post("/incidents/{incident_id}/validate", dependencies=[Depends(role_required(*CHECKERS))])
def validate_incident(incident_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.validate_incident(incident_id)


@router.post("/incidents/{incident_id}/reject", dependencies=[Depends(role_required(*CHECKERS))])
def reject_incident(incident_id: int, payload: RejectBody, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.reject_incident(incident_id, payload.reason)


@router.post("/incidents/{incident_id}/cancel", dependencies=[Depends(role_required(*CREATORS))])
def cancel_incident(incident_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.cancel_incident(incident_id)


# ---------------- demandes d'ajustement ----------------
@router.post("/adjustment-requests", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required("secretaire"))])
def create_adjustment_request(payload: AdjustmentCreate, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.create_adjustment_request(payload.model_dump())


@router.get("/adjustment-requests", dependencies=[Depends(role_required("secretaire", "admin"))])
def list_adjustment_requests(status: Optional[str] = Query(None, max_length=20), mine_only: bool = False,
                             current_user: Any = Depends(get_current_user),
                             ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        see_all = "admin" in _roles(current_user)
        return ctrl.list_adjustment_requests(status, mine_only or not see_all)


@router.post("/adjustment-requests/{request_id}/cancel", dependencies=[Depends(role_required("secretaire"))])
def cancel_adjustment_request(request_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.cancel_adjustment(request_id)


@router.post("/adjustment-requests/{request_id}/approve", dependencies=[Depends(role_required("admin"))])
def approve_adjustment_request(request_id: int, ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.approve_adjustment(request_id)


@router.post("/adjustment-requests/{request_id}/reject", dependencies=[Depends(role_required("admin"))])
def reject_adjustment_request(request_id: int, payload: AdjustmentReject,
                              ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.reject_adjustment(request_id, payload.note)


# ---------------- liste minimale des produits (filtres) ----------------
@router.get("/products", dependencies=[Depends(role_required("StockController", "admin", "Assistant"))])
def list_products_lookup(ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.list_products_lookup()


# ---------------- historique des mouvements ----------------
@router.get("/movements", dependencies=[Depends(role_required("StockController", "admin", "Assistant"))])
def list_movements(product_id: Optional[int] = Query(None, gt=0),
                   movement_type: Optional[str] = Query(None, max_length=50),
                   date_from: Optional[date] = None, date_to: Optional[date] = None,
                   page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
                   ctrl: StockController = Depends(get_stock_controller)):
    with _errors():
        return ctrl.list_movements(product_id, movement_type, date_from, date_to, page, per_page)
