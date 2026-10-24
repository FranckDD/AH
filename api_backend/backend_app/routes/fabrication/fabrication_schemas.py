# api_backend/backend_app/routes/fabrication/fabrication_schemas.py
"""Entrees strictes du routeur /fabrication (bornes alignees sur la migration 023).

Quantites Numeric(12,3), couts Numeric(12,2), en Decimal (jamais float). Champs inconnus refuses.
"""
from datetime import date
from decimal import Decimal
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt

Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3, allow_inf_nan=False)]
Cost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)]
Threshold = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=3, allow_inf_nan=False)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------------- intrants ----------------
class IntrantCreate(_Strict):
    name: str = Field(min_length=1, max_length=150)
    unit: str = Field(min_length=1, max_length=20)
    is_container: bool = False


class IntrantUpdate(_Strict):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    unit: Optional[str] = Field(None, min_length=1, max_length=20)
    is_container: Optional[bool] = None
    is_active: Optional[bool] = None


class ThresholdBody(_Strict):
    value: Threshold


# ---------------- achats ----------------
class PurchaseCreate(_Strict):
    intrant_id: int
    supplier: Optional[str] = Field(None, max_length=150)
    delivery_ref: Optional[str] = Field(None, max_length=100)
    purchase_date: date
    quantity: Quantity
    unit_cost: Cost


class PurchaseUpdate(_Strict):
    supplier: Optional[str] = Field(None, max_length=150)
    delivery_ref: Optional[str] = Field(None, max_length=100)
    purchase_date: Optional[date] = None
    quantity: Optional[Quantity] = None
    unit_cost: Optional[Cost] = None


class CancelBody(_Strict):
    reason: str = Field(min_length=1, max_length=500)


# ---------------- lots ----------------
Count = Annotated[int, Field(ge=0, le=2_000_000_000, strict=True)]
LostQty = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=3, allow_inf_nan=False)]


class ConsumptionItem(_Strict):
    purchase_id: int
    quantity: Quantity


class BatchCreate(_Strict):
    product_id: int
    production_date: date
    producer_name: Optional[str] = Field(None, max_length=150)


class BatchUpdate(_Strict):
    product_id: Optional[int] = None
    production_date: Optional[date] = None
    producer_name: Optional[str] = Field(None, max_length=150)
    consumptions: Optional[List[ConsumptionItem]] = None


class BatchFinish(_Strict):
    qty_good: Count
    qty_damaged: Count = 0
    qty_rejected: Count = 0
    liquid_lost: LostQty = Decimal("0")


class BatchShip(_Strict):
    delivery_date: date
    expiry_date: Optional[date] = None
    justification: Optional[str] = Field(None, max_length=5000)


# ---------------- sorties declarees ----------------
class OutputCreate(_Strict):
    """Motif strict, sans rognage ni casse : ' autre ' et 'Echantillon' -> 422 (str_strip_whitespace
    desactive ici). quantity : entier JSON strict (2.5, 2.0, "2", true -> 422)."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    reason: Literal["echantillon", "autre"]
    quantity: Annotated[StrictInt, Field(ge=1, le=1_000_000)]
    note: Optional[str] = Field(None, max_length=2000)


class OutputCancel(_Strict):
    reason: str = Field(min_length=1, max_length=500)  # aligne sur le controleur (_text ..., 500)


# ---------------- reglages ----------------
class SettingsUpdate(_Strict):
    tolerance_pct: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2,
                                            allow_inf_nan=False)]
    stale_days: Annotated[int, Field(gt=0, le=3650, strict=True)]
