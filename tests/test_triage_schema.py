# tests/test_triage_schema.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from tests.conftest import create_test_user, create_test_patient


def test_medical_records_triage_columns_exist(db_session):
    row = db_session.execute(text("""
        SELECT column_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'medical_records'
          AND column_name IN ('needs_doctor_review', 'assigned_doctor_id', 'reviewed_by', 'reviewed_at')
    """)).fetchall()
    cols = {r[0]: r for r in row}
    assert set(cols.keys()) == {'needs_doctor_review', 'assigned_doctor_id', 'reviewed_by', 'reviewed_at'}
    assert cols['needs_doctor_review'][1] == 'NO'


def test_appointments_doctor_id_is_nullable(db_session):
    row = db_session.execute(text("""
        SELECT is_nullable FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'doctor_id'
    """)).fetchone()
    assert row[0] == 'YES'


def test_appointment_without_doctor_id_can_be_inserted(db_session):
    nurse = create_test_user(db_session, "triage_schema_nurse", "nurse")
    patient_id, _ = create_test_patient(db_session, nurse)
    db_session.execute(text("""
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status)
        VALUES (:patient_id, NULL, CURRENT_DATE, '09:00', 'pending')
    """), {"patient_id": patient_id})
    db_session.flush()
