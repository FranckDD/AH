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

class ParametreOrder(BaseModel):
    ids: List[int]

class ParametreUpdate(BaseModel):
    nom_parametre: Optional[str] = None
    unite: Optional[str] = None
    type_valeur: Optional[str] = None
    input_type: Optional[str] = None
    options_list: Optional[str] = None
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
    # Anciennes bornes en annees (peuvent manquer sur une ligne qui n'a que des jours / SA).
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    age_min_days: Optional[int] = Field(None, ge=0)
    age_max_days: Optional[int] = Field(None, ge=0)
    ga_min_weeks: Optional[int] = Field(None, ge=0, le=45)
    ga_max_weeks: Optional[int] = Field(None, ge=0, le=45)
    valeur_min: Decimal
    valeur_max: Decimal

class ReferenceRangeCreate(ReferenceRangeBase):
    pass

class RangeIn(BaseModel):
    """Plage de reference saisie depuis le catalogue (le parametre vient de l'URL)."""
    sexe: str = Field(..., pattern="^[MFX]$")
    # Anciennes bornes en annees : seules ecrites si aucune borne en jours / SA n'est donnee (defauts 0 / 150).
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    # Bornes en jours (inclusives) et en semaines d'amenorrhee ; absent = borne ouverte / sans critere.
    age_min_days: Optional[int] = Field(None, ge=0)
    age_max_days: Optional[int] = Field(None, ge=0)
    ga_min_weeks: Optional[int] = Field(None, ge=0, le=45)
    ga_max_weeks: Optional[int] = Field(None, ge=0, le=45)
    valeur_min: Decimal
    valeur_max: Decimal

    @model_validator(mode="after")
    def _bounds(self):
        if self.age_min is not None and self.age_max is not None and self.age_min > self.age_max:
            raise ValueError("age_min doit etre inferieur ou egal a age_max")
        if (self.age_min_days is not None and self.age_max_days is not None
                and self.age_min_days > self.age_max_days):
            raise ValueError("age_min_days doit etre inferieur ou egal a age_max_days")
        if (self.ga_min_weeks is not None and self.ga_max_weeks is not None
                and self.ga_min_weeks > self.ga_max_weeks):
            raise ValueError("ga_min_weeks doit etre inferieur ou egal a ga_max_weeks")
        if self.valeur_min > self.valeur_max:
            raise ValueError("valeur_min doit etre inferieure ou egale a valeur_max")
        return self

    def to_columns(self) -> dict:
        """Colonnes a ecrire : jours / SA tels quels ; les annees heritees sont ecrites (defauts 0 / 150)
        seulement quand aucune borne en jours ni SA n'est donnee, sinon uniquement si elles sont fournies."""
        data = self.model_dump()
        modern = any(data[k] is not None for k in ("age_min_days", "age_max_days", "ga_min_weeks", "ga_max_weeks"))
        if not modern:
            data["age_min"] = 0 if data["age_min"] is None else data["age_min"]
            data["age_max"] = 150 if data["age_max"] is None else data["age_max"]
        return data

class ReferenceRangeUpdate(BaseModel):
    parametre_id: Optional[int] = None
    sexe: Optional[str] = Field(None, max_length=1)
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    age_min_days: Optional[int] = Field(None, ge=0)
    age_max_days: Optional[int] = Field(None, ge=0)
    ga_min_weeks: Optional[int] = Field(None, ge=0, le=45)
    ga_max_weeks: Optional[int] = Field(None, ge=0, le=45)
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
    # Semaines d'amenorrhee au prelevement (ecriture : medecin/nurse/laborantin/admin ; 403 sinon)
    gestational_age_weeks: Optional[int] = None
    # Grossesse d'un patient externe (colonne separee, jamais dans external_patient_info) et statut a la reception
    external_pregnancy_info: Optional[Dict[str, Any]] = None
    pregnancy_status_at_result: Optional[str] = None
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
    # Ligne de facture (examen facture a la caisse) que cet examen execute : une ligne ne se recoit
    # qu'une fois (409 sinon).
    origin_caisse_item_id: Optional[int] = None

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
    # received_at : heure de reception (ISO 8601) sur l'appareil, pour la reception faite hors ligne ; le serveur en
    # tire le jour du numero de dossier (borne par resolve_client_time). Absent : heure serveur.
    received_at: Optional[str] = None
    # Semaines d'amenorrhee au prelevement, commune a tous les examens du lot (voir require_pregnancy_write)
    gestational_age_weeks: Optional[int] = None
    # Grossesse d'un patient externe (statut, DPA, numero de suivi) : colonne separee de external_patient_info,
    # que les flux de synchronisation livrent. Statut de grossesse CHOISI pour cette demande (enceinte,
    # non_enceinte, inconnu) : cliche du rapport de subvention, sans modifier la fiche du patient.
    external_pregnancy_info: Optional[Dict[str, Any]] = None
    pregnancy_status_at_result: Optional[str] = None

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
    dossier_year: Optional[int] = None
    dossier_counter: Optional[int] = None
    dossier_rank: Optional[int] = None
    dossier: Optional[str] = None  # "289/02 du 08/10/2026", nul tant que non attribue
    # Retire de la reponse pour tout role non autorise a voir la grossesse (filtre central)
    gestational_age_weeks: Optional[int] = None
    external_pregnancy_info: Optional[Dict[str, Any]] = None
    class Config:
        from_attributes = True

class RecentPendingItem(BaseModel):
    id: int
    patient_name: str
    code_patient: str
    test_type: str        

class PassageExamOut(BaseModel):
    result_id: int
    examen_nom: str
    status: Optional[str] = None


class RecentPassageOut(BaseModel):
    """Un patient une seule fois avec tous les examens de son passage (batch_id)."""
    batch_id: Optional[str] = None
    patient_name: str
    code_patient: str
    first_pending_id: int
    exams: List[PassageExamOut]


class LabStatsOut(BaseModel):
    pending: int
    completed_today: int
    #revenue_month: float
    critical: int
    total_month: int
    max_exam_count: int
    top_exams: Dict[str, int]
    recent_pending: List[RecentPendingItem]
    recent_passages: List[RecentPassageOut] = []

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
    nb_anormaux: int = 0
    corrected: bool = False
    dossier: Optional[str] = None

class PaginatedLabHistoryOut(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int
    items: List[PaginatedLabItemOut]


class LabAmendIn(BaseModel):
    """Correction d'un resultat valide : le motif est obligatoire."""
    reason: str
    values: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = Field(default=None, max_length=1000)
    conclusion: Optional[str] = Field(default=None, max_length=5000)

    @model_validator(mode='after')
    def check_reason(self):
        self.reason = (self.reason or "").strip()
        if not self.reason:
            raise ValueError("Le motif de la correction est obligatoire.")
        return self
