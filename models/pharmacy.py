# models/pharmacy.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Pharmacy(Base):
    __tablename__ = 'pharmacy'

    medication_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id    = Column(Integer, ForeignKey('patients.patient_id'), nullable=True)
    drug_name     = Column(String(100), nullable=False)
    quantity      = Column(Integer)
    medication_type = Column(String(20), nullable=False)
    prescribed_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    name_dr       = Column(String(100))

    patient    = relationship('Patient', back_populates='pharmacies')
    prescriber = relationship('User')