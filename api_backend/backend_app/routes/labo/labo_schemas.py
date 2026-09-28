from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Any, Dict, Union
from datetime import datetime
from decimal import Decimal 
from uuid import UUID

# ====================================================================
# 1. SCHÉMAS DE CONFIGURATION DES EXAMENS (CRUD)
# ====================================================================

class ExamenBase(BaseModel):
    """Schéma de base pour les données d'un examen."""
    code: str = Field(..., max_length=20)
    nom: str
    categorie: str
    prix: Decimal = Field(..., decimal_places=2, ge=0) 

class ExamenCreate(ExamenBase):
    pass

class ExamenUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=20)
    nom: Optional[str] = None
    categorie: Optional[str] = None
    prix: Optional[Decimal] = Field(None, decimal_places=2, ge=0)

class ExamenOut(BaseModel):
    id: int
    code: str
    nom: str
    categorie: str
    prix: Decimal 

    @field_validator('prix', mode='before')
    @classmethod
    def set_default_price(cls, v):
        if v is None:
            return Decimal(0.0)
        return v

    class Config:
        from_attributes = True

# ====================================================================
# 2. SCHÉMAS DES PARAMÈTRES
# ====================================================================

class ParametreBase(BaseModel):
    nom_parametre: str
    unite: str
    type_valeur: str
    examen_id: int

class ParametreCreate(ParametreBase):
    pass

class ParametreUpdate(BaseModel):
    nom_parametre: Optional[str] = None
    unite: Optional[str] = None
    type_valeur: Optional[str] = None
    examen_id: Optional[int] = None 

class ParametreOut(ParametreBase):
    id: int
    class Config:
        from_attributes = True

# ====================================================================
# 3. SCHÉMAS DES PLAGES DE RÉFÉRENCE
# ====================================================================

class ReferenceRangeBase(BaseModel):
    parametre_id: int
    sexe: str = Field(..., max_length=1) 
    age_min: int = Field(ge=0)
    age_max: int = Field(ge=0)
    valeur_min: Decimal
    valeur_max: Decimal

class ReferenceRangeCreate(ReferenceRangeBase):
    pass

class ReferenceRangeUpdate(BaseModel):
    parametre_id: Optional[int] = None
    sexe: Optional[str] = Field(None, max_length=1)
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    valeur_min: Optional[Decimal] = None
    valeur_max: Optional[Decimal] = None

class ReferenceRangeOut(ReferenceRangeBase):
    id: int
    class Config:
        from_attributes = True

# ====================================================================
# 4. SCHÉMAS DES RÉSULTATS (C'est ici que j'ai corrigé)
# ====================================================================

class LabResultDetailCreate(BaseModel):
    parametre_id: int
    valeur_text: Optional[str] = None
    valeur_num: Optional[float] = None

class LabWorklistOut(BaseModel):
    prescription_id: int
    date: datetime
    patient_id: Optional[int]
    patient_name: str
    exams_requested: Optional[Any] 
    doctor: Optional[str]
    notes: Optional[str]    

class LabResultCreate(BaseModel):
    """Pour la création unitaire (non batch)"""
    examen_id: int
    patient_id: Optional[int] = None
    prescribed_by_id: Optional[int] = None
    external_patient_info: Optional[Dict[str, Any]] = None
    origin_prescription_id: Optional[int] = None
    details: List[LabResultDetailCreate] = Field(default_factory=list)

    @model_validator(mode='after')
    def check_patient_exists(self):
        if not self.patient_id and not self.external_patient_info:
            raise ValueError("Un patient_id ou external_patient_info est requis.")
        return self


# --- 🟢 CORRECTION MAJEURE ICI (BATCH) ---

class BatchItem(BaseModel):
    """
    Représente une demande d'examen dans le panier.
    On ne demande PAS la valeur ici, car l'examen n'est pas encore fait.
    """
    examen_id: int  # Doit correspondre exactement à ce que le JS envoie
    value: Optional[Union[float, str]] = None
    note: Optional[str] = None # Optionnel : note spécifique à cet examen
    # uuid genere par le client (hors ligne) - permet le rejeu idempotent
    # d'un item deja envoye (meme motif que patients.uuid). Absent en ligne.
    uuid: Optional[UUID] = None

class BatchResultCreate(BaseModel):
    """
    Le payload reçu du Frontend pour une demande multiple.
    """
    patient_id: Optional[int] = None
    # patient_uuid : patient interne cree hors ligne dans le meme geste,
    # pas encore de patient_id cote client (chantier 4 sous-projet 5, meme
    # motif que consultation/prescription au sous-projet 4).
    patient_uuid: Optional[UUID] = None
    prescribed_by_id: Optional[int] = None
    prescribed_by_name: Optional[str] = None
    external_patient_info: Optional[Dict[str, Any]] = None
    # Prescription medicale source (worklist medecin) - propage l'exclusion
    # cote get_lab_worklist() une fois le dossier cree. Jusqu'ici jamais
    # effectivement lu par le backend malgre son envoi depuis LabReception.vue
    # (bug reel corrige dans ce chantier, hors perimetre hors-ligne).
    origin_prescription_id: Optional[int] = None
    # batch_uuid : identite de lot generee par le client hors ligne,
    # volontairement PARTAGEE par tous les items de cette reception -
    # permet de retrouver le code LAB deja attribue a un item-frere envoye
    # dans une operation CRUD separee (chaque ligne locale = son propre
    # appel HTTP hors ligne, contrairement a l'envoi synchrone en ligne).
    batch_uuid: Optional[str] = None

    # Liste des examens (ex: [ {examen_id: 1}, {examen_id: 5} ])
    results: List[BatchItem]

    @model_validator(mode='after')
    def check_patient_exists(self):
        if not self.patient_id and not self.patient_uuid and not self.external_patient_info:
            raise ValueError("Un patient_id, patient_uuid ou external_patient_info est requis.")
        return self

# ----------------------------------------

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
    patient_id: Optional[int] 
    examen_id: int
    code_lab_patient: Optional[str]
    test_date: Optional[datetime]
    status: Optional[str]
    note: Optional[str] = None
    external_patient_info: Optional[Dict[str, Any]] = None 
    details: List[LabResultOutDetail] = Field(default_factory=list)
    batch_id: Optional[UUID] = None
    class Config:
        from_attributes = True

class RecentPendingItem(BaseModel):
    id: int
    patient_name: str
    code_patient: str
    test_type: str        

class LabStatsOut(BaseModel):
    pending: int
    completed_today: int
    #revenue_month: float
    critical: int
    total_month: int
    max_exam_count: int
    top_exams: Dict[str, int]
    recent_pending: List[RecentPendingItem]

# --- AJOUT POUR LA PAGINATION ---

class PaginatedLabItemOut(BaseModel):
    result_id: int
    code: Optional[str] = None
    patient_name: str
    patient_sexe: str
    patient_age: Union[int, str]
    is_external: bool
    examen_nom: str
    test_date: str
    status: Optional[str] = None
    batch_id: Optional[str] = None

class PaginatedLabHistoryOut(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    items: List[PaginatedLabItemOut]
