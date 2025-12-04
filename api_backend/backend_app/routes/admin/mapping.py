# app/routes/users/mapping.py
from __future__ import annotations
from typing import Any, Dict, Optional
from ...utils.mapping_general import get_field  # utilitaire générique que tu as déjà
#from app.utils.mapping_general import to_datetime as _to_datetime  # si nécessaire

def normalize_user_data(raw: Any) -> Dict[str, Any]:
    """
    Prépare les données user (ORM/dict/pydantic) pour la sortie API.
    Ne retourne jamais password_hash.
    """
    def _role_name(r):
        # Tente d'abord d'obtenir l'objet lié, puis son attribut 'role_name'
        ar = get_field(r, "application_role") 
        if hasattr(ar, "role_name"):
            return getattr(ar, "role_name", None)
        # Si 'r' est un dict plat (ou si get_field a déjà extrait la valeur seule)
        return get_field(r, "role_name")

    def _specialty_name(r):
        # Tente d'abord d'obtenir l'objet lié, puis son attribut 'name'
        sp = get_field(r, "specialty")
        if hasattr(sp, "name"):
            return getattr(sp, "name", None)
        # Si 'r' est un dict plat (ou si get_field a déjà extrait la valeur seule)
        return get_field(r, "specialty_name")

    out: Dict[str, Any] = {
        "user_id": get_field(raw, "user_id"),
        "username": get_field(raw, "username"),
        "full_name": get_field(raw, "full_name"),
        
        # 🟢 AJOUTS POUR EMAIL ET CONTACT
        "email": get_field(raw, "email"),
        "contact": get_field(raw, "contact"),
        # -----------------------------
        
        "is_active": get_field(raw, "is_active"),
        "postgres_role": get_field(raw, "postgres_role"),
        "role_id": get_field(raw, "role_id"),
        "role_name": _role_name(raw),
        "specialty_id": get_field(raw, "specialty_id"),
        "specialty_name": _specialty_name(raw),
    }

    # Inclure la propriété calculée 'roles' (si présente sur l'objet ORM)
    roles_prop = None
    try:
        # C'est la méthode la plus sûre pour les propriétés ORM
        roles_prop = getattr(raw, "roles", None)
    except Exception:
        roles_prop = None
        
    # Si la propriété 'roles' n'existe pas ou est None, assurez-vous que la valeur est une liste pour Pydantic
    if roles_prop is None:
        roles_prop = []
        # Fallback pour inclure le rôle principal si 'roles' n'existe pas
        if out["role_name"] and isinstance(out["role_name"], str):
             roles_prop.append(out["role_name"])
             
    out["roles"] = roles_prop

    return out


