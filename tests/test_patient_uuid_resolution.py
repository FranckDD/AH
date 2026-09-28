# tests/test_patient_uuid_resolution.py
from datetime import date

from sqlalchemy import text

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def _uuid_of(db_session, patient_id):
    return db_session.execute(
        text("SELECT uuid::text FROM patients WHERE patient_id = :pid"), {"pid": patient_id}
    ).scalar()


def test_medical_record_par_patient_uuid(db_session, api_client):
    """Consultation creee hors ligne pour un patient lui-meme cree hors
    ligne : le client ne connait que l'uuid du patient."""
    medecin = create_test_user(db_session, "test_res_med1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="ResMed")
    db_session.flush()
    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_res_med1", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_uuid": _uuid_of(db_session, patient_id),
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["patient_id"] == patient_id


def test_medical_record_patient_uuid_inconnu_renvoie_422(db_session, api_client):
    create_test_user(db_session, "test_res_med2", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_res_med2", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_uuid": "eeeeeeee-1111-2222-3333-444444444444",
        "motif_code": "consultation",
    }, headers=headers)
    assert resp.status_code == 422, resp.text


def test_medical_record_sans_patient_renvoie_400(db_session, api_client):
    create_test_user(db_session, "test_res_med3", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_res_med3", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={"motif_code": "consultation"}, headers=headers)
    assert resp.status_code == 400, resp.text


def test_prescription_par_patient_uuid(db_session, api_client):
    medecin = create_test_user(db_session, "test_res_presc1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="ResPresc")
    db_session.flush()
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_res_presc1", TEST_PASSWORD)

    resp = client.post("/prescriptions/", json={
        "patient_uuid": _uuid_of(db_session, patient_id),
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date.today()),
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["patient_id"] == patient_id


def test_prescription_patient_uuid_inconnu_renvoie_422(db_session, api_client):
    create_test_user(db_session, "test_res_presc2", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_res_presc2", TEST_PASSWORD)

    resp = client.post("/prescriptions/", json={
        "patient_uuid": "ffffffff-1111-2222-3333-444444444444",
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date.today()),
    }, headers=headers)
    assert resp.status_code == 422, resp.text
