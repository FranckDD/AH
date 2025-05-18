# repositories/prescription_repo.py
from sqlalchemy import text
from models.database import DatabaseManager
from sqlalchemy.orm import Session
from models.prescription import Prescription

class PrescriptionRepository:
    def __init__(self):
        self.db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
        self.session: Session = self.db.get_session()

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
            data['patient_id'] = self.get(prescription_id).patient_id

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
