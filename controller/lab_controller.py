import logging
from models.lab import Examen
from repositories.lab_repo import LabRepository
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import func

class LabController:
    def __init__(self, repo: LabRepository, current_user=None):
        self.repo = repo
        self.user = current_user
        self.log = logging.getLogger(__name__)


    # --- HELPER D'AFFICHAGE ---
    def _format_patient_name(self, result) -> str:
        """
        Génère le nom du patient pour l'affichage.
        Gère les cas Internes (relation SQL) et Externes (JSON).
        """
        # 1. Cas Interne : Relation SQL existante
        if result.patient:
            return f"{result.patient.first_name} {result.patient.last_name}"
        
        # 2. Cas Externe : Données dans le JSONB
        if result.external_patient_info:
            # On suppose que le JSON contient une clé 'nom' ou 'name'
            info = result.external_patient_info
            nom = info.get('nom') or info.get('name') or 'Inconnu'
            return f"{nom} (Externe)"
            
        return "Patient Inconnu"    

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

    def list_examens(self) -> List[Examen]:
            """Utilisé par la vue caisse pour afficher la liste des examens"""
            return self.repo.list_all_examens()

    def get_examen(self, examen_id: int) -> Examen:
        ex = self.repo.get_examen_by_id(examen_id)
        if not ex:
            raise ValueError(f"Examen non trouvé (ID={examen_id})")
        return ex
    

    # --- NOUVELLE MÉTHODE POUR LE DOSSIER ---
    def get_patient_lab_history(self, patient_id: int) -> List[Dict]:
        results = self.repo.list_results_for_patient(patient_id)
        out = []
        for r in results:
            # Correction ici : Vérifier si la date existe
            test_date_str = r.test_date.strftime('%Y-%m-%d %H:%M') if r.test_date else '-'

            out.append({
                'result_id': r.result_id,
                # Utiliser la variable corrigée
                'test_date': test_date_str, 
                'examen_name': r.examen.nom if r.examen else 'Inconnu',
                'status': r.status,
                'technician': r.technician_name or 'Inconnu',
                'prescribed_by': r.prescribed_by or 'Inconnu'
            })
        return out

    # Résultats
    # --- CRÉATION DE RÉSULTAT (Mise à jour pour Externe) ---
    def create_result(
        self, 
        examen_id: int, 
        details: List[Dict],
        patient_id: Optional[int] = None, 
        external_patient_info: Optional[Dict] = None
    ) -> Dict:
        """
        Crée une analyse.
        - Si patient_id est fourni -> Patient Interne.
        - Si external_patient_info est fourni -> Patient Externe.
        """
        
        # Validation basique avant d'appeler le repo
        if not patient_id and not external_patient_info:
            raise ValueError("Impossible de créer une analyse sans patient (ID ou Infos Externes requis).")

        # Préparation du payload
        payload = {
            "examen_id": examen_id,
            "test_date": datetime.now(),
            "prescribed_by": getattr(self.user, "user_id", None), # Attention: user_id ou id selon votre modèle User
            "technician_id": getattr(self.user, "user_id", None),
            "technician_name": getattr(self.user, "username", None),
            # On passe les deux, le repo saura lequel utiliser (patient_id sera None pour externe)
            "patient_id": patient_id,
            "external_patient_info": external_patient_info 
        }

        # On ajoute les détails pour la création atomique dans le repo
        if details:
            payload["details"] = details

        # Appel du Repository (qui gère la génération du code EXT/LAB)
        lr = self.repo.create_lab_result(payload)

        return {
            "result_id": lr.result_id, 
            "code_lab_patient": lr.code_lab_patient,
            "status": "created"
        }


    def get_result(self, result_id: int) -> Optional[Dict]:
        fr = self.repo.get_full_lab_result(result_id)
        if not fr: return None
        
        return {
            "result": {
                "id": fr.result_id,
                "code": fr.code_lab_patient,
                "status": fr.status,
                "test_date": fr.test_date,
                "patient_name": self._format_patient_name(fr),
                "is_external": (fr.patient_id is None),
                "external_info": fr.external_patient_info # On renvoie les détails bruts si besoin (tel, etc.)
            },
            "examen": {
                "nom": fr.examen.nom if fr.examen else "N/A"
            },
            "details": fr.details
        }

    def complete_result(self, result_id:int, age:int, sexe:str) -> Dict:
        cr = self.repo.complete_result(result_id, age, sexe)
        return {"status":cr.status}
    
    def list_results_by_status(self, status: str) -> List[Dict]:
        results = self.repo.list_results_by_status(status)
        out = []
        for r in results:
            # Gestion sécurisée de la date (pour éviter l'erreur strftime sur None)
            date_str = r.test_date.strftime('%Y-%m-%d %H:%M') if r.test_date else "Date inconnue"

            out.append({
                'result_id':        r.result_id,
                'code_lab_patient': r.code_lab_patient,
                # 🟢 Utilisation du helper pour le nom (Interne ou Externe)
                'patient_name':     self._format_patient_name(r),
                'examen_name':      r.examen.nom if r.examen else "Examen supprimé",
                'test_date':        date_str,
                'status':           r.status,
                'is_external':      (r.patient_id is None) # Flag utile pour le frontend
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
    

    def complete_result(self, result_id: int, age: int, sexe: str) -> Dict:
        # Note : Pour un patient externe, l'âge et le sexe doivent être fournis 
        # par le frontend lors de la validation, car on ne les a pas en BDD patient.
        cr = self.repo.complete_result(result_id, age, sexe)
        return {"status": cr.status if cr else "error"}

    # --- HISTORIQUE (Pour le dossier patient interne) ---
    def get_patient_lab_history(self, patient_id: int) -> List[Dict]:
        """
        Récupère l'historique pour un patient interne (ID connu).
        """
        results = self.repo.list_results_for_patient(patient_id)
        out = []
        for r in results:
            date_str = r.test_date.strftime('%Y-%m-%d %H:%M') if r.test_date else '-'
            out.append({
                'result_id': r.result_id,
                'code_lab': r.code_lab_patient,
                'test_date': date_str,
                'examen_name': r.examen.nom if r.examen else 'Inconnu',
                'status': r.status,
                'technician': r.technician_name or 'Inconnu',
                # 'prescribed_by' est un ID, idéalement on voudrait le nom, 
                # mais laissons l'ID ou gérons une jointure User si besoin.
                'prescribed_by': r.prescribed_by 
            })
        return out
    
   