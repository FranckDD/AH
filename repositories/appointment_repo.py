#Appointment_repo.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import date, datetime, timedelta, time
from models.appointment import Appointment
from models.database import DatabaseManager
from models.patient import Patient  # adapte selon ton projet




class AppointmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, appointment: dict | Appointment) -> Appointment:
            """
            Accept either:
            - an ORM Appointment instance -> add & commit
            - a dict with fields -> construct an Appointment and commit
            """
            if appointment is None:
                raise ValueError("appointment cannot be None")

            # If it's already an Appointment instance
            if isinstance(appointment, Appointment):
                self.session.add(appointment)
                self.session.commit()
                self.session.refresh(appointment)
                return appointment

            # otherwise expect a dict
            data = dict(appointment)  # copy

            # Normalize possible date/time strings -> SQLAlchemy expects python date/time objects
            # appointment_date may be ISO string 'YYYY-MM-DD'
            if "appointment_date" in data and isinstance(data["appointment_date"], str):
                try:
                    data["appointment_date"] = datetime.fromisoformat(data["appointment_date"]).date()
                except Exception:
                    # ignore, DB may accept string or raise later
                    pass

            # appointment_time may be 'HH:MM'
            if "appointment_time" in data and isinstance(data["appointment_time"], str):
                try:
                    hh, mm = data["appointment_time"].split(":")
                    data["appointment_time"] = time(int(hh), int(mm))
                except Exception:
                    pass

            # Allowed fields — adapt to your model if names differ
            allowed = ("patient_id", "doctor_id", "specialty",
                    "appointment_date", "appointment_time", "reason", "status")

            appt = Appointment()
            for k in allowed:
                if k in data:
                    setattr(appt, k, data[k])

            self.session.add(appt)
            self.session.commit()
            self.session.refresh(appt)
            return appt
    
    def list_paginated_with_relations(
        self, page: int = 1, per_page: int = 20,
        date_from: Optional[date] = None, date_to: Optional[date] = None,
        patient_id: Optional[int] = None, doctor_id: Optional[int] = None, search: Optional[str] = None
    ) -> Tuple[List[Appointment], int]:
        q = self.session.query(Appointment).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor)
        ).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())

        if date_from and date_to:
            q = q.filter(and_(Appointment.appointment_date >= date_from, Appointment.appointment_date <= date_to))
        if patient_id:
            q = q.filter(Appointment.patient_id == patient_id)
        if doctor_id:
            q = q.filter(Appointment.doctor_id == doctor_id)
        # optional search across patient code or reason
        if search:
            s = f"%{search}%"
            # join patient search by code or name
            q = q.join(Patient, Appointment.patient).filter(
                (Patient.code_patient.ilike(s)) |
                (Patient.first_name.ilike(s)) |
                (Patient.last_name.ilike(s)) |
                (Appointment.reason.ilike(s))
            )

        total = q.count()
        skip = max(0, (int(page)-1) * int(per_page))
        items = q.offset(skip).limit(int(per_page)).all()
        return items, total

    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        return (self.session.query(Appointment)
                .options(joinedload(Appointment.patient), joinedload(Appointment.doctor))
                .filter(Appointment.id == appointment_id).one_or_none())

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

    def update(self, appointment_id: int, data: dict) -> Optional[Appointment]:
        appt = self.session.query(Appointment).filter(Appointment.id == appointment_id).one_or_none()
        if not appt:
            return None
        for k, v in data.items():
            setattr(appt, k, v)
        self.session.commit()
        self.session.refresh(appt)
        return appt

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
    
        # helper for counting by day (used by dashboard)
    def count_by_day(self, target_date: date) -> int:
        return (self.session.query(Appointment)
                .filter(Appointment.appointment_date == target_date)
                .count())
    

    def upcoming_for_day(self, doctor_id: int, target_date: date) -> List[Dict[str, Any]]:
        from models.appointment import Appointment
        q = self.session.query(Appointment).filter(Appointment.doctor_id == doctor_id)

        try:
            q = q.filter(func.date(Appointment.appointment_date) == target_date)
        except Exception:
            start_dt = datetime.combine(target_date, time.min)
            end_dt = start_dt + timedelta(days=1)
            q = q.filter(Appointment.appointment_date >= start_dt,
                            Appointment.appointment_date < end_dt)

        q = q.order_by(Appointment.appointment_date)
        rows = q.all()

        def _to_dict(a):
            return {
                "appointment_id": getattr(a, "appointment_id", None),
                "patient_id": getattr(a, "patient_id", None),
                "doctor_id": getattr(a, "doctor_id", None),
                "scheduled_at": getattr(a, "appointment_date", None),
                "status": getattr(a, "status", None),
                "notes": getattr(a, "notes", None),
            }

        return [_to_dict(r) for r in rows] or []
    

    
    def get_appointments_by_day(self, target_day):
        if isinstance(target_day, str):
            target_day = date.fromisoformat(target_day)
        elif isinstance(target_day, datetime):
            target_day = target_day.date()

        q = (self.session.query(Appointment)
            .filter(func.date(Appointment.appointment_date) == target_day)
            .order_by(Appointment.appointment_date))
        
        return q.all()


