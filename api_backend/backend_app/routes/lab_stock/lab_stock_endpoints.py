# api_backend/backend_app/routes/lab_stock/lab_stock_endpoints.py
"""Routeur /lab-stock : produits du labo, signalement, demandes « a commander ».

Garde de role PAR ROUTE (matrice du plan, constantes ci-dessous ; aucun autre role).
Erreurs du controleur : LabStockNotFoundError -> 404, LabStockConflictError -> 409,
PermissionError -> 403, ValueError -> 422.
Tasks 3-5 : RECEIVERS (receptions), COUNTERS (comptage), SPENDERS (depenses), RECEIPT_CANCEL.
"""
from contextlib import contextmanager
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.lab_stock_controller import LabStockController, LabStockCountConflictError
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockConflictError, LabStockNotFoundError, LabStockRepository
from repositories.notification_repo import NotificationRepository
from datetime import date

from .lab_stock_schemas import CancelBody, CountBody, OrderBody, ProductCreate, ProductUpdate, ReceiptCreate, SignalBody

router = APIRouter(prefix="/lab-stock", tags=["Stock labo"])

# ---- matrice des roles (codes role_required) ----
READERS = ("laborantin", "StockController", "promoteur", "ToxicoManager", "admin")
PRODUCT_WRITERS = ("laborantin", "StockController", "admin")
RECEIVERS = ("StockController", "promoteur", "admin")
COUNTERS = ("laborantin", "admin")
SIGNALERS = COUNTERS
ORDERERS = ("promoteur", "ToxicoManager", "admin")
SPENDERS = ("promoteur", "ToxicoManager", "admin")
RECEIPT_CANCELLERS = ("admin",)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_lab_stock_controller(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LabStockController:
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), current_user)


@contextmanager
def _errors():
    try:
        yield
    except LabStockCountConflictError as e:
        raise HTTPException(status_code=409, detail={"message": str(e), "conflicts": e.conflicts})
    except LabStockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LabStockConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------- produits ----------------
@router.get("/products", dependencies=[Depends(role_required(*READERS))])
def list_products(include_inactive: bool = False,
                  ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.list_products(include_inactive)


@router.post("/products", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*PRODUCT_WRITERS))])
def create_product(payload: ProductCreate, ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.create_product(payload.model_dump())


@router.put("/products/{product_id}", dependencies=[Depends(role_required(*PRODUCT_WRITERS))])
def update_product(product_id: int, payload: ProductUpdate,
                   ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.update_product(product_id, payload.model_dump(exclude_unset=True))


@router.post("/products/{product_id}/signal", dependencies=[Depends(role_required(*SIGNALERS))])
def signal_product(product_id: int, payload: SignalBody,
                   ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.signal(product_id, payload.level)


# ---------------- demandes / commande ----------------
@router.get("/requests", dependencies=[Depends(role_required(*READERS))])
def list_requests(status: Optional[str] = Query(None, max_length=20),
                  ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.list_requests(status)


@router.post("/requests/{request_id}/order", dependencies=[Depends(role_required(*ORDERERS))])
def order_request(request_id: int, payload: OrderBody,
                  ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.mark_ordered(request_id, payload.expected_date)


@router.put("/requests/{request_id}/order", dependencies=[Depends(role_required(*ORDERERS))])
def update_order_date(request_id: int, payload: OrderBody,
                      ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.update_expected_date(request_id, payload.expected_date)


@router.post("/requests/{request_id}/cancel", dependencies=[Depends(role_required(*ORDERERS))])
def cancel_request(request_id: int, payload: CancelBody,
                   ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.cancel_request(request_id, payload.reason)


# ---------------- receptions ----------------
@router.post("/receipts", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*RECEIVERS))])
def create_receipt(payload: ReceiptCreate, ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.create_receipt(payload.model_dump())


@router.get("/receipts", dependencies=[Depends(role_required(*READERS))])
def list_receipts(supplier: Optional[str] = Query(None, max_length=150),
                  date_from: Optional[date] = Query(None, alias="from"),
                  date_to: Optional[date] = Query(None, alias="to"),
                  ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.list_receipts({"supplier": supplier, "from": date_from, "to": date_to})


@router.get("/receipts/{receipt_id}", dependencies=[Depends(role_required(*READERS))])
def get_receipt(receipt_id: int, ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.get_receipt(receipt_id)


@router.post("/receipts/{receipt_id}/cancel", dependencies=[Depends(role_required(*RECEIPT_CANCELLERS))])
def cancel_receipt(receipt_id: int, payload: CancelBody,
                   ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.cancel_receipt(receipt_id, payload.reason)


# ---------------- comptage / alertes / historique ----------------
@router.post("/counts", dependencies=[Depends(role_required(*COUNTERS))])
def submit_count(payload: CountBody, ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.submit_count([ln.model_dump() for ln in payload.lines])


@router.get("/counts/status", dependencies=[Depends(role_required(*READERS))])
def count_status(ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.get_count_status()


@router.get("/alerts", dependencies=[Depends(role_required(*READERS))])
def get_alerts(ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.get_alerts()


@router.get("/movements", dependencies=[Depends(role_required(*READERS))])
def list_movements(product_id: Optional[int] = None, limit: int = Query(200, ge=1, le=1000),
                   ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.list_movements(product_id, limit)


# ---------------- depenses ----------------
@router.get("/expenses", dependencies=[Depends(role_required(*SPENDERS))])
def expenses(date_from: Optional[date] = Query(None, alias="from"),
             date_to: Optional[date] = Query(None, alias="to"),
             ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.expenses(date_from, date_to)


@router.get("/products/{product_id}/price-history", dependencies=[Depends(role_required(*SPENDERS))])
def price_history(product_id: int, ctrl: LabStockController = Depends(get_lab_stock_controller)):
    with _errors():
        return ctrl.price_history(product_id)
