# controller/appointment_controller.py
import logging
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple, Any

from sqlalchemy.exc import SQLAlchemyError
from models.appointment import Appointment
from models.medical_speciality import MedicalSpecialty
from datetime import datetime, time

def _serialize_patient(patient) -> Dict[str, Any]:
    if not patient:
        return {}
    return {
        "patient_id": getattr(patient, "id", None) or getattr(patient, "patient_id", None),
        "code_patient": getattr(patient, "code_patient", None),
        "first_name": getattr(patient, "first_name", None),
        "last_name": getattr(patient, "last_name", None),
        "contact_phone": getattr(patient, "contact_phone", None),
        # ajoute d'autres champs utiles si besoin
    }

def _serialize_doctor(doctor) -> Dict[str, Any]:
    if not doctor:
        return {}
    return {
        "doctor_id": getattr(doctor, "id", None),
        "full_name": getattr(doctor, "full_name", None) or getattr(doctor, "username", None),
    }

def _serialize_appointment(appt) -> Dict[str, Any]:
    # appt can be ORM obj or dict
    if isinstance(appt, dict):
        # assume already serialized
        return appt
    p = _serialize_patient(getattr(appt, "patient", None))
    d = _serialize_doctor(getattr(appt, "doctor", None))
    ad = getattr(appt, "appointment_date", None)
    at = getattr(appt, "appointment_time", None)
    if hasattr(ad, "strftime"):
        ad = ad.strftime("%Y-%m-%d") # type: ignore
    if hasattr(at, "strftime"):
        at = at.strftime("%H:%M") # type: ignore
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


    def list_appointments(self, page: int = 1, per_page: int = 20,
                          date_from: Optional[str] = None, date_to: Optional[str] = None,
                          doctor_id: Optional[int] = None, patient_id: Optional[int] = None,
                          search: Optional[str] = None) -> Dict[str, Any]:
        # convert date strings to date objects if strings
        df = date_from
        dt = date_to
        try:
            if isinstance(date_from, str):
                df = datetime.fromisoformat(date_from).date()
            if isinstance(date_to, str):
                dt = datetime.fromisoformat(date_to).date()
        except Exception:
            df, dt = date_from, date_to

        items, total = self.repo.list_paginated_with_relations(page=page, per_page=per_page,
                                                               date_from=df, date_to=dt,
                                                               patient_id=patient_id, doctor_id=doctor_id,
                                                               search=search)
        # return raw ORM list + total -> route will handle serialization/validation
        return {"items": items, "total": total} 

    def get_by_day(self, target_date: date) -> List[Dict[str, Any]]:
        appts = self.repo.find_by_date_range(target_date, target_date)
        return [_serialize_appointment(a) for a in appts]

    def count_by_day(self, target_date: date) -> int:
        return self.repo.count_by_day(target_date) 

    """def book_appointment(self, data: dict) -> Appointment:
        if 'patient_id' not in data:
            raise ValueError("patient_id manquant")
        appt = Appointment(
            patient_id=data['patient_id'],
            doctor_id=self.user.user_id,
            specialty=data.get('specialty'),
            appointment_date=data.get('appointment_date'),
            appointment_time=data.get('appointment_time'),
            reason=data.get('reason'),
            status='pending'
        )
        session = self.repo.session
        try:
            session.add(appt)
            session.commit()
            return appt
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Erreur création RDV: {e}")
            raise"""

    """def modify_appointment(self, appointment_id: int, **kwargs) -> Optional[Appointment]:
        appt = self.repo.get_by_id(appointment_id)
        if not appt:
            self.logger.warning(f"RDV introuvable: id={appointment_id}")
            return None
        for field, value in kwargs.items():
            if hasattr(appt, field):
                setattr(appt, field, value)
        return self.repo.update(appt)"""
    
    def book_appointment(self, data: dict) -> Appointment:
        """
        Create an Appointment. Returns the ORM appointment.
        The repo.create accepts dicts now and will return the ORM instance.
        """
        if not data or "patient_id" not in data:
            raise ValueError("patient_id manquant")
        # ensure doctor_id
        if "doctor_id" not in data or data.get("doctor_id") is None:
            if getattr(self.user, "user_id", None) is not None:
                data["doctor_id"] = self.user.user_id
        # normalize date/time (strings -> python objects) done in repo.create as well
        appt = self.repo.create(data)
        return appt

    def modify_appointment(self, appointment_id: int, appointment_data: Optional[dict] = None, **kwargs) -> Optional[Appointment]:
        """
        Accept either modify_appointment(id, {'status':'pending', ...}) OR modify_appointment(id, status='pending').
        Returns the updated ORM instance (or None).
        """
        data = {}
        if appointment_data:
            # if appointment_data came as dict
            data.update(appointment_data)
        if kwargs:
            data.update(kwargs)
        if not data:
            # nothing to update -> return the fresh object
            return self.repo.get_by_id(appointment_id)

        updated = self.repo.update(appointment_id, data)
        return updated

    def cancel_appointment(self, appointment_id: int) -> Optional[Appointment]:
        # Set status -> use repo.update(appointment_id, data)
        return self.modify_appointment(appointment_id, {"status": "cancelled"})

    def complete_appointment(self, appointment_id: int) -> Optional[Appointment]:
        return self.modify_appointment(appointment_id, {"status": "completed"})


    """def get_by_day(self, target_date: date) -> List[Appointment]:
        return self.repo.find_by_date_range(target_date, target_date)"""

    def get_by_week(self, start_date: date) -> List[Appointment]:
        return self.repo.find_by_date_range(start_date, start_date + timedelta(days=6))

    def get_by_month(self, year: int, month: int) -> List[Appointment]:
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return self.repo.find_by_date_range(start, end)

    def search_by_patient(self, patient_id: int) -> List[Appointment]:
        return self.repo.find_by_patient(patient_id)

    def get_all_specialties(self) -> List[str]:
        """
        Retourne la liste des noms de spécialités triés alphabétiquement.
        """
        session = self.repo.session
        specs = (session
                 .query(MedicalSpecialty)
                 .order_by(MedicalSpecialty.name)
                 .all())
        return [s.name for s in specs]

    # ——— Wrappers KPI ———
    
    def weekly_appointments(self, doctor_id: Optional[int], year: int):
        """
        Retourne la répartition hebdomadaire des RDV pour un médecin donné.
        """
        return self.repo.appointments_per_week_for_doctor(doctor_id, year)

    def upcoming_appointments(self, doctor_id: Optional[int] = None, limit: int = 5):
        """
        Retourne les prochains RDV (par défaut les 5 prochains).
        """
        return self.repo.next_appointments_for_doctor(doctor_id, limit=limit)
    
    def _resolve_doctor(self, doctor_id: Optional[int]) -> int:
        if doctor_id is not None:
            return doctor_id
        if getattr(self.user, 'user_id', None) is not None:
            return self.user.user_id
        raise RuntimeError("doctor_id non disponible")
    
    # KPI wrappers
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
        if year is None:
            year = date.today().year
        return self.repo.appointments_per_month_for_doctor(d, year)

    """def upcoming_today(self, doctor_id: Optional[int] = None) -> List[Appointment]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.upcoming_for_day(d, date.today())"""
    
    def get_appointments_by_day(self, target_day):
        return self.repo.get_appointments_by_day(target_day)

    
        # —— Versions filtrées par médecin —— #

    def get_by_day_doctor(self, doctor_id: Optional[int], target_date: date) -> List[Appointment]:
        """
        Récupère tous les RDV d’un médecin pour une journée donnée.
        """
        d = self._resolve_doctor(doctor_id)
        return self.repo.find_by_date_range_for_doctor(d, target_date, target_date)

    def get_by_week_doctor(self, doctor_id: Optional[int], start_date: date) -> List[Appointment]:
        """
        Récupère tous les RDV d’un médecin pour une semaine (7 jours).
        """
        d = self._resolve_doctor(doctor_id)
        return self.repo.find_by_date_range_for_doctor(d, start_date, start_date + timedelta(days=6))

    def get_by_month_doctor(self, doctor_id: Optional[int], year: int, month: int) -> List[Appointment]:
        """
        Récupère tous les RDV d’un médecin pour un mois précis.
        """
        d = self._resolve_doctor(doctor_id)
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return self.repo.find_by_date_range_for_doctor(d, start, end)

    def search_by_patient_doctor(self, doctor_id: Optional[int], patient_id: int) -> List[Appointment]:
        """
        Récupère tous les RDV d’un médecin pour un patient donné.
        """
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
        """
        Retourne les rendez-vous filtrés par médecin.
        """
        return self.repo.search_by_doctor(doctor_id)
    
    def upcoming_today(self, doctor_id: Optional[int] = None):
        d = doctor_id or getattr(self.user, "user_id", None)
        if d is None:
            raise RuntimeError("Doctor id non disponible")

        try:
            if hasattr(self.repo, "upcoming_for_day"):
                return self.repo.upcoming_for_day(d, date.today())
            # fallback si ancien repo avait une méthode nommée différemment
            if hasattr(self.repo, "upcoming"):
                return self.repo.upcoming(d, date.today())
            raise RuntimeError("AppointmentRepository: méthode 'upcoming_for_day' introuvable")
        except Exception as e:
            self.logger.exception("Erreur upcoming_today: %s", e)
            raise

