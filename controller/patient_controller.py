# controller/patient_controller.py
import logging
from sqlalchemy import func
from typing import Optional, Dict, Any, List    
from models.application_role import ApplicationRole
from models.user import User
from datetime import date, timedelta

class PatientController:
    def __init__(self, repo, current_user):
        self.repo = repo
        self.user = current_user
        self.logger = logging.getLogger(__name__)

    def create_patient(self, data: dict) -> tuple[int,str]:
        required = ['first_name', 'last_name', 'birth_date']
        if any(not data.get(f) for f in required):
            raise ValueError("Champs obligatoires manquants")
        return self.repo.create_patient(data, self.user)

    def update_patient(self, patient_id: int, data: dict) -> tuple[int, str]:
        return self.repo.update_patient(patient_id, data, self.user)

    def delete_patient(self, patient_id: int) -> bool:
        return self.repo.delete_patient(patient_id)

    def get_patient(self, patient_id: int) -> dict:
        return self.repo.get_by_id(patient_id)

    def list_patients(self, page=1, per_page=10, search=None):
        # 1) Récupère le role_name de l'utilisateur via la relation User.role_id
        user_role_name = (
            self.repo.session
                .query(ApplicationRole.role_name)
                .join(User, User.role_id == ApplicationRole.role_id)
                .filter(User.user_id == self.user.user_id)
                .scalar() or ''
        )
        role_lower = user_role_name.lower()

        # 2) Si c'est un secrétaire, on renvoie tous les patients créés par un secrétaire
        if 'secr' in role_lower:
            return self.repo.find_by_creator_role(role_lower)

        # 3) Sinon, pagination + recherche
        return self.repo.list_patients(page=page, per_page=per_page, search=search)
    
    def list_spiritual_patients(self):
        return self.repo.find_by_creator_role('secretaire')
    
    def find_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        p = self.repo.find_by_code(code)
        if not p:
            return None
        return {
            'patient_id':    p.patient_id,
            'code_patient':  p.code_patient,
            'first_name':    p.first_name,
            'last_name':     p.last_name,
            'birth_date':    p.birth_date,
            'gender':        p.gender,
            'national_id':   p.national_id,
            'contact_phone': p.contact_phone,
            'assurance':     p.assurance,
            'residence':     p.residence,
            'father_name':   p.father_name,
            'mother_name':   p.mother_name,
        }

    def find_patient(self, query: str):
        if not query:
            return None
        q = query.strip()
        if q.isdigit():
            pid = int(q)
            return self.repo.find_by_id(pid)
        else:
            return self.repo.find_by_code(q)
        

    def patients_followed_by_doctor(self, doctor_id: Optional[int] = None, page=1, per_page=50):
        d = doctor_id or getattr(self.user, 'user_id', None)
        if d is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.patients_followed_by_doctor(d, page=page, per_page=per_page)

    def patients_by_consultation_type(self, doctor_id: Optional[int] = None, start: Optional[date]=None, end: Optional[date]=None):
        d = doctor_id or getattr(self.user, 'user_id', None)
        if d is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.patients_by_consultation_type_for_doctor(d, start=start, end=end)
    
    def patients_for_day(self, target_date: date, doctor_id: Optional[int] = None):
        d = doctor_id or getattr(self.user, 'user_id', None)
        if d is None:
            raise RuntimeError("doctor_id non disponible")
        return self.repo.patients_for_day(d, target_date)
    
    
    def count_registered(self, period: str = "day") -> int:
        """
        Retourne le nombre de patients enregistrés selon la période.
        period: "day" pour aujourd'hui, "week" pour cette semaine
        """
        today = date.today()
        
        if period == "day":
            return self.repo.count_by_creation_date(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return self.repo.count_by_creation_date_range(start_week, end_week)
        else:
            raise ValueError("Période non valide. Utilisez 'day' ou 'week'")

    def find_by_patient_presc(self, query: str):
        """
        Méthode dédiée au lookup depuis la UI prescription.
        Retourne une dict (comme find_by_code / find_patient) ou None.
        """
        if not query:
            return None
        q = query.strip()
        try:
            # utilise le repo utilitaire
            p = self.repo.find_for_prescription(q)
            if not p:
                return None

            # si repo renvoie un objet ORM, normaliser en dict similaire à find_by_code
            if hasattr(p, "__dict__") and not isinstance(p, dict):
                return {
                    'patient_id':    getattr(p, 'patient_id', None),
                    'code_patient':  getattr(p, 'code_patient', None),
                    'first_name':    getattr(p, 'first_name', None),
                    'last_name':     getattr(p, 'last_name', None),
                    'birth_date':    getattr(p, 'birth_date', None),
                    'gender':        getattr(p, 'gender', None),
                    'national_id':   getattr(p, 'national_id', None),
                    'contact_phone': getattr(p, 'contact_phone', None),
                    'assurance':     getattr(p, 'assurance', None),
                    'residence':     getattr(p, 'residence', None),
                    'father_name':   getattr(p, 'father_name', None),
                    'mother_name':   getattr(p, 'mother_name', None),
                }
            # sinon retourner tel quel (si déjà dict)
            return p
        except Exception as e:
            self.logger.exception("Erreur find_by_patient_presc: %s", e)
            return None
        
    def new_patients_for_day(self, target_date: date, doctor_id: Optional[int] = None,
                         page: int = 1, per_page: int = 200) -> List[Dict[str, Any]]:
        """
        Retourne la liste des patients créés le jour 'target_date'.
        Renvoie une liste de dicts simples (pratique pour l'UI).
        """
        # Si doctor_id non fourni, on peut laisser None (global) ou utiliser self.user.user_id selon les besoins.
        pats = self.repo.get_new_patients_for_day(target_date, doctor_id=doctor_id, page=page, per_page=per_page)

        def serialize(p):
            # tolérance sur noms d'attributs
            pid = getattr(p, "patient_id", None) or getattr(p, "id", None)
            code = getattr(p, "code_patient", None)
            fname = getattr(p, "first_name", None)
            lname = getattr(p, "last_name", None)
            birth = getattr(p, "birth_date", None)
            # compute age if birth_date is date
            age = None
            try:
                if birth:
                    today = date.today()
                    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except Exception:
                age = None
            return {
                "patient_id": pid,
                "code_patient": code,
                "first_name": fname,
                "last_name": lname,
                "birth_date": birth,
                "age": age,
            }

        return [serialize(p) for p in pats]    

