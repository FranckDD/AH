# api_backend/app/routes/patients/patients_schemas.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date
from typing import Optional, Any
import re

# --- helpers de normalisation ---
_MALE = {"m", "male", "homme", "man", "monsieur", "masculin", "h"}
_FEMALE = {"f", "female", "femme", "woman", "madame", "feminin"}
_OTHER = {"o", "other", "autre", "a", "non-binaire", "non binaire", "nb", "autre"}

_phone_clean_re = re.compile(r"[ \-\(\)\.]+")

def _normalize_gender_value(raw: Any) -> Optional[str]:
    """
    Retourne 'M', 'F' ou 'A' si on reconnaît la valeur (variant -> normalisé).
    Si non reconnu, retourne la valeur brute (string) pour ne pas casser la réponse.
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
    # non reconnu -> renvoyer la valeur brute (ex: "Homme " non standard)
    return s

def _normalize_phone_value(raw: Any) -> Optional[str]:
    """
    Essaie de normaliser un téléphone en +<digits>.
    Si impossible (lettres, longueur hors plage), renvoie la valeur brute pour
    ne pas provoquer d'erreur sur les données existantes en base.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # Suppression séparateurs courants
    cleaned = _phone_clean_re.sub("", s)

    # Si contient des lettres -> on renvoie la valeur brute
    if re.search(r"[A-Za-z]", cleaned):
        return s

    # Extraction des chiffres
    digits = "".join(re.findall(r"\d+", cleaned))
    if len(digits) < 1:
        return s

    # Si longueur raisonnable -> renvoyer +digits (on n'est pas trop strict ici)
    if 1 <= len(digits) <= 15:
        return "+" + digits if not cleaned.startswith("+") else "+" + digits

    # sinon renvoyer brut
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

    # Normalisation avant parsing (input)
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

    # validators "before" pour normaliser les valeurs venant de la BD
    @field_validator("gender", mode="before")
    @classmethod
    def _val_gender_resp(cls, v):
        return _normalize_gender_value(v)

    @field_validator("contact_phone", mode="before")
    @classmethod
    def _val_phone_resp(cls, v):
        return _normalize_phone_value(v)

    # Pydantic v2 : lecture depuis attributs ORM si on passe un ORM object
    model_config = ConfigDict(from_attributes=True)
