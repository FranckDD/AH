from sqlalchemy import text, func
from models.database import DatabaseManager
from sqlalchemy.orm import Session
from models.medical_record import MedicalRecord
from sqlalchemy.orm import joinedload
from datetime import date, timedelta
from typing import List

class MedicalRecordRepository:
    def __init__(self, session: Session):
        self.session = session


    def list_records(self, patient_id=None, page=1, per_page=20):
        #q = self.session.query(MedicalRecord).options(joinedload(MedicalRecord.patient))
        q = self.session.query(MedicalRecord)
        if patient_id:
            q = q.filter_by(patient_id=patient_id)
        return q.offset((page-1)*per_page).limit(per_page).all()

    def get(self, record_id):
        return self.session.get(MedicalRecord, record_id)

    def create(self, data: dict):
        # Appelle la procédure SQL
        sql = text(
            "CALL public.create_medical_record(:patient_id, LOCALTIMESTAMP, :marital_status, :bp,"
            " :temperature, :weight, :height, :medical_history, :allergies,"
            " :symptoms, :diagnosis, :treatment, :severity, :notes, :motif_code)"
        )
        self.session.execute(sql, data)
        self.session.commit()
        return True

    def update(self, record_id: int, data: dict):
        # on ne veut plus passer patient_id à la procédure d’update
        # supprimez-le du dict si présent
        data = data.copy()
        data.pop('patient_id', None)

        # ajoute le record_id
        data['record_id'] = record_id

        sql = text(
            "CALL public.update_medical_record("
            " :record_id,"
            " :marital_status,"
            " :bp,"
            " :temperature,"
            " :weight,"
            " :height,"
            " :medical_history,"
            " :allergies,"
            " :symptoms,"
            " :diagnosis,"
            " :treatment,"
            " :severity,"
            " :notes,"
            " :motif_code)"
        )
        self.session.execute(sql, data)
        self.session.commit()
        return True


    def delete(self, record_id: int):
        # On suppose exist proc delete_medical_record
        sql = text("CALL public.delete_medical_record(:record_id)")
        self.session.execute(sql, {'record_id': record_id})
        self.session.commit()
        return True

    def get_motifs(self) -> list:
        # Récupère code et label_fr
        result = self.session.execute(text(
            "SELECT code, label_fr FROM motif_translations ORDER BY label_fr"
        ))
                # row here is a Row; use mappings() to get dict-like rows
        return [dict(row) for row in result.mappings()]
    
    def find_by_date_range(self, start_date: date, end_date: date) -> List[MedicalRecord]:
        return (
            self.session
                .query(MedicalRecord)
                .filter(func.date(MedicalRecord.consultation_date) >= start_date)
                .filter(func.date(MedicalRecord.consultation_date) <= end_date)
                .all()
        )
