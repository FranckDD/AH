# models/lab.py
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import String, Integer, SmallInteger, Numeric, DateTime, ForeignKey, Text, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID # <--- IMPORT IMPORTANT
import uuid
from models.patient import Patient
from sqlalchemy.sql import func
from sqlalchemy import event
from .database import Base


class Examen(Base):
    __tablename__ = "examens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(Text, nullable=False)
    categorie: Mapped[str] = mapped_column(Text, nullable=False)

    parametres: Mapped[List["Parametre"]] = relationship("Parametre", back_populates="examen")
    prix = mapped_column(Numeric(10, 2), default=0.0)
    # Catalogue etendu (migration 041) : impression fidele aux fiches du laboratoire.
    # layout_family : CHECK en base (table, three_columns, label_value, narrative, boxed).
    section: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    layout_family: Mapped[str] = mapped_column(String(20), nullable=False, default="label_value", server_default="label_value")
    signature_label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    print_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    # Migration 045 : blocs de texte fixe de la fiche [{position, text, style}] (liste ordonnee).
    fixed_notes: Mapped[Optional[list]] = mapped_column(JSONB(none_as_null=True), nullable=True)


class Parametre(Base):
    __tablename__ = "parametres"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    examen_id: Mapped[int] = mapped_column(ForeignKey("examens.id"), nullable=False)
    nom_parametre: Mapped[str] = mapped_column(Text, nullable=False)
    unite: Mapped[str] = mapped_column(Text, nullable=False)
    type_valeur: Mapped[str] = mapped_column(Text, nullable=False)
    # Position d'affichage dans l'examen (banc, detail, fiche imprimee, catalogue)
    ordre: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    examen: Mapped["Examen"] = relationship("Examen", back_populates="parametres")
    reference_ranges: Mapped[List["ReferenceRange"]] = relationship("ReferenceRange", back_populates="parametre")
    result_details: Mapped[List["LabResultDetail"]] = relationship("LabResultDetail", back_populates="parametre")
    # --- OPTIMISATION : UI DYNAMIQUE ---
    input_type: Mapped[str] = mapped_column(String(20), default="numeric") # numeric, text, area, select
    options_list: Mapped[Optional[str]] = mapped_column(Text) # Pour 'select', ex: "Positif,Négatif"
    # Catalogue etendu (migration 041). result_kind : CHECK en base (numeric, text, choice, pos_neg) ;
    # type_valeur / input_type restent la source du banc de saisie actuel.
    print_label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_kind: Mapped[str] = mapped_column(String(10), nullable=False, default="numeric", server_default="numeric")
    choices: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    # Migration 045 : sous-titre de la fiche et texte de norme tel qu'imprime (tout le parametre).
    group_label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    norm_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ReferenceRange(Base):
    __tablename__ = "reference_ranges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parametre_id: Mapped[int] = mapped_column(ForeignKey("parametres.id"), nullable=False)
    sexe: Mapped[str] = mapped_column(String(1), nullable=False)
    # Anciennes bornes en annees entieres (lecture heritee, nullables depuis la migration 040).
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Bornes en jours (inclusives) et en semaines d'amenorrhee ; NULL = borne ouverte / sans critere.
    age_min_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ga_min_weeks: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    ga_max_weeks: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    valeur_min: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    valeur_max: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    # Migration 045 : texte imprime de cette plage (« 4,0 - 5,5 », zeros de precision gardes).
    display_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    # Semaines d'amenorrhee au prelevement (0 a 45, CHECK en base, migration 039). Donnee de grossesse :
    # jamais exposee au secretariat (voir utils/pregnancy_visibility.py).
    gestational_age_weeks: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    # Grossesse d'un patient EXTERNE (statut, DPA, numero de suivi, SA) : colonne SEPAREE d'external_patient_info,
    # qui est livre par un flux PowerSync. Aucun flux ne selectionne cette colonne (migration 042).
    external_pregnancy_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Statut de grossesse AU MOMENT de la reception (enceinte / non_enceinte / inconnu) : base du rapport de
    # subvention, independante du statut actuel du dossier. NULL pour les lignes anterieures a la migration 042.
    pregnancy_status_at_result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Ligne de facture (examen facture a la caisse) deja recue : index unique partiel en base
    # (migration 030), une ligne ne se recoit qu'une fois.
    origin_caisse_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("caisse_item.item_id", ondelete="SET NULL"), nullable=True)
    # Resultat valide puis corrige (voir LabResultAmendment) - jamais modifie en silence.
    corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    corrected_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    # Numero de dossier officiel NNN/NN du JJ/MM/AAAA (migration 037) : attribue par le serveur a
    # l'enregistrement a la reception (utils/lab_dossier.py), nul tant que non attribue.
    dossier_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dossier_counter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dossier_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    patient_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Texte libre CONCLUSION (<= 5000, CHECK en base, migration 044) ; `note` sert de NB.
    conclusion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Copie figee d'impression ecrite UNE fois a la validation (utils/lab_snapshot.py) ; NULL = ancien resultat.
    # Immuable (garde before_update ci-dessous) sauf remplacement par une correction (amend_result), qui
    # archive la copie precedente dans print_snapshot_history. Migration 044.
    print_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, active_history=True)
    print_snapshot_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    print_snapshot_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    print_snapshot_history: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, active_history=True)

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


class LabResultAmendment(Base):
    """Correction d'un resultat deja valide : motif obligatoire + valeurs d'AVANT conservees."""
    __tablename__ = "lab_result_amendments"
    amendment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("lab_results.result_id", ondelete="CASCADE"), nullable=False)
    amended_by: Mapped[Optional[int]] = mapped_column(Integer)
    amended_by_name: Mapped[Optional[str]] = mapped_column(Text)
    amended_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, server_default=func.timezone('Africa/Douala', func.now()))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_values: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    previous_note: Mapped[Optional[str]] = mapped_column(Text)


class LabExternalPrescriber(Base):
    """Memoire des prescripteurs saisis librement pour un patient externe (suggestions a la reception)."""
    __tablename__ = "lab_external_prescribers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False, default='')
    last_used_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

Index("uq_lab_external_prescribers_title_name", LabExternalPrescriber.title, func.lower(LabExternalPrescriber.name), unique=True)


class LabSnapshotImmutableError(Exception):
    """La copie figee d'un resultat valide ne se modifie pas (migration 044)."""


def _guard_print_snapshot(mapper, connection, target):
    """before_update : print_snapshot/_at/_by ne changent qu'une fois (NULL -> copie) ou lors d'une correction
    qui pose `target._snapshot_rewrite_ok = True` (LabRepository.amend_result)."""
    from sqlalchemy import inspect as _inspect
    state = _inspect(target)
    if getattr(target, "_snapshot_rewrite_ok", False):
        return
    for attr in ("print_snapshot", "print_snapshot_at", "print_snapshot_by", "print_snapshot_history"):
        hist = state.attrs[attr].history
        if not hist.has_changes():
            continue
        old = [v for v in (hist.deleted or ()) if v is not None]
        if old:
            raise LabSnapshotImmutableError(
                f"La copie figee du resultat {target.result_id} est immuable (colonne {attr}).")


event.listen(LabResult, "before_update", _guard_print_snapshot)
