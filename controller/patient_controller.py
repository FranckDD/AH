# controllers/patient_controller.py
import logging
from sqlalchemy import func
from models.application_role import ApplicationRole
from models.user import User

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
    
    def find_by_code(self, code: str) -> dict:
        p = self.repo.find_by_code(code)
        if not p:
            return None
        # selon votre design, renvoyez un dict ou un objet
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
        """
        Si 'query' est composé uniquement de chiffres (isdigit()), on recherche par ID.
        Sinon, on cherche par code (find_by_code), ce qui fera la normalisation (majuscule + 'AH2').
        Renvoie un objet Patient ou None.
        """
        if not query:
            return None

        q = query.strip()
        if q.isdigit():
            # Recherche par ID
            pid = int(q)
            return self.repo.find_by_id(pid)
        else:
            # Recherche par code, normalisation incluse dans find_by_code
            return self.repo.find_by_code(q)
        
        
