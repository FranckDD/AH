# app/utils/mapping.py
from __future__ import annotations
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, List, Callable, Union



def get_field(raw: Any, name: str) -> Any:
    """Extrait un champ d’un dict, d’un objet ORM ou d’un modèle Pydantic."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get(name)
    if hasattr(raw, "model_dump"):  # Pydantic v2
        try:
            return raw.model_dump().get(name)
        except Exception:
            pass
    if hasattr(raw, name):
        return getattr(raw, name)
    return None


def to_list_of_str(value: Any) -> Optional[List[str]]:
    """Convertit un champ en liste de str (utile pour prescriptions, tags...)."""
    if value is None:
        return None
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts if len(parts) > 1 else [value.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime depuis ISO, SQL string ou objet natif."""
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
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None
    return None


def parse_decimal(value: Any) -> Optional[Decimal]:
    """Convertit un champ en Decimal (ou None si invalide)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


# -------------------------
# Normalisations spécifiques
# -------------------------

def normalize_gender(raw: Any) -> str | None:
    """Standardise le genre -> 'M'|'F'|'O' ou None."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    if s in ("m", "male", "homme", "man", "monsieur"):
        return "M"
    if s in ("f", "female", "femme", "woman", "madame"):
        return "F"
    if s in ("o", "other", "autre", "non-binaire", "non binaire", "nb"):
        return "O"
    if s.upper() in ("M", "F", "O"):
        return s.upper()
    return None


_re_phone = re.compile(r"^\+?\d{7,15}$")
def normalize_phone(raw: Any) -> str | None:
    """Nettoie et valide numéro de téléphone international (+xxxxxxxx)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    cleaned = re.sub(r"[ \-\(\)]", "", s)
    if _re_phone.match(cleaned):
        return cleaned if cleaned.startswith("+") else "+" + cleaned
    return None


# -------------------------
# Générateur générique
# -------------------------

def normalize_data(raw: Any, fields: Dict[str, Union[str, Callable[[Any], Any]]]) -> Dict[str, Any]:
    """
    Transforme un objet brut en dict prêt pour un schéma Pydantic.
    :param raw: ORM, dict ou modèle
    :param fields: mapping { "nom_champ_schema": "nom_champ_source" | fonction }
    """
    out: Dict[str, Any] = {}
    for key, src in fields.items():
        if callable(src):
            out[key] = src(raw)
        else:
            out[key] = get_field(raw, src)
    return out
