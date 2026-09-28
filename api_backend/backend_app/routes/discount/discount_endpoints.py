# api_backend/backend_app/routes/discount/discount_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import Any, List, Dict, Optional
from datetime import date

from ...database import SessionLocal
from ...rate_limit import limiter
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from repositories.discount_request_repo import DiscountRequestRepository
from models.discount_request import DiscountRequest
from repositories.caisse_repo import CaisseRepository
from repositories.notification_repo import NotificationRepository
from repositories.audit_repo import AuditRepository
from controller.discount_request_controller import DiscountRequestController
from .discount_schemas import DiscountRequestCreate, DiscountRequestCancel, DiscountRequestDecide

router = APIRouter(prefix="/discount-requests", tags=["discount-requests"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_discount_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> DiscountRequestController:
    return DiscountRequestController(
        repo=DiscountRequestRepository(db),
        caisse_repo=CaisseRepository(db),
        notification_repo=NotificationRepository(db),
        audit_repo=AuditRepository(db),
        current_user=current_user,
    )


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_required("secretaire"))])
def create_discount_request(payload: DiscountRequestCreate, ctrl: DiscountRequestController = Depends(get_discount_controller)):
    try:
        req = ctrl.create_request(payload.invoice_data, payload.requested_to)
        return {"id": req.id, "transaction_id": req.transaction_id, "status": req.status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/{request_id}/cancel", dependencies=[Depends(role_required("secretaire"))])
def cancel_discount_request(request_id: int, payload: DiscountRequestCancel, ctrl: DiscountRequestController = Depends(get_discount_controller)):
    try:
        req = ctrl.cancel_and_reassign(request_id, payload.new_requested_to)
        return {"id": req.id, "status": req.status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))


def _items_summary(tx) -> str:
    """Resume court des lignes de facture (pas de nom produit/examen en base
    cote CaisseItem, seulement type+quantite) - suffisant pour que le manager
    ne decide plus a l'aveugle sans exiger de jointure supplementaire."""
    if not tx or not tx.items:
        return ""
    return ", ".join(f"{it.item_type} x{it.quantity}" for it in tx.items)


@router.get("/pending", dependencies=[Depends(role_required("admin", "promoteur"))])
def list_pending_discount_requests(ctrl: DiscountRequestController = Depends(get_discount_controller)):
    pending = ctrl.repo.list_pending_for_recipient(ctrl.user.user_id)
    return [
        {
            "id": r.id, "transaction_id": r.transaction_id, "original_amount": float(r.original_amount),
            "requested_by": r.requested_by, "created_at": r.created_at.isoformat() if r.created_at else None,
            "patient_label": r.transaction.patient_label if r.transaction else None,
            "items_summary": _items_summary(r.transaction),
            "requested_by_name": (r.requester.full_name or r.requester.username) if r.requester else None,
        }
        for r in pending
    ]


def _scope_requested_by(ctrl: DiscountRequestController) -> Optional[int]:
    """secretaire -> ne voit que ses propres demandes (moindre privilege) ;
    admin/promoteur -> vue de supervision complete (decision brainstorming
    2026-09-28, ecran d'historique/KPI)."""
    return ctrl.user.user_id if "secretaire" in ctrl.user.roles else None


def _request_to_history_dict(r: DiscountRequest) -> Dict[str, Any]:
    reduced_amount = 0.0
    if r.status == "approved" and r.decision_percent:
        reduced_amount = float(r.original_amount) * (r.decision_percent / 100)
    return {
        "id": r.id,
        "transaction_id": r.transaction_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "status": r.status,
        "patient_label": r.transaction.patient_label if r.transaction else None,
        "requested_by_name": (r.requester.full_name or r.requester.username) if r.requester else None,
        "requested_to_name": (r.recipient.full_name or r.recipient.username) if r.recipient else None,
        "decided_by_name": (r.decider.full_name or r.decider.username) if r.decider else None,
        "original_amount": float(r.original_amount),
        "decision_percent": r.decision_percent,
        "decision_echelonne_deadline": r.decision_echelonne_deadline.isoformat() if r.decision_echelonne_deadline else None,
        "reduced_amount": reduced_amount,
    }


@router.get("/history", dependencies=[Depends(role_required("secretaire", "admin", "promoteur"))])
def list_discount_request_history(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    ctrl: DiscountRequestController = Depends(get_discount_controller),
):
    requested_by = _scope_requested_by(ctrl)
    items, total = ctrl.repo.list_history(
        requested_by=requested_by, date_from=date_from, date_to=date_to,
        status=status_filter, page=page, per_page=per_page,
    )
    return {
        "data": [_request_to_history_dict(r) for r in items],
        "total": total, "page": page, "per_page": per_page,
    }


@router.get("/kpi", dependencies=[Depends(role_required("secretaire", "admin", "promoteur"))])
def get_discount_request_kpi(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    ctrl: DiscountRequestController = Depends(get_discount_controller),
):
    requested_by = _scope_requested_by(ctrl)
    return ctrl.repo.kpi(requested_by=requested_by, date_from=date_from, date_to=date_to)


@router.post("/{request_id}/decide", dependencies=[Depends(role_required("admin", "promoteur"))])
@limiter.limit("20/minute")  # garde-fou anti-abus large ; le vrai anti-bruteforce (mots de passe
# incorrects uniquement, ne compte plus les decisions reussies - residu corrige 2026-09-28)
# vit maintenant dans DiscountRequestController.decide_request via Redis.
def decide_discount_request(request: Request, request_id: int, payload: DiscountRequestDecide, ctrl: DiscountRequestController = Depends(get_discount_controller)):
    try:
        req = ctrl.decide_request(
            request_id, payload.password, payload.refuse,
            payload.decision_percent, payload.decision_echelonne_deadline,
        )
        return {"id": req.id, "status": req.status}
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
