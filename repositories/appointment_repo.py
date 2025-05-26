from sqlalchemy.orm import Session
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