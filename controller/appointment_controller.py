import logging
from datetime import date, timedelta
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
        # data must include patient_id
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
        try:
            session = self.repo.session
            session.add(appt)
            session.commit()
            return appt
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Erreur création RDV: {e}")
            raise

    def modify_appointment(self, appointment_id: int, **kwargs) -> Appointment:
        appt = self.repo.get_by_id(appointment_id)
        if not appt:
            self.logger.warning(f"RDV introuvable: id={appointment_id}")
            return None
        for field, value in kwargs.items():
            if hasattr(appt, field):
                setattr(appt, field, value)
        return self.repo.update(appt)

    def cancel_appointment(self, appointment_id: int) -> Appointment:
        appt = self.repo.get_by_id(appointment_id)
        if not appt:
            self.logger.warning(f"Annulation impossible, RDV introuvable: id={appointment_id}")
            return None
        appt.status = 'cancelled'
        return self.repo.update(appt)

    def get_by_day(self, target_date: date) -> list[Appointment]:
        return self.repo.find_by_date_range(target_date, target_date)

    def get_by_week(self, start_date: date) -> list[Appointment]:
        return self.repo.find_by_date_range(start_date, start_date + timedelta(days=6))

    def get_by_month(self, year: int, month: int) -> list[Appointment]:
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return self.repo.find_by_date_range(start, end)

    def search_by_patient(self, patient_id: int) -> list[Appointment]:
        return self.repo.find_by_patient(patient_id)

    def search_by_doctor(self, doctor_id: int = None) -> list[Appointment]:
        return self.repo.find_by_doctor(doctor_id or self.user.user_id)

    def get_all_specialties(self) -> list[str]:
        """
        Retourne la liste des noms de spécialités triés alphabétiquement.
        """
        session = self.repo.session
        specs = (session
                 .query(MedicalSpecialty)
                 .order_by(MedicalSpecialty.name)
                 .all())
        return [s.name for s in specs]