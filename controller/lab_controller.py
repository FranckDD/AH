import logging
from repositories.lab_repo import LabRepository
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import func

class LabController:
    def __init__(self, repo: LabRepository, current_user=None):
        self.repo = repo
        self.user = current_user
        self.log = logging.getLogger(__name__)

    # Examens
    def create_examen(self, code:str, nom:str, categorie:str) -> Dict:
        ex = self.repo.create_examen({"code":code, "nom":nom, "categorie":categorie})
        return {"id":ex.id, "code":ex.code}
    
    def list_parametres_for_examen(self, examen_id: int) -> List[Dict]:
        params = self.repo.list_parametres_for_examen(examen_id)
        return [
            {
                "id": p.id,
                "nom_parametre": p.nom_parametre,
                "unite": p.unite,
                "type_valeur": p.type_valeur
            }
            for p in params
        ]

    

    # In LabController class
    def list_examens(self) -> List[Dict]:
        # Add 'categorie' to the returned dictionary
        return [{
            "id": e.id, 
            "code": e.code, 
            "nom": e.nom,
            "categorie": e.categorie  # Add this line
        } for e in self.repo.list_examens()]

    # Résultats
    def create_result(self, patient_id: Optional[int], examen_id: int, details: List[Dict]) -> Dict:
        # génère le code labo avant création
        code_lab = self.generate_lab_code(patient_id)
        lr = self.repo.create_lab_result({
            'patient_id': patient_id,
            'examen_id': examen_id,
            'test_date': datetime.now(),
            'prescribed_by': self.user.id,
            'technician_id': self.user.id,
            'technician_name': self.user.username,
            'code_lab_patient': code_lab   # il faudra ajouter cette colonne à votre modèle LabResult
        })
        for d in details:
            d.update({'result_id': lr.result_id})
            self.repo.add_result_detail(d)
        return {"result_id": lr.result_id, "code_lab_patient": code_lab}

    def get_result(self, result_id:int) -> Optional[Dict]:
        fr = self.repo.get_full_lab_result(result_id)
        if not fr: return None
        return {
            "result":fr,
            "details":fr.details
        }

    def complete_result(self, result_id:int, age:int, sexe:str) -> Dict:
        cr = self.repo.complete_result(result_id, age, sexe)
        return {"status":cr.status}
    
    def list_results_by_status(self, status: str) -> List[Dict]:
        results = self.repo.list_results_by_status(status)
        out = []
        for r in results:
            out.append({
                'result_id':        r.result_id,
                'code_lab_patient': r.code_lab_patient,
                # concaténation inline
                'patient_name':     f"{r.patient.first_name} {r.patient.last_name}",
                'examen_name':      r.examen.nom,
                'test_date':        r.test_date.strftime('%Y-%m-%d %H:%M'),
                'status':           r.status,
            })
        return out


    def get_patient_age(self, result_id: int) -> int:
        res = self.repo.get_full_lab_result(result_id)
        birth = res.patient.birth_date  # suppose birth_date exists
        today = datetime.now().date()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    def get_patient_sex(self, result_id: int) -> str:
        res = self.repo.get_full_lab_result(result_id)
        return res.patient.sexe
    
    def list_params(self) -> List[Dict]:
        return [{
            "id": p.id,
            "nom_parametre": p.nom_parametre,
            "unite": p.unite,
            "type_valeur": p.type_valeur,
            "examen_id": p.examen_id,
            "examen": {
                "id": p.examen.id,
                "nom": p.examen.nom,
                "categorie": p.examen.categorie
            }
        } for p in self.repo.list_parametres()]

    def update_param(self, param_id: int, data: Dict) -> Dict:
        p = self.repo.update_parametre(param_id, data)
        return {"id": p.id} if p else {}

    def delete_param(self, param_id: int) -> None:
        self.repo.delete_parametre(param_id)

    def create_param(self, data: dict) -> Dict:
        p = self.repo.create_parametre(data)
        return {
            "id": p.id,
            "nom_parametre": p.nom_parametre,
            "unite": p.unite,
            "type_valeur": p.type_valeur,
            "examen_id": p.examen_id
        }
    
    def get_param(self, param_id: int) -> Optional[Dict]:
        p = self.repo.get_parametre(param_id)
        if p:
            return {
                "id": p.id,
                "nom_parametre": p.nom_parametre,
                "unite": p.unite,
                "type_valeur": p.type_valeur,
                "examen_id": p.examen_id,
                "examen": {
                    "id": p.examen.id,
                    "nom": p.examen.nom,
                    "categorie": p.examen.categorie
                }
            }
        return None
    
    def list_reference_ranges(self, parametre_id: Optional[int] = None) -> List[Dict]:
        ranges = self.repo.list_reference_ranges(parametre_id)
        return [
            {
                "id":    rr.id,
                "parametre_id":  rr.parametre_id,
                "sexe": rr.sexe,
                "age_min": rr.age_min,
                "age_max": rr.age_max,
                "valeur_min": float(rr.valeur_min),
                "valeur_max": float(rr.valeur_max),
            }
            for rr in ranges
        ]

    def get_reference_range(self, range_id: int) -> Optional[Dict]:
        rr = self.repo.get_reference_range(range_id)
        if not rr:
            return None
        return {
            "id":    rr.id,
            "parametre_id":  rr.parametre_id,
            "sexe": rr.sexe,
            "age_min": rr.age_min,
            "age_max": rr.age_max,
            "valeur_min": float(rr.valeur_min),
            "valeur_max": float(rr.valeur_max),
        }

    def create_reference_range(self, data: Dict) -> Dict:
        """
        data doit contenir : parametre_id, sexe, age_min, age_max, valeur_min, valeur_max
        """
        rr = self.repo.create_reference_range(data)
        return {
            "id": rr.id,
            "parametre_id": rr.parametre_id,
            "sexe": rr.sexe,
            "age_min": rr.age_min,
            "age_max": rr.age_max,
            "valeur_min": float(rr.valeur_min),
            "valeur_max": float(rr.valeur_max),
        }

    def update_reference_range(self, range_id: int, data: Dict) -> Optional[Dict]:
        rr = self.repo.update_reference_range(range_id, data)
        if not rr:
            return None
        return {
            "id": rr.id,
            "parametre_id": rr.parametre_id,
            "sexe": rr.sexe,
            "age_min": rr.age_min,
            "age_max": rr.age_max,
            "valeur_min": float(rr.valeur_min),
            "valeur_max": float(rr.valeur_max),
        }

    def delete_reference_range(self, range_id: int) -> bool:
        return self.repo.delete_reference_range(range_id)
    
    def generate_external_patient_code(self) -> str:
        """Génère un code EXT- unique pour un patient externe"""
        return self.repo.generate_lab_code(patient_id=None)
    
    def create_external_patient(self, data: dict) -> dict:
        """Crée un patient externe et retourne son code"""
        code_patient = self.generate_external_patient_code()
        # Stocker les données du patient externe si nécessaire
        # (dans une table dédiée ou dans la session)
        return {"code_patient": code_patient, **data}
    
   