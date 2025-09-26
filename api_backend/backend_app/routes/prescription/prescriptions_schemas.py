# app/routes/prescriptions/schemas.py
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from datetime import date

class PrescriptionBase(BaseModel):
    patient_id: int = Field(..., description="Identifiant du patient")
    medical_record_id: Optional[int] = None
    medication: Optional[str] = Field(None, min_length=1)
    dosage: Optional[str] = Field(None, min_length=1)
    frequency: Optional[str] = Field(None, min_length=1)
    duration: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date doit être antérieure ou égale à end_date")
        return self


class PrescriptionCreate(PrescriptionBase):
    medication: Optional[str] = Field(..., min_length=1)
    dosage: Optional[str] = Field(..., min_length=1)
    frequency: Optional[str] = Field(..., min_length=1)
    start_date: Optional[date] = Field(...)  # type: ignore


class PrescriptionUpdate(PrescriptionBase):
    pass


class PrescriptionResponse(PrescriptionBase):
    prescription_id: int
    patient_id: Optional[int] = Field(...)  # type: ignore
    medical_record_id: Optional[int] = None
    prescribed_by: Optional[int] = None
    prescribed_by_name: Optional[str] = None

    # optionally include a nested patient payload (dict) so UI can display code_patient without extra calls
    patient: Optional[dict] = None

    

    class Config:
        from_attributes = True


class PrescriptionListResponse(BaseModel):
    data: List[PrescriptionResponse]
    total: int
    page: int
    per_page: int

    model_config = {"from_attributes": True}
