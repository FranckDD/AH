from sqlalchemy.orm import Session
from repositories.audit_repo import AuditRepository
from typing import Optional, List, Dict, Any
from datetime import date

class AuditController:
    """Gère la lecture des journaux d'audit pour l'affichage dans l'interface Admin."""
    def __init__(self, repo: AuditRepository):
        self.repo = repo

    def list_access_logs(
        self, 
        page: int = 1, 
        per_page: int = 20, 
        user_id: Optional[int] = None, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère les logs d'accès avec pagination et filtres."""
        
        # Le repository doit implémenter cette méthode de lecture
        # Elle doit retourner un dictionnaire avec 'data', 'total', 'page', 'per_page', 'total_pages'
        return self.repo.get_access_logs_paginated(
            page=page,
            per_page=per_page,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            action_type=action_type
        )

    def list_action_logs(
        self, 
        page: int = 1, 
        per_page: int = 20, 
        user_id: Optional[int] = None, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None,
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère les logs d'actions utilisateur avec pagination et filtres."""
        
        # Le repository doit implémenter cette méthode de lecture
        return self.repo.get_action_logs_paginated(
            page=page,
            per_page=per_page,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            resource_type=resource_type
        )