# models/lab.py
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID # <--- IMPORT IMPORTANT
import uuid
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
    prix = mapped_column(Numeric(10, 2), default=0.0)


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
    # --- OPTIMISATION : UI DYNAMIQUE ---
    input_type: Mapped[str] = mapped_column(String(20), default="numeric") # numeric, text, area, select
    options_list: Mapped[Optional[str]] = mapped_column(Text) # Pour 'select', ex: "Positif,Négatif"


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
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), nullable=True)
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
    # --- PONT PRESCRIPTION ---
    origin_prescription_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prescriptions.prescription_id"), nullable=True)
    
    # Infos Patient Externe (JSONB)
    external_patient_info: Mapped[Optional[dict]] = mapped_column(JSON)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    # uuid : identite stable connue AVANT confirmation serveur (genere par
    # le client hors ligne) - permet la resolution idempotente d'un dossier
    # cree hors ligne (voir get_lab_result_by_uuid). batch_uuid : identite
    # de LOT generee par le client, volontairement PARTAGEE par toutes les
    # lignes d'une meme reception a plusieurs examens - permet de retrouver
    # "un autre item de ce lot a-t-il deja ete cree ?" quand chaque ligne
    # part dans sa propre operation CRUD PowerSync (voir get_lab_result_by_batch_uuid,
    # remplace la logique "le premier de la boucle genere, les suivants
    # reutilisent" qui supposait un seul appel HTTP synchrone).
    # default=uuid.uuid4 (pas seulement le DEFAULT gen_random_uuid() cote DB,
    # migration 012) : sans lui, toute construction directe LabResult(**data)
    # qui ne passe pas 'uuid' envoie un NULL explicite (SQLAlchemy inclut les
    # colonnes NOT NULL sans default connu dans l'INSERT), violant la
    # contrainte - meme motif deja etabli sur patients.uuid/medical_records.uuid.
    uuid: Mapped[Optional["uuid.UUID"]] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    batch_uuid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    prescribed_by_name: Mapped[Optional[str]] = mapped_column(String(100))

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

    interpretation: Mapped[Optional[str]] = mapped_column(String(50))
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)

    result: Mapped["LabResult"] = relationship("LabResult", back_populates="details")
    parametre: Mapped["Parametre"] = relationship("Parametre", back_populates="result_details")
