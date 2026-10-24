# api_backend/backend_app/routes/fabrication/fabrication_endpoints.py
"""Routeur /fabrication : intrants et achats d'intrants.

Garde de role PAR ROUTE : lecture READERS, ecriture WRITERS (ProductionManager seul),
seuil d'un intrant SETTINGS_WRITERS (admin seul). Tout autre role : 403.
Erreurs du controleur : FabricationNotFoundError -> 404, FabricationConflictError -> 409,
PermissionError -> 403, ValueError -> 422.
Lots et consommations (tache 4) : section a la suite.
"""
from contextlib import contextmanager
from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from controller.fabrication_controller import (
    FabricationConflictError, FabricationController, FabricationNotFoundError,
)
from repositories.fabrication_repo import FabricationJustificationRequired
from repositories.audit_repo import AuditRepository
from repositories.fabrication_repo import FabricationRepository

from .fabrication_schemas import (
    BatchCreate, BatchFinish, BatchShip, BatchUpdate, CancelBody, OutputCancel, OutputCreate, SettingsUpdate, IntrantCreate, IntrantUpdate, PurchaseCreate, PurchaseUpdate, ThresholdBody,
)

router = APIRouter(prefix="/fabrication", tags=["Fabrication"])

# ---- matrice des roles (codes role_required) ----
READERS = ("ProductionManager", "promoteur", "admin")
WRITERS = ("ProductionManager",)
SETTINGS_WRITERS = ("admin",)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_fabrication_controller(
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FabricationController:
    return FabricationController(FabricationRepository(db), AuditRepository(db), current_user)


@contextmanager
def _errors():
    try:
        yield
    except FabricationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FabricationConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except FabricationJustificationRequired as e:
        raise HTTPException(status_code=422, detail={"code": "justification_required", "message": str(e)})
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------- intrants ----------------
@router.get("/intrants", dependencies=[Depends(role_required(*READERS))])
def list_intrants(include_inactive: bool = False,
                  ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.list_intrants(include_inactive)


@router.post("/intrants", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*WRITERS))])
def create_intrant(payload: IntrantCreate, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.create_intrant(payload.model_dump())


@router.put("/intrants/{intrant_id}", dependencies=[Depends(role_required(*WRITERS))])
def update_intrant(intrant_id: int, payload: IntrantUpdate,
                   ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.update_intrant(intrant_id, payload.model_dump(exclude_unset=True))


@router.put("/intrants/{intrant_id}/threshold", dependencies=[Depends(role_required(*SETTINGS_WRITERS))])
def set_threshold(intrant_id: int, payload: ThresholdBody,
                  ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.set_threshold(intrant_id, payload.value)


# ---------------- achats ----------------
@router.get("/purchases", dependencies=[Depends(role_required(*READERS))])
def list_purchases(intrant_id: Optional[int] = Query(None),
                   date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
                   ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.list_purchases(intrant_id, date_from, date_to)


@router.post("/purchases", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*WRITERS))])
def create_purchase(payload: PurchaseCreate, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.create_purchase(payload.model_dump())


@router.put("/purchases/{purchase_id}", dependencies=[Depends(role_required(*WRITERS))])
def update_purchase(purchase_id: int, payload: PurchaseUpdate,
                    ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.update_purchase(purchase_id, payload.model_dump(exclude_unset=True))


@router.post("/purchases/{purchase_id}/cancel", dependencies=[Depends(role_required(*WRITERS))])
def cancel_purchase(purchase_id: int, payload: CancelBody,
                    ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.cancel_purchase(purchase_id, payload.reason)


# ---------------- lots ----------------
@router.get("/batches", dependencies=[Depends(role_required(*READERS))])
def list_batches(status_filter: Optional[str] = Query(None, alias="status"),
                 date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
                 ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.list_batches(status_filter, date_from, date_to)


@router.post("/batches", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*WRITERS))])
def create_batch(payload: BatchCreate, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.create_batch(payload.product_id, payload.production_date, payload.producer_name)


@router.get("/batches/{batch_id}", dependencies=[Depends(role_required(*READERS))])
def get_batch(batch_id: int, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.get_batch(batch_id)


@router.put("/batches/{batch_id}", dependencies=[Depends(role_required(*WRITERS))])
def update_batch(batch_id: int, payload: BatchUpdate,
                 ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.update_batch(batch_id, payload.model_dump(exclude_unset=True))


@router.post("/batches/{batch_id}/start", dependencies=[Depends(role_required(*WRITERS))])
def start_batch(batch_id: int, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.start_batch(batch_id)


@router.post("/batches/{batch_id}/finish", dependencies=[Depends(role_required(*WRITERS))])
def finish_batch(batch_id: int, payload: BatchFinish,
                 ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.finish_batch(batch_id, payload.qty_good, payload.qty_damaged,
                                 payload.qty_rejected, payload.liquid_lost)


@router.post("/batches/{batch_id}/reopen", dependencies=[Depends(role_required(*WRITERS))])
def reopen_batch(batch_id: int, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.reopen_batch(batch_id)


@router.post("/batches/{batch_id}/cancel", dependencies=[Depends(role_required(*WRITERS))])
def cancel_batch(batch_id: int, payload: CancelBody,
                 ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.cancel_batch(batch_id, payload.reason)


@router.post("/batches/{batch_id}/ship", dependencies=[Depends(role_required(*WRITERS))])
def ship_batch(batch_id: int, payload: BatchShip,
               ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.ship_batch(batch_id, payload.delivery_date, payload.expiry_date,
                               payload.justification)


# ---------------- sorties declarees ----------------
MAX_ID = 2**31 - 1  # identifiants de chemin bornes (Integer Postgres)


@router.post("/batches/{batch_id}/outputs", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(role_required(*WRITERS))])
def declare_output(payload: OutputCreate, batch_id: int = Path(ge=1, le=MAX_ID),
                   ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.declare_output(batch_id, payload.reason, payload.quantity, payload.note)


@router.post("/batches/{batch_id}/outputs/{output_id}/cancel", dependencies=[Depends(role_required(*WRITERS))])
def cancel_output(payload: OutputCancel, batch_id: int = Path(ge=1, le=MAX_ID), output_id: int = Path(ge=1, le=MAX_ID),
                  ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.cancel_output(batch_id, output_id, payload.reason)


@router.get("/outputs", dependencies=[Depends(role_required(*READERS))])
def list_outputs(date_from: Optional[date] = Query(None), date_to: Optional[date] = Query(None),
                 reason: Optional[str] = Query(None),
                 ctrl: FabricationController = Depends(get_fabrication_controller)):
    """200 lignes au plus (plafond du controleur), les plus recentes d'abord."""
    with _errors():
        return ctrl.list_outputs(date_from, date_to, reason)


# ---------------- reglages ----------------
@router.get("/settings", dependencies=[Depends(role_required(*READERS))])
def get_settings(ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.get_settings()


@router.put("/settings", dependencies=[Depends(role_required(*SETTINGS_WRITERS))])
def update_settings(payload: SettingsUpdate,
                    ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.update_settings(payload.tolerance_pct, payload.stale_days)


# ---------------- anomalies, resume, cout, tracabilite (lecture) ----------------
@router.get("/anomalies", dependencies=[Depends(role_required(*READERS))])
def list_anomalies(ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.list_anomalies()


@router.get("/summary", dependencies=[Depends(role_required(*READERS))])
def summary(ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.summary()


@router.get("/products", dependencies=[Depends(role_required(*READERS))])
def list_products(ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.list_products()


@router.get("/products/{product_id}/cost", dependencies=[Depends(role_required(*READERS))])
def cost_by_product(product_id: int, ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        return ctrl.cost_by_product(product_id)


@router.get("/trace/production-lot/{production_lot_id}", dependencies=[Depends(role_required(*READERS))])
def trace_production_lot(production_lot_id: int,
                         ctrl: FabricationController = Depends(get_fabrication_controller)):
    with _errors():
        out = ctrl.trace_production_lot(production_lot_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Ce lot ne vient pas de la Fabrication.")
    return out
