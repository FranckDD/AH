# repositories/patient_repository.py
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session
from models.database import DatabaseManager
from models.patient import Patient

class PatientRepository:
    def __init__(self, db_url=None):
        # Permet d'injecter une URL différente pour tests
        self.db: DatabaseManager = DatabaseManager(db_url or "postgresql://postgres:Admin_2025@localhost/AH2")
        self.session: Session    = self.db.get_session()

    def generate_patient_code(self, birth_date: date, last_name: str, first_name: str, mother_name: str) -> str:
        prefix = "AH2-"
        year   = birth_date.strftime('%y')
        month  = birth_date.strftime('%m')
        day    = birth_date.strftime('%d')
        letter_last   = (last_name[0] if last_name else 'X').upper()
        letter_mother = (mother_name[0] if mother_name else 'X').upper()
        return f"{prefix}{year}{month}{day}{letter_last}{letter_mother}"

    def create_patient(self, data: dict, current_user) -> int:
        code = self.generate_patient_code(
            birth_date  = data['birth_date'],
            last_name   = data['last_name'],
            first_name  = data['first_name'],
            mother_name = data.get('mother_name', '')
            
        )
        sql = text("""
            CALL public.create_patient(
                :code_patient, :first_name, :last_name, :birth_date,
                :gender, :contact_phone, :residence,
                :national_id, :assurance, :father_name, :mother_name, :created_by, :created_by_name,
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

    def get_by_id(self, patient_id: int) -> dict:
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

    def list_patients(self, page: int=1, per_page: int=10, search: str=None):
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
    
    def find_by_code(self, code: str):
        """Retourne le Patient dont code_patient == code, ou None."""
        return (
            self.session
                .query(Patient)
                .filter(Patient.code_patient == code)
                .first()
        )
