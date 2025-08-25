# models/lab.py
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.patient import Patient
from sqlalchemy.sql import func
from .database import Base

class Examen(Base):
    __tablename__ = "examens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(Text, nullable=False)
    categorie: Mapped[str] = mapped_column(Text, nullable=False)

    parametres: Mapped[List["Parametre"]] = relationship("Parametre", back_populates="examen")


class Parametre(Base):
    __tablename__ = "parametres"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    examen_id: Mapped[int] = mapped_column(ForeignKey("examens.id"), nullable=False)
    nom_parametre: Mapped[str] = mapped_column(Text, nullable=False)
    unite: Mapped[str] = mapped_column(Text, nullable=False)
    type_valeur: Mapped[str] = mapped_column(Text, nullable=False)

    examen: Mapped["Examen"] = relationship("Examen", back_populates="parametres")
    reference_ranges: Mapped[List["ReferenceRange"]] = relationship("ReferenceRange", back_populates="parametre")
    result_details: Mapped[List["LabResultDetail"]] = relationship("LabResultDetail", back_populates="parametre")


class ReferenceRange(Base):
    __tablename__ = "reference_ranges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parametre_id: Mapped[int] = mapped_column(ForeignKey("parametres.id"), nullable=False)
    sexe: Mapped[str] = mapped_column(String(1), nullable=False)
    age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    valeur_min: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    valeur_max: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    parametre: Mapped["Parametre"] = relationship("Parametre", back_populates="reference_ranges")


class LabResult(Base):
    __tablename__ = "lab_results"

    result_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), nullable=False)
    test_type: Mapped[str] = mapped_column(String(100), nullable=False)
    test_date: Mapped[Optional[DateTime]] = mapped_column(DateTime, server_default=func.now())
    prescribed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"))
    technician_name: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    note: Mapped[Optional[str]] = mapped_column(String(1000))
    examen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("examens.id"))
    code_lab_patient: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    
    created_by: Mapped[Optional[int]] = mapped_column(Integer)
    created_by_name: Mapped[Optional[str]] = mapped_column(Text)
    last_updated_by: Mapped[Optional[int]] = mapped_column(Integer)
    last_updated_by_name: Mapped[Optional[str]] = mapped_column(Text)

    # Relations
    details: Mapped[List["LabResultDetail"]] = relationship(
        "LabResultDetail",
        back_populates="result",
        cascade="all, delete-orphan"
    )
    examen: Mapped["Examen"] = relationship("Examen")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="lab_results")



class LabResultDetail(Base):
    __tablename__ = "lab_result_details"
    detail_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("lab_results.result_id"), nullable=False)
    parametre_id: Mapped[int] = mapped_column(ForeignKey("parametres.id"), nullable=False)
    valeur_text: Mapped[str] = mapped_column(Text, nullable=False)
    valeur_num: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)

    interpretation: Mapped[Optional[str]] = mapped_column(String(20))
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    result: Mapped["LabResult"] = relationship("LabResult", back_populates="details")
    parametre: Mapped["Parametre"] = relationship("Parametre", back_populates="result_details")
