# controllers/prescription_controller.py

import logging
import os
import json
import redis
import datetime
from datetime import date, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from celery import Task
from sqlalchemy import text # 🟢 Required for the DB Context Fix

# --- Imports App ---
from repositories.prescription_repo import PrescriptionRepository
from repositories.audit_repo import AuditRepository

# --- Optimisation ---
try:
    from tasks.prescription_tasks import task_notify_new_prescription
    task_notify_new_prescription: Task = task_notify_new_prescription # type: ignore
except ImportError:
    task_notify_new_prescription = None # type: ignore

# Config Redis
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class PrescriptionController:
    def __init__(self, repo=None, patient_controller=None, current_user=None, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo or PrescriptionRepository()  # type: ignore
        self.patient_ctrl = patient_controller
        self.current_user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)

    # --- LECTURE OPTIMISÉE (CACHE) ---

    def _resolve_doctor(self, doctor_id: Optional[int]) -> int:
        """Meme motif que MedicalRecordController/AppointmentController :
        doctor_id explicite prioritaire, sinon le medecin authentifie."""
        if doctor_id is not None:
            return doctor_id
        if self.current_user and getattr(self.current_user, 'user_id', None) is not None:
            return self.current_user.user_id
        raise RuntimeError("doctor_id non disponible")

    def count_prescriptions(self, period: str = "day", doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> int:
        """
        Compteur prescriptions (Cache 5 min).

        Diverge deliberement du pattern _resolve_doctor "toujours
        resoudre" utilise par MedicalRecordController/AppointmentController
        (registre I1) : un vrai appelant existant (desktop,
        api_backend/backend_app/gateway/remote_gateway.py:542,624,
        get_prescriptions_count) appelle cet endpoint SANS doctor_id et
        attend le total etablissement, comportement d'origine a preserver.
        Donc ici, doctor_id=None => pas de filtre (etablissement) ; un
        doctor_id explicite (nouveau, pour un futur tableau de bord medecin
        personnel) le scope reellement via _resolve_doctor.

        Si start ET end sont fournis, ignore `period` et compte sur cette
        plage de dates arbitraire (ferme le gap decouvert au chantier
        "tableau de bord medecin" : les 4 autres sources KPI de ce
        tableau de bord acceptent deja une plage de dates libre, seule
        celle-ci etait limitee a jour/semaine).
        """
        if start is not None and end is not None:
            d = self._resolve_doctor(doctor_id) if doctor_id is not None else None
            cache_scope = d if d is not None else "all"
            CACHE_KEY = f"prescription:stats:count:range:{start}:{end}:{cache_scope}"

            try:
                cached = redis_client.get(CACHE_KEY)
                if cached: return int(cached) # type: ignore
            except Exception: pass

            res = self.repo.count_by_prescription_date_range(start, end, doctor_id=d)

            try:
                redis_client.setex(CACHE_KEY, 300, res)
            except Exception: pass

            return res

        today = date.today()
        d = self._resolve_doctor(doctor_id) if doctor_id is not None else None
        cache_scope = d if d is not None else "all"
        CACHE_KEY = f"prescription:stats:count:{period}:{today}:{cache_scope}"

        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return int(cached) # type: ignore
        except Exception: pass

        if period == "day":
            res = self.repo.count_by_prescription_date(today, doctor_id=d)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            res = self.repo.count_by_prescription_date_range(start_week, end_week, doctor_id=d)
        else:
            raise ValueError("Période non valide")

        try:
            redis_client.setex(CACHE_KEY, 300, res)
        except Exception: pass

        return res

    # --- ÉCRITURE AVEC FIX DB CONTEXT, INVALIDATION & CELERY ---

    def create_prescription(self, data: dict):
        # 1. Prepare Data
        if self.current_user:
            data['prescribed_by'] = self.current_user.user_id
            data['prescribed_by_name'] = self.current_user.username
        else:
            data['prescribed_by'] = None
            data['prescribed_by_name'] = None
            
        # 🟢 2. FIX: Set DB Session Context for Audit Trigger
        # This prevents "null value in column user_id of audit_user_actions"
        if self.current_user and hasattr(self.repo, 'session'):
            try:
                uid = self.current_user.user_id
                # On définit la variable de session que le Trigger PostgreSQL attend.
                # 'app.current_user_id' est le standard pour RLS/Audit.
                # set_config(..., true) = equivalent parametre de SET LOCAL, evite
                # l'interpolation f-string directe dans le SQL.
                self.repo.session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(uid)},
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to set DB audit context: {e}")

        # 3. Execute DB Creation
        presc = self.repo.create(data)
        
        # 4. Invalidation Cache
        try:
            today = date.today()
            keys = [
                f"prescription:stats:count:day:{today}",
                f"prescription:stats:count:week:{today}"
            ]
            redis_client.delete(*keys)
        except Exception: pass

        # 5. 🟢 Tâche Celery (Notification Pharmacie)
        if task_notify_new_prescription:
            try:
                # Récupération ID (attribut 'prescription_id' ou 'id' selon le modèle)
                pid = getattr(presc, 'prescription_id', None) or getattr(presc, 'id', None)
                
                if pid:
                    # retry=False : evite d'amplifier l'attente HTTP si le
                    # broker Celery est injoignable (best-effort, pas de
                    # retry automatique sur une simple notification).
                    task_notify_new_prescription.apply_async(
                        kwargs={
                            "prescription_id": pid,
                            "patient_id": data.get('patient_id'),
                            "medication": data.get('medication', 'Non spécifié'),
                        },
                        retry=False,
                    )
                    print(f"⚡ [CELERY] Notification prescription #{pid} envoyée.")
            except Exception as e:
                print(f"⚠️ [CELERY] Erreur tâche prescription: {e}")

        # 6. Python Audit (Redundant but safe)
        if self.audit_repo and self.current_user:
            try:
                pid = getattr(presc, 'prescription_id', None)
                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="CREATE",
                    resource_id=pid,
                    details=f"Patient: {data.get('patient_id')}. Médicament: {data.get('medication')}" # type: ignore
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return presc

    def update_prescription(self, prescription_id: int, data: dict):
        if self.current_user:
            data['prescribed_by'] = self.current_user.user_id
            data['prescribed_by_name'] = self.current_user.username
        
        # 🟢 FIX: Set Context for Update as well
        if self.current_user and hasattr(self.repo, 'session'):
            try:
                uid = self.current_user.user_id
                self.repo.session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(uid)},
                )
            except Exception: pass

        presc = self.repo.update(prescription_id, data)

        # presc est None si prescription_id n'existe pas (repo.update() ne
        # leve plus d'exception dans ce cas) - ne pas logger une fausse
        # entree d'audit "UPDATE" pour une mise a jour qui n'a rien fait.
        if presc and self.audit_repo and self.current_user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="UPDATE",
                    resource_id=prescription_id,
                    new_values=data
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
        return presc

    def delete_prescription(self, prescription_id: int):
        # 🟢 FIX: Set Context for Delete
        if self.current_user and hasattr(self.repo, 'session'):
            try:
                uid = self.current_user.user_id
                self.repo.session.execute(
                    text("SELECT set_config('app.current_user_id', :uid, true)"),
                    {"uid": str(uid)},
                )
            except Exception: pass

        res = self.repo.delete(prescription_id)
        
        # Invalidation Cache
        try:
            today = date.today()
            keys = [
                f"prescription:stats:count:day:{today}",
                f"prescription:stats:count:week:{today}"
            ]
            redis_client.delete(*keys)
        except Exception: pass

        if res and self.audit_repo and self.current_user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="DELETE",
                    resource_id=prescription_id
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
        return res

    # --- MÉTHODES STANDARD (Sans Cache) ---

    def get_patient_prescriptions(self, patient_id: int, status: str = None):
        """Récupère toutes les prescriptions d'un patient."""
        items, total = self.repo.list_paginated_with_relations(
            page=1, per_page=100,
            patient_id=patient_id
        )
        if status:
            items = [p for p in items if p.status == status]
        return items

    def list_prescriptions(self, page: int = 1, per_page: int = 20,
                           date_from: Optional[str] = None, date_to: Optional[str] = None,
                           patient_id: Optional[int] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """Retourne un dict {data: [...], total: N}."""
        df = date_from
        dt = date_to
        try:
            if isinstance(date_from, str):
                df = datetime.datetime.fromisoformat(date_from).date() # type: ignore
            if isinstance(date_to, str):
                dt = datetime.datetime.fromisoformat(date_to).date() # type: ignore
        except Exception:
            df, dt = date_from, date_to # type: ignore

        try:
            items, total = self.repo.list_paginated_with_relations(
                page=page, per_page=per_page,
                date_from=df, date_to=dt, # type: ignore
                patient_id=patient_id,
                search=search
            )
            return {"data": items, "total": total}
        except Exception as e:
            self.logger.error(f"Erreur list_prescriptions: {e}", exc_info=True)
            raise

    def get_prescription(self, prescription_id: int):
        return self.repo.get(prescription_id)
    
    def get_by_day(self, target_date: date) -> list:
        return self.repo.find_by_date_range(target_date, target_date)
    
    # Wrappers KPI
    def renewals_for_doctor(self, doctor_id: Optional[int] = None, within_days: int = 14):
        d = doctor_id or getattr(self.current_user, 'user_id', None)
        if d is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.find_renewals_for_doctor(d, within_days)

    def count_renewals_for_doctor(self, doctor_id: Optional[int] = None, within_days: int = 14) -> int:
        d = doctor_id or getattr(self.current_user, 'user_id', None)
        if d is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.count_renewals_for_doctor(d, within_days)