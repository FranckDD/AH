from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ConsultationBase(BaseModel):
    patient_id: Optional[int] = Field(None, description="ID patient")
    type_consultation: Optional[str] = Field(None, max_length=50)
    presc_generic: Optional[List[str]] = Field(None)
    presc_med_spirituel: Optional[List[str]] = Field(None)
    mp_type: Optional[str] = Field(None)
    psaume: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
    fr_registered_at: Optional[datetime] = Field(None)
    fr_appointment_at: Optional[datetime] = Field(None)
    fr_amount_paid: Optional[Decimal] = Field(None)
    fr_observation: Optional[str] = Field(None)
    consultation_date: Optional[datetime] = Field(None)

    model_config = ConfigDict()


class ConsultationCreate(ConsultationBase):
    # garder Optional[...] dans l'annotation pour éviter l'erreur Pylance,
    # mais rendre le champ requis via Field(...)
    patient_id: Optional[int] = Field(..., description="ID du patient (obligatoire)")
    type_consultation: Optional[str] = Field(..., description="Type de consultation (obligatoire)")


class ConsultationUpdate(BaseModel):
    patient_id: Optional[int] = None
    type_consultation: Optional[str] = None
    presc_generic: Optional[List[str]] = None
    presc_med_spirituel: Optional[List[str]] = None
    mp_type: Optional[str] = None
    psaume: Optional[str] = None
    notes: Optional[str] = None
    fr_registered_at: Optional[datetime] = None
    fr_appointment_at: Optional[datetime] = None
    fr_amount_paid: Optional[Decimal] = None
    fr_observation: Optional[str] = None
    consultation_date: Optional[datetime] = None

    model_config = ConfigDict()


class ConsultationResponse(ConsultationBase):
    consultation_id: int = Field(..., description="PK")
    created_by: Optional[int] = Field(None)
    created_by_name: Optional[str] = Field(None)

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "consultation_id": 123,
            "patient_id": 45,
            "type_consultation": "spirituelle",
            "presc_generic": ["ANALG01", "VITC"],
            "presc_med_spirituel": ["PS1", "PS2"],
            "mp_type": "PB01",
            "psaume": "23",
            "notes": "Patient calme.",
            "fr_registered_at": "2025-08-01T10:00:00",
            "fr_appointment_at": "2025-08-07T14:30:00",
            "fr_amount_paid": "5000.00",
            "fr_observation": "Paiement partiel",
            "consultation_date": "2025-08-01T09:30:00",
            "created_by": 3,
            "created_by_name": "dr.john"
        }
    })
