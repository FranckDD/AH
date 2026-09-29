# controller/appointment_controller.py

import logging
import os
import json
import redis
from datetime import date, timedelta, datetime, time
from typing import Optional, Dict, List, Tuple, Any
from dotenv import load_dotenv
from celery import Task

from sqlalchemy.exc import SQLAlchemyError
from models.appointment import Appointment
from models.medical_speciality import MedicalSpecialty

# --- Optimisation ---
try:
    from tasks.appointment_tasks import task_notify_appointment_action
    # Astuce typage: on utilise Any ou on ne type pas pour éviter l'erreur Pylance
    task_notify_appointment_action = task_notify_appointment_action 
except ImportError:
    task_notify_appointment_action = None 

# Config Redis
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


# --- Helpers de sérialisation (inchangés) ---
def _serialize_patient(patient) -> Dict[str, Any]:
    if not patient: return {}
    return {
        "patient_id": getattr(patient, "id", None) or getattr(patient, "patient_id", None),
        "code_patient": getattr(patient, "code_patient", None),
        "first_name": getattr(patient, "first_name", None),
        "last_name": getattr(patient, "last_name", None),
        "contact_phone": getattr(patient, "contact_phone", None),
    }

def _serialize_doctor(doctor) -> Dict[str, Any]:
    if not doctor: return {}
    return {
        "doctor_id": getattr(doctor, "id", None),
        "full_name": getattr(doctor, "full_name", None) or getattr(doctor, "username", None),
    }

def _serialize_appointment(appt) -> Dict[str, Any]:
    if isinstance(appt, dict): return appt
    p = _serialize_patient(getattr(appt, "patient", None))
    d = _serialize_doctor(getattr(appt, "doctor", None))
    ad = getattr(appt, "appointment_date", None)
    at = getattr(appt, "appointment_time", None)
    if hasattr(ad, "strftime"): ad = ad.strftime("%Y-%m-%d") # type: ignore
    if hasattr(at, "strftime"): at = at.strftime("%H:%M") # type: ignore
    return {
        "appointment_id": getattr(appt, "id", None),
        "patient_id": getattr(appt, "patient_id", None),
        "patient": p,
        "doctor": d,
        "specialty": getattr(appt, "specialty", None),
        "appointment_date": ad,
        "appointment_time": at,
        "reason": getattr(appt, "reason", None),
        "status": getattr(appt, "status", None),
    }


class AppointmentController:
    def __init__(self, repo, patient_controller, current_user):
        self.repo = repo
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.logger = logging.getLogger(__name__)

    # --- LECTURE OPTIMISÉE (CACHE) ---

    def get_all_specialties(self) -> List[str]:
        """
        Retourne la liste des spécialités (Cache 24h car très statique).
        """
        CACHE_KEY = "appointment:static:specialties"
        
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return json.loads(cached) # type: ignore
        except Exception: pass

        session = self.repo.session
        specs = (session.query(MedicalSpecialty).order_by(MedicalSpecialty.name).all())
        result = [s.name for s in specs]
        
        try:
            redis_client.setex(CACHE_KEY, 86400, json.dumps(result))
        except Exception: pass
        
        return result

    def upcoming_appointments(self, doctor_id: Optional[int] = None, limit: int = 5):
        """
        Prochains RDV (Cache court 1 min pour dashboard réactif).
        """
        d_id = doctor_id or getattr(self.user, 'user_id', 'all')
        CACHE_KEY = f"appointment:dashboard:upcoming:{d_id}:{limit}"
        
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return json.loads(cached) # type: ignore
        except Exception: pass

        # Si doctor_id est None, on résout l'utilisateur courant, sinon None
        target_id = self._resolve_doctor_safe(doctor_id)
        
        data = self.repo.next_appointments_for_doctor(target_id, limit=limit)
        # On doit sérialiser pour le cache car ce sont des objets ORM
        serialized = [_serialize_appointment(a) for a in data]
        
        try:
            redis_client.setex(CACHE_KEY, 60, json.dumps(serialized))
        except Exception: pass
        
        return data # On retourne les objets ORM si non-cache, le serializer de la route gèrera

    # --- ÉCRITURE AVEC INVALIDATION & CELERY ---

    def _invalidate_doctor_cache(self, doctor_id):
        """Supprime les caches liés à un médecin spécifique."""
        try:
            keys = [
                f"appointment:dashboard:upcoming:{doctor_id}:*",
                f"appointment:stats:total:{doctor_id}:*"
            ]
            # On pourrait utiliser scan_iter pour être plus précis mais delete simple suffit pour les clés connues
            # Ici on utilise un pattern simple pour l'exemple
            redis_client.delete(*[k.replace('*', '5') for k in keys]) # Hack rapide, idéalement utiliser keys() ou scan
            
            # Plus propre: supprimer tout ce qui concerne le dashboard
            scan_keys = redis_client.keys(f"appointment:dashboard:upcoming:{doctor_id}:*")
            if scan_keys: redis_client.delete(*scan_keys)
            
        except Exception: pass

    def book_appointment(self, data: dict) -> Appointment:
        if not data or "patient_id" not in data:
            raise ValueError("patient_id manquant")
        
        # Ensure doctor_id - ne retombe sur le createur QUE si la cle est
        # absente du dict (vrai appelant historique, jamais le nouveau
        # formulaire web qui envoie toujours la cle, y compris a None pour
        # "Non assigne" explicite - chantier triage 2026-09-29, voir
        # commentaire de book_appointment() dans le plan de ce chantier).
        if "doctor_id" not in data:
            if getattr(self.user, "user_id", None) is not None:
                data["doctor_id"] = self.user.user_id
        
        appt = self.repo.create(data)
        
        # 1. Invalidation Cache
        doc_id = data.get("doctor_id")
        if doc_id: self._invalidate_doctor_cache(doc_id)

        # 2. 🟢 Tâche Celery (Notification)
        if task_notify_appointment_action:
            try:
                # Récupération infos pour notification
                pat_name = "Patient" # Idéalement récupérer via repo patient
                doc_name = "Docteur"
                appt_id = getattr(appt, "id", None)
                date_str = str(data.get("appointment_date", ""))
                
                if appt_id:
                    task_notify_appointment_action.delay(
                        appointment_id=appt_id,
                        action="created",
                        patient_name=pat_name,
                        doctor_name=doc_name,
                        date_time=date_str
                    )
            except Exception as e:
                self.logger.warning(f"⚠️ [CELERY] Erreur notification RDV: {e}")

        return appt

    def cancel_appointment(self, appointment_id: int) -> Optional[Appointment]:
        updated = self.modify_appointment(appointment_id, {"status": "cancelled"})
        
        # Trigger notification annulation
        if updated and task_notify_appointment_action:
            try:
                task_notify_appointment_action.delay(
                    appointment_id=appointment_id,
                    action="cancelled",
                    patient_name="Patient", # Simplification
                    doctor_name="Docteur",
                    date_time=str(updated.appointment_date)
                )
            except Exception: pass
            
        return updated

    def modify_appointment(self, appointment_id: int, appointment_data: Optional[dict] = None, **kwargs) -> Optional[Appointment]:
        data = {}
        if appointment_data: data.update(appointment_data)
        if kwargs: data.update(kwargs)
        
        if not data: return self.repo.get_by_id(appointment_id)

        updated = self.repo.update(appointment_id, data)
        
        # Invalidation Cache si changement
        if updated:
            doc_id = getattr(updated, 'doctor_id', None)
            if doc_id: self._invalidate_doctor_cache(doc_id)
            
        return updated

    def complete_appointment(self, appointment_id: int) -> Optional[Appointment]:
        return self.modify_appointment(appointment_id, {"status": "completed"})

    # --- MÉTHODES STANDARD (Recherche / Liste) ---

    def list_appointments(self, page: int = 1, per_page: int = 20,
                          date_from: Optional[str] = None, date_to: Optional[str] = None,
                          doctor_id: Optional[int] = None, patient_id: Optional[int] = None,
                          search: Optional[str] = None) -> Dict[str, Any]:
        df = date_from
        dt = date_to
        try:
            if isinstance(date_from, str):
                df = datetime.fromisoformat(date_from).date() # type: ignore
            if isinstance(date_to, str):
                dt = datetime.fromisoformat(date_to).date() # type: ignore
        except Exception:
            df, dt = date_from, date_to

        items, total = self.repo.list_paginated_with_relations(page=page, per_page=per_page,
                                                               date_from=df, date_to=dt, # type: ignore
                                                               patient_id=patient_id, doctor_id=doctor_id,
                                                               search=search)
        return {"items": items, "total": total}

    def get_by_day(self, target_date: date) -> List[Dict[str, Any]]:
        appts = self.repo.find_by_date_range(target_date, target_date)
        return [_serialize_appointment(a) for a in appts]

    def count_by_day(self, target_date: date) -> int:
        return self.repo.count_by_day(target_date)

    def get_by_week(self, start_date: date) -> List[Appointment]:
        return self.repo.find_by_date_range(start_date, start_date + timedelta(days=6))

    def get_by_month(self, year: int, month: int) -> List[Appointment]:
        start = date(year, month, 1)
        if month == 12: end = date(year, 12, 31)
        else: end = date(year, month + 1, 1) - timedelta(days=1)
        return self.repo.find_by_date_range(start, end)

    def search_by_patient(self, patient_id: int) -> List[Appointment]:
        return self.repo.find_by_patient(patient_id)

    # --- WRAPPERS KPI & UTILS ---

    def _resolve_doctor(self, doctor_id: Optional[int]) -> int:
        if doctor_id is not None: return doctor_id
        if getattr(self.user, 'user_id', None) is not None: return self.user.user_id
        raise RuntimeError("doctor_id non disponible")
        
    def _resolve_doctor_safe(self, doctor_id: Optional[int]) -> Optional[int]:
        """Version safe qui retourne None au lieu de crash si pas d'ID (pour le cache global)"""
        if doctor_id is not None: return doctor_id
        if getattr(self.user, 'user_id', None) is not None: return self.user.user_id
        return None

    def weekly_appointments(self, doctor_id: Optional[int], year: int):
        return self.repo.appointments_per_week_for_doctor(doctor_id, year)

    def count_by_status(self, doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> Dict[str,int]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.count_by_status_for_doctor(d, start, end)

    def total_appointments(self, doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> int:
        d = self._resolve_doctor(doctor_id)
        return self.repo.count_total_for_doctor(d, start, end)

    def appointments_time_series(self, doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> List[Tuple[str,int]]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.appointments_per_day_for_doctor(d, start, end)

    def distinct_patients_count(self, doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> int:
        d = self._resolve_doctor(doctor_id)
        return self.repo.count_distinct_patients_for_doctor(d, start, end)

    def monthly_breakdown(self, year: Optional[int] = None, doctor_id: Optional[int] = None):
        d = self._resolve_doctor(doctor_id)
        if year is None: year = date.today().year
        return self.repo.appointments_per_month_for_doctor(d, year)
        
    def get_appointments_by_day(self, target_day):
        return self.repo.get_appointments_by_day(target_day)

    # —— Versions filtrées par médecin —— #

    def get_by_day_doctor(self, doctor_id: Optional[int], target_date: date) -> List[Appointment]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.find_by_date_range_for_doctor(d, target_date, target_date)

    def get_by_week_doctor(self, doctor_id: Optional[int], start_date: date) -> List[Appointment]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.find_by_date_range_for_doctor(d, start_date, start_date + timedelta(days=6))

    def get_by_month_doctor(self, doctor_id: Optional[int], year: int, month: int) -> List[Appointment]:
        d = self._resolve_doctor(doctor_id)
        start = date(year, month, 1)
        if month == 12: end = date(year, 12, 31)
        else: end = date(year, month + 1, 1) - timedelta(days=1)
        return self.repo.find_by_date_range_for_doctor(d, start, end)

    def search_by_patient_doctor(self, doctor_id: Optional[int], patient_id: int) -> List[Appointment]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.find_by_patient_for_doctor(d, patient_id)
    
    def count_consultations(self, period="day"):
        today = date.today()
        if period == "day":
            return self.repo.count_completed_by_date(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return self.repo.count_completed_by_date_range(start_week, end_week)
        return 0
    
    def search_by_doctor(self, doctor_id: int):
        return self.repo.search_by_doctor(doctor_id)
    
    def upcoming_today(self, doctor_id: Optional[int] = None):
        d = doctor_id or getattr(self.user, "user_id", None)
        if d is None: raise RuntimeError("Doctor id non disponible")
        try:
            if hasattr(self.repo, "upcoming_for_day"):
                return self.repo.upcoming_for_day(d, date.today())
            if hasattr(self.repo, "upcoming"):
                return self.repo.upcoming(d, date.today())
            raise RuntimeError("AppointmentRepository: méthode 'upcoming_for_day' introuvable")
        except Exception as e:
            self.logger.exception("Erreur upcoming_today: %s", e)
            raise