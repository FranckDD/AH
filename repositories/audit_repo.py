from sqlalchemy.orm import Session, Query
from sqlalchemy import func
from models.audit import AuditAccess, AuditUserAction
from typing import Optional, Dict, Any, List, Type
from models.user import User 
from datetime import date, timedelta ,datetime

class AuditRepository:
    """
    Gère toutes les opérations CRUD et de lecture pour les logs d'audit.
    Ne gère PAS les commits ou les rollbacks ; ces opérations sont déléguées 
    à la transaction parente (Controller ou Route).
    """
    def __init__(self, session: Session):
        self.session = session

    # --- Utility pour la Pagination et le Filtrage ---
    def _apply_filters_and_paginate(
        self, 
        query: Query, 
        model: Type[AuditAccess] | Type[AuditUserAction], 
        page: int, 
        per_page: int, 
        user_id: Optional[int], 
        date_from: Optional[date], 
        date_to: Optional[date], 
        specific_filter_key: Optional[str] = None, 
        specific_filter_value: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # 1. Filtre par utilisateur
        if user_id is not None:
            query = query.filter(model.user_id == user_id)
        
        # 2. Filtre par date
        if date_from:
            query = query.filter(model.timestamp >= date_from)
        if date_to:
            # Inclut la fin de la journée
            query = query.filter(model.timestamp < date_to + timedelta(days=1)) 
        
        # 3. Filtre spécifique (action_type ou resource_type)
        if specific_filter_key and specific_filter_value:
            column = getattr(model, specific_filter_key)
            # Recherche partielle et insensible à la casse
            query = query.filter(column.ilike(f"%{specific_filter_value}%"))
            
        # 4. Calcul du total
        total = query.count()
        total_pages = (total + per_page - 1) // per_page
        
        # 5. Pagination
        offset = (page - 1) * per_page
        data = query.order_by(model.timestamp.desc()).offset(offset).limit(per_page).all()
        
        return {
            "data": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }
    
    def _serialize_data(self, data: Any) -> Any:
        """
        Parcourt récursivement les données pour convertir les objets date/datetime
        en chaînes de caractères compatibles JSON.
        """
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_data(v) for v in data]
        elif isinstance(data, (date, datetime)):
            return data.isoformat() # Convertit 1998-06-01 en "1998-06-01"
        return data

    # --- NOUVELLE FONCTION DE LECTURE : Logs d'Accès ---
    def get_access_logs_paginated(
        self, 
        page: int, 
        per_page: int, 
        user_id: Optional[int] = None, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None, 
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère les logs d'accès avec filtres spécifiques à AuditAccess."""
        
        query = self.session.query(AuditAccess)
        
        return self._apply_filters_and_paginate(
            query=query,
            model=AuditAccess,
            page=page,
            per_page=per_page,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            specific_filter_key="action_type",
            specific_filter_value=action_type
        )

    # --- NOUVELLE FONCTION DE LECTURE : Logs d'Actions ---
    def get_action_logs_paginated(
        self, 
        page: int, 
        per_page: int, 
        user_id: Optional[int] = None, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None, 
        resource_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère les logs d'actions avec filtres spécifiques à AuditUserAction."""
        
        query = self.session.query(AuditUserAction)
        
        return self._apply_filters_and_paginate(
            query=query,
            model=AuditUserAction,
            page=page,
            per_page=per_page,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            specific_filter_key="resource_type",
            specific_filter_value=resource_type
        )
    
    # --- Log d'Accès (Fonction d'écriture) ---
    def log_access(self, current_user: Optional[User], action_type: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None, details: Optional[str] = None):
        """ Enregistre un événement de connexion/déconnexion/échec. """
        
        user_id = current_user.user_id if current_user else None
        
        log = AuditAccess(
            user_id=user_id,
            action_type=action_type,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        # 🟢 AJOUT à la session. PAS de commit isolé.
        self.session.add(log)

    # --- Log d'Actions Utilisateur (Fonction d'écriture corrigée) ---
    def log_user_action(self, current_user: User, resource_type: str, action_performed: str, resource_id: Optional[int] = None, old_values: Optional[Dict[str, Any]] = None, new_values: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None, details: Optional[str] = None):
        """ Enregistre une action CRUD importante sur une ressource. """
        
        username_val = getattr(current_user, 'full_name', getattr(current_user, 'username', 'Inconnu'))
        
        # 🟢 NETTOYAGE DES DONNÉES AVANT INSERTION
        # On convertit les dates en string pour éviter "TypeError: Object of type date is not JSON serializable"
        safe_old_values = self._serialize_data(old_values) if old_values else None
        safe_new_values = self._serialize_data(new_values) if new_values else None

        log = AuditUserAction(
            user_id=current_user.user_id,
            username=username_val,
            resource_type=resource_type,
            resource_id=resource_id,
            action_performed=action_performed,
            old_values=safe_old_values, # Utiliser la version "safe"
            new_values=safe_new_values, # Utiliser la version "safe"
            ip_address=ip_address
            # details=details 
        )
        # 🟢 AJOUT à la session. PAS de commit isolé.
        self.session.add(log)
        
    # Alias pour compatibilité avec le code existant qui appelle log_activity
    def log_activity(self, user: User, action_type: str, details: str, target_id: Optional[int] = None):
        """ Alias de compatibilité pour log_user_action """
        
        resource_type = "Unknown"
        if "TOXICO" in action_type:
            resource_type = "Toxicology"
        
        # Les détails sont stockés dans le JSONB 'new_values'
        self.log_user_action(
            current_user=user,
            resource_type=resource_type,
            action_performed=action_type,
            resource_id=target_id,
            new_values={"details": details} 
        )

    # 🛑 LA MÉTHODE _commit_log A ÉTÉ RETIRÉE POUR FORCER L'ATOMICITÉ.
    # Le commit doit être fait par le PatientController après l'insertion du Patient ET du Log.