# app/routes/users/mapping.py
from __future__ import annotations
from typing import Any, Dict, Optional
from app.utils.mapping_general import get_field  # utilitaire générique que tu as déjà
#from app.utils.mapping_general import to_datetime as _to_datetime  # si nécessaire

def normalize_user_data(raw: Any) -> Dict[str, Any]:
    """
    Prépare les données user (ORM/dict/pydantic) pour la sortie API.
    Ne retourne jamais password_hash.
    """
    def _role_name(r):
        ar = get_field(r, "application_role") or get_field(getattr(r, "application_role", None), "role_name")
        # get_field returned either object or value; handle both:
        if hasattr(ar, "role_name"):
            return getattr(ar, "role_name", None)
        return ar

    def _specialty_name(r):
        sp = get_field(r, "specialty") or get_field(getattr(r, "specialty", None), "name")
        if hasattr(sp, "name"):
            return getattr(sp, "name", None)
        return sp

    out: Dict[str, Any] = {
        "user_id": get_field(raw, "user_id"),
        "username": get_field(raw, "username"),
        "full_name": get_field(raw, "full_name"),
        "is_active": get_field(raw, "is_active"),
        "postgres_role": get_field(raw, "postgres_role"),
        "role_id": get_field(raw, "role_id"),
        "role_name": _role_name(raw),
        "specialty_id": get_field(raw, "specialty_id"),
        "specialty_name": _specialty_name(raw),
    }

    # include computed roles property if present (from model property)
    roles_prop = None
    try:
        roles_prop = getattr(raw, "roles", None)
    except Exception:
        roles_prop = None
    out["roles"] = roles_prop

    return out


