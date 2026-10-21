# api_backend/backend_app/routes/stock/stock_schemas.py
"""Entrees strictes du routeur /stock (bornes alignees sur les colonnes de la migration 019)."""
from datetime import date
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_QTY = 1_000_000

Qty = Annotated[int, Field(strict=True, ge=0, le=MAX_QTY)]
PositiveQty = Annotated[int, Field(strict=True, gt=0, le=MAX_QTY)]
Id = Annotated[int, Field(strict=True, gt=0)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


def _opt(max_len: int):
    return Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=max_len)]]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LotCreate(_Strict):
    product_id: Id
    quantity_produced: PositiveQty
    production_date: date
    delivery_date: Optional[date] = None
    expiry_date: Optional[date] = None
    producer: _opt(150) = None


class LotDeliver(_Strict):
    delivery_date: Optional[date] = None


class ReceiptLineIn(_Strict):
    product_id: Optional[Id] = None
    qty_expected: Optional[Qty] = None
    qty_good: Qty = 0
    qty_damaged: Qty = 0
    qty_lost: Qty = 0
    qty_defective: Qty = 0
    lot_number: _opt(30) = None
    expiry_date: Optional[date] = None


class ReceiptCreate(_Strict):
    origin: Literal["fabrication", "fournisseur"]
    production_lot_id: Optional[Id] = None
    supplier: _opt(150) = None
    delivery_ref: _opt(100) = None
    received_date: date
    lines: List[ReceiptLineIn] = Field(min_length=1, max_length=500)


class ReceiptLineCorrection(_Strict):
    id: Id
    qty_good: Optional[Qty] = None
    qty_damaged: Optional[Qty] = None
    qty_lost: Optional[Qty] = None
    qty_defective: Optional[Qty] = None


class ReceiptLinesUpdate(_Strict):
    lines: List[ReceiptLineCorrection] = Field(min_length=1, max_length=500)


class RejectBody(_Strict):
    reason: Reason


class IncidentCreate(_Strict):
    product_id: Id
    kind: Literal["endommage", "perdu", "defectueux"]
    quantity: PositiveQty
    reason: Reason
    incident_date: date


class AdjustmentCreate(_Strict):
    product_id: Id
    kind: Literal["reapprovisionnement", "correction"]
    quantity: Qty
    reason: Reason


class AdjustmentReject(_Strict):
    note: Reason
