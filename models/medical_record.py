# models/medical_record.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class MedicalRecord(Base):
    __tablename__ = 'medical_records'

    record_id          = Column(Integer, primary_key=True)
    patient_id         = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    consultation_date  = Column(DateTime, server_default=func.now())
    marital_status     = Column(String(20))  # Ajout de la colonne statut matrimonial
    bp                 = Column(String(10))
    temperature        = Column(Numeric(4,1))
    weight             = Column(Numeric(5,2))
    height             = Column(Numeric(5,2))
    medical_history    = Column(Text)
    allergies          = Column(Text)
    symptoms           = Column(Text)
    diagnosis          = Column(Text)
    treatment          = Column(Text)
    severity           = Column(String(20))
    notes              = Column(Text)
    motif_code         = Column(String(20), nullable=False)

    # Champs d'audit si besoin
    created_by         = Column(Integer, ForeignKey('users.user_id'))
    created_by_name    = Column(String(100))
    last_updated_by    = Column(Integer, ForeignKey('users.user_id'))
    last_updated_by_name = Column(String(100))

    # Relation vers Patient
    patient            = relationship("Patient", back_populates="medical_records")
    prescriptions = relationship("Prescription", back_populates="medical_record", cascade="all, delete-orphan")
