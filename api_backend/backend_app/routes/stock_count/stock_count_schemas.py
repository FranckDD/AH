# api_backend/backend_app/routes/stock_count/stock_count_schemas.py
"""Entrees strictes du routeur /stock-counts.

StrictInt : bool, float (y compris 2.0 en JSON) et chaines numeriques refuses (422).
Pas de str_strip_whitespace : l'observation est nettoyee par le controleur (validate_counts).
"""
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt

INT32_MAX = 2**31 - 1


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartBody(_Strict):
    scope: Literal["tous", "selection"] = "tous"


class CountLine(_Strict):
    product_id: Annotated[StrictInt, Field(ge=1, le=INT32_MAX)]
    counted_qty: Annotated[StrictInt, Field(ge=0, le=10_000_000)]
    observation: Optional[str] = Field(None, max_length=1000)
    # heure de comptage de la ligne (ISO avec decalage, ou UTC naif) ; analysee par le controleur (422 si invalide)
    counted_at: Optional[str] = Field(None, max_length=40)


class SubmitBody(_Strict):
    lines: List[CountLine] = Field(min_length=1, max_length=5000)
    # heure du navigateur a l envoi (ISO) : sert a corriger l ecart d horloge des counted_at
    client_now: Optional[str] = Field(None, max_length=40)


class SettingsBody(_Strict):
    interval_days: Annotated[StrictInt, Field(ge=1, le=365)]
