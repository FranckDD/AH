from pydantic import BaseModel, Field, field_validator
from datetime import datetime, date
from typing import Optional

class PharmacyCreate(BaseModel):
    drug_name: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=0)
    threshold: int = Field(..., ge=0)
    medication_type: str = Field(..., min_length=1)
    forme: str = Field("Autre")
    dosage_mg: Optional[float] = Field(None, ge=0)
    price: float = Field(..., ge=0, description="Prix unitaire")
    expiry_date: Optional[date] = None
    prescribed_by: Optional[int] = None
    name_dr: Optional[str] = None

class PharmacyUpdate(BaseModel):
    drug_name: Optional[str] = Field(None, min_length=1)
    quantity: Optional[int] = Field(None, ge=0)
    threshold: Optional[int] = Field(None, ge=0)
    medication_type: Optional[str] = Field(None, min_length=1)
    forme: Optional[str] = None
    dosage_mg: Optional[float] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    expiry_date: Optional[date] = None
    prescribed_by: Optional[int] = None
    name_dr: Optional[str] = None

class PharmacyResponse(BaseModel):
    medication_id: int
    patient_id: Optional[int] = None
    drug_name: str
    quantity: int
    threshold: int
    medication_type: str
    forme: str
    dosage_mg: Optional[float] = None
    price: float
    expiry_date: Optional[datetime] = None
    stock_status: str
    prescribed_by: Optional[int] = None
    name_dr: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("expiry_date", mode="before")
    @classmethod
    def parse_expiry_date(cls, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime(value.year, value.month, value.day)
        return value
    
class CriticalStockCount(BaseModel):
    """Schéma pour le KPI du nombre de produits en stock critique/épuisé."""
    stock_alerts_count: int

    class Config:
        from_attributes = True   

class ExpiringProductCount(BaseModel):
    """Schéma pour le KPI du nombre de produits expirant bientôt."""
    expiring_alerts_count: int

    class Config:
        from_attributes = True

class TotalStockValue(BaseModel):
    """Schéma pour le KPI de la valeur monétaire totale du stock."""
    total_stock_value: float

    class Config:
        from_attributes = True         

# Schéma pour les KPI de comptage (comme Naturel/Pharmaceutique)
class CategoryCount(BaseModel):
    category_count: int

# Schéma pour l'agrégation de toutes les stats (doit correspondre à la sortie du Controller)
class StockDashboardStats(BaseModel):
    totalValue: float
    countPharma: int
    countNatural: int
    lowStockAlerts: int
    expiredCount: int        