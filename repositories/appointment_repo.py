#Appointment_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import List, Dict, Tuple, Optional
from datetime import date, datetime, timedelta
from models.appointment import Appointment
from models.database import DatabaseManager



class AppointmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, appointment: Appointment) -> Appointment:
        self.session.add(appointment)
        self.session.commit()
        return appointment

    def get_by_id(self, id: int) -> Appointment:
        return self.session.query(Appointment).filter_by(id=id).first()

    def list_all(self) -> list[Appointment]:
        return self.session.query(Appointment).order_by(Appointment.appointment_date).all()

    def find_by_patient(self, patient_id: int) -> list[Appointment]:
        return self.session.query(Appointment).filter_by(patient_id=patient_id).all()

    def find_by_doctor(self, doctor_id: int) -> list[Appointment]:
        return self.session.query(Appointment).filter_by(doctor_id=doctor_id).all()

    def find_by_date_range(self, start_date, end_date) -> list[Appointment]:
        return (
            self.session
                .query(Appointment)
                .filter(Appointment.appointment_date >= start_date,
                        Appointment.appointment_date <= end_date)
                .all()
        )

    def update(self, appointment: Appointment) -> Appointment:
        self.session.merge(appointment)
        self.session.commit()
        return appointment

    def delete(self, appointment: Appointment) -> None:
        self.session.delete(appointment)
        self.session.commit()


    #KPI DashBoard Medecin
    def count_by_status_for_doctor(self,
                                   doctor_id: int,
                                   start_date: Optional[date] = None,
                                   end_date: Optional[date] = None) -> Dict[str,int]:
        q = self.session.query(Appointment.status, func.count(Appointment.id)) \
                        .filter(Appointment.doctor_id == doctor_id)
        if start_date:
            q = q.filter(Appointment.appointment_date >= start_date)
        if end_date:
            q = q.filter(Appointment.appointment_date <= end_date)
        rows = q.group_by(Appointment.status).all()
        return {status or "unknown": int(cnt) for status, cnt in rows}

    def count_total_for_doctor(self,
                               doctor_id: int,
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None) -> int:
        q = self.session.query(func.count(Appointment.id)).filter(Appointment.doctor_id == doctor_id)
        if start_date:
            q = q.filter(Appointment.appointment_date >= start_date)
        if end_date:
            q = q.filter(Appointment.appointment_date <= end_date)
        return int(q.scalar() or 0)

    def appointments_per_day_for_doctor(self,
                                        doctor_id: int,
                                        start_date: Optional[date] = None,
                                        end_date: Optional[date] = None) -> List[Tuple[str,int]]:
        """
        Retourne [(YYYY-MM-DD, count), ...] pour chaque jour présent entre start..end.
        Si start_date/end_date sont None, on retourne toutes les dates groupées (attention).
        """
        q = self.session.query(Appointment.appointment_date, func.count(Appointment.id)) \
                        .filter(Appointment.doctor_id == doctor_id)
        if start_date:
            q = q.filter(Appointment.appointment_date >= start_date)
        if end_date:
            q = q.filter(Appointment.appointment_date <= end_date)
        q = q.group_by(Appointment.appointment_date).order_by(Appointment.appointment_date)
        return [(d.isoformat(), int(c)) for d, c in q.all()]

    def count_distinct_patients_for_doctor(self,
                                           doctor_id: int,
                                           start_date: Optional[date] = None,
                                           end_date: Optional[date] = None) -> int:
        q = self.session.query(func.count(func.distinct(Appointment.patient_id))) \
                        .filter(Appointment.doctor_id == doctor_id)
        if start_date:
            q = q.filter(Appointment.appointment_date >= start_date)
        if end_date:
            q = q.filter(Appointment.appointment_date <= end_date)
        return int(q.scalar() or 0)

    def appointments_per_month_for_doctor(self,
                                          doctor_id: int,
                                          year: int) -> List[Tuple[int,int]]:
        """
        Retourne list de (month_int, count) pour l'année donnée.
        """
        q = self.session.query(
                extract('month', Appointment.appointment_date).label('m'),
                func.count(Appointment.id)
            ).filter(Appointment.doctor_id == doctor_id) \
             .filter(extract('year', Appointment.appointment_date) == year) \
             .group_by('m').order_by('m')
        return [(int(m), int(cnt)) for m, cnt in q.all()]

    def find_by_doctor_and_date_range(self,
                                      doctor_id: int,
                                      start_date: Optional[date],
                                      end_date: Optional[date]) -> List[Appointment]:
        q = self.session.query(Appointment).filter(Appointment.doctor_id == doctor_id)
        if start_date:
            q = q.filter(Appointment.appointment_date >= start_date)
        if end_date:
            q = q.filter(Appointment.appointment_date <= end_date)
        return q.order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    def appointments_per_week_for_doctor(self,
                                         doctor_id: int,
                                         year: int) -> List[Tuple[int, int]]:
        """
        Retourne [(week_number, count), ...] pour un médecin donné dans l'année spécifiée.
        """
        q = self.session.query(
                extract('week', Appointment.appointment_date).label('w'),
                func.count(Appointment.id)
            ).filter(Appointment.doctor_id == doctor_id) \
             .filter(extract('year', Appointment.appointment_date) == year) \
             .group_by('w').order_by('w')
        return [(int(w), int(cnt)) for w, cnt in q.all()]

    def next_appointments_for_doctor(self,
                                     doctor_id: int,
                                     limit: int = 5) -> List[Appointment]:
        """
        Retourne la liste des prochains RDV futurs pour ce médecin, triés par date/heure.
        """
        now = datetime.now()
        q = self.session.query(Appointment) \
                        .filter(Appointment.doctor_id == doctor_id) \
                        .filter(Appointment.appointment_date >= now.date()) \
                        .order_by(Appointment.appointment_date, Appointment.appointment_time) \
                        .limit(limit)
        return q.all()
    
    def find_by_date_range_for_doctor(self, doctor_id: int, start_date, end_date) -> list[Appointment]:
        return (
            self.session
                .query(Appointment)
                .filter(Appointment.doctor_id == doctor_id)
                .filter(Appointment.appointment_date >= start_date,
                        Appointment.appointment_date <= end_date)
                .all()
        )

    def find_by_patient_for_doctor(self, doctor_id: int, patient_id: int) -> list[Appointment]:
        return (
            self.session
                .query(Appointment)
                .filter(Appointment.doctor_id == doctor_id)
                .filter(Appointment.patient_id == patient_id)
                .all()
        )
    
    # appointment_repo.py
    def count_consultations(self, period: str = "day") -> int:
        today = date.today()
        if period == "day":
            return (
                self.session.query(Appointment)
                .filter(Appointment.appointment_date == today,
                        Appointment.status == "completed")
                .count()
            )
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            return (
                self.session.query(Appointment)
                .filter(Appointment.appointment_date >= start_week,
                        Appointment.status == "completed")
                .count()
            )
        return 0

