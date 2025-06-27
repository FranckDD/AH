# api_backend/app/routes/patients/patients_schemas.py
from pydantic import BaseModel
from datetime import date
from typing import Optional

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    gender: Optional[str]
    contact_phone: Optional[str]
    residence: Optional[str]

class PatientUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    birth_date: Optional[date]
    gender: Optional[str]
    contact_phone: Optional[str]
    residence: Optional[str]

class PatientResponse(BaseModel):
    patient_id: int
    code_patient: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Optional[str]
    contact_phone: Optional[str]
    residence: Optional[str]

    class Config:
        orm_mode = True
