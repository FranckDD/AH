# repositories/repo_offline/appointment_repo_offline.py
import uuid
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

class AppointmentRepositoryOffline:
    """
    Repository Offline pour appointments (SQLite via SQLAlchemy).
    Méthodes KPI alignées avec la version online.
    Détecte automatiquement si la colonne user_id ou doctor_id existe
    et s'adapte.
    """

    def __init__(self, session):
        self.session = session
        self.user_col = self._detect_user_column()  # 'user_id' or 'doctor_id'

    # ---------------------------
    # Helpers de normalisation
    # ---------------------------
    def _detect_user_column(self) -> str:
        """
        Vérifie PRAGMA table_info(appointments) et retourne la colonne
        qui représente l'utilisateur/doctor sur les appointments.
        Priorité: 'user_id' puis 'doctor_id'. Si aucune trouvée, retourne 'user_id'.
        """
        try:
            res = self.session.execute(text("PRAGMA table_info(appointments)")).fetchall()
            cols = [row[1] for row in res]  # row[1] = name
            if "user_id" in cols:
                return "user_id"
            if "doctor_id" in cols:
                return "doctor_id"
            # fallback
            return "user_id"
        except Exception:
            return "user_id"

    def _to_iso_datetime(self, v) -> Optional[str]:
        """Convertit date/datetime/str en chaîne ISO compatible SQLite (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(v, date) and not isinstance(v, datetime):
            return v.isoformat()  # YYYY-MM-DD
        if isinstance(v, str):
            s = v.strip()
            # try parse ISO-like (full datetime)
            try:
                dt = datetime.fromisoformat(s)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                # likely a 'YYYY-MM-DD' date string -> return as is
                return s
        return str(v)

    def _to_time_obj(self, v) -> Optional[time]:
        """
        Convertit string 'HH:MM'/'HH:MM:SS' ou datetime/datetime.time en datetime.time.
        Retourne None si impossible / None en entrée.
        """
        if v is None:
            return None
        if isinstance(v, time):
            return v
        if isinstance(v, datetime):
            return v.time()
        if isinstance(v, str):
            s = v.strip()
            for fmt in ("%H:%M:%S", "%H:%M"):
                try:
                    return datetime.strptime(s, fmt).time()
                except Exception:
                    pass
            try:
                return datetime.fromisoformat(s).time()
            except Exception:
                return None
        return None

    def _time_to_str(self, t: Optional[time]) -> Optional[str]:
        """Convertit datetime.time en 'HH:MM:SS' ou retourne None."""
        if t is None:
            return None
        return t.strftime("%H:%M:%S")

    def _ensure_int(self, v, default=None) -> Optional[int]:
        try:
            return None if v is None else int(v)
        except Exception:
            return default

    # ---------------------------
    # CRUD basique
    # ---------------------------

    def create(self, data: dict) -> int:
        """
        data keys: patient_id (required), user_id or doctor_id (optional),
        appointment_date (date/datetime/str), appointment_time (str/time), specialty, reason, status.
        Retourne appointment_id (int).
        """
        if "patient_id" not in data:
            raise ValueError("patient_id requis pour créer un rendez-vous")

        appt_uuid = str(uuid.uuid4())
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # normalize IDs
        patient_id = self._ensure_int(data.get("patient_id"))
        user_id = data.get("user_id") or data.get("doctor_id")
        user_id = self._ensure_int(user_id, default=None)

        # normalize date/time for SQLite:
        appt_date = self._to_iso_datetime(data.get("appointment_date"))
        appt_time_obj = self._to_time_obj(data.get("appointment_time"))
        appt_time_str = self._time_to_str(appt_time_obj)

        # build SQL with dynamic user column name
        user_col = self.user_col
        sql = text(f"""
            INSERT INTO appointments
            (uuid, patient_id, {user_col}, specialty, appointment_date, appointment_time, reason, status, created_at, updated_at)
            VALUES (:uuid, :patient_id, :{user_col}, :specialty, :appointment_date, :appointment_time, :reason, :status, :created_at, :updated_at)
        """)
        params: Dict[str, Any] = {
            "uuid": appt_uuid,
            "patient_id": patient_id,
            user_col: user_id,
            "specialty": data.get("specialty"),
            "appointment_date": appt_date,         # string 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
            "appointment_time": appt_time_str,     # string 'HH:MM:SS' or None
            "reason": data.get("reason"),
            "status": data.get("status", "pending"),
            "created_at": now,
            "updated_at": now
        }

        try:
            res = self.session.execute(sql, params)
            self.session.commit()
            lastrow = getattr(res, "lastrowid", None)
            if not lastrow:
                row = self.session.execute(text("SELECT last_insert_rowid() AS id")).mappings().first()
                lastrow = row["id"] if row else None
            return int(lastrow)
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        sql = text("SELECT * FROM appointments WHERE appointment_id = :id")
        row = self.session.execute(sql, {"id": appointment_id}).mappings().first()
        return dict(row) if row else None

    def update(self, appointment_id: int, data: dict) -> bool:
        allowed = ["user_id", "patient_id", "specialty", "appointment_date", "appointment_time", "reason", "status"]
        sets = []
        params: Dict[str, Any] = {"id": appointment_id, "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
        user_col = self.user_col
        for k in allowed:
            if k in data:
                # map incoming 'doctor_id' -> actual column if needed
                if k == "user_id":
                    params[user_col] = self._ensure_int(data[k], default=None)
                    sets.append(f"{user_col} = :{user_col}")
                elif k == "appointment_date":
                    params[k] = self._to_iso_datetime(data[k])
                    sets.append(f"{k} = :{k}")
                elif k == "appointment_time":
                    tobj = self._to_time_obj(data[k])
                    params[k] = self._time_to_str(tobj)
                    sets.append(f"{k} = :{k}")
                elif k in ("patient_id",):
                    params[k] = self._ensure_int(data[k], default=None)
                    sets.append(f"{k} = :{k}")
                else:
                    params[k] = data[k]
                    sets.append(f"{k} = :{k}")

        if not sets:
            return False
        sql = text(f"UPDATE appointments SET {', '.join(sets)}, updated_at = :updated_at WHERE appointment_id = :id")
        try:
            res = self.session.execute(sql, params)
            self.session.commit()
            return res.rowcount > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete(self, appointment_id: int) -> bool:
        sql = text("DELETE FROM appointments WHERE appointment_id = :id")
        try:
            res = self.session.execute(sql, {"id": appointment_id})
            self.session.commit()
            return res.rowcount > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    # ---------------------------
    # Requêtes simples
    # ---------------------------

    def find_by_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        params = {"start": self._to_iso_datetime(start_date), "end": self._to_iso_datetime(end_date)}
        sql = text("""
            SELECT * FROM appointments
            WHERE date(appointment_date) >= :start AND date(appointment_date) <= :end
            ORDER BY appointment_date
        """)
        rows = self.session.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def find_by_patient(self, patient_id: int) -> List[Dict[str, Any]]:
        sql = text("SELECT * FROM appointments WHERE patient_id = :pid ORDER BY appointment_date DESC")
        rows = self.session.execute(sql, {"pid": int(patient_id)}).mappings().all()
        return [dict(r) for r in rows]

    def next_appointments_for_doctor(self, doctor_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        user_col = self.user_col
        sql = text(f"""
            SELECT * FROM appointments
            WHERE {user_col} = :doc AND date(appointment_date) >= date('now')
            ORDER BY appointment_date ASC
            LIMIT :lim
        """)
        rows = self.session.execute(sql, {"doc": int(doctor_id), "lim": int(limit)}).mappings().all()
        return [dict(r) for r in rows]

    # ---------------------------
    # KPI de base
    # ---------------------------

    def count_by_status_for_doctor(self, doctor_id: int, start: Optional[date] = None, end: Optional[date] = None) -> Dict[str,int]:
        user_col = self.user_col
        params: Dict[str, Any] = {"doc": int(doctor_id)}
        where = f"{user_col} = :doc"
        if start:
            params["start"] = self._to_iso_datetime(start)
            where += " AND date(appointment_date) >= :start"
        if end:
            params["end"] = self._to_iso_datetime(end)
            where += " AND date(appointment_date) <= :end"
        sql = text(f"SELECT status, COUNT(*) AS cnt FROM appointments WHERE {where} GROUP BY status")
        rows = self.session.execute(sql, params).mappings().all()
        return {(r["status"] or "unknown"): int(r["cnt"]) for r in rows}

    def appointments_per_day_for_doctor(self, doctor_id: int, start: Optional[date] = None, end: Optional[date] = None) -> List[Tuple[str,int]]:
        user_col = self.user_col
        params: Dict[str, Any] = {"doc": int(doctor_id)}
        where = f"{user_col} = :doc"
        if start:
            params["start"] = self._to_iso_datetime(start)
            where += " AND date(appointment_date) >= :start"
        if end:
            params["end"] = self._to_iso_datetime(end)
            where += " AND date(appointment_date) <= :end"
        sql = text(f"""
            SELECT date(appointment_date) AS d, COUNT(*) AS cnt
            FROM appointments WHERE {where}
            GROUP BY d ORDER BY d
        """)
        rows = self.session.execute(sql, params).mappings().all()
        return [(r["d"], int(r["cnt"])) for r in rows]

    def count_distinct_patients_for_doctor(
        self, doctor_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> int:
        user_col = self.user_col
        params: Dict[str, Any] = {"doc": int(doctor_id)}
        where = f"{user_col} = :doc"
        if start_date:
            params["start"] = self._to_iso_datetime(start_date)
            where += " AND date(appointment_date) >= :start"
        if end_date:
            params["end"] = self._to_iso_datetime(end_date)
            where += " AND date(appointment_date) <= :end"
        sql = text(f"SELECT COUNT(DISTINCT patient_id) AS cnt FROM appointments WHERE {where}")
        row = self.session.execute(sql, params).mappings().first()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0

    # ---------------------------
    # KPI avancées (semaines / mois / spécialités)
    # ---------------------------

    def appointments_per_week_for_doctor(self, doctor_id: int, weeks: int = 4) -> List[Tuple[str,int]]:
        user_col = self.user_col
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(weeks=weeks)
        params = {"doc": int(doctor_id), "start": self._to_iso_datetime(start_dt), "end": self._to_iso_datetime(end_dt)}
        sql = text(f"""
            SELECT strftime('%Y-%W', appointment_date) AS week, COUNT(*) AS cnt
            FROM appointments
            WHERE {user_col} = :doc AND appointment_date BETWEEN :start AND :end
            GROUP BY week
            ORDER BY week
        """)
        rows = self.session.execute(sql, params).mappings().all()
        return [(r["week"], int(r["cnt"])) for r in rows]

    def appointments_per_month_for_doctor(self, doctor_id: int, months: int = 6) -> List[Tuple[str,int]]:
        user_col = self.user_col
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=30 * max(1, int(months)))
        params = {"doc": int(doctor_id), "start": self._to_iso_datetime(start_dt), "end": self._to_iso_datetime(end_dt)}
        sql = text(f"""
            SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS cnt
            FROM appointments
            WHERE {user_col} = :doc AND appointment_date BETWEEN :start AND :end
            GROUP BY month
            ORDER BY month
        """)
        rows = self.session.execute(sql, params).mappings().all()
        return [(r["month"], int(r["cnt"])) for r in rows]

    def appointments_by_specialty_for_doctor(self, doctor_id: int, start: Optional[date] = None, end: Optional[date] = None) -> Dict[str,int]:
        user_col = self.user_col
        params: Dict[str, Any] = {"doc": int(doctor_id)}
        where = f"{user_col} = :doc"
        if start:
            params["start"] = self._to_iso_datetime(start)
            where += " AND date(appointment_date) >= :start"
        if end:
            params["end"] = self._to_iso_datetime(end)
            where += " AND date(appointment_date) <= :end"
        sql = text(f"""
            SELECT specialty, COUNT(*) AS cnt
            FROM appointments
            WHERE {where}
            GROUP BY specialty
        """)
        rows = self.session.execute(sql, params).mappings().all()
        return {(r["specialty"] or "unknown"): int(r["cnt"]) for r in rows}

    def count_total_for_doctor(self, doctor_id: int, start: Optional[date] = None, end: Optional[date] = None) -> int:
        user_col = self.user_col
        params: Dict[str, Any] = {"doc": int(doctor_id)}
        where = f"{user_col} = :doc"
        if start:
            params["start"] = self._to_iso_datetime(start)
            where += " AND date(appointment_date) >= :start"
        if end:
            params["end"] = self._to_iso_datetime(end)
            where += " AND date(appointment_date) <= :end"
        sql = text(f"SELECT COUNT(*) AS cnt FROM appointments WHERE {where}")
        row = self.session.execute(sql, params).mappings().first()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0

    def list_all(self) -> List[Dict[str, Any]]:
        sql = text("SELECT * FROM appointments ORDER BY appointment_date DESC")
        rows = self.session.execute(sql).mappings().all()
        return [dict(r) for r in rows]
