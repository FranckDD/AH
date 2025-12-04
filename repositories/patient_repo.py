# repositories/patient_repository.py
from datetime import date
from sqlalchemy import text, or_
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
from sqlalchemy.engine import Result



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
        """
        Crée un nouveau patient via la fonction stockée Postgres.
        NE FAIT PAS de commit, la transaction est gérée par le Service appelant.
        """
        # 1. Génération du code et préparation des params
        code = self.generate_patient_code(
            birth_date=data['birth_date'],
            last_name=data['last_name'],
            first_name=data['first_name'],
            mother_name=data.get('mother_name', '')
        )

        def _get(x, default=None):
            v = data.get(x, default)
            if isinstance(v, str) and v.strip() == "": return None
            return v
        
        # 2. Paramètres pour la FUNCTION
        # J'ai ajouté l'utilisation de 'full_name' comme fallback pour 'username' 
        # car 'full_name' semble être plus complet dans votre modèle User.
        creator_name = getattr(current_user, "full_name", getattr(current_user, "username", None))
        
        params = {
            "code_patient": code,
            "first_name": _get("first_name"),
            "last_name": _get("last_name"),
            "birth_date": _get("birth_date"),
            "gender": _get("gender"),
            "contact_phone": _get("contact_phone"),
            "residence": _get("residence"),
            "national_id": _get("national_id"),
            "assurance": _get("assurance"),
            "father_name": _get("father_name"),
            "mother_name": _get("mother_name"),
            "created_by": getattr(current_user, "user_id", None),
            "created_by_name": creator_name,
            "last_updated_by": getattr(current_user, "user_id", None),
            "last_updated_by_name": creator_name,
            
            "is_clinical": data.get('is_clinical', False),
            "is_toxicology": data.get('is_toxicology', False),
            "is_spiritual": data.get('is_spiritual', False),
        }

        sql = text("""
            SELECT * FROM public.create_patient(
                p_code_patient          => :code_patient,
                p_first_name            => :first_name,
                p_last_name             => :last_name,
                p_birth_date            => :birth_date,
                p_gender                => :gender,
                p_contact_phone         => :contact_phone,
                p_residence             => :residence,
                p_national_id           => :national_id,
                p_assurance             => :assurance,
                p_father_name           => :father_name,
                p_mother_name           => :mother_name,
                p_created_by            => :created_by,
                p_created_by_name       => :created_by_name,
                p_last_updated_by       => :last_updated_by,
                p_last_updated_by_name  => :last_updated_by_name,
                p_is_clinical           => :is_clinical,
                p_is_toxicology         => :is_toxicology,
                p_is_spiritual          => :is_spiritual
            );
        """)

        # 🛑 PAS DE try/except/commit/rollback ICI
        
        result: Result = self.session.execute(sql, params)
        row = result.fetchone()

        if row is None:
            # Laisse l'exception remonter, le Controller gérera le rollback.
            raise Exception("La fonction stockée n'a retourné aucune donnée.")
        
        patient_id, patient_code = row[0], row[1]
        
        # 🛑 self.session.commit() RETIRÉ
        
        return int(patient_id), patient_code

    def update_patient(self, patient_id: int, data: dict, current_user) -> int:
        """
        Met à jour un patient via la procédure stockée.
        NE FAIT PAS de commit, la transaction est gérée par le Service appelant.
        """
        
        updater_name = getattr(current_user, "full_name", getattr(current_user, "username", None))
        
        params = {
            'patient_id': patient_id,
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'birth_date': data.get('birth_date'),
            'gender': data.get('gender'),
            'national_id': data.get('national_id'),
            'contact_phone': data.get('contact_phone'),
            'assurance': data.get('assurance'),
            'residence': data.get('residence'),
            'father_name': data.get('father_name'),
            'mother_name': data.get('mother_name'),
            'last_updated_by': current_user.user_id,
            'last_updated_by_name': updater_name,
            
            # Drapeaux
            "is_clinical": data.get('is_clinical'),
            "is_toxicology": data.get('is_toxicology'),
            "is_spiritual": data.get('is_spiritual'),
        }

        sql = text("""
            CALL public.update_patient(
                p_patient_id            => :patient_id,
                p_first_name            => :first_name,
                p_last_name             => :last_name,
                p_birth_date            => :birth_date,
                p_gender                => :gender,
                p_national_id           => :national_id,
                p_contact_phone         => :contact_phone,
                p_assurance             => :assurance,
                p_residence             => :residence,
                p_father_name           => :father_name,
                p_mother_name           => :mother_name,
                p_last_updated_by       => :last_updated_by,
                p_last_updated_by_name  => :last_updated_by_name,
                p_is_clinical           => :is_clinical,
                p_is_toxicology         => :is_toxicology,
                p_is_spiritual          => :is_spiritual
            );
        """)

        # 🛑 Remplacer le try/except/commit/rollback par une simple exécution:
        self.session.execute(sql, params)
        
        # 🛑 self.session.commit() RETIRÉ
        
        return patient_id



    def delete_patient(self, patient_id: int, user_id: int) -> bool:
        """Suppression Logique (Soft Delete)"""
        # Vérif existence + non supprimé
        exists = self.session.query(Patient).filter(Patient.patient_id == patient_id, Patient.is_deleted == False).first()
        if not exists:
            return False

        # Appel procédure delete (qui fait un UPDATE is_deleted=true)
        sql = text("CALL public.delete_patient(:patient_id, :deleted_by)")
        try:
            self.session.execute(sql, {'patient_id': patient_id, 'deleted_by': user_id})
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, patient_id: int) -> Optional[Dict[str, Any]]:
        # On ajoute le filtre is_deleted == False
        p = self.session.query(Patient).filter(Patient.patient_id == patient_id, Patient.is_deleted == False).first()
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
            'mother_name': p.mother_name,
            # 🟢
            'is_clinical': p.is_clinical,
            'is_toxicology': p.is_toxicology,
            'is_spiritual': p.is_spiritual
        }
    
    def list_patients(self, page: int = 1, per_page: int = 10, search: Optional[str] = None, filters: Dict[str, bool] = None):
        # Filtre de base : Non supprimés
        query = self.session.query(Patient).filter(Patient.is_deleted == False)

        # 1. Filtres de Service
        if filters:
            if filters.get('is_clinical'):
                query = query.filter(Patient.is_clinical == True)
            if filters.get('is_toxicology'):
                query = query.filter(Patient.is_toxicology == True)
            if filters.get('is_spiritual'):
                query = query.filter(Patient.is_spiritual == True)

        # 2. Recherche
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.national_id.ilike(term),
                    Patient.code_patient.ilike(term),
                    Patient.contact_phone.ilike(term)
                )
            )
        
        query = query.order_by(Patient.last_updated_at.desc()) 
        return query.offset((page - 1) * per_page).limit(per_page).all()
    
    def find_by_code(self, code: Optional[str]):
        if not code: return None
        raw = code.strip().upper()
        if not raw.startswith("AH2-"): raw = "AH2-" + raw
        
        return self.session.query(Patient).filter(
            func.upper(Patient.code_patient) == raw,
            Patient.is_deleted == False # <-- ICI
        ).first()
    
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
    
    def _day_range(self, target_day: date) -> (datetime, datetime): # type: ignore
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
    
    def count_patients_by_creator_role(self, role_name: str) -> int:
        """
        Compte le nombre total de patients créés par des utilisateurs ayant un rôle spécifique.
        """
        q = (
            self.session.query(Patient.patient_id) # Sélectionner l'ID pour le comptage
            .join(User, Patient.created_by == User.user_id)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
            .filter(func.lower(ApplicationRole.role_name) == role_name.lower())
            .distinct() # S'assurer de compter les patients uniques
        )
        return q.count()
    
    SECRETARY_ROLE_NAME = "secretaire" # Constante pour la clarté

    # 1. KPI Nouveaux Patients Spirituels (sur une période)
    def count_new_spiritual_patients_by_range(self, start_date: datetime, end_date: datetime) -> int:
        """
        Compte le nombre de patients créés par une 'secretaire' dans une plage de dates.
        """
        q = (
            self.session.query(Patient.patient_id)
            .join(User, Patient.created_by == User.user_id)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
            .filter(func.lower(ApplicationRole.role_name) == SECRETARY_ROLE_NAME) # type: ignore
            .filter(Patient.created_at >= start_date)
            .filter(Patient.created_at < end_date)
            .distinct()
        )
        return q.count()

    # 2. KPI Statut Actif/Inactif des Patients Spirituels
    def get_spiritual_patient_status_distribution(self, active_threshold_days: int = 365) -> Dict[str, int]:
        """
        Calcule la distribution Actifs/Inactifs UNIQUEMENT pour les patients Spirituels (créés par 'secretaire').
        """
        date_limit = datetime.combine(date.today() - timedelta(days=active_threshold_days), time.min)

        # 1. Sous-requête des patients spirituels
        spiritual_patients_query = (
            self.session.query(Patient)
            .join(User, Patient.created_by == User.user_id)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
            .filter(func.lower(ApplicationRole.role_name) == SECRETARY_ROLE_NAME)
        )
        
        # 2. Compter le total des patients spirituels
        total_count = spiritual_patients_query.count()

        # 3. Compter les patients spirituels actifs (ayant un RDV récent)
        active_patient_ids_query = (
            spiritual_patients_query
            .join(Appointment, Patient.patient_id == Appointment.patient_id)
            .filter(Appointment.appointment_date >= date_limit)
            .distinct()
            .subquery()
        )

        active_count = self.session.query(func.count(active_patient_ids_query.c.patient_id)).scalar()
        
        inactive_count = total_count - int(active_count or 0)

        return {
            "active_patients_count": int(active_count or 0),
            "inactive_patients_count": inactive_count,
            "total_patients_count": total_count,
        }

    # 3. KPI Répartition Assurance des Patients Spirituels
    def get_spiritual_assurance_distribution(self) -> Dict[str, int]:
        """
        Compte le nombre de patients par type d'assurance, UNIQUEMENT pour les patients Spirituels.
        """
        q = (
            self.session.query(Patient.assurance, func.count(Patient.patient_id))
            .join(User, Patient.created_by == User.user_id)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
            .filter(func.lower(ApplicationRole.role_name) == SECRETARY_ROLE_NAME)
            .group_by(Patient.assurance)
            .all()
        )
        
        result = {}
        for assurance_type, count in q:
            key = assurance_type.strip() if assurance_type else "Non spécifié"
            result[key] = int(count)
            
        return result

