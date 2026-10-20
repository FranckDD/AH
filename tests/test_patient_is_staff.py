# tests/test_patient_is_staff.py
"""Task 4 (reduction personnel) : patients.is_staff - lecture sur
GET /patients/ et GET /patients/{id}, ecriture uniquement via
PUT /patients/{id}/staff (admin, promoteur)."""
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from models.audit import AuditUserAction
from models.patient import Patient
from tests.conftest import auth_headers, create_test_patient, create_test_user

PASSWORD = "TestPass123!"


def _setup(db_session, api_client, login, role, first_name="StaffT"):
    user = create_test_user(db_session, login, role, password=PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, first_name=first_name)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, login, PASSWORD)
    return client, headers, patient_id


def _is_staff_db(db_session, patient_id):
    db_session.expire_all()
    return db_session.query(Patient).filter_by(patient_id=patient_id).one().is_staff


def test_admin_and_promoteur_can_set_staff(db_session, api_client):
    client, headers, patient_id = _setup(db_session, api_client, "staff_admin", "admin")
    resp = client.put(f"/patients/{patient_id}/staff", json={"is_staff": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"patient_id": patient_id, "is_staff": True}
    assert _is_staff_db(db_session, patient_id) is True

    create_test_user(db_session, "staff_promo", "promoteur", password=PASSWORD)
    headers_p = auth_headers(client, "staff_promo", PASSWORD)
    resp = client.put(f"/patients/{patient_id}/staff", json={"is_staff": False}, headers=headers_p)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"patient_id": patient_id, "is_staff": False}
    assert _is_staff_db(db_session, patient_id) is False


def test_secretaire_medecin_nurse_get_403(db_session, api_client):
    client, _, patient_id = _setup(db_session, api_client, "staff_creator", "admin")
    for role in ("secretaire", "medecin", "nurse"):
        login = f"staff_{role}"
        create_test_user(db_session, login, role, password=PASSWORD)
        headers = auth_headers(client, login, PASSWORD)
        resp = client.put(f"/patients/{patient_id}/staff", json={"is_staff": True}, headers=headers)
        assert resp.status_code == 403, f"{role}: {resp.status_code}"
    assert _is_staff_db(db_session, patient_id) is False


def test_put_patient_with_is_staff_in_body_does_not_change_it(db_session, api_client):
    client, headers, patient_id = _setup(db_session, api_client, "staff_secr", "secretaire")
    resp = client.put(
        f"/patients/{patient_id}",
        json={"first_name": "Renomme", "is_staff": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_staff"] is False
    assert _is_staff_db(db_session, patient_id) is False


def test_set_staff_unknown_patient_404(db_session, api_client):
    client, headers, _ = _setup(db_session, api_client, "staff_admin404", "admin")
    resp = client.put("/patients/999999999/staff", json={"is_staff": True}, headers=headers)
    assert resp.status_code == 404


def test_set_staff_soft_deleted_patient_404(db_session, api_client):
    client, headers, patient_id = _setup(db_session, api_client, "staff_admin_sd", "admin")
    db_session.query(Patient).filter_by(patient_id=patient_id).update({"is_deleted": True})
    db_session.flush()
    resp = client.put(f"/patients/{patient_id}/staff", json={"is_staff": True}, headers=headers)
    assert resp.status_code == 404
    assert _is_staff_db(db_session, patient_id) is False


def test_get_patients_list_and_detail_expose_is_staff(db_session, api_client):
    client, headers, patient_id = _setup(db_session, api_client, "staff_admin_get", "admin", "ExposeStaff")

    detail = client.get(f"/patients/{patient_id}", headers=headers).json()
    assert detail["is_staff"] is False

    assert client.put(f"/patients/{patient_id}/staff", json={"is_staff": True}, headers=headers).status_code == 200

    detail = client.get(f"/patients/{patient_id}", headers=headers).json()
    assert detail["is_staff"] is True

    listing = client.get("/patients/", params={"search": "ExposeStaff", "per_page": 100}, headers=headers).json()
    rows = [p for p in listing["data"] if p["patient_id"] == patient_id]
    assert len(rows) == 1
    assert rows[0]["is_staff"] is True


def test_set_staff_writes_audit(db_session, api_client):
    client, headers, patient_id = _setup(db_session, api_client, "staff_admin_audit", "admin")
    resp = client.put(f"/patients/{patient_id}/staff", json={"is_staff": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    log = (
        db_session.query(AuditUserAction)
        .filter_by(resource_type="Patient", action_performed="SET_STAFF", resource_id=patient_id)
        .one()
    )
    assert log.old_values == {"is_staff": False}
    assert log.new_values == {"is_staff": True}
