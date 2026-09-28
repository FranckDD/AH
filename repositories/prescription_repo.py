# repositories/prescription_repo.py
import uuid
from sqlalchemy import text
from models.database import DatabaseManager
from sqlalchemy.orm import Session
from models.prescription import Prescription
from models.patient import Patient
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlalchemy import and_
from datetime import date, timedelta
from typing import List, Optional, Tuple

class PrescriptionDateOrderError(ValueError):
    """La date de fin resultante serait anterieure a la date de debut resultante."""
    pass


class PrescriptionMissingDurationError(ValueError):
    """Une prescription non-labo resultante n'a pas de duration (colonne NOT NULL en base)."""
    pass


class PrescriptionContentError(ValueError):
    """
    Une prescription non-labo resultante n'a pas de medicament, ou une
    prescription labo resultante n'a pas de liste d'examens. Regroupees
    sous une seule exception (contrairement a PrescriptionMissingDurationError,
    qui protege une contrainte NOT NULL en base independante du type de
    prescription) : medicament et liste d'examens sont les deux faces
    d'une meme regle metier - laquelle des deux est requise depend
    entierement de is_lab_order, exactement le calcul deja fait par
    check_content() cote schema. Le message precise le champ concerne,
    l'appelant API n'a pas besoin de distinguer les deux cas par le type
    d'exception.
    """
    pass


class PrescriptionRepository:
    def __init__(self, session: Session):
        self.session = session

    def _validate_content_consistency(
        self, prescription: Prescription, touched_keys: Optional[set] = None
    ) -> None:
        """
        Verifie l'etat EFFECTIF de la prescription (apres creation, ou
        apres fusion d'une mise a jour partielle sur l'objet existant) -
        pas seulement les champs presents dans la requete en cours.
        Appelee par create() et update() pour ne pas dupliquer la regle.

        touched_keys : cles explicitement presentes dans le payload de
        CETTE requete. None pour une creation (l'objet est construit en
        un seul appel, tout est implicitement "fourni" par le payload
        ou par les valeurs par defaut du schema - deja valide en amont
        par check_content()). Pour une mise a jour, utilise pour
        decider si lab_exams_list doit etre verifiee (voir plus bas).

        prescriptions.duration est NOT NULL en base. Une prescription
        labo la remplit automatiquement ("N/A", cote schema Pydantic,
        set_defaults_for_lab_orders). Une prescription non-labo doit
        fournir une valeur reelle - y compris quand la bascule
        is_lab_order True -> False se fait sans reenvoyer duration
        (registre E6 ; verifie explicitement sur ce cas, le plus
        subtil : une prescription labo existante dont duration est
        deja NULL en base bascule vers non-labo sans fournir duration).

        Meme logique pour medication : requise des qu'une prescription
        est effectivement non-labo, y compris apres bascule sans
        reenvoyer medication.

        lab_exams_list est traitee differemment : c'est une regle
        metier pure (aucune contrainte NOT NULL en base - la colonne a
        un DEFAULT '[]'::jsonb), pas une contrainte a proteger a tout
        prix. Sur une mise a jour qui bascule is_lab_order (False ->
        True) SANS toucher lab_exams_list, exiger l'etat effectif
        rejetterait a tort la bascule : une prescription qui n'a jamais
        ete labo a '[]' en base (valeur par defaut de la colonne,
        jamais reellement "fournie" par personne), pas une vraie liste
        vide envoyee par un client. Verifiee seulement si le client a
        explicitement touche ce champ dans cette requete (ou toujours,
        sur une creation, ou aucun etat prealable n'existe a preserver).
        """
        if not prescription.is_lab_order:
            if not prescription.duration:
                raise PrescriptionMissingDurationError(
                    "La durée est requise pour une prescription qui n'est pas une demande d'examen."
                )
            if not prescription.medication:
                raise PrescriptionContentError(
                    "Le nom du médicament est requis pour une prescription qui n'est pas une demande d'examen."
                )
        else:
            if touched_keys is None or "lab_exams_list" in touched_keys:
                if not prescription.lab_exams_list or len(prescription.lab_exams_list) == 0:
                    raise PrescriptionContentError(
                        "La liste des examens est requise pour une demande d'examen."
                    )

    def list_paginated_with_relations(
        self,
        page: int = 1,
        per_page: int = 20,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        patient_id: Optional[int] = None,
        search: Optional[str] = None
    ) -> Tuple[List[Prescription], int]:
        """
        Retourne (items, total) avec joined patient.
        search -> recherche sur Patient.code_patient ou Prescription.medication (ilike %s%)
        Filtrage par date sur start_date (utilisable avec date_from/date_to)
        """
        q = self.session.query(Prescription).options(
            joinedload(Prescription.patient)
        ).order_by(Prescription.start_date.desc())

        if date_from and date_to:
            q = q.filter(and_(Prescription.start_date >= date_from, Prescription.start_date <= date_to))

        if patient_id:
            q = q.filter(Prescription.patient_id == patient_id)

        if search:
            s = f"%{search}%"
            # join patient to search by code / name if needed
            q = q.join(Patient, Prescription.patient).filter(
                (Patient.code_patient.ilike(s)) |
                (Patient.first_name.ilike(s)) |
                (Patient.last_name.ilike(s)) |
                (Prescription.medication.ilike(s))
            )

        total = q.count()
        skip = max(0, (int(page) - 1) * int(per_page))
        items = q.offset(skip).limit(int(per_page)).all()
        return items, total    

    def list(self, patient_id=None, page=1, per_page=20):
        q = self.session.query(Prescription)
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        return q.order_by(Prescription.start_date.desc()) \
                .offset((page-1)*per_page) \
                .limit(per_page).all()

    def get(self, prescription_id):
        return self.session.get(Prescription, prescription_id)

    def create(self, data: dict) -> Prescription:
        """
        Crée une prescription via l'ORM directement.
        Plus besoin de procédure stockée.
        """
        try:
            # Le modele attend un uuid.UUID (colonne UUID(as_uuid=True)),
            # pas une chaine brute - meme motif que appointment_repo.py.
            # Si absent/None, le defaut Postgres (gen_random_uuid()) s'applique.
            if data.get('uuid') is not None and not isinstance(data['uuid'], uuid.UUID):
                data['uuid'] = uuid.UUID(str(data['uuid']))

            # On crée l'objet directement avec le dictionnaire
            # SQLAlchemy va mapper les clés du dict aux colonnes du modèle
            new_prescription = Prescription(**data)

            self._validate_content_consistency(new_prescription)

            self.session.add(new_prescription)
            self.session.commit()
            
            # Refresh pour récupérer l'ID généré et les valeurs par défaut (ex: uuid)
            self.session.refresh(new_prescription)
            return new_prescription
        except Exception as e:
            self.session.rollback()
            raise e

    def update(self, prescription_id: int, data: dict) -> Optional[Prescription]:
        """
        Met à jour via l'ORM.
        """
        try:
            # 1. On récupère l'objet existant
            prescription = self.get(prescription_id)
            if not prescription:
                return None

            # 2. On met à jour chaque attribut présent dans data
            for key, value in data.items():
                # On s'assure que l'attribut existe dans le modèle pour éviter les erreurs
                if hasattr(prescription, key):
                    setattr(prescription, key, value)

            # Un PUT partiel peut ne fournir que start_date OU end_date :
            # on valide l'ordre des dates EFFECTIVES (apres fusion avec
            # les valeurs deja en base), pas seulement celles de cette
            # requete - sinon un changement de start_date seul pourrait
            # depasser silencieusement l'end_date deja existante, sans
            # que rien ne le detecte (l'ancienne procedure stockee le
            # faisait ; elle n'est plus appelee depuis le passage a l'ORM).
            if prescription.start_date is not None and prescription.end_date is not None:
                if prescription.end_date < prescription.start_date:
                    raise PrescriptionDateOrderError(
                        "La date de fin ne peut pas être antérieure à la date de début."
                    )

            self._validate_content_consistency(prescription, touched_keys=set(data.keys()))

            # 3. Commit
            self.session.commit()
            self.session.refresh(prescription)
            return prescription
        except (PrescriptionDateOrderError, PrescriptionMissingDurationError, PrescriptionContentError):
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise e

    def delete(self, prescription_id: int) -> bool:
        try:
            prescription = self.get(prescription_id)
            if prescription:
                self.session.delete(prescription)
                self.session.commit()
                return True
            return False
        except Exception:
            self.session.rollback()
            raise

    def find_by_date_range(self, start_date: date, end_date: date) -> List:
        return (
            self.session
                .query(Prescription)
                .filter(func.date(Prescription.start_date) >= start_date)
                .filter(func.date(Prescription.end_date) <= end_date)
                .all()
        )

    def find_renewals_for_doctor(self, doctor_id: int, within_days: int = 14):
        """
        Retourne ordonnances dont end_date dans (today .. today+within_days) pour le docteur.
        """
        today = date.today()
        target = today + timedelta(days=within_days)
        return (
            self.session.query(Prescription)
                .filter(Prescription.prescribed_by == doctor_id)
                .filter(func.date(Prescription.end_date) >= today)
                .filter(func.date(Prescription.end_date) <= target)
                .order_by(Prescription.end_date)
                .all()
        )
    
    def count_renewals_for_doctor(self, doctor_id: int, within_days: int = 14) -> int:
        today = date.today()
        target = today + timedelta(days=within_days)
        q = (
            self.session.query(func.count(Prescription.prescription_id))
                .filter(Prescription.prescribed_by == doctor_id)
                .filter(func.date(Prescription.end_date) >= today)
                .filter(func.date(Prescription.end_date) <= target)
        )
        return int(q.scalar() or 0)

    def count_active_for_doctor(self, doctor_id: int) -> int:
        q = self.session.query(func.count(Prescription.prescription_id)).filter(Prescription.prescribed_by == doctor_id).filter(Prescription.status == 'active')
        return int(q.scalar() or 0)
    
    def count_by_prescription_date(self, prescription_date: date, doctor_id: Optional[int] = None) -> int:
        """Compte les prescriptions pour une date spécifique, filtre optionnel par médecin."""
        query = (
            self.session.query(Prescription)
            .filter(func.date(Prescription.start_date) == prescription_date)
        )
        if doctor_id is not None:
            query = query.filter(Prescription.prescribed_by == doctor_id)
        return query.count()

    def count_by_prescription_date_range(self, start_date: date, end_date: date, doctor_id: Optional[int] = None) -> int:
        """Compte les prescriptions dans une plage de dates, filtre optionnel par médecin."""
        query = (
            self.session.query(Prescription)
            .filter(func.date(Prescription.start_date) >= start_date)
            .filter(func.date(Prescription.start_date) <= end_date)
        )
        if doctor_id is not None:
            query = query.filter(Prescription.prescribed_by == doctor_id)
        return query.count()