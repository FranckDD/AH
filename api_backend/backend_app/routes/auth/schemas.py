from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserPasswordUpdate(BaseModel):
    old_password: str = Field(..., min_length=4, description="Mot de passe actuel pour vérification")
    new_password: str = Field(..., min_length=8, description="Nouveau mot de passe")
    confirm_password: str = Field(..., min_length=8, description="Confirmation du nouveau mot de passe")

    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Les nouveaux mots de passe ne correspondent pas')
        return v


class SelfProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
