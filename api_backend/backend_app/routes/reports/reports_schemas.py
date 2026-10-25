# api_backend/backend_app/routes/reports/reports_schemas.py
"""Entrees strictes du routeur /reports.

StrictInt : bool, float (y compris 3.0 en JSON) et chaines numeriques refuses (422).
"""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class SettingsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cancelled_sales_threshold: Annotated[StrictInt, Field(ge=1, le=1000)]
    adjustment_pending_days: Annotated[StrictInt, Field(ge=1, le=365)]
