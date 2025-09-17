# repositories/patient_repository.py
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session
from models.database import DatabaseManager
from models.patient import Patient
from sqlalchemy import func
from models.user import User
from models.application_role import ApplicationRole
from models.appointment import Appointment
from models.medical_record import MedicalRecord
from datetime import datetime, date, timedelta,time
from sqlalchemy.exc import SQLAlchemyError


from typing import Optional, Tuple, Dict, Any, List

class PatientRepository:
    def __init__(self, session: Session):
        self.session = session

    def generate_patient_code(
        self,
        birth_date: date,
        last_name: Optional[str],
        first_name: Optional[str],
        father_name: Optional[str] = None,
        mother_name: Optional[str] = None
    ) -> str:
        prefix = "AH2-"
        ymd = birth_date.strftime('%y%m%d')

        # Lettre parentale : priorité mère → père → X
        parent_initial = (
            (mother_name or '').strip()[0:1].upper()
            or (father_name or '').strip()[0:1].upper()
            or 'X'
        )
        # Lettre nom de famille (ou X)
        last_initial = (last_name or 'X')[0].upper()

        base_code = f"{prefix}{ymd}{last_initial}{parent_initial}"
        code = base_code
        i = 1
        while self.session.query(Patient).filter(Patient.code_patient == code).first():
            i += 1
            code = f"{base_code}{i}"

        return code

    def create_patient(self, data: dict, current_user) -> Tuple[int, str]:
        # Génère le code (ta fonction existante)
        code = self.generate_patient_code(
            birth_date  = data['birth_date'],
            last_name   = data['last_name'],
            first_name  = data['first_name'],
            mother_name = data.get('mother_name', '')
        )

        # Prépare la requête CALL avec affectation nommée (=>)
        sql = text("""
            CALL public.create_patient(
                p_code_patient         => :code_patient,
                p_first_name           => :first_name,
                p_last_name            => :last_name,
                p_birth_date           => :birth_date,
                p_gender               => :gender,
                p_contact_phone        => :contact_phone,
                p_residence            => :residence,
                p_national_id          => :national_id,
                p_assurance            => :assurance,
                p_father_name          => :father_name,
                p_mother_name          => :mother_name,
                p_created_by           => :created_by,
                p_created_by_name      => :created_by_name,
                p_last_updated_by      => :last_updated_by,
                p_last_updated_by_name => :last_updated_by_name
            );
        """)

        # Normalize / fallback values
        def _get(x, default=None):
            v = data.get(x, default)
            # Optionally convert empty strings to None
            if isinstance(v, str) and v.strip() == "":
                return None
            return v

        # ensure birth_date is a date object if possible (SQLAlchemy will adapt date objects)
        bd = data.get("birth_date")
        # (si bd est une str au format ISO, tu peux la parser ici, sinon laisse tel quel)
        params = {
            "code_patient": code,
            "first_name": _get("first_name"),
            "last_name": _get("last_name"),
            "birth_date": bd,
            "gender": _get("gender"),
            "contact_phone": _get("contact_phone"),
            "residence": _get("residence"),
            "national_id": _get("national_id"),
            "assurance": _get("assurance"),
            "father_name": _get("father_name"),
            "mother_name": _get("mother_name"),
            "created_by": getattr(current_user, "user_id", None),
            "created_by_name": getattr(current_user, "username", None),
            "last_updated_by": getattr(current_user, "user_id", None),
            "last_updated_by_name": getattr(current_user, "username", None),
        }

        try:
            # Exécute la procédure avec les binds nommés
            self.session.execute(sql, params)

            # Récupère l'id inséré : currval sur la même session fonctionne
            new_id = self.session.execute(text("SELECT currval('patients_patient_id_seq')")).scalar_one()

            # Commit
            self.session.commit()
            return new_id, code

        except SQLAlchemyError as e:
            # rollback sécurisé et lever l'exception pour remontée
            try:
                self.session.rollback()
            except Exception:
                pass
            raise

    def update_patient(self, patient_id: int, data: dict, current_user) -> int:
        sql = text("""
            CALL public.update_patient(
                p_patient_id           => :patient_id,
                p_first_name           => :first_name,
                p_last_name            => :last_name,
                p_birth_date           => :birth_date,
                p_gender               => :gender,
                p_national_id          => :national_id,
                p_contact_phone        => :contact_phone,
                p_assurance            => :assurance,
                p_residence            => :residence,
                p_father_name          => :father_name,
                p_mother_name          => :mother_name,
                p_last_updated_by      => :last_updated_by,
                p_last_updated_by_name => :last_updated_by_name
            )
        """)

        params = {
            'patient_id'           : patient_id,
            'first_name'           : data.get('first_name'),
            'last_name'            : data.get('last_name'),
            'birth_date'           : data.get('birth_date'),
            'gender'               : data.get('gender'),
            'national_id'          : data.get('national_id'),
            'contact_phone'        : data.get('contact_phone'),
            'assurance'            : data.get('assurance'),
            'residence'            : data.get('residence'),
            'father_name'          : data.get('father_name'),
            'mother_name'          : data.get('mother_name'),
            'last_updated_by'      : current_user.user_id,
            'last_updated_by_name' : current_user.username
        }

        self.session.execute(sql, params)
        self.session.commit()
        return patient_id



    def delete_patient(self, patient_id: int) -> bool:
        self.session.execute(text("CALL public.delete_patient(:patient_id)"), {'patient_id': patient_id})
        self.session.commit()
        return True

    def get_by_id(self, patient_id: int) ->  Optional[Dict[str, Any]]:
        p = self.session.query(Patient).get(patient_id)
        if not p:
            return None
        return {
            'patient_id': p.patient_id,
            'code_patient': p.code_patient,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'birth_date': p.birth_date,
            'gender': p.gender,
            'national_id': p.national_id,
            'contact_phone': p.contact_phone,
            'assurance': p.assurance,
            'residence': p.residence,
            'father_name': p.father_name,
            'mother_name': p.mother_name
        }

    def list_patients(self, page: int=1, per_page: int=10, search: Optional[str] = None):
        query = self.session.query(Patient)
        if search:
            term = f"%{search}%"
            query = query.filter(
                Patient.first_name.ilike(term) |
                Patient.last_name.ilike(term) |
                Patient.national_id.ilike(term) |
                Patient.code_patient.ilike(term)
            )
        return query.order_by(Patient.last_name).offset((page-1)*per_page).limit(per_page).all()
    
    def find_by_code(self, code: Optional[str]):
        """
        Retourne le Patient dont code_patient correspond à 'code', 
        en normalisant :
          - on trim() et on met en majuscules,
          - on ajoute 'AH2-' en préfixe si absent.
        La comparaison est ensuite faite en majuscules (case-insensitive).
        """
        if not code:
            return None

        # 1) Normalisation de la saisie :
        raw = code.strip().upper()
        if not raw.startswith("AH2-"):
            raw = "AH2-" + raw

        # 2) Requête case-insensitive sur code_patient
        return (
            self.session
                .query(Patient)
                .filter(func.upper(Patient.code_patient) == raw)
                .first()
        )
    
    def find_by_creator_role(self, role_name: str):
        """
        Renvoie tous les patients dont le créateur a pour role_name (secrétaire, etc.).
        """
        return (
            self.session.query(Patient)
                .join(User, Patient.created_by == User.user_id)
                .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
                # on compare sur role_name, pas name
                .filter(func.lower(ApplicationRole.role_name) == role_name.lower())
                .order_by(Patient.last_name)
                .all()
        )

    def find_by_id(self, patient_id: int):
        """
        Retourne le Patient dont patient_id == patient_id, ou None si inexistant.
        """
        return self.session.query(Patient).get(patient_id)
    
    def find_for_prescription(self, query: str):
        """
        Retourne l'objet patient (ORM object) ou None.
        Si query est numérique, on recherche par id, sinon par code.
        Cette méthode est un simple wrapper qui utilise les méthodes existantes
        find_by_id / find_by_code (ou get_by_id / find_by_code selon naming).
        """
        if not query:
            return None
        q = query.strip()
        try:
            if q.isdigit():
                pid = int(q)
                # méthode existante pour récupérer par id
                return self.get_by_id(pid)
            # sinon recherche par code
            return self.find_by_code(q)
        except Exception:
            # Ne pas remonter d'exception non gérée — le controller gérera
            return None
    
    def patients_by_consultation_type(self, doctor_id: int):
        """
        Retourne dict {type_consultation: count} pour les patients liés aux RDV du docteur.
        """
        res = (
            self.session.query(Patient.type_consultation, func.count(func.distinct(Patient.patient_id)))
            .join(Appointment, Appointment.patient_id == Patient.patient_id)
            .filter(Appointment.doctor_id == doctor_id)
            .group_by(Patient.type_consultation)
            .all()
        )
        return {k or "Non spécifié": v for k, v in res}
    
    def patients_followed_by_doctor(self, doctor_id: int, page:int=1, per_page:int=50) -> List:
        q = (
            self.session.query(Patient)
            .join(Appointment, Appointment.patient_id == Patient.patient_id)
            .filter(Appointment.doctor_id == doctor_id)
            .group_by(Patient.patient_id)  # distinct patients
            .order_by(Patient.last_name)
        )
        return q.offset((page-1)*per_page).limit(per_page).all()                                                            

    def patients_count_for_doctor(self, doctor_id: int) -> int:
        q = (
            self.session.query(func.count(func.distinct(Patient.patient_id)))
            .join(Appointment, Appointment.patient_id == Patient.patient_id)
            .filter(Appointment.doctor_id == doctor_id)
        )
        return int(q.scalar() or 0)

    def patients_by_consultation_type_for_doctor(self, doctor_id: int, start: Optional[date] = None, end: Optional[date] = None) -> Dict[str,int]:
        """
        Compte patients par type de consultation en joignant medical_records.
        Version simple : compte medical_records (ou les patients liés) ; si tu veux 'dernier motif par patient' => subquery plus bas.
        """
        q = (
            self.session.query(MedicalRecord.motif_code, func.count(func.distinct(MedicalRecord.patient_id)))
            .join(Appointment, Appointment.patient_id == MedicalRecord.patient_id)
            .filter(Appointment.doctor_id == doctor_id)
        )
        if start:
            q = q.filter(func.date(MedicalRecord.consultation_date) >= start)
        if end:
            q = q.filter(func.date(MedicalRecord.consultation_date) <= end)
        q = q.group_by(MedicalRecord.motif_code)
        rows = q.all()
        return { (motif or "Non spécifié"): int(cnt) for motif, cnt in rows }
    
    def patients_for_day(self, doctor_id: int, target_date: date) -> List:
        """
        Retourne la liste (distincte) des patients qui ont un RDV pour ce doctor_id à target_date.
        Renvoie des objets Patient ORM (ou dict selon ta convention).w
        """
        q = (
            self.session.query(Patient)
                .join(Appointment, Appointment.patient_id == Patient.patient_id)
                .filter(Appointment.doctor_id == doctor_id)
                .filter(func.date(Appointment.appointment_date) == target_date)
                .group_by(Patient.patient_id)
                .order_by(Patient.last_name)
        )
        return q.all()
    
    # patient_repo.py
    def count_registered(self, period: str = "day") -> int:
        today = date.today()
        if period == "day":
            return (
                self.session.query(Patient)
                .filter(Patient.created_at >= today)
                .count()
            )
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            return (
                self.session.query(Patient)
                .filter(Patient.created_at >= start_week)
                .count()
            )
        return 0
    

    def count_by_creation_date(self, creation_date: date) -> int:
        """Compte les patients créés à une date spécifique."""
        return (
            self.session.query(Patient)
            .filter(func.date(Patient.created_at) == creation_date)
            .count()
        )

    def count_by_creation_date_range(self, start_date: date, end_date: date) -> int:
        """Compte les patients créés dans une plage de dates."""
        return (
            self.session.query(Patient)
            .filter(func.date(Patient.created_at) >= start_date)
            .filter(func.date(Patient.created_at) <= end_date)
            .count()
        )
    
    def _day_range(self, target_day: date) -> (datetime, datetime):
        start = datetime.combine(target_day, time.min)
        end = start + timedelta(days=1)
        return start, end

    def _get_creation_column(self):
        """
        Retourne l'attribut colonne pour la date de création (created_at, date_created, created_on).
        """
        for name in ("created_at", "date_created", "created_on"):
            col = getattr(Patient, name, None)
            if col is not None:
                return col
        return None

    def find_by_creation_date_range(self,
                                    start_date: datetime,
                                    end_date: datetime,
                                    doctor_id: Optional[int] = None,
                                    page: Optional[int] = None,
                                    per_page: Optional[int] = None) -> List[Patient]:
        """
        Retourne les patients dont la date de création est dans [start_date, end_date).
        Si doctor_id est fourni, filtre sur Patient.created_by == doctor_id (si colonne présente).
        """
        created_col = self._get_creation_column()
        if created_col is None:
            raise RuntimeError("Patient model: aucune colonne de date de création trouvée (checked: created_at, date_created, created_on)")

        q = self.session.query(Patient)

        # Filtre plage
        q = q.filter(created_col >= start_date, created_col < end_date)

        # Si on a un filtre par créateur (created_by)
        if doctor_id is not None and hasattr(Patient, "created_by"):
            q = q.filter(getattr(Patient, "created_by") == doctor_id)

        q = q.order_by(Patient.last_name.asc(), Patient.first_name.asc())

        if page is not None and per_page is not None:
            q = q.offset((int(page) - 1) * int(per_page)).limit(int(per_page))

        return q.all()

    
    def get_new_patients_for_day(self, target_day: date, doctor_id: Optional[int] = None,
                                 page: int = 1, per_page: int = 200) -> List[Patient]:
        start, end = self._day_range(target_day)
        return self.find_by_creation_date_range(start, end, doctor_id=doctor_id, page=page, per_page=per_page)

