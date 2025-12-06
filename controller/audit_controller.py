from typing import Optional, Dict, Any, List
from datetime import date
from repositories.audit_repo import AuditRepository
# Import des modèles pour le typage si nécessaire, mais le repo gère déjà la requête

class AuditController:
    """
    Contrôleur pour la lecture des logs d'audit.
    L'écriture se fait via injection dans les autres contrôleurs (Patient, Prescription, etc.).
    """
    def __init__(self, repo: AuditRepository):
        self.repo = repo

    def list_access_logs(self, page: int, per_page: int, user_id=None, date_from=None, date_to=None, action_type=None) -> Dict[str, Any]:
        result = self.repo.get_access_logs_paginated(
            page=page, per_page=per_page, user_id=user_id,
            date_from=date_from, date_to=date_to, action_type=action_type
        )
        
        data_list = []
        for log in result["data"]:
            
            # 🟢 MAPPING FIXE : Assure que l'ID de sortie est 'id'
            # (utilise log.access_id qui est la clé primaire dans votre modèle)
            
            user_name = None
            # Tente de récupérer le username via la relation (si votre repo la charge)
            if hasattr(log, "user") and log.user:
                user_name = log.user.username
            
            data_list.append({
                "id": log.access_id, # C'est la ligne clé pour résoudre le 500
                "user_id": log.user_id,
                "user_name": user_name or "Système/Inconnu",
                "action_type": log.action_type,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
                "timestamp": log.timestamp.isoformat() # Assure un format de date sérialisable
            })
            
        result["data"] = data_list
        return result

    def list_action_logs(self, page: int, per_page: int, user_id=None, date_from=None, date_to=None, resource_type=None) -> Dict[str, Any]:
        result = self.repo.get_action_logs_paginated(
            page=page, per_page=per_page, user_id=user_id,
            date_from=date_from, date_to=date_to, resource_type=resource_type
        )
        
        data_list = []
        for log in result["data"]:
            
            # 🟢 MAPPING FIXE : Assure que l'ID de sortie est 'id'
            # (utilise log.action_id qui est la clé primaire dans votre modèle)
            
            user_name = log.username # Récupère le nom s'il est stocké en dur
            if not user_name and hasattr(log, "user") and log.user:
                user_name = log.user.username # Ou via la relation

            data_list.append({
                "id": log.action_id, # C'est la ligne clé pour résoudre le 500
                "user_id": log.user_id,
                "user_name": user_name or "Inconnu",
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "action_performed": log.action_performed,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat(), # Assure un format de date sérialisable
                "username": log.username
            })

        result["data"] = data_list
        return result