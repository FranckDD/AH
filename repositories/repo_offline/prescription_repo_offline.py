# repositories/repo_offline/prescription_repo_offline.py
import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

class PrescriptionRepositoryOffline:
    def __init__(self, session):
        self.session = session

    def create(self, data: dict) -> int:
        """
        data expects keys: patient_id, medical_record_id (opt), medication, dosage, frequency, duration,
        start_date, end_date, notes, prescribed_by, prescribed_by_name
        """
        presc_uuid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        sql = text("""
            INSERT INTO prescriptions (uuid, patient_id, medical_record_id, medication, dosage, frequency, duration,
                start_date, end_date, notes, status, prescribed_by, prescribed_by_name, created_at, last_modified)
            VALUES (:uuid, :patient_id, :medical_record_id, :medication, :dosage, :frequency, :duration,
                :start_date, :end_date, :notes, :status, :prescribed_by, :prescribed_by_name, :created_at, :last_modified)
        """)
        params = {
            "uuid": presc_uuid,
            "patient_id": data.get("patient_id"),
            "medical_record_id": data.get("medical_record_id"),
            "medication": data["medication"],
            "dosage": data.get("dosage"),
            "frequency": data.get("frequency"),
            "duration": data.get("duration"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "notes": data.get("notes"),
            "status": data.get("status", "active"),
            "prescribed_by": data.get("prescribed_by"),
            "prescribed_by_name": data.get("prescribed_by_name"),
            "created_at": now,
            "last_modified": now
        }
        try:
            res = self.session.execute(sql, params)
            self.session.commit()
            lastrow = res.lastrowid if hasattr(res, "lastrowid") else None
            if not lastrow:
                row = self.session.execute(text("SELECT last_insert_rowid() AS id")).mappings().first()
                lastrow = row["id"]
            return int(lastrow)
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get(self, prescription_id: int) -> Optional[Dict[str, Any]]:
        sql = text("SELECT * FROM prescriptions WHERE prescription_id = :id")
        row = self.session.execute(sql, {"id": prescription_id}).mappings().first()
        return dict(row) if row else None

    def update(self, prescription_id: int, data: dict) -> bool:
        allowed = ["medication", "dosage", "frequency", "duration", "start_date", "end_date", "notes", "status"]
        sets = []
        params = {"id": prescription_id, "last_modified": datetime.utcnow().isoformat()}
        for k in allowed:
            if k in data:
                sets.append(f"{k} = :{k}")
                params[k] = data[k]
        if not sets:
            return False
        sql = text(f"UPDATE prescriptions SET {', '.join(sets)}, last_modified = :last_modified WHERE prescription_id = :id")
        try:
            res = self.session.execute(sql, params)
            self.session.commit()
            return res.rowcount > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete(self, prescription_id: int) -> bool:
        sql = text("DELETE FROM prescriptions WHERE prescription_id = :id")
        try:
            res = self.session.execute(sql, {"id": prescription_id})
            self.session.commit()
            return res.rowcount > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def list(self, patient_id: Optional[int] = None, page: int = 1, per_page: int = 20):
        params = {}
        where = ""
        if patient_id:
            where = "WHERE patient_id = :pid"
            params["pid"] = patient_id
        offset = (page - 1) * per_page
        sql = text(f"SELECT * FROM prescriptions {where} ORDER BY created_at DESC LIMIT :lim OFFSET :off")
        params.update({"lim": per_page, "off": offset})
        rows = self.session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def find_by_date_range(self, start_date: date, end_date: date):
        sql = text("SELECT * FROM prescriptions WHERE date(created_at) >= :start AND date(created_at) <= :end ORDER BY created_at DESC")
        rows = self.session.execute(sql, {"start": start_date.isoformat(), "end": end_date.isoformat()}).mappings().all()
        return [dict(r) for r in rows]

    def find_renewals_for_doctor(self, doctor_id: int, within_days: int = 14):
        """
        Renewal heuristic: prescriptions for patients where the last prescription by this doctor is within 'within_days'.
        (Simple implementation: join appointments to prescriptions or filter prescribed_by)
        """
        since = (datetime.utcnow() - timedelta(days=within_days)).date().isoformat()
        sql = text("""
            SELECT p.*
            FROM prescriptions p
            WHERE p.prescribed_by = :doc AND date(p.created_at) >= :since
            ORDER BY p.created_at DESC
        """)
        rows = self.session.execute(sql, {"doc": doctor_id, "since": since}).mappings().all()
        return [dict(r) for r in rows]

    def count_by_prescription_date(self, target_date: date) -> int:
        sql = text("SELECT COUNT(*) AS cnt FROM prescriptions WHERE date(created_at) = :d")
        row = self.session.execute(sql, {"d": target_date.isoformat()}).mappings().first()
        return int(row["cnt"] or 0)

    def count_by_prescription_date_range(self, start_date: date, end_date: date) -> int:
        sql = text("SELECT COUNT(*) AS cnt FROM prescriptions WHERE date(created_at) >= :start AND date(created_at) <= :end")
        row = self.session.execute(sql, {"start": start_date.isoformat(), "end": end_date.isoformat()}).mappings().first()
        return int(row["cnt"] or 0)
    
    # repositories/repo_offline/prescription_repo_offline.py
# Ajoutez ces méthodes à la classe PrescriptionRepositoryOffline

def count_active_for_doctor(self, doctor_id: int) -> int:
    sql = text("SELECT COUNT(*) AS cnt FROM prescriptions WHERE prescribed_by = :doc AND status = 'active'")
    row = self.session.execute(sql, {"doc": doctor_id}).mappings().first()
    return int(row["cnt"] or 0) if row else 0

def count_renewals_for_doctor(self, doctor_id: int, within_days: int = 14) -> int:
    today = date.today()
    target = today + timedelta(days=within_days)
    sql = text("""
        SELECT COUNT(*) AS cnt 
        FROM prescriptions 
        WHERE prescribed_by = :doc 
        AND date(end_date) >= :today 
        AND date(end_date) <= :target
    """)
    params = {"doc": doctor_id, "today": today.isoformat(), "target": target.isoformat()}
    row = self.session.execute(sql, params).mappings().first()
    return int(row["cnt"] or 0) if row else 0
