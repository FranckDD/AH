# models/prescription.py
import uuid
from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base

class Prescription(Base):
    __tablename__ = 'prescriptions'
    prescription_id = Column(Integer, primary_key=True)
    patient_id      = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    medical_record_id = Column(Integer, ForeignKey('medical_records.record_id'))
    medication      = Column(String(100), nullable=False)
    dosage          = Column(String(50), nullable=False)
    frequency       = Column(String(50), nullable=False)
    duration        = Column(String(50), nullable=False)
    start_date      = Column(Date, nullable=False)
    end_date        = Column(Date)
    notes           = Column(Text)
    status          = Column(String(20), default="active")
    prescribed_by   = Column(Integer, ForeignKey("users.user_id"))
    prescribed_by_name = Column(String(100))
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    #relations
    patient         = relationship("Patient", back_populates="prescriptions")
    medical_record = relationship("MedicalRecord", back_populates="prescriptions")
    
