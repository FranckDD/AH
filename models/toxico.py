from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

# --- ENUMS (Pour garder le code propre) ---
class ToxicoPhaseEnum(enum.IntEnum):
    PHASE_1 = 1
    PHASE_2 = 2
    PHASE_3 = 3
    PHASE_4 = 4

# --- MODÈLES ---

class ToxicoDossier(Base):
    __tablename__ = 'toxico_dossiers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # FK vers Patient (Unique)
    patient_id = Column(Integer, ForeignKey('patients.patient_id'), nullable=False, unique=True)
    
    admission_date = Column(Date, nullable=False)
    substance = Column(String(100), nullable=False)
    
    # FK vers User (Psychologue)
    psychologist_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    current_phase = Column(Integer, default=1, nullable=False)
    relapse_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    guardian_name = Column(String(150))
    guardian_contact = Column(String(50))
    consent_file = Column(String(255))
    notes_admission = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # --- RELATIONS ---
    # Relation vers le Patient (doit correspondre au back_populates dans models/patient.py)
    patient = relationship("Patient", back_populates="toxico_dossier")
    
    # Relation vers le User (Psychologue)
    psychologist = relationship("User", foreign_keys=[psychologist_id])
    
    # Relations vers les sous-tables
    phase_history = relationship("ToxicoPhaseHistory", back_populates="dossier", cascade="all, delete-orphan", order_by="desc(ToxicoPhaseHistory.start_date)")
    evaluations = relationship("ToxicoEvaluation", back_populates="dossier", cascade="all, delete-orphan", order_by="desc(ToxicoEvaluation.created_at)")


class ToxicoPhaseHistory(Base):
    __tablename__ = 'toxico_phase_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dossier_id = Column(Integer, ForeignKey('toxico_dossiers.id'), nullable=False)
    
    phase = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="En cours")
    comments = Column(Text)

    dossier = relationship("ToxicoDossier", back_populates="phase_history")


class ToxicoEvaluation(Base):
    __tablename__ = 'toxico_evaluations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dossier_id = Column(Integer, ForeignKey('toxico_dossiers.id'), nullable=False)
    
    created_at = Column(DateTime, default=func.now())
    created_by = Column(Integer, ForeignKey('users.user_id'))
    
    decision = Column(String(50), nullable=False) # MAINTAIN, PROGRESS, REGRESS
    observation = Column(Text, nullable=False)
    recommendation = Column(Text)
    
    phase_before = Column(Integer)
    phase_after = Column(Integer)
    is_relapse = Column(Boolean, default=False)
    
    dossier = relationship("ToxicoDossier", back_populates="evaluations")
    # Qui a fait l'évaluation ?
    evaluator = relationship("User", foreign_keys=[created_by])