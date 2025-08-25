# repositories/prescription_repo.py
from sqlalchemy import text
from models.database import DatabaseManager
from sqlalchemy.orm import Session
from models.prescription import Prescription
from sqlalchemy import func
from datetime import date, timedelta
from typing import List

class PrescriptionRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(self, patient_id=None, page=1, per_page=20):
        q = self.session.query(Prescription)
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        return q.order_by(Prescription.start_date.desc()) \
                .offset((page-1)*per_page) \
                .limit(per_page).all()

    def get(self, prescription_id):
        return self.session.get(Prescription, prescription_id)

    def create(self, data: dict):
        sql = text("""
            CALL public.create_prescription(
              :patient_id,
              :medication,
              :dosage,
              :frequency,
              :duration,
              :medical_record_id,
              :start_date,
              :end_date,
              :notes,
              :prescribed_by,
              :prescribed_by_name
            )
        """
        )
        try:
            self.session.execute(sql, data)
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise

    def update(self, prescription_id: int, data: dict):
        data['prescription_id'] = prescription_id
        if 'patient_id' not in data:
            prescription = self.get(prescription_id)
            if prescription is None:
                raise ValueError(f"Prescription with ID {prescription_id} not found")
            data['patient_id'] = prescription.patient_id

        sql = text("""
            CALL public.update_prescription(
              :prescription_id,
              :patient_id,
              :medication,
              :dosage,
              :frequency,
              :duration,
              :medical_record_id,
              :start_date,
              :end_date,
              :notes,
              :prescribed_by,
              :prescribed_by_name
            )
        """
        )
        try:
            self.session.execute(sql, data)
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise

    def delete(self, prescription_id: int):
        try:
            self.session.execute(
                text("DELETE FROM public.prescriptions WHERE prescription_id = :prescription_id"),
                {'prescription_id': prescription_id}
            )
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise

    def find_by_date_range(self, start_date: date, end_date: date) -> List:
        return (
            self.session
                .query(Prescription)
                .filter(func.date(Prescription.start_date) >= start_date)
                .filter(func.date(Prescription.end_date) <= end_date)
                .all()
        )

    def find_renewals_for_doctor(self, doctor_id: int, within_days: int = 14):
        """
        Retourne ordonnances dont end_date dans (today .. today+within_days) pour le docteur.
        """
        today = date.today()
        target = today + timedelta(days=within_days)
        return (
            self.session.query(Prescription)
                .filter(Prescription.prescribed_by == doctor_id)
                .filter(func.date(Prescription.end_date) >= today)
                .filter(func.date(Prescription.end_date) <= target)
                .order_by(Prescription.end_date)
                .all()
        )
    
    def count_renewals_for_doctor(self, doctor_id: int, within_days: int = 14) -> int:
        today = date.today()
        target = today + timedelta(days=within_days)
        q = (
            self.session.query(func.count(Prescription.prescription_id))
                .filter(Prescription.prescribed_by == doctor_id)
                .filter(func.date(Prescription.end_date) >= today)
                .filter(func.date(Prescription.end_date) <= target)
        )
        return int(q.scalar() or 0)

    def count_active_for_doctor(self, doctor_id: int) -> int:
        q = self.session.query(func.count(Prescription.prescription_id)).filter(Prescription.prescribed_by == doctor_id).filter(Prescription.status == 'active')
        return int(q.scalar() or 0)
    
    def count_by_prescription_date(self, prescription_date: date) -> int:
        """Compte les prescriptions pour une date spécifique."""
        return (
            self.session.query(Prescription)
            .filter(func.date(Prescription.start_date) == prescription_date)
            .count()
        )

    def count_by_prescription_date_range(self, start_date: date, end_date: date) -> int:
        """Compte les prescriptions dans une plage de dates."""
        return (
            self.session.query(Prescription)
            .filter(func.date(Prescription.start_date) >= start_date)
            .filter(func.date(Prescription.start_date) <= end_date)
            .count()
        )