from fastapi import Depends, HTTPException, status
from app.routes.auth.auth_endpoints import get_current_user

# Définition des permissions par module
PERMISSIONS = {
    "caisse": ["secretaire", "admin"],
    "consultation_spirituel": ["secretaire", "admin"],
    "appointment": ["personnel medical", "admin"],
    "prescription": ["personnel medical", "admin"],
    "labo": ["laborantin", "admin"],
    "dashboard": ["admin"],
    "user_management": ["admin"],
    "pharmacy": ["personnel medical", "admin"]
}

def require_permission(module: str):
    """Dépendance pour vérifier les permissions de l'utilisateur"""
    async def permission_checker(current_user=Depends(get_current_user)):
        required_roles = PERMISSIONS.get(module, [])
        
        # L'admin a tous les accès
        if "admin" in current_user.roles:
            return current_user
        
        # Vérifier si l'utilisateur a un des rôles requis
        if not any(role in required_roles for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les droits nécessaires pour accéder à cette ressource",
            )
        return current_user
    return Depends(permission_checker)

# Définition des permissions spécifiques
CAISSE_PERMISSION = require_permission("caisse")
SPIRITUAL_PERMISSION = require_permission("consultation_spirituel")
MEDICAL_PERMISSION = require_permission("appointment")
PRESCRIPTION_PERMISSION = require_permission("prescription")
LAB_PERMISSION = require_permission("labo")
DASHBOARD_PERMISSION = require_permission("dashboard")
USER_MANAGEMENT_PERMISSION = require_permission("user_management")
PHARMACY_PERMISSION = require_permission("pharmacy")