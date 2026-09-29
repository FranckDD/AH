import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.appointment import appointment_endpoints
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, appointment_endpoints)


def test_book_appointment_explicit_null_doctor_stays_unassigned(db_session, api_client):
    """Le repli automatique sur le createur ne doit jamais ecraser un
    choix explicite 'Non assigne' venant du formulaire web (payload avec
    doctor_id=None, pas une cle absente)."""
    nurse = create_test_user(db_session, "triage_appt_nurse1", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    headers = auth_headers(client, "triage_appt_nurse1", TEST_PASSWORD)

    resp = client.post("/appointments/", json={
        "patient_id": patient_id, "doctor_id": None,
        "appointment_date": "2026-10-15", "appointment_time": "09:00", "reason": "Test",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["doctor_id"] is None


def test_book_appointment_explicit_doctor_id_respected(db_session, api_client):
    nurse = create_test_user(db_session, "triage_appt_nurse2", "nurse", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "triage_appt_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    headers = auth_headers(client, "triage_appt_nurse2", TEST_PASSWORD)

    resp = client.post("/appointments/", json={
        "patient_id": patient_id, "doctor_id": medecin.user_id,
        "appointment_date": "2026-10-15", "appointment_time": "09:30", "reason": "Test",
    }, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["doctor_id"] == medecin.user_id
