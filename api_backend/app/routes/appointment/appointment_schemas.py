# app/routes/appointment/appointment_schemas.py
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date, time, datetime

# -----------------------
# Base réutilisable (pour Update / Response)
# -----------------------
class AppointmentBase(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None
    specialty: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    reason: Optional[str] = None
    status: Optional[str] = None

    model_config = {"from_attributes": True}


# -----------------------
# Création : modèle distinct (champs requis)
# -----------------------
class AppointmentCreate(BaseModel):
    # on ne hérite PAS de AppointmentBase pour éviter les conflits Pylance
    patient_id: int = Field(..., description="Identifiant du patient")
    appointment_date: date = Field(..., description="Date du rendez-vous")
    appointment_time: time = Field(..., description="Heure du rendez-vous")
    specialty: Optional[str] = Field(None, description="Spécialité médicale")
    reason: Optional[str] = Field(None, description="Motif / commentaire")

    model_config = {"from_attributes": True}


# -----------------------
# Mise à jour : tout optionnel (hérite de la base)
# -----------------------
class AppointmentUpdate(AppointmentBase):
    # utiliser model_dump(exclude_unset=True) dans l'endpoint pour partial update
    pass


# -----------------------
# Réponse : inclut les métadonnées
# -----------------------
class AppointmentResponse(AppointmentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # si tu préfères, remplace dict par un schéma Pydantic pour patient/doctor
    patient: Optional[dict] = None
    doctor: Optional[dict] = None

    model_config = {"from_attributes": True}
