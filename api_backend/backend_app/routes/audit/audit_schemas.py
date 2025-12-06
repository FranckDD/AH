# Fichier: api_backend/backend_app/routes/audit/audit_schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- SCHEMAS DE BASE ---

class AuditAccessRead(BaseModel):
    # Mappe 'access_id' (BDD) vers 'id' (JSON)
    id: int = Field(..., alias="access_id") 
    
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime

    # Permet de peupler via 'id' OU 'access_id'
    model_config = ConfigDict(from_attributes=True, populate_by_name=True) 

class AuditUserActionRead(BaseModel):
    # Mappe 'action_id' (BDD) vers 'id' (JSON)
    id: int = Field(..., alias="action_id")
    
    user_id: int
    user_name: Optional[str] = None
    resource_type: str
    resource_id: Optional[int] = None 
    action_performed: str
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    username: Optional[str] = None 

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# --- SCHEMAS DE LISTE PAGINÉE (CRUCIAUX POUR L'ENDPOINT) ---

class AuditAccessListResponse(BaseModel):
    data: List[AuditAccessRead]
    total: int
    page: int
    per_page: int
    total_pages: int # Optionnel, selon votre controller

class AuditUserActionListResponse(BaseModel):
    data: List[AuditUserActionRead]
    total: int
    page: int
    per_page: int
    total_pages: int # Optionnel