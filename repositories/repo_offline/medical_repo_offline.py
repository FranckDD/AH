import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

class MedicalRecordRepositoryOffline:
    def __init__(self, session):
        self.session = session
        self._appointment_user_col: Optional[str] = None

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def _detect_appointment_user_col(self) -> Optional[str]:
        if self._appointment_user_col is not None:
            return self._appointment_user_col
        try:
            rows = self.session.execute(text("PRAGMA table_info(appointments)")).fetchall()
            cols = [r[1] for r in rows]
            if "user_id" in cols:
                col = "user_id"
            elif "doctor_id" in cols:
                col = "doctor_id"
            else:
                col = None
        except Exception:
            col = None
        self._appointment_user_col = col
        return col

    def _get_user_col_or_raise(self) -> str:
        col = self._detect_appointment_user_col()
        if not col:
            raise RuntimeError("Table 'appointments' ne contient ni 'user_id' ni 'doctor_id' — vérifie le schéma offline.")
        return col

    def create(self, data: dict) -> int:
        record_uuid = str(uuid.uuid4())
        now = self._now()

        sql = text("""
            INSERT INTO medical_records (
                uuid, patient_id, appointment_id, consultation_date, marital_status, bp, temperature,
                weight, height, medical_history, allergies, symptoms, diagnosis, treatment, severity, notes, motif_code,
                created_by, created_by_name, last_updated_by, last_updated_by_name,
                created_at, updated_at, revision, sync_status
            )
            VALUES (
                :uuid, :patient_id, :appointment_id, :consultation_date, :marital_status, :bp, :temperature,
                :weight, :height, :medical_history, :allergies, :symptoms, :diagnosis, :treatment, :severity, :notes, :motif_code,
                :created_by, :created_by_name, :last_updated_by, :last_updated_by_name,
                :created_at, :updated_at, :revision, :sync_status
            )
        """)

        params = {
            "uuid": record_uuid,
            "patient_id": data["patient_id"],
            "appointment_id": data.get("appointment_id"),
            "consultation_date": data.get("consultation_date"),
            "marital_status": data.get("marital_status"),
            "bp": data.get("bp"),
            "temperature": data.get("temperature"),
            "weight": data.get("weight"),
            "height": data.get("height"),
            "medical_history": data.get("medical_history"),
            "allergies": data.get("allergies"),
            "symptoms": data.get("symptoms"),
            "diagnosis": data.get("diagnosis"),
            "treatment": data.get("treatment"),
            "severity": data.get("severity"),
            "notes": data.get("notes"),
            "motif_code": data.get("motif_code"),
            "created_by": data.get("created_by"),
            "created_by_name": data.get("created_by_name"),
            "last_updated_by": data.get("last_updated_by"),
            "last_updated_by_name": data.get("last_updated_by_name"),
            "created_at": now,
            "updated_at": now,
            "revision": 1,
            "sync_status": "created"
        }

        try:
            res = self.session.execute(sql, params)
            self.session.commit()

            new_id = getattr(res, "lastrowid", None)
            if new_id is None:
                row = self.session.execute(text("SELECT last_insert_rowid() AS id")).mappings().first()
                new_id = row["id"] if row and "id" in row else None

            if new_id is None:
                raise RuntimeError("Impossible de déterminer l'ID inséré pour medical_records")

            return int(new_id)
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        sql = text("SELECT * FROM medical_records WHERE record_id = :id")
        row = self.session.execute(sql, {"id": record_id}).mappings().first()
        return dict(row) if row else None

    def update(self, record_id: int, data: dict) -> bool:
        allowed = ["marital_status", "bp", "temperature", "weight", "height", "medical_history",
                   "allergies", "symptoms", "diagnosis", "treatment", "severity", "notes", "motif_code", "appointment_id"]
        sets = []
        params = {"id": record_id, "updated_at": self._now()}
        for k in allowed:
            if k in data:
                sets.append(f"{k} = :{k}")
                params[k] = data[k]
        if not sets:
            return False
        sql = text(f"""
            UPDATE medical_records
            SET {', '.join(sets)},
                updated_at = :updated_at,
                last_modified = :updated_at,
                revision = COALESCE(revision, 1) + 1,
                sync_status = 'updated'
            WHERE record_id = :id
        """)
        try:
            res = self.session.execute(sql, params)
            self.session.commit()
            return (getattr(res, "rowcount", None) or 0) > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete(self, record_id: int) -> bool:
        sql = text("DELETE FROM medical_records WHERE record_id = :id")
        try:
            res = self.session.execute(sql, {"id": record_id})
            self.session.commit()
            return (getattr(res, "rowcount", None) or 0) > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def list_records(self, patient_id: Optional[int] = None, page: int = 1, per_page: int = 20):
        params = {}
        where = ""
        if patient_id:
            where = "WHERE patient_id = :pid"
            params["pid"] = patient_id
        offset = (page - 1) * per_page
        sql = text(f"SELECT * FROM medical_records {where} ORDER BY consultation_date DESC LIMIT :lim OFFSET :off")
        params.update({"lim": per_page, "off": offset})
        rows = self.session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def find_by_date_range(self, start_date: date, end_date: date):
        sql = text("""
            SELECT * FROM medical_records
            WHERE date(consultation_date) >= :start AND date(consultation_date) <= :end
            ORDER BY consultation_date DESC
        """)
        rows = self.session.execute(sql, {"start": start_date.isoformat(), "end": end_date.isoformat()}).mappings().all()
        return [dict(r) for r in rows]

    def get_motifs(self):
        sql = text("SELECT DISTINCT motif_code FROM medical_records")
        rows = self.session.execute(sql).mappings().all()
        return [r["motif_code"] for r in rows if r["motif_code"]]

    def get_last_for_patient(self, patient_id: int):
        sql = text("SELECT * FROM medical_records WHERE patient_id = :pid ORDER BY consultation_date DESC LIMIT 1")
        row = self.session.execute(sql, {"pid": patient_id}).mappings().first()
        return dict(row) if row else None

    def count_by_consultation_date(self, target_date: date) -> int:
        sql = text("SELECT COUNT(*) AS cnt FROM medical_records WHERE date(consultation_date) = :d")
        row = self.session.execute(sql, {"d": target_date.isoformat()}).mappings().first()
        return int(row["cnt"] or 0) if row else 0

    def count_by_consultation_date_range(self, start_date: date, end_date: date) -> int:
        sql = text("""
            SELECT COUNT(*) AS cnt
            FROM medical_records
            WHERE date(consultation_date) >= :start AND date(consultation_date) <= :end
        """)
        row = self.session.execute(sql, {"start": start_date.isoformat(), "end": end_date.isoformat()}).mappings().first()
        return int(row["cnt"] or 0) if row else 0

    def breakdown_by_motif_for_doctor(self, doctor_id: int, start=None, end=None):
        user_col = self._get_user_col_or_raise()
        params = {"doc": doctor_id}
        where_clauses = [f"a.{user_col} = :doc"]
        if start:
            where_clauses.append("date(mr.consultation_date) >= :start")
            params["start"] = start.isoformat()
        if end:
            where_clauses.append("date(mr.consultation_date) <= :end")
            params["end"] = end.isoformat()

        where = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT mr.motif_code AS motif, COUNT(DISTINCT mr.patient_id) AS cnt
            FROM medical_records mr
            JOIN appointments a ON a.appointment_id = mr.appointment_id
            WHERE {where}
            GROUP BY mr.motif_code
        """)
        rows = self.session.execute(sql, params).mappings().all()
        return { (r["motif"] or "Non spécifié"): int(r["cnt"]) for r in rows }
