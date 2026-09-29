from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime
from typing import Generic, TypeVar, List, Optional



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
    appointment_id: Optional[int] = None

    model_config = {"from_attributes": True}


class MedicalRecordCreate(MedicalRecordBase):
    # patient_id devient optionnel a la creation SEULEMENT (la reponse garde
    # patient_id obligatoire via MedicalRecordBase) : un patient cree hors
    # ligne n'est connu que par son uuid (resolution cote endpoint).
    patient_id: Optional[int] = None
    patient_uuid: Optional[str] = Field(None, description="UUID du patient cree hors ligne (resolu en patient_id cote serveur)")
    consultation_date: Optional[datetime] = None  # server_default possible
    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")
    needs_doctor_review: Optional[bool] = False
    assigned_doctor_id: Optional[int] = None


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

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int


class MedicalRecordResponse(MedicalRecordBase):
    record_id: int
    consultation_date: Optional[datetime] = None
    created_by: Optional[int] = None
    created_by_name: Optional[str] = None
    last_updated_by: Optional[int] = None
    last_updated_by_name: Optional[str] = None
    patient: Optional[dict] = None
    uuid: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        return str(v) if v is not None else v

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


class PendingReviewRecordOut(BaseModel):
    record_id: int
    patient_id: int
    patient_name: str
    motif_code: str
    consultation_date: Optional[str] = None
    created_by_name: Optional[str] = None
    assigned_doctor_id: Optional[int] = None

    model_config = {"from_attributes": True}