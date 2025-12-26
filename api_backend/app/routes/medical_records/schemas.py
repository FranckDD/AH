from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime
from typing import Optional

# Pydantic v2: use model_config to accept ORM objects via attributes
class MedicalRecordBase(BaseModel):
    patient_id: int
    marital_status: Optional[str] = Field(None, max_length=50)
    bp: Optional[str] = Field(None, max_length=20)
    temperature: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    motif_code: str = Field(..., min_length=1, max_length=50)

    model_config = {"from_attributes": True}


class MedicalRecordCreate(MedicalRecordBase):
    consultation_date: Optional[datetime] = None  # server_default possible


class MedicalRecordUpdate(BaseModel):
    # tous optionnels
    marital_status: Optional[str] = Field(None, max_length=50)
    bp: Optional[str] = Field(None, max_length=20)
    temperature: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    medical_history: Optional[str] = None
    allergies: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    motif_code: Optional[str] = None
    consultation_date: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MedicalRecordResponse(MedicalRecordBase):
    record_id: int
    consultation_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    last_updated_by: Optional[int] = None
    last_updated_by_name: Optional[str] = None

    model_config = {"from_attributes": True}

    # validators: cast string -> float if DB stored as text
    @field_validator("temperature", mode="before")
    def _cast_temperature(cls, v):
        if v is None or isinstance(v, (float, int)):
            return v
        try:
            return float(v)
        except Exception:
            raise ValueError("temperature invalide")

    @field_validator("weight", mode="before")
    def _cast_weight(cls, v):
        if v is None or isinstance(v, (float, int)):
            return v
        try:
            return float(v)
        except Exception:
            raise ValueError("weight invalide")

    @field_validator("height", mode="before")
    def _cast_height(cls, v):
        if v is None or isinstance(v, (float, int)):
            return v
        try:
            return float(v)
        except Exception:
            raise ValueError("height invalide")

    @field_validator("motif_code", mode="before")
    def _normalize_motif(cls, v):
        if v is None:
            return v
        return str(v).strip().lower()