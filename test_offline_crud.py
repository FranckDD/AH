# test_offline_crud.py
from datetime import date, datetime
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Session SQLite in-memory pour tests
engine = create_engine("sqlite:///:memory:", echo=True, future=True)
Session = sessionmaker(bind=engine, future=True)
session = Session()

# --- Création des tables ---
session.execute(text("""
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_patient TEXT,
    first_name TEXT,
    last_name TEXT,
    birth_date TEXT,
    gender TEXT,
    national_id TEXT,
    contact_phone TEXT,
    assurance TEXT,
    residence TEXT,
    father_name TEXT,
    mother_name TEXT,
    created_at TEXT,
    last_updated_at TEXT,
    last_modified TEXT,
    uuid TEXT,
    revision INTEGER,
    sync_status TEXT
)
"""))

session.execute(text("""
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    user_id INTEGER,
    appointment_date TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""))

session.execute(text("""
CREATE TABLE IF NOT EXISTS medical_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    patient_id INTEGER,
    appointment_id INTEGER,
    consultation_date TEXT,
    marital_status TEXT,
    bp TEXT,
    temperature TEXT,
    weight TEXT,
    height TEXT,
    medical_history TEXT,
    allergies TEXT,
    symptoms TEXT,
    diagnosis TEXT,
    treatment TEXT,
    severity TEXT,
    notes TEXT,
    motif_code TEXT,
    created_by INTEGER,
    created_by_name TEXT,
    last_updated_by INTEGER,
    last_updated_by_name TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""))

session.commit()

# --- Insert patient ---
patient_uuid = str(uuid.uuid4())
session.execute(
    text("""
    INSERT INTO patients (code_patient, first_name, last_name, birth_date, gender, created_at, last_updated_at, last_modified, uuid, revision, sync_status)
    VALUES (:code_patient, :first_name, :last_name, :birth_date, :gender, :created_at, :last_updated_at, :last_modified, :uuid, :revision, :sync_status)
    """),
    {
        "code_patient": "AH2-000001",
        "first_name": "John",
        "last_name": "Doe",
        "birth_date": date(1990,1,1).isoformat(),
        "gender": "M",
        "created_at": datetime.utcnow().isoformat(),
        "last_updated_at": datetime.utcnow().isoformat(),
        "last_modified": datetime.utcnow().isoformat(),
        "uuid": patient_uuid,
        "revision": 1,
        "sync_status": "created"
    }
)

patient_id = session.execute(text("SELECT last_insert_rowid()")).scalar_one()

# --- Insert appointment ---
appointment_date = datetime.utcnow().isoformat()
session.execute(
    text("INSERT INTO appointments (patient_id, user_id, appointment_date, created_at, updated_at) VALUES (:pid, :uid, :date, :created_at, :updated_at)"),
    {
        "pid": patient_id,
        "uid": 1,
        "date": appointment_date,
        "created_at": appointment_date,
        "updated_at": appointment_date
    }
)

appointment_id = session.execute(text("SELECT last_insert_rowid()")).scalar_one()

# --- Insert medical record ---
record_uuid = str(uuid.uuid4())
session.execute(
    text("""
    INSERT INTO medical_records (uuid, patient_id, appointment_id, consultation_date, created_by, created_by_name, last_updated_by, last_updated_by_name, created_at, updated_at)
    VALUES (:uuid, :pid, :aid, :consultation_date, :created_by, :created_by_name, :last_updated_by, :last_updated_by_name, :created_at, :updated_at)
    """),
    {
        "uuid": record_uuid,
        "pid": patient_id,
        "aid": appointment_id,
        "consultation_date": appointment_date,
        "created_by": 1,
        "created_by_name": "Dr. Smith",
        "last_updated_by": 1,
        "last_updated_by_name": "Dr. Smith",
        "created_at": appointment_date,
        "updated_at": appointment_date
    }
)

session.commit()

# --- Lire et afficher patient ---
patient = session.execute(text("SELECT * FROM patients WHERE patient_id = :id"), {"id": patient_id}).mappings().first()
print("Patient:", dict(patient))

# --- Lire et afficher appointment ---
appt = session.execute(text("SELECT * FROM appointments WHERE appointment_id = :id"), {"id": appointment_id}).mappings().first()
print("Appointment:", dict(appt))

# --- Lire et afficher medical record ---
record = session.execute(text("SELECT * FROM medical_records WHERE uuid = :uuid"), {"uuid": record_uuid}).mappings().first()
print("Medical Record:", dict(record))

# --- Update patient ---
session.execute(
    text("UPDATE patients SET first_name = :fname, last_updated_at = :updated WHERE patient_id = :id"),
    {"fname": "Jane", "updated": datetime.utcnow().isoformat(), "id": patient_id}
)
session.commit()

updated_patient = session.execute(text("SELECT * FROM patients WHERE patient_id = :id"), {"id": patient_id}).mappings().first()
print("Updated Patient:", dict(updated_patient))

# --- Delete medical record ---
session.execute(text("DELETE FROM medical_records WHERE uuid = :uuid"), {"uuid": record_uuid})
session.commit()
deleted_record = session.execute(text("SELECT * FROM medical_records WHERE uuid = :uuid"), {"uuid": record_uuid}).mappings().first()
print("Deleted Record:", deleted_record)  # doit être None

session.close()
