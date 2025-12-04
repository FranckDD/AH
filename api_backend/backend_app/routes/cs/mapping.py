from __future__ import annotations
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

def _get_field(raw: Any, name: str):
    """Récupère un champ depuis un dict ou un objet ORM/Pydantic"""
    if isinstance(raw, dict):
        return raw.get(name)
    if hasattr(raw, "model_dump"):
        try:
            return raw.model_dump().get(name)
        except Exception:
            pass
    if hasattr(raw, name):
        return getattr(raw, name)
    return None

def _to_list_of_str(value: Any) -> List[str]:
    """
    Convertit une valeur en liste de strings.
    CORRECTION IMPORTANTE : Renvoie [] au lieu de None pour satisfaire Pydantic.
    """
    if value is None:
        return []  # 🟢 CORRECTION : Renvoie une liste vide, pas None
    
    if isinstance(value, str):
        # Gestion des chaînes vides ou mal formatées "{}"
        clean_val = value.strip().replace("{", "").replace("}", "")
        if not clean_val:
            return []
        parts = [p.strip() for p in clean_val.split(",") if p.strip()]
        return parts
        
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v is not None]
        
    return [str(value)]

def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            try:
                # Format fallback courant
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
    return None

def _parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

# --- FONCTION DE NORMALISATION AMÉLIORÉE ---
def normalize_consultation_data(raw: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    # 1. Récupération Standard (Ton code existant)
    for f in ("consultation_id", "patient_id", "created_by"):
        data[f] = _get_field(raw, f)

    if data.get("consultation_id") is None:
        data["consultation_id"] = _get_field(raw, "consultation_id") or _get_field(raw, "id")

    # Récupération Nom (Avec Fallback relationnel)
    data["created_by_name"] = _get_field(raw, "created_by_name") or (
        (_get_field(raw, "creator") and getattr(_get_field(raw, "creator"), "username", None))
    ) or "Conseiller"

    data["type_consultation"] = _get_field(raw, "type_consultation")
    data["notes"] = _get_field(raw, "notes")
    data["psaume"] = _get_field(raw, "psaume")
    data["mp_type"] = _get_field(raw, "mp_type")

    data["presc_generic"] = _to_list_of_str(_get_field(raw, "presc_generic"))
    data["presc_med_spirituel"] = _to_list_of_str(_get_field(raw, "presc_med_spirituel"))

    data["consultation_date"] = _parse_datetime(
        _get_field(raw, "consultation_date") or _get_field(raw, "date")
    )
    
    data["fr_registered_at"] = _parse_datetime(_get_field(raw, "fr_registered_at"))
    data["fr_appointment_at"] = _parse_datetime(_get_field(raw, "fr_appointment_at"))
    data["fr_amount_paid"] = _parse_decimal(_get_field(raw, "fr_amount_paid"))
    data["fr_observation"] = _get_field(raw, "fr_observation")

    # --- AJOUTS POUR LA VUE (PATCH ALIAS) ---
    
    # Alias ID
    data["id"] = data["consultation_id"]
    
    # Alias TYPE (Le front utilise souvent record.type)
    data["type"] = data["type_consultation"] or "Suivi Spirituel"

    # Alias DATE
    data["date"] = data["consultation_date"]

    # Alias INTERVENANT
    data["intervenant"] = data["created_by_name"]

    return data