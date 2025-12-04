# models/patient.py
import uuid
from sqlalchemy import Column, Integer, String, Date, Text, Sequence, ForeignKey, TIMESTAMP, Boolean # ⬅️ Import de Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
import models

class Patient(Base):
    __tablename__ = 'patients'

    patient_id      = Column(Integer, Sequence('patients_patient_id_seq'), primary_key=True)
    code_patient    = Column(String(20), unique=True)    # Le code automatique
    first_name      = Column(String(50), nullable=False)
    last_name       = Column(String(50), nullable=False)
    birth_date      = Column(Date, nullable=False)
    gender          = Column(String(10))
    national_id     = Column(String(20), unique=True)
    contact_phone   = Column(String(20))
    assurance       = Column(String(20))
    residence       = Column(Text)
    father_name     = Column(String(100))
    mother_name     = Column(String(100))
    
    # 🟢 DRAPEAUX DE SERVICE (pour le filtrage des vues)
    # Si le patient est suivi dans ce service.
    is_clinical     = Column(Boolean, default=False)
    is_toxicology   = Column(Boolean, default=False)
    is_spiritual    = Column(Boolean, default=False)

    # 🟢 CHAMPS DE SUPPRESSION LOGIQUE
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    deleted_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)

    # Métadonnées
    created_at      = Column(TIMESTAMP, server_default=func.now())
    created_by      = Column(Integer, ForeignKey('users.user_id'))
    created_by_name = Column(String(100))
    last_updated_by = Column(Integer, ForeignKey('users.user_id'))
    last_updated_by_name = Column(String(100))
    last_updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    
    # 🔗 RELATIONS (Inchangées)
    prescriptions = relationship(
        "Prescription",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    medical_records = relationship(
        "MedicalRecord",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    appointments = relationship(
        "Appointment",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    spiritual_consultations = relationship(
        'ConsultationSpirituel',
        back_populates='patient',
        cascade='all, delete-orphan'
    )
    pharmacies = relationship(
        'Pharmacy',
        back_populates='patient',
        cascade='all, delete-orphan'
    )
    caisse_entries_by_id = relationship(
        'Caisse',
        back_populates='patient_by_id',
        cascade='all, delete-orphan'
    )
    lab_results = relationship(
        "LabResult",
        back_populates="patient",
        cascade="all, delete-orphan"
    )
    # Ajout pour Toxicologie (One-to-One)
    toxico_dossier = relationship("ToxicoDossier", uselist=False, back_populates="patient")