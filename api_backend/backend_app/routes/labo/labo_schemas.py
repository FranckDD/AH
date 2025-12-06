from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from decimal import Decimal 

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
    """Schéma de sortie pour un examen."""
    id: int
    code: str
    nom: str
    categorie: str
    prix: Decimal 

    # 🟢 CORRECTION CRITIQUE : Gérer les prix NULL en base de données
    @field_validator('prix', mode='before')
    @classmethod
    def set_default_price(cls, v):
        # Si la valeur venant de la DB est None, on retourne 0.0
        if v is None:
            return Decimal(0.0)
        return v

    class Config:
        from_attributes = True

# ====================================================================
# 2. SCHÉMAS DE CONFIGURATION DES PARAMÈTRES (CRUD)
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
    # Pour éviter les problèmes de récursion circulaire, on peut rendre examen optionnel
    # ou utiliser une référence simplifiée si nécessaire.
    # examen: Optional[ExamenOut] = None 

    class Config:
        from_attributes = True

# ====================================================================
# 3. SCHÉMAS DES PLAGES DE RÉFÉRENCE (CRUD)
# ====================================================================

class ReferenceRangeBase(BaseModel):
    parametre_id: int
    sexe: str = Field(..., max_length=1) # M, F, X (tous)
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
# 4. SCHÉMAS DES RÉSULTATS DE LABORATOIRE (CRÉATION/SORTIE)
# ====================================================================

class LabResultDetailCreate(BaseModel):
    """Schéma pour les détails envoyés lors de la création d'un résultat."""
    parametre_id: int
    valeur_text: Optional[str] = None
    valeur_num: Optional[float] = None

class LabResultCreate(BaseModel):
    """Schéma utilisé pour créer un résultat de laboratoire."""
    examen_id: int
    
    # Patient Interne (ID) ou Patient Externe (Infos)
    patient_id: Optional[int] = None
    external_patient_info: Optional[Dict[str, Any]] = None

    details: List[LabResultDetailCreate] = Field(default_factory=list)

    # Validation pour s'assurer qu'au moins un identifiant patient est présent
    def model_post_init(self, context: Any) -> None:
        if self.patient_id is None and self.external_patient_info is None:
            raise ValueError("Un patient_id ou external_patient_info est requis pour la création d'un résultat.")


class LabResultOutDetail(BaseModel):
    """Schéma de sortie pour un détail de résultat."""
    detail_id: int # Assurez-vous que votre modèle SQLAlchemy a 'detail_id' ou 'id' mappé ici
    parametre_id: int
    valeur_text: Optional[str]
    valeur_num: Optional[float]
    interpretation: Optional[str]
    flagged: Optional[bool]

    class Config:
        from_attributes = True

class LabResultOut(BaseModel):
    """Schéma de sortie pour le résultat complet de laboratoire."""
    result_id: int
    patient_id: Optional[int] 
    examen_id: int
    code_lab_patient: Optional[str]
    test_date: Optional[datetime]
    status: Optional[str]
    
    external_patient_info: Optional[Dict[str, Any]] = None 
    
    details: List[LabResultOutDetail] = Field(default_factory=list)

    class Config:
        from_attributes = True