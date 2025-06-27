from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Examen(Base):
    __tablename__ = 'examens'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    nom = Column(Text, nullable=False)
    categorie = Column(Text, nullable=False)
    
    parametres = relationship("Parametre", back_populates="examen")

class Parametre(Base):
    __tablename__ = 'parametres'
    
    id = Column(Integer, primary_key=True)
    examen_id = Column(Integer, ForeignKey('examens.id'), nullable=False)
    nom_parametre = Column(Text, nullable=False)
    unite = Column(Text, nullable=False)
    type_valeur = Column(Text, nullable=False)
    
    examen = relationship("Examen", back_populates="parametres")
    reference_ranges = relationship("ReferenceRange", back_populates="parametre")
    result_details = relationship("LabResultDetail", back_populates="parametre")

class ReferenceRange(Base):
    __tablename__ = 'reference_ranges'
    
    id = Column(Integer, primary_key=True)
    parametre_id = Column(Integer, ForeignKey('parametres.id'), nullable=False)
    sexe = Column(String(1), nullable=False)
    age_min = Column(Integer, nullable=False)
    age_max = Column(Integer, nullable=False)
    valeur_min = Column(Numeric, nullable=False)
    valeur_max = Column(Numeric, nullable=False)
    
    parametre = relationship("Parametre", back_populates="reference_ranges")

class LabResult(Base):
    __tablename__ = 'lab_results'
    
    code_lab_patient = Column(String(20), unique=True, nullable=False)
    result_id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    examen_id = Column(Integer, ForeignKey('examens.id'), nullable=False)
    test_date = Column(DateTime, server_default=func.now())
    prescribed_by = Column(Integer, ForeignKey('users.user_id'))
    technician_id = Column(Integer, ForeignKey('users.user_id'))
    technician_name = Column(String(100))
    status = Column(String(20), default='pending')
    note = Column(Text)
    
    details = relationship("LabResultDetail", back_populates="result")
    examen = relationship("Examen")
    patient = relationship("Patient", back_populates="lab_results")

class LabResultDetail(Base):
    __tablename__ = 'lab_result_details'
    
    detail_id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('lab_results.result_id'), nullable=False)
    parametre_id = Column(Integer, ForeignKey('parametres.id'), nullable=False)
    valeur_text = Column(Text, nullable=False)
    valeur_num = Column(Numeric)  # Générée automatiquement si possible
    
    result = relationship("LabResult", back_populates="details")
    parametre = relationship("Parametre", back_populates="result_details")
    
    # Pour la comparaison avec les plages de référence
    interpretation = Column(String(20))
    flagged = Column(Boolean, default=False)