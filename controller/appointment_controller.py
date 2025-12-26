# controller/appointment_controller.py
import logging
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple

from sqlalchemy.exc import SQLAlchemyError
from models.appointment import Appointment
from models.medical_speciality import MedicalSpecialty

class AppointmentController:
    def __init__(self, repo, patient_controller, current_user):
        self.repo = repo
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.logger = logging.getLogger(__name__)

    def book_appointment(self, data: dict) -> Appointment:
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
            raise

    def modify_appointment(self, appointment_id: int, **kwargs) -> Optional[Appointment]:
        appt = self.repo.get_by_id(appointment_id)
        if not appt:
            self.logger.warning(f"RDV introuvable: id={appointment_id}")
            return None
        for field, value in kwargs.items():
            if hasattr(appt, field):
                setattr(appt, field, value)
        return self.repo.update(appt)

    def cancel_appointment(self, appointment_id: int) -> Optional[Appointment]:
        appt = self.repo.get_by_id(appointment_id)
        if not appt:
            self.logger.warning(f"Annulation impossible, RDV introuvable: id={appointment_id}")
            return None
        appt.status = 'cancelled'
        return self.repo.update(appt)
    
    def complete_appointment(self, appointment_id: int) -> Optional[Appointment]:
        appt = self.repo.get_by_id(appointment_id)
        if not appt:
            self.logger.warning(f"Impossible de compléter, RDV introuvable: id={appointment_id}")
            return None
        appt.status = 'completed'
        return self.repo.update(appt)


    def get_by_day(self, target_date: date) -> List[Appointment]:
        return self.repo.find_by_date_range(target_date, target_date)

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
    
    def weekly_appointments(self, doctor_id: int, year: int):
        """
        Retourne la répartition hebdomadaire des RDV pour un médecin donné.
        """
        return self.repo.appointments_per_week_for_doctor(doctor_id, year)

    def upcoming_appointments(self, doctor_id: int, limit: int = 5):
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

    def upcoming_today(self, doctor_id: Optional[int] = None) -> List[Appointment]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.upcoming_for_day(d, date.today())
    
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

