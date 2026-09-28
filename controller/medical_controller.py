# controllers/medical_controller.py

import logging
import os
import json
import redis
from datetime import date, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from celery import Task

# --- Imports App ---
from repositories.medical_repo import MedicalRecordRepository
from repositories.audit_repo import AuditRepository

# --- Optimisation ---
try:
    from tasks.medical_tasks import task_process_medical_record_creation
    task_process_medical_record_creation: Task = task_process_medical_record_creation # type: ignore
except ImportError:
    task_process_medical_record_creation = None # type: ignore

# 🟢 CONFIGURATION REDIS
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class MedicalRecordController:
    def __init__(self, repo=None, patient_controller=None, current_user=None, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo or MedicalRecordRepository() # type: ignore
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)

    # --- MÉTHODES DE LECTURE OPTIMISÉES (CACHE) ---

    def count_consultations(self, period: str = "day") -> int:
        """Retourne le nombre de consultations selon la période. Optimisé avec Redis."""
        today = date.today()
        CACHE_KEY = f"medical:stats:count:{period}:{today}"

        try:
            cached_count = redis_client.get(CACHE_KEY)
            if cached_count is not None:
                return int(cached_count) # type: ignore
        except Exception: pass

        if period == "day":
            res = self.repo.count_by_consultation_date(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            res = self.repo.count_by_consultation_date_range(start_week, end_week)
        else:
            raise ValueError("Période non valide. Utilisez 'day' ou 'week'")

        try:
            redis_client.setex(CACHE_KEY, 300, res)
        except Exception: pass
        
        return res

    def count_preconsultations(self, period="day"):
        """Compte les pré-consultations (Cache Redis)."""
        today = date.today()
        CACHE_KEY = f"medical:stats:precount:{period}:{today}"
        
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return int(cached) # type: ignore
        except Exception: pass

        if period == "day":
            res = self.repo.count_preconsultations(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            res = self.repo.count_preconsultations(start_week, end_week)
        else:
            return 0
            
        try:
            redis_client.setex(CACHE_KEY, 300, res)
        except Exception: pass
        
        return res

    def get_patient_dme_summary(self, patient_id: int) -> Dict[str, Any]:
        """Récupère les informations vitales pour l'en-tête du dossier patient."""
        if not self.patient_ctrl:
            raise RuntimeError("PatientController manquant")
        
        patient = self.patient_ctrl.get_patient(patient_id)
        if not patient:
            raise ValueError("Patient introuvable")

        last_record = self.repo.get_last_for_patient(patient_id)

        summary = {
            "patient_id": patient['patient_id'],
            "full_name": f"{patient['first_name']} {patient['last_name']}",
            "code": patient['code_patient'],
            "age": self._calculate_age(patient['birth_date']),
            "gender": patient['gender'],
            "flags": self.patient_ctrl.repo.compute_domain_flags(patient_id),
            "last_consultation_date": last_record.consultation_date if last_record else None,
            "last_bp": last_record.bp if last_record else None,
            "last_weight": float(last_record.weight) if last_record and last_record.weight else None,
            "last_temp": float(last_record.temperature) if last_record and last_record.temperature else None,
            "last_diagnosis": last_record.diagnosis if last_record else None,
            "allergies": last_record.allergies if last_record else "Aucune signalée (Dossier vide)"
        }
        return summary

    # --- ÉCRITURE (Avec Audit Python Uniquement) ---

    def create_record(self, data: dict):
        # Bug reel trouve le 2026-09-28 en construisant le KPI "consultations
        # realisees" (medecin/nurse) : created_by/created_by_name n'etaient
        # JAMAIS renseignes a la creation, alors que
        # MedicalRecordRepository.create() les accepte deja (procedure
        # stockee create_medical_record, aucune migration necessaire) -
        # personne ne les mettait jamais dans `data` avant cet appel.
        # Ecrasement inconditionnel plutot que setdefault : le schema d'entree
        # (MedicalRecordCreate) ne declare meme pas ces deux champs
        # aujourd'hui (bonne chose), mais l'auteur d'un dossier medical ne
        # doit de toute facon jamais pouvoir venir du client, meme si le
        # schema evolue un jour - le serveur reste la seule source pour
        # cette identite.
        # Consequence du bug avant ce correctif : count_records_for_doctor()
        # /breakdown_by_motif_for_doctor() (filtres WHERE created_by =
        # doctor_id) renvoyaient toujours 0 pour tout le monde - le KPI
        # "Dossiers medicaux (cumul)" de DoctorKpiView.vue etait casse en
        # silence depuis le debut.
        if self.user:
            data['created_by'] = getattr(self.user, 'user_id', None)
            data['created_by_name'] = getattr(self.user, 'full_name', None) or getattr(self.user, 'username', None)

        # 1. Création via Repo (qui appelle la Procédure SQL corrigée)
        record = self.repo.create(data)
        
        # 2. Invalidation Cache
        try:
            today = date.today()
            keys_to_delete = [
                f"medical:stats:count:day:{today}",
                f"medical:stats:count:week:{today}",
                f"medical:stats:precount:day:{today}",
            ]
            redis_client.delete(*keys_to_delete)
        except Exception: pass

        # 3. Tâche Celery
        if task_process_medical_record_creation:
            try:
                rec_id = getattr(record, 'record_id', None) or getattr(record, 'id', None)
                pat_id = data.get('patient_id')
                doc_id = getattr(self.user, 'user_id', 0) if self.user else 0
                
                if rec_id:
                    task_process_medical_record_creation.delay(
                        record_id=rec_id,
                        patient_id=pat_id,
                        doctor_id=doc_id
                    )
            except Exception as e:
                self.logger.warning(f"Erreur Celery: {e}")

        # 4. Audit Applicatif (Python)
        if self.audit_repo and self.user:
            try:
                rec_id = getattr(record, 'record_id', None)
                pat_id = data.get('patient_id')
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="CREATE",
                    resource_id=rec_id,
                    details=f"Patient ID: {pat_id}. Motif: {data.get('motif_code')}"
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return record

    def update_record(self, record_id: int, data: dict):
        record = self.repo.update(record_id, data)
        
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="UPDATE",
                    resource_id=record_id,
                    new_values=data
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return record

    def delete_record(self, record_id: int):
        result = self.repo.delete(record_id)
        
        try:
            today = date.today()
            keys_to_delete = [
                f"medical:stats:count:day:{today}",
                f"medical:stats:count:week:{today}"
            ]
            redis_client.delete(*keys_to_delete)
        except Exception: pass

        if result and self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="DELETE",
                    resource_id=record_id
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return result

    # --- MÉTHODES STANDARD ---

    def list_records(self, patient_id=None, page=1, per_page=20, 
                     date_from=None, date_to=None, motif_code=None, 
                     severity=None, search=None):
        try:
            severity_map = {"Faible": "low", "Moyen": "medium", "Élevé": "high"}
            if severity in severity_map:
                severity = severity_map[severity]
                
            result = self.repo.list_records(
                patient_id=patient_id,
                page=page,
                per_page=per_page,
                date_from=date_from,
                date_to=date_to,
                motif_code=motif_code,
                severity=severity,
                search=search
            )
            return result
        except Exception as e:
            self.logger.error(f"Erreur list_records: {e}", exc_info=True)
            raise

    def get_record(self, record_id: int):
        return self.repo.get(record_id)

    def list_motifs(self) -> list[dict]:
        return self.repo.get_motifs()

    def find_patient(self, query: str):
        if not self.patient_ctrl:
            raise RuntimeError("PatientController non fourni")
        if query.isdigit():
            return self.patient_ctrl.get_patient(int(query))
        return self.patient_ctrl.find_by_code(query)
    
    def get_by_day(self, target_date: date) -> list:
        return self.repo.find_by_date_range(target_date, target_date)
    
    def get_last_for_patient(self, patient_id: int):
        return self.repo.get_last_for_patient(patient_id)
    
    def _calculate_age(self, birth_date):
        if not birth_date: return 0
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    # --- WRAPPERS KPI ---

    def _resolve_doctor(self, doctor_id: Optional[int]) -> int:
        if doctor_id is not None:
            return doctor_id
        if self.user and getattr(self.user, 'user_id', None) is not None:
            return self.user.user_id
        raise RuntimeError("doctor_id non disponible")

    def count_records_for_doctor(self, doctor_id: Optional[int]=None, start: Optional[date]=None, end: Optional[date]=None) -> int:
        d = self._resolve_doctor(doctor_id)
        return self.repo.count_records_for_doctor(d, start, end)

    def consultation_type_distribution(self, doctor_id: Optional[int]=None, start: Optional[date]=None, end: Optional[date]=None) -> Dict[str,int]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.breakdown_by_motif_for_doctor(d, start, end)
    
    def get_patient_history(self, patient_id: int):
        return self.repo.get_full_history(patient_id)