# models/pharmacy.py

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from .database import Base  # supposons que Base = declarative_base()

class Pharmacy(Base):
    __tablename__ = 'pharmacy'

    medication_id    = Column(Integer, primary_key=True, autoincrement=True)
    patient_id       = Column(Integer, ForeignKey('patients.patient_id'), nullable=True)
    drug_name        = Column(String(100), nullable=False)
    quantity         = Column(Integer, nullable=False, default=0)
    threshold        = Column(Integer, nullable=False, default=0)
    medication_type  = Column(String(20), nullable=False)
    dosage_mg        = Column(Numeric(10, 2), nullable=True)
    expiry_date      = Column(DateTime, nullable=True)
    stock_status     = Column(String(20), nullable=False, default='normal')
    prescribed_by    = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    name_dr          = Column(String(100), nullable=True)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at       = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations (si besoin)
    patient   = relationship('Patient', back_populates='pharmacies')
    prescriber = relationship('User')

    movements = relationship('StockMovement', back_populates='product', cascade='all, delete-orphan')

    def __repr__(self):
        return (
            f"<Pharmacy(id={self.medication_id}, name={self.drug_name}, "
            f"qty={self.quantity}, status={self.stock_status})>"
        )

    def update_stock_status(self):
        """
        Met à jour le champ stock_status en fonction de quantity et threshold.
        """
        if self.quantity <= 0:
            self.stock_status = 'épuisé'
        elif self.quantity <= self.threshold:
            self.stock_status = 'critique'
        else:
            self.stock_status = 'normal'
