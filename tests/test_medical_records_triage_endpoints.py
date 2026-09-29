import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, medical_records_endpoint)


def test_create_record_with_review_flag_appears_in_pending_list(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse1", "nurse", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "triage_hep_medecin1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    nurse_headers = auth_headers(client, "triage_hep_nurse1", TEST_PASSWORD)
    medecin_headers = auth_headers(client, "triage_hep_medecin1", TEST_PASSWORD)

    client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": medecin.user_id,
    }, headers=nurse_headers)

    resp = client.get("/medical_records/pending-review", headers=medecin_headers)
    assert resp.status_code == 200
    assert any(r["patient_id"] == patient_id for r in resp.json())


def test_claim_forbidden_for_nurse(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse2", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    headers = auth_headers(client, "triage_hep_nurse2", TEST_PASSWORD)

    create_resp = client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    }, headers=headers)
    record_id = create_resp.json()["record_id"]

    resp = client.post(f"/medical_records/{record_id}/claim", headers=headers)
    assert resp.status_code == 403


def test_claim_success_removes_from_pending_list(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse3", "nurse", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "triage_hep_medecin3", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    nurse_headers = auth_headers(client, "triage_hep_nurse3", TEST_PASSWORD)
    medecin_headers = auth_headers(client, "triage_hep_medecin3", TEST_PASSWORD)

    create_resp = client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    }, headers=nurse_headers)
    record_id = create_resp.json()["record_id"]

    claim_resp = client.post(f"/medical_records/{record_id}/claim", headers=medecin_headers)
    assert claim_resp.status_code == 200

    pending = client.get("/medical_records/pending-review", headers=medecin_headers)
    assert record_id not in [r["record_id"] for r in pending.json()]


def test_claim_twice_returns_409(db_session, api_client):
    nurse = create_test_user(db_session, "triage_hep_nurse4", "nurse", password=TEST_PASSWORD)
    medecin_a = create_test_user(db_session, "triage_hep_medecin_a4", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "triage_hep_medecin_b4", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    client = _client(api_client)
    nurse_headers = auth_headers(client, "triage_hep_nurse4", TEST_PASSWORD)
    headers_a = auth_headers(client, "triage_hep_medecin_a4", TEST_PASSWORD)
    headers_b = auth_headers(client, "triage_hep_medecin_b4", TEST_PASSWORD)

    create_resp = client.post("/medical_records/", json={
        "patient_id": patient_id, "motif_code": "consultation",
        "needs_doctor_review": True, "assigned_doctor_id": None,
    }, headers=nurse_headers)
    record_id = create_resp.json()["record_id"]

    assert client.post(f"/medical_records/{record_id}/claim", headers=headers_a).status_code == 200
    assert client.post(f"/medical_records/{record_id}/claim", headers=headers_b).status_code == 409
