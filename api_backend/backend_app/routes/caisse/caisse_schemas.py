# app/routes/caisse/caisse_schemas.py
from datetime import datetime
from typing import Optional,List
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

# --- 1. Schéma pour une transaction impayée (Liste d'Action) ---
class UnpaidTransactionSchema(BaseModel):
    transaction_id: int = Field(..., description="ID unique de la transaction Caisse.")
    patient_name: str = Field(..., description="Nom complet du patient ou label saisi (calculé dans le Repo).")
    patient_contact: str = Field(..., description="Numéro de téléphone du patient.")
    
    # La date est renvoyée en format ISO (string) par la fonction de mapping
    date: Optional[str] = Field(None, description="Date de la transaction ('paid_at').") 
    
    total_amount: float = Field(..., description="Montant total de la facture (Caisse.amount).")
    paid_amount: float = Field(..., description="Montant déjà payé (Caisse.advance_amount).")
    remaining_due: float = Field(..., description="Montant restant dû (calculé: total_amount - paid_amount).")
    status: str = Field(..., description="Statut de la transaction (ex: 'active', 'partially_paid').")

    class Config:
        # Permet à Pydantic d'extraire les données des objets SQLAlchemy
        from_attributes = True

# --- 2. Schéma pour les KPIs Financiers de la Caisse ---
class FinancialKpiSchema(BaseModel):
    total_paid: float = Field(..., description="Total encaissé (somme des advance_amount) dans la période.")
    total_factured: float = Field(..., description="Total facturé (somme des amount) dans la période.")
    remaining_due: float = Field(..., description="Montant impayé total sur les transactions actives de la période.")
    recouvrement_rate: float = Field(..., description="Taux de recouvrement (total_paid / total_factured) * 100.")
    total_transactions: int = Field(..., description="Nombre total de transactions actives dans la période.")

    class Config:
        from_attributes = True 

# --- NOUVEAU SCHÉMA POUR LA RÉPARTITION DES PAIEMENTS ---
class PaymentDistributionItem(BaseModel):
    """Représente un mode de paiement et le total associé."""
    method: str = Field(..., description="Nom du mode de paiement (ex: Espèces, OM, Chèque).")
    total: float = Field(..., description="Total encaissé pour ce mode de paiement dans la période.")

class PaymentDistributionSchema(BaseModel):
    """Schéma de réponse pour la distribution des paiements (Liste des items)."""
    distribution: List[PaymentDistributionItem] = Field(..., description="Liste des totaux groupés par mode de paiement.")

    class Config:
        from_attributes = True   

   


# --- NOUVEAU SCHÉMA POUR UN VERSEMENT ÉCHELONNÉ ---
class InstallmentPaymentIn(BaseModel):
    paid_amount: float = Field(..., gt=0, description="Montant du versement effectué maintenant.")
    payment_method: str = Field(..., description="Mode de paiement utilisé pour ce versement (ex: Espèces, Virement).") 
    payment_type: Optional[str] = Field("VERSEMENT_ECHEANCE", description="Type de versement. Par défaut 'VERSEMENT_ECHEANCE', peut être 'SOLDE'.")
    note: Optional[str] = Field(None, description="Note spécifique à ce versement.")
    
    class Config:
        from_attributes = True


class PaymentEchelonneOut(BaseModel):
    payment_id: int
    transaction_id: int
    paid_amount: float
    payment_date: datetime
    payment_method: str
    payment_type: str
    handled_by: int
    note: Optional[str]

    class Config:
        from_attributes = True                    
