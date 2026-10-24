# api_backend/backend_app/routes/cash_closure/cash_closure_schemas.py
"""Corps stricts de /cash-closure et /payment-modes : champs inconnus refuses, montants en
chaines Decimal (jamais de float), validation metier dans le controleur."""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CountItem(_Strict):
    mode: StrictStr
    counted: StrictStr
    comment: Optional[StrictStr] = None


class CloseBody(_Strict):
    counts: List[CountItem]
    # garde double onglet : valeur de GET /status ; obligatoire, null s'il n'y a encore aucune cloture
    last_closed_at: Optional[StrictStr]


class StartBody(_Strict):
    opening_cash: StrictStr


class ModeUpdate(_Strict):
    label: Optional[StrictStr] = None
    is_active: Optional[StrictBool] = None
    sort_order: Optional[StrictInt] = None


class CorrectionCreate(_Strict):
    mode_code: StrictStr
    amount_delta: StrictStr
    reason: StrictStr


class DecideBody(_Strict):
    approve: StrictBool
