# app/routes/caisse/caisse_schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# Schéma de base
class CaisseBase(BaseModel):
    montant: Optional[float] = Field(None, description="Montant payé")
    mode_paiement: Optional[str] = Field(None, description="Mode de paiement")
    description: Optional[str] = Field(None, description="Description du paiement")

# Création
class CaisseCreate(CaisseBase):
    patient_id: Optional[int] = Field(..., description="ID du patient lié")
    consultation_id: Optional[int] = Field(None, description="ID consultation (si applicable)")
    montant: Optional[float] = Field(..., description="Montant obligatoire")
    mode_paiement: Optional[str] = Field(..., description="Mode de paiement obligatoire")

# Mise à jour
class CaisseUpdate(CaisseBase):
    montant: Optional[float] = Field(None, description="Nouveau montant")
    mode_paiement: Optional[str] = Field(None, description="Nouveau mode de paiement")
    description: Optional[str] = Field(None, description="Nouvelle description")

# Réponse complète
class CaisseOut(CaisseBase):
    id: int
    patient_id: Optional[int]
    consultation_id: Optional[int]
    date_paiement: datetime

    class Config:
        from_attributes = True
