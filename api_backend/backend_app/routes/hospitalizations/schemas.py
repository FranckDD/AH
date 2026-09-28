from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class HospitalizationAdmit(BaseModel):
    patient_id: int
    admission_reason: Optional[str] = None


class HospitalizationStatusCreate(BaseModel):
    status: str = Field(..., description="AMELIORATION | STABLE | AGGRAVATION")
    note: Optional[str] = None


class HospitalizationDischarge(BaseModel):
    discharge_disposition: str = Field(
        ..., description="GUERI | TRANSFERE | SORTIE_CONTRE_AVIS_MEDICAL | DECES"
    )
    discharge_note: Optional[str] = None


class HospitalizationStatusUpdateOut(BaseModel):
    id: int
    status: str
    note: Optional[str] = None
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class HospitalizationOut(BaseModel):
    id: int
    patient_id: int
    admitted_at: datetime
    admitted_by: int
    admission_reason: Optional[str] = None
    discharged_at: Optional[datetime] = None
    discharge_disposition: Optional[str] = None
    discharge_note: Optional[str] = None
    discharged_by: Optional[int] = None
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    status_updates: List[HospitalizationStatusUpdateOut] = []

    model_config = {"from_attributes": True}


class HospitalizationCountOut(BaseModel):
    count: int
