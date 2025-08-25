from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional

class PharmacyCreate(BaseModel):
    drug_name: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=0)
    threshold: int = Field(..., ge=0)
    medication_type: str = Field(..., min_length=1)
    forme: str = Field("Autre")
    dosage_mg: Optional[float] = Field(None, ge=0)
    expiry_date: Optional[date] = None
    prescribed_by: Optional[int] = None
    name_dr: Optional[str] = None

class PharmacyUpdate(BaseModel):
    drug_name: Optional[str] = Field(None, min_length=1)
    quantity: Optional[int] = Field(None, ge=0)
    threshold: Optional[int] = Field(None, ge=0)
    medication_type: Optional[str] = Field(None, min_length=1)
    forme: Optional[str] = None
    dosage_mg: Optional[float] = Field(None, ge=0)
    expiry_date: Optional[date] = None
    prescribed_by: Optional[int] = None
    name_dr: Optional[str] = None

class PharmacyResponse(BaseModel):
    medication_id: int
    patient_id: Optional[int] = None
    drug_name: str
    quantity: int
    threshold: int
    medication_type: str
    forme: str
    dosage_mg: Optional[float] = None
    expiry_date: Optional[datetime] = None
    stock_status: str
    prescribed_by: Optional[int] = None
    name_dr: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("expiry_date", mode="before")
    @classmethod
    def parse_expiry_date(cls, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime(value.year, value.month, value.day)
        return value