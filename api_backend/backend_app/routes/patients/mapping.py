import re
from typing import Any, Dict

# Normalize gender values from DB -> 'M'|'F'|'O' or None
def normalize_gender(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    # variations fréquentes
    if s in ("m", "male", "homme", "man", "monsieur"):
        return "M"
    if s in ("f", "female", "femme", "woman", "madame"):
        return "F"
    if s in ("o", "other", "autre", "non-binaire", "non binaire", "nb"):
        return "O"
    # Si la DB contient "M" ou "F" déjà
    if s.upper() in ("M", "F", "O"):
        return s.upper()
    return None

# Normalize phone number.
_re_phone = re.compile(r"^\+?\d{7,15}$")

def normalize_phone(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # remove spaces, parentheses, dashes
    cleaned = re.sub(r"[ \-\(\)]", "", s)
    if _re_phone.match(cleaned):
        # ensure leading +
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned
    return None

def model_to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convertit soit un dict déjà, soit un ORM instance (avec attributs simples) en dict
    en ne prenant que les champs utilisés par PatientResponse.
    """
    if isinstance(obj, dict):
        base = dict(obj)
    else:
        # objet SQLAlchemy simple : on lit attributs explicitement
        base = {
            "patient_id": getattr(obj, "patient_id", None),
            "code_patient": getattr(obj, "code_patient", None),
            "first_name": getattr(obj, "first_name", None),
            "last_name": getattr(obj, "last_name", None),
            "birth_date": getattr(obj, "birth_date", None),
            "gender": getattr(obj, "gender", None),
            "national_id": getattr(obj, "national_id", None),
            "contact_phone": getattr(obj, "contact_phone", None),
            "assurance": getattr(obj, "assurance", None),
            "residence": getattr(obj, "residence", None),
            "father_name": getattr(obj, "father_name", None),
            "mother_name": getattr(obj, "mother_name", None),
            
            # 🟢 Ajout des drapeaux booléens (avec valeur par défaut False)
            "is_clinical": getattr(obj, "is_clinical", False),
            "is_toxicology": getattr(obj, "is_toxicology", False),
            "is_spiritual": getattr(obj, "is_spiritual", False),
        }
    return base

def normalize_patient_data(raw_obj: Any) -> Dict[str, Any]:
    """
    Applique les normalisations nécessaires pour rendre les données
    compatibles avec les schémas Pydantic de réponse.
    """
    d = model_to_dict(raw_obj)
    
    # gender normalization
    d["gender"] = normalize_gender(d.get("gender"))
    # phone normalization
    d["contact_phone"] = normalize_phone(d.get("contact_phone"))
    
    # Sécurisation : on s'assure que les drapeaux sont présents dans le dict final
    d.setdefault("is_clinical", False)
    d.setdefault("is_toxicology", False)
    d.setdefault("is_spiritual", False)
    
    return d