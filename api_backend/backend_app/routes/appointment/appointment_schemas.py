# app/routes/appointment/appointment_schemas.py
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import date, time, datetime
from typing import List

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
    uuid: Optional[str] = Field(None, description="UUID client (creation hors ligne PowerSync) - si absent, Postgres en genere un")

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
    uuid: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # si tu préfères, remplace dict par un schéma Pydantic pour patient/doctor
    patient: Optional[dict] = None
    doctor: Optional[dict] = None

    # La colonne appointments.uuid est un UUID(as_uuid=True) cote SQLAlchemy :
    # l'ORM renvoie un objet uuid.UUID, pas une chaine. Pydantic v2 (contrairement
    # a v1) ne coerce plus automatiquement UUID -> str, ce qui casse from_attributes
    # (ValidationError "Input should be a valid string") sur toute reponse qui
    # inclut ce champ. Normaliser explicitement en str avant validation.
    @field_validator("uuid", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        return str(v) if v is not None else v

    model_config = {"from_attributes": True}

class AppointmentListResponse(BaseModel):
    data: List[AppointmentResponse]
    total: int
    page: int
    per_page: int

    model_config = {"from_attributes": True}   
