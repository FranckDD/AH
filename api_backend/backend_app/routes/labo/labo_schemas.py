from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class LabResultDetailCreate(BaseModel):
    parametre_id: int
    valeur_text: Optional[str] = None
    valeur_num: Optional[float] = None

class LabResultCreate(BaseModel):
    patient_id: Optional[int] = None
    examen_id: int
    details: List[LabResultDetailCreate] = Field(default_factory=list)

class LabResultOutDetail(BaseModel):
    detail_id: int
    parametre_id: int
    valeur_text: Optional[str]
    valeur_num: Optional[float]
    interpretation: Optional[str]
    flagged: Optional[bool]

    class Config:
        from_attributes = True

class LabResultOut(BaseModel):
    result_id: int
    patient_id: int
    examen_id: int
    code_lab_patient: Optional[str]
    test_date: Optional[datetime]
    status: Optional[str]
    details: List[LabResultOutDetail] = []

    class Config:
        from_attributes = True
