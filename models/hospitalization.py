from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

DISCHARGE_DISPOSITIONS = ("GUERI", "TRANSFERE", "SORTIE_CONTRE_AVIS_MEDICAL", "DECES")
CLINICAL_STATUSES = ("AMELIORATION", "STABLE", "AGGRAVATION")


class Hospitalization(Base):
    __tablename__ = 'hospitalizations'

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    admitted_at = Column(DateTime, nullable=False, server_default=func.now())
    admitted_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    admission_reason = Column(Text)
    discharged_at = Column(DateTime, nullable=True)
    discharge_disposition = Column(String(30), nullable=True)
    discharge_note = Column(Text)
    discharged_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient")
    admitted_by_user = relationship("User", foreign_keys=[admitted_by])
    discharged_by_user = relationship("User", foreign_keys=[discharged_by])
    status_updates = relationship(
        "HospitalizationStatusUpdate",
        back_populates="hospitalization",
        cascade="all, delete-orphan",
        order_by="desc(HospitalizationStatusUpdate.created_at)",
    )


class HospitalizationStatusUpdate(Base):
    __tablename__ = 'hospitalization_status_updates'

    id = Column(Integer, primary_key=True)
    hospitalization_id = Column(Integer, ForeignKey('hospitalizations.id'), nullable=False)
    status = Column(String(20), nullable=False)
    note = Column(Text)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    hospitalization = relationship("Hospitalization", back_populates="status_updates")
    created_by_user = relationship("User", foreign_keys=[created_by])
