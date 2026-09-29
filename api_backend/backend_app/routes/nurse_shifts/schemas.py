# api_backend/backend_app/routes/nurse_shifts/schemas.py
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field


class NurseShiftCreate(BaseModel):
    shift_date: date
    shift_type: str = Field(..., description="MATIN | APRES_MIDI | NUIT")
    nurse_id: int


class NurseShiftOut(BaseModel):
    id: int
    shift_date: date
    shift_type: str
    nurse_id: int
    nurse_name: Optional[str] = None
    created_by: int
    created_by_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActiveNurseOut(BaseModel):
    user_id: int
    full_name: str
    is_head_nurse: bool
