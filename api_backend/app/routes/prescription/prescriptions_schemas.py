# app/routes/prescriptions/schemas.py
from typing import Optional
from pydantic import BaseModel, Field, model_validator, ValidationError
from datetime import date

# Pydantic v2: we can still use BaseModel; adjust for model_dump/model_validate usage

class PrescriptionBase(BaseModel):
    patient_id: Optional[int] = None
    medical_record_id: Optional[int] = None
    medication: Optional[str] = Field(None, min_length=1)
    dosage: Optional[str] = Field(None, min_length=1)
    frequency: Optional[str] = Field(None, min_length=1)
    duration: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}  # if you relied on orm_mode

    @model_validator(mode="after")
    def check_dates(self):
        """Valide que start_date <= end_date si les deux sont fournis."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date doit être antérieure ou égale à end_date")
        return self


class PrescriptionCreate(PrescriptionBase):
    # pour création, rendre required les champs logiques
    medication: Optional[str] = Field(..., min_length=1)
    dosage: Optional[str] = Field(..., min_length=1)
    frequency: Optional[str] = Field(..., min_length=1)
    start_date: Optional[date] = Field(...) # type: ignore

class PrescriptionUpdate(PrescriptionBase):
    # mises à jour: tout optionnel (mais on n'utilisera PAS exclude_unset dans endpoint pour stock proc)
    pass

class PrescriptionResponse(PrescriptionBase):
    prescription_id: int
    patient_id: Optional[int] = Field(...) # type: ignore
    medical_record_id: Optional[int] = None
    prescribed_by: Optional[int] = None
    prescribed_by_name: Optional[str] = None

    class Config:
        from_attributes = True
