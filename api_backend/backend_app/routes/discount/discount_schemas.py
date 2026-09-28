# api_backend/backend_app/routes/discount/discount_schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import date


class DiscountRequestCreate(BaseModel):
    invoice_data: Dict[str, Any]
    requested_to: int


class DiscountRequestCancel(BaseModel):
    new_requested_to: int


class DiscountRequestDecide(BaseModel):
    password: str
    refuse: bool = False
    decision_percent: Optional[int] = None
    decision_echelonne_deadline: Optional[date] = None
