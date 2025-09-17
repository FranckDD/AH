import uuid
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Classe pour convertir les dictionnaires en objets avec attributs
class PatientObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class PatientRepositoryOffline:
    def __init__(self, session: Session):
        self.session = session
        self._appointment_user_col: Optional[str] = None

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def _generate_code(self, birth_date: date, last_name: Optional[str], first_name: Optional[str],
                       father_name: Optional[str] = None, mother_name: Optional[str] = None) -> str:
        prefix = "AH2-"
        ymd = birth_date.strftime('%y%m%d')
        parent_initial = ((mother_name or '').strip()[:1].upper() or (father_name or '').strip()[:1].upper() or 'X')
        last_initial = (last_name or 'X')[0].upper()
        base_code = f"{prefix}{ymd}{last_initial}{parent_initial}"
        code = base_code
        i = 1
        while self.session.execute(text("SELECT 1 FROM patients WHERE code_patient = :c"), {"c": code}).fetchone():
            i += 1
            code = f"{base_code}{i}"
        return code

    # -------------------------
    # Detection colonne user/doctor
    # -------------------------
    def _detect_appointment_user_col(self) -> Optional[str]:
        """
        Retourne la colonne à utiliser pour le médecin dans la table appointments,
        typiquement 'user_id' (offline) ou 'doctor_id' (postgres). Met en cache le résultat.
        """
        if self._appointment_user_col is not None:
            return self._appointment_user_col
        try:
            # pragma table_info renvoie des rows (cid, name, type, ...)
            rows = self.session.execute(text("PRAGMA table_info(appointments)")).fetchall()
            cols = [r[1] for r in rows]  # index 1 = name
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

    # -------------------------
    # CRUD patients
    # -------------------------
    def create_patient(self, data: dict, current_user) -> Tuple[int, str]:
        birth_date = data['birth_date'] if isinstance(data['birth_date'], date) else date.fromisoformat(data['birth_date'])
        code = self._generate_code(
            birth_date=birth_date,
            last_name=data.get('last_name'),
            first_name=data.get('first_name'),
            father_name=data.get('father_name'),
            mother_name=data.get('mother_name')
        )
        now = self._now()
        row_uuid = str(uuid.uuid4())
        q = text("""
            INSERT INTO patients (
                code_patient, first_name, last_name, birth_date, gender,
                national_id, contact_phone, assurance, residence,
                father_name, mother_name,
                created_at, last_updated_at, last_modified, uuid, revision, sync_status
            ) VALUES (
                :code_patient, :first_name, :last_name, :birth_date, :gender,
                :national_id, :contact_phone, :assurance, :residence,
                :father_name, :mother_name,
                :created_at, :last_updated_at, :last_modified, :uuid, :revision, :sync_status
            )
        """)
        params = {
            "code_patient": code,
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "birth_date": birth_date.isoformat(),
            "gender": data.get("gender"),
            "national_id": data.get("national_id"),
            "contact_phone": data.get("contact_phone"),
            "assurance": data.get("assurance"),
            "residence": data.get("residence"),
            "father_name": data.get("father_name"),
            "mother_name": data.get("mother_name"),
            "created_at": now,
            "last_updated_at": now,
            "last_modified": now,
            "uuid": row_uuid,
            "revision": 1,
            "sync_status": "created"
        }
        try:
            res = self.session.execute(q, params)
            self.session.commit()

            # récupérer id en toute sécurité
            new_id = getattr(res, "lastrowid", None)
            if new_id is None:
                row = self.session.execute(text("SELECT last_insert_rowid() AS id")).mappings().first()
                new_id = row["id"] if row and "id" in row else None

            if new_id is None:
                raise RuntimeError("Impossible de déterminer l'ID inséré pour patients")

            return int(new_id), code
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def update_patient(self, patient_id: int, data: dict, current_user) -> int:
        set_clauses = []
        params = {"patient_id": patient_id, "last_modified": self._now()}
        for k, v in data.items():
            if k in ("first_name","last_name","birth_date","gender","national_id","contact_phone","assurance","residence","father_name","mother_name"):
                set_clauses.append(f"{k} = :{k}")
                params[k] = (v.isoformat() if isinstance(v, date) else v)
        if not set_clauses:
            return patient_id
        update_sql = f"""
            UPDATE patients SET
                {', '.join(set_clauses)},
                last_updated_at = :last_modified,
                last_modified = :last_modified,
                revision = COALESCE(revision, 1) + 1,
                sync_status = 'updated'
            WHERE patient_id = :patient_id
        """
        try:
            self.session.execute(text(update_sql), params)
            self.session.commit()
            return patient_id
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete_patient(self, patient_id: int) -> bool:
        now = self._now()
        sql = text("""
            UPDATE patients
            SET sync_status = 'deleted',
                last_updated_at = :now,
                last_modified = :now,
                revision = COALESCE(revision, 1) + 1
            WHERE patient_id = :id
        """)
        try:
            res = self.session.execute(sql, {"id": patient_id, "now": now})
            self.session.commit()
            return (getattr(res, "rowcount", None) or 0) > 0
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, patient_id: int) -> Optional[PatientObject]:
        r = self.session.execute(text("SELECT * FROM patients WHERE patient_id = :id"), {"id": patient_id}).mappings().first()
        return PatientObject(**dict(r)) if r else None

    def list_patients(self, page: int = 1, per_page: int = 10, search: Optional[str] = None) -> List[PatientObject]:
        q = "SELECT * FROM patients"
        params = {}
        if search:
            params["term"] = f"%{search}%"
            q += " WHERE first_name LIKE :term OR last_name LIKE :term OR code_patient LIKE :term OR national_id LIKE :term"
        q += " ORDER BY last_name LIMIT :limit OFFSET :offset"
        params["limit"] = per_page
        params["offset"] = (page-1)*per_page
        rows = self.session.execute(text(q), params).mappings().all()
        return [PatientObject(**dict(r)) for r in rows]

    def find_by_code(self, code: Optional[str]):
        if not code:
            return None
        raw = code.strip().upper()
        if not raw.startswith("AH2-"):
            raw = "AH2-" + raw
        r = self.session.execute(text("SELECT * FROM patients WHERE UPPER(code_patient) = :c"), {"c": raw}).mappings().first()
        return PatientObject(**dict(r)) if r else None

    # -------------------------
    # Requêtes liées aux RDV (utilisent user/doctor col dynamique)
    # -------------------------
# inside PatientRepositoryOffline
    def _user_col(self) -> str:
        try:
            rows = self.session.execute(text("PRAGMA table_info(appointments)")).fetchall()
            cols = [r[1] for r in rows]
            return "doctor_id" if "doctor_id" in cols else ("user_id" if "user_id" in cols else "user_id")
        except Exception:
            return "user_id"

    def patients_for_day(self, doctor_id: int, target_date: date) -> List[PatientObject]:
        uc = self._user_col()
        sql = text(f"""
            SELECT DISTINCT p.*
            FROM patients p
            JOIN appointments a ON a.patient_id = p.patient_id
            WHERE a.{uc} = :doc
            AND date(a.appointment_date) = :d
            ORDER BY p.last_name
        """)
        rows = self.session.execute(sql, {"doc": doctor_id, "d": target_date.isoformat()}).mappings().all()
        return [PatientObject(**dict(r)) for r in rows]


    def patients_count_for_doctor(self, doctor_id: int) -> int:
        user_col = self._get_user_col_or_raise()
        sql = text(f"""
            SELECT COUNT(DISTINCT p.patient_id) AS cnt
            FROM patients p
            JOIN appointments a ON a.patient_id = p.patient_id
            WHERE a.{user_col} = :doc
        """)
        row = self.session.execute(sql, {"doc": doctor_id}).mappings().first()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0

    def patients_followed_by_doctor(self, doctor_id: int, page: int = 1, per_page: int = 50) -> List[PatientObject]:
        user_col = self._get_user_col_or_raise()
        sql = text(f"""
            SELECT DISTINCT p.*
            FROM patients p
            JOIN appointments a ON a.patient_id = p.patient_id
            WHERE a.{user_col} = :doc
            ORDER BY p.last_name
            LIMIT :limit OFFSET :offset
        """)
        params = {"doc": doctor_id, "limit": per_page, "offset": (page-1)*per_page}
        rows = self.session.execute(sql, params).mappings().all()
        return [PatientObject(**dict(r)) for r in rows]

    def count_registered(self, period: str = "day") -> int:
        today = date.today()
        sql = "SELECT COUNT(*) AS cnt FROM patients WHERE date(created_at) >= :start"

        if period == "day":
            params = {"start": today.isoformat()}
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            params = {"start": start_week.isoformat()}
        else:
            return 0

        row = self.session.execute(text(sql), params).mappings().first()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0

    def count_by_creation_date(self, creation_date: date) -> int:
        sql = text("SELECT COUNT(*) AS cnt FROM patients WHERE date(created_at) = :d")
        row = self.session.execute(sql, {"d": creation_date.isoformat()}).mappings().first()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0

    def count_by_creation_date_range(self, start_date: date, end_date: date) -> int:
        sql = text("SELECT COUNT(*) AS cnt FROM patients WHERE date(created_at) >= :start AND date(created_at) <= :end")
        params = {"start": start_date.isoformat(), "end": end_date.isoformat()}
        row = self.session.execute(sql, params).mappings().first()
        return int(row["cnt"]) if row and row["cnt"] is not None else 0
