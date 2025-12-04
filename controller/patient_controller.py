# controller/patient_controller.py
import logging
from sqlalchemy import func
from typing import Optional, Dict, Any, List
from models.application_role import ApplicationRole
from models.user import User
from datetime import date, timedelta, datetime, time
from repositories.audit_repo import AuditRepository
from sqlalchemy.exc import SQLAlchemyError # 🟢 AJOUT


class PatientController:
    def __init__(self, repo, current_user, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.session = repo.session
        self.logger = logging.getLogger(__name__)

    def create_patient(self, data: dict) -> tuple[int,str]:
        """
        Crée un patient et son log d'audit de manière atomique.
        Si l'une des deux étapes échoue, toute l'opération est annulée (rollback).
        """
        required = ['first_name', 'last_name', 'birth_date']
        if any(not data.get(f) for f in required):
            raise ValueError("Champs obligatoires manquants")
        
        # 🟢 1. Injection automatique des drapeaux selon le rôle (Logique métier)
        user_app_role = getattr(self.user, 'role_name', '').lower()

        if 'secretaire' in user_app_role:
            data['is_spiritual'] = True
        elif 'medecin' in user_app_role or 'nurse' in user_app_role or 'assistant' in user_app_role:
            data['is_clinical'] = True
        # L'admin/toxico utilise les valeurs passées ou par défaut (False)
            
        try:
            # 2. Opération Patient : Ajout à la session
            result = self.repo.create_patient(data, self.user)
            patient_id, patient_code = result
            
            # 3. Opération Audit : Ajout à la session
            if self.audit_repo and self.user:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Patient",
                    action_performed="CREATE",
                    resource_id=patient_id,
                    details=f"Nom: {data.get('last_name')} {data.get('first_name')}",
                    new_values=data 
                )
            
            # 4. Validation Atomique : Commit toutes les opérations en même temps
            self.session.commit()
            
            return patient_id, patient_code

        except SQLAlchemyError as e:
            # 5. Annulation Atomique : Rollback toutes les opérations en cas d'erreur BD
            self.session.rollback()
            self.logger.error(f"Erreur SQL lors de la création atomique du patient : {e}")
            raise # Remonte l'erreur pour la gestion d'API (500)
        except Exception as e:
             # Annulation pour les autres erreurs (ex: ValueError)
            self.session.rollback()
            raise # Remonte l'erreur (pour la gestion d'API, souvent 400)

    def update_patient(self, patient_id: int, data: dict) -> tuple[int, str]:
        """
        Met à jour un patient et son log d'audit de manière atomique.
        """
        # 1. Récupérer l'état actuel (pour protéger les drapeaux et l'audit)
        existing_patient = self.repo.get_by_id(patient_id)
        if not existing_patient:
            raise ValueError("Patient introuvable")

        # 2. Logique de protection des drapeaux
        user_app_role = getattr(self.user, 'role_name', '').lower()

        if 'admin' not in user_app_role:
            # Protection TOXICOLOGIE (Réservé Admin)
            data['is_toxicology'] = existing_patient['is_toxicology']

            # Protection CLINIQUE (Réservé Médecin/Nurse/Assistant)
            if not ('medecin' in user_app_role or 'nurse' in user_app_role or 'assistant' in user_app_role):
                data['is_clinical'] = existing_patient['is_clinical']

            # Protection SPIRITUEL (Réservé Secrétaire)
            if 'secretaire' not in user_app_role:
                data['is_spiritual'] = existing_patient['is_spiritual']
        
        # Préparation des anciennes valeurs pour l'audit
        old_values = {k: existing_patient.get(k) for k in data.keys() if k in existing_patient}

        try:
            # 3. Opération Patient : Ajout à la session
            self.repo.update_patient(patient_id, data, self.user)
            
            # 4. Opération Audit : Ajout à la session
            if self.audit_repo and self.user:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Patient",
                    action_performed="UPDATE",
                    resource_id=patient_id,
                    old_values=old_values, 
                    new_values=data
                )
                
            # 5. Validation Atomique : Commit toutes les opérations en même temps
            self.session.commit()
            
            return patient_id, existing_patient['code_patient']

        except SQLAlchemyError as e:
            # 6. Annulation Atomique : Rollback toutes les opérations en cas d'erreur BD
            self.session.rollback()
            self.logger.error(f"Erreur SQL lors de la mise à jour atomique du patient : {e}")
            raise # Remonte l'erreur
        except Exception:
            self.session.rollback()
            raise

    def delete_patient(self, patient_id: int) -> bool:
        # 🟢 Passage de l'ID utilisateur pour le Soft Delete
        user_id = getattr(self.user, 'user_id', None)
        success = self.repo.delete_patient(patient_id, user_id)
        
        if success and self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Patient",
                    action_performed="SOFT_DELETE",
                    resource_id=patient_id
                )
            except Exception: pass
        return success

    def get_patient(self, patient_id: int) -> dict:
        return self.repo.get_by_id(patient_id)

    def list_patients(self, page=1, per_page=10, search=None):
        # 🟢 1. Récupération du rôle APPLICATIF
        user_app_role = getattr(self.user, 'role_name', '').lower()
        filters = {}

        # 🟢 2. Filtres de visibilité
        if 'secretaire' in user_app_role:
            filters['is_spiritual'] = True
        elif 'medecin' in user_app_role or 'nurse' in user_app_role or 'assistant' in user_app_role:
            filters['is_clinical'] = True
        
        # 'admin' voit TOUT (pas de filtre).
        # 'toxico' n'est pas un rôle distinct, c'est l'admin qui gère.

        return self.repo.list_patients(page=page, per_page=per_page, search=search, filters=filters)
    
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
    
    def get_spiritual_new_patients_count_kpi(self, period: str = "week") -> int:
        """
        KPI Nouveaux Patients Spirituels : Retourne le nombre de patients créés par Secrétaire.
        """
        today = date.today()
        
        if period == "day":
            start_date = datetime.combine(today, time.min)
            end_date = start_date + timedelta(days=1)
        elif period == "week":
            # Début de la semaine (Lundi)
            start_date = datetime.combine(today - timedelta(days=today.weekday()), time.min)
            end_date = start_date + timedelta(days=7)
        else:
            raise ValueError("Période non valide. Utilisez 'day' ou 'week'")
            
        # Utilisation de la nouvelle méthode Repo spécialisée
        return self.repo.count_new_spiritual_patients_by_range(start_date=start_date, end_date=end_date)

    def get_spiritual_patient_status_kpi(self) -> Dict[str, int]:
        """
        KPI Statut Patients Spirituels : Retourne la distribution Actifs / Inactifs.
        """
        # Utilisation de la nouvelle méthode Repo spécialisée
        return self.repo.get_spiritual_patient_status_distribution()

    def get_spiritual_assurance_distribution_kpi(self) -> Dict[str, int]:
        """
        KPI Répartition Assurance Patients Spirituels.
        """
        # Utilisation de la nouvelle méthode Repo spécialisée
        return self.repo.get_spiritual_assurance_distribution()

