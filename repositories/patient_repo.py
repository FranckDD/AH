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
from datetime import datetime, date, timedelta


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
        code = self.generate_patient_code(
            birth_date  = data['birth_date'],
            last_name   = data['last_name'],
            first_name  = data['first_name'],
            mother_name = data.get('mother_name', '')
            
        )
        sql = text("""
            CALL public.create_patient(
                :code_patient, :first_name, :last_name, :birth_date,
                :gender, :national_id, :contact_phone, :assurance, :residence,
                :father_name, :mother_name, :created_by, :created_by_name,
    :last_updated_by, :last_updated_by_name 
                   ) """
        )
        params = {
            'code_patient'  : code,
            'first_name'    : data['first_name'],
            'last_name'     : data['last_name'],
            'birth_date'    : data['birth_date'],
            'gender'        : data.get('gender'),
            'contact_phone' : data.get('contact_phone'),
            'residence'     : data.get('residence'),
            'national_id'   : data.get('national_id'),
            'assurance'     : data.get('assurance'),
            'father_name'   : data.get('father_name'),
            'mother_name'   : data.get('mother_name'),
            'created_by'    : current_user.user_id,
            'created_by_name': current_user.username,
            'last_updated_by': current_user.user_id,
            'last_updated_by_name':current_user.username
        }
        self.session.execute(sql, params)
        new_id = self.session.execute(text("SELECT currval('patients_patient_id_seq')")).scalar_one()
        self.session.commit()
        return new_id, code

    def update_patient(self, patient_id: int, data: dict, current_user) -> int:
        sql = text("""
            CALL public.update_patient(
                :patient_id,
                :first_name, :last_name, :birth_date, :gender,
                :national_id, :contact_phone, :assurance, :residence,
                :father_name, :mother_name,
                :last_updated_by, :last_updated_by_name
            )
        """)

        # on reprend data (first_name, last_name, …) et on ajoute les deux clés
        params = {
            **data,
            'patient_id'           : patient_id,
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
        Renvoie des objets Patient ORM (ou dict selon ta convention).
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

