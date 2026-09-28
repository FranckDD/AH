from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date
from typing import Optional, Any, Dict, List
import re
import uuid as uuid_lib

# --- helpers de normalisation ---
_MALE = {"m", "male", "homme", "man", "monsieur", "masculin", "h"}
_FEMALE = {"f", "female", "femme", "woman", "madame", "feminin"}
_OTHER = {"o", "other", "autre", "a", "non-binaire", "non binaire", "nb", "autre"}

_phone_clean_re = re.compile(r"[ \-\(\)\.]+")

def _normalize_gender_value(raw: Any) -> Optional[str]:
    """
    Retourne 'M', 'F' ou 'A' si on reconnaît la valeur.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s_low = s.lower()
    if s_low in _MALE:
        return "M"
    if s_low in _FEMALE:
        return "F"
    if s_low in _OTHER:
        return "A"
    if len(s) == 1:
        up = s.upper()
        if up in {"M", "F", "A", "O"}:
            return "A" if up == "O" else up
    return s

def _normalize_phone_value(raw: Any) -> Optional[str]:
    """
    Essaie de normaliser un téléphone en +<digits>.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        # Chaine vide explicite (distincte de None/absent) : l'appelant
        # veut effacer le champ. public.update_patient fait
        # COALESCE(p_contact_phone, contact_phone) - seul NULL signifie
        # "ne pas modifier" ; "" est une vraie valeur qui efface la
        # colonne. Retourner None ici la reconvertirait a tort en
        # "ne pas modifier" (voir chantier 7a, correctif final).
        return ""

    cleaned = _phone_clean_re.sub("", s)

    if re.search(r"[A-Za-z]", cleaned):
        return s

    digits = "".join(re.findall(r"\d+", cleaned))
    if len(digits) < 1:
        return s

    if 1 <= len(digits) <= 15:
        return "+" + digits if not cleaned.startswith("+") else "+" + digits

    return s

# --- Schémas ---

class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    birth_date: date = Field(...)
    gender: Optional[str] = None
    national_id: Optional[str] = None
    contact_phone: Optional[str] = None
    assurance: Optional[str] = None
    residence: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    
    # 🟢 Drapeaux optionnels à la création (par défaut False)
    is_clinical: bool = False
    is_toxicology: bool = False
    is_spiritual: bool = False

    # Chantier 4 sous-projet 4 : uuid client d'un patient cree hors ligne
    # (PowerSync). Persiste tel quel ; un rejeu du meme uuid est idempotent
    # cote endpoint (voir patients_endpoints.create_patient).
    uuid: Optional[str] = None

    @field_validator("uuid", mode="before")
    @classmethod
    def _val_uuid_create(cls, v):
        if v in (None, ""):
            return None
        return str(uuid_lib.UUID(str(v)))

    @field_validator("gender", mode="before")
    @classmethod
    def _val_gender_create(cls, v):
        return _normalize_gender_value(v)

    @field_validator("contact_phone", mode="before")
    @classmethod
    def _val_phone_create(cls, v):
        return _normalize_phone_value(v)


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1)
    last_name: Optional[str] = Field(None, min_length=1)
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    national_id: Optional[str] = None
    contact_phone: Optional[str] = None
    assurance: Optional[str] = None
    residence: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    
    # 🟢 Drapeaux optionnels à la mise à jour
    is_clinical: Optional[bool] = None
    is_toxicology: Optional[bool] = None
    is_spiritual: Optional[bool] = None

    @field_validator("gender", mode="before")
    @classmethod
    def _val_gender_update(cls, v):
        return _normalize_gender_value(v)

    @field_validator("contact_phone", mode="before")
    @classmethod
    def _val_phone_update(cls, v):
        return _normalize_phone_value(v)


class PatientResponse(BaseModel):
    patient_id: int
    code_patient: str
    first_name: str
    last_name: str
    birth_date: date
    gender: Optional[str] = None
    national_id: Optional[str] = None
    contact_phone: Optional[str] = None
    assurance: Optional[str] = None
    residence: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    
    # 🟢 Drapeaux de service (Information essentielle pour le frontend)
    is_clinical: bool
    is_toxicology: bool
    is_spiritual: bool

    @field_validator("gender", mode="before")
    @classmethod
    def _val_gender_resp(cls, v):
        return _normalize_gender_value(v)

    @field_validator("contact_phone", mode="before")
    @classmethod
    def _val_phone_resp(cls, v):
        return _normalize_phone_value(v)

    model_config = ConfigDict(from_attributes=True)


# --- Schémas KPI (Patients Spirituels) ---

class NewPatientCount(BaseModel):
    """Schéma pour le KPI 1: Nombre de nouveaux patients (Spirituels)."""
    new_patients_count: int = Field(..., description="Nombre de patients créés sur la période (jour/semaine).")

class PatientStatusDistribution(BaseModel):
    """Schéma pour le KPI 2: Distribution Actif/Inactif des patients (Spirituels)."""
    active_patients_count: int = Field(..., description="Nombre de patients actifs (RDV récent).")
    inactive_patients_count: int = Field(..., description="Nombre de patients inactifs.")
    total_patients_count: int = Field(..., description="Total des patients spirituels.")

class PatientAssuranceDistribution(BaseModel):
    """Schéma pour le KPI 3: Répartition par Assurance des patients (Spirituels)."""
    assurance_distribution: Dict[str, int] = Field(
        ...,
        description="Dictionnaire (Assurance -> Nombre de patients). Clé 'Non spécifié' pour les patients sans assurance."
    )

class PatientListResponse(BaseModel):
    data: List[PatientResponse]
    total: int
    page: int
    per_page: int
    total_pages: int    


class PatientGlobalCounts(BaseModel):
    total_all: int
    total_clinical: int
    total_toxicology: int
    total_spiritual: int    