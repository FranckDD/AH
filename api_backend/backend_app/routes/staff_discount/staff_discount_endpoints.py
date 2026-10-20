# api_backend/backend_app/routes/staff_discount/staff_discount_endpoints.py
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import SessionLocal
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user, role_required
from repositories.staff_discount_repo import StaffDiscountRepository
from repositories.audit_repo import AuditRepository
from controller.staff_discount_controller import StaffDiscountController

router = APIRouter(prefix="/staff-discount-rules", tags=["staff-discount-rules"])


class StaffDiscountRuleUpdate(BaseModel):
    min_invoice_amount: float = Field(ge=0, le=99_999_999.99, allow_inf_nan=False)
    rate_percent: int
    is_active: bool = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_staff_discount_controller(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> StaffDiscountController:
    return StaffDiscountController(
        repo=StaffDiscountRepository(db),
        current_user=current_user,
        audit_repo=AuditRepository(db),
    )


@router.get("", dependencies=[Depends(role_required("admin", "promoteur", "secretaire"))])
def list_staff_discount_rules(ctrl: StaffDiscountController = Depends(get_staff_discount_controller)):
    return ctrl.list_rules()


@router.put("/{category}", dependencies=[Depends(role_required("admin", "promoteur"))])
def update_staff_discount_rule(
    category: str,
    payload: StaffDiscountRuleUpdate,
    ctrl: StaffDiscountController = Depends(get_staff_discount_controller),
):
    try:
        return ctrl.update_rule(category, payload.min_invoice_amount, payload.rate_percent, payload.is_active)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
