from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .database import Base

class MedicalSpecialty(Base):
    __tablename__ = 'medical_specialties'

    specialty_id = Column(Integer, primary_key=True)
    name         = Column(String(100), unique=True, nullable=False)

    # relation vers Appointment si besoin ou vers User
    doctors = relationship("User", back_populates="specialty")