# app/routes/users/users_schemas.py
from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    postgres_role: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    specialty_id: Optional[int] = None

    model_config = ConfigDict()

class UserCreate(UserBase):
    # On garde Optional[...] pour éviter le warning Pylance, mais Field(...) rend le champ requis.
    username: Optional[str] = Field(..., description="Nom d'utilisateur (unique)")
    password: Optional[str] = Field(..., description="Mot de passe en clair")
    full_name: Optional[str] = Field(..., description="Nom complet")

    model_config = ConfigDict()

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    postgres_role: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    specialty_id: Optional[int] = None

    model_config = ConfigDict()

class UserOut(BaseModel):
    user_id: int
    username: str
    full_name: str
    is_active: bool
    postgres_role: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    specialty_id: Optional[int] = None
    specialty_name: Optional[str] = None
    roles: Optional[List[str]] = None  # propriété calculée si présente

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "user_id": 1,
            "username": "dr.john",
            "full_name": "John Doe",
            "is_active": True,
            "postgres_role": "readonly",
            "role_id": 2,
            "role_name": "medecin",
            "specialty_id": 3,
            "specialty_name": "Cardiologie",
            "roles": ["medecin"]
        }
    })
