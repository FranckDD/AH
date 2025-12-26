# app/security/roles.py
from fastapi import Depends, HTTPException, status
from typing import Set
from app.routes.auth.auth_endpoints import get_current_user
from app.security.role_map import normalize_role_name, normalize_roles_list

def require_roles(*allowed_roles: str):
    """
    Factory qui renvoie une dépendance FastAPI.
    allowed_roles peut contenir des aliases FR/EN ou les codes canoniques (ex: "admin", "medecin").
    Exemple d'utilisation: Depends(require_roles("secretaire", "admin"))
    """
    # Normaliser la liste autorisée en codes canoniques (lowercase)
    allowed_canon: Set[str] = set()
    for r in allowed_roles:
        if not r:
            continue
        canon = normalize_role_name(r) or r.strip().lower()
        allowed_canon.add(canon)

    async def dependency(current_user = Depends(get_current_user)):
        user_roles = getattr(current_user, "roles", []) or []
        user_roles_canon = set(r.strip().lower() for r in user_roles if r)

        if not (user_roles_canon & allowed_canon):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : rôle utilisateur insuffisant"
            )
        return current_user

    return dependency
