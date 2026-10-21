# api_backend/backend_app/routes/lab_stock/lab_stock_schemas.py
"""Entrees strictes du routeur /lab-stock (bornes alignees sur la migration 021).

La validation metier (nom vide, seuil negatif, date passee, motif vide) reste dans le
controleur -> 422 ; ces schemas refusent surtout les champs inconnus (extra=forbid)."""
from datetime import date
from decimal import Decimal
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Threshold = Annotated[int, Field(strict=True, le=1_000_000)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductCreate(_Strict):
    name: str = Field(max_length=150)
    packaging: Optional[str] = Field(None, max_length=100)
    alert_threshold: Threshold = 0
    supplier: Optional[str] = Field(None, max_length=150)
    # toute valeur de quantite envoyee est refusee (extra=forbid) : le stock part de 0


class ProductUpdate(_Strict):
    name: Optional[str] = Field(None, max_length=150)
    packaging: Optional[str] = Field(None, max_length=100)
    alert_threshold: Optional[Threshold] = None
    supplier: Optional[str] = Field(None, max_length=150)
    is_active: Optional[bool] = None


class SignalBody(_Strict):
    level: Literal["bientot_fini", "fini"]


class OrderBody(_Strict):
    expected_date: date


class ReceiptLineIn(_Strict):
    # ni line_total ni total_amount : le serveur les calcule (extra=forbid les refuse)
    product_id: int
    ordered_qty: Optional[int] = Field(None, ge=0, le=1_000_000)
    received_qty: int = Field(le=1_000_000)
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    lot_number: str = Field(max_length=50)
    expiry_date: date
    note: Optional[str] = Field(None, max_length=2000)


class ReceiptCreate(_Strict):
    invoice_number: str = Field(max_length=100)
    supplier: str = Field(max_length=150)
    delivery_date: date
    lines: List[ReceiptLineIn] = Field(min_length=1, max_length=200)


class CancelBody(_Strict):
    reason: str = Field(max_length=2000)


class CountLineIn(_Strict):
    product_id: int
    previous_qty: int = Field(ge=0, le=1_000_000)
    counted_qty: int = Field(ge=0, le=1_000_000)


class CountBody(_Strict):
    lines: List[CountLineIn] = Field(min_length=1, max_length=500)
