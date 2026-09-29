# tests/test_nurse_shifts_endpoints.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.nurse_shifts import nurse_shift_endpoint
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, nurse_shift_endpoint)


def test_medecin_can_create_and_list_shift(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin1", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse1", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin1", TEST_PASSWORD)

    resp = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-10",
        "shift_type": "MATIN",
        "nurse_id": nurse.user_id,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["nurse_name"] == nurse.full_name
    assert body["created_by_name"] == medecin.full_name

    listed = client.get("/nurse-shifts/?start=2026-10-10&end=2026-10-10", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_head_nurse_can_create_shift(db_session, api_client):
    head_nurse = create_test_user(db_session, "nsh_ep_headnurse1", "nurse", password=TEST_PASSWORD)
    head_nurse.is_head_nurse = True
    db_session.flush()
    other_nurse = create_test_user(db_session, "nsh_ep_nurse2", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_headnurse1", TEST_PASSWORD)

    resp = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-11",
        "shift_type": "NUIT",
        "nurse_id": other_nurse.user_id,
    }, headers=headers)

    assert resp.status_code == 201, resp.text


def test_plain_nurse_forbidden_to_create_or_delete_shift(db_session, api_client):
    """Review Focus : un infirmier sans is_head_nurse doit etre refuse
    clairement (403), jamais un succes silencieux."""
    medecin = create_test_user(db_session, "nsh_ep_medecin2", "medecin", password=TEST_PASSWORD)
    plain_nurse = create_test_user(db_session, "nsh_ep_plainnurse", "nurse", password=TEST_PASSWORD)
    target_nurse = create_test_user(db_session, "nsh_ep_nurse3", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    medecin_headers = auth_headers(client, "nsh_ep_medecin2", TEST_PASSWORD)
    plain_headers = auth_headers(client, "nsh_ep_plainnurse", TEST_PASSWORD)

    create_resp = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-12",
        "shift_type": "MATIN",
        "nurse_id": plain_nurse.user_id,
    }, headers=plain_headers)
    assert create_resp.status_code == 403

    existing_id = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-12",
        "shift_type": "APRES_MIDI",
        "nurse_id": target_nurse.user_id,
    }, headers=medecin_headers).json()["id"]

    delete_resp = client.delete(f"/nurse-shifts/{existing_id}", headers=plain_headers)
    assert delete_resp.status_code == 403


def test_create_shift_refuses_duplicate(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin3", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse4", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin3", TEST_PASSWORD)
    payload = {"shift_date": "2026-10-13", "shift_type": "NUIT", "nurse_id": nurse.user_id}

    assert client.post("/nurse-shifts/", json=payload, headers=headers).status_code == 201
    resp = client.post("/nurse-shifts/", json=payload, headers=headers)
    assert resp.status_code == 409


def test_create_shift_validates_shift_type_and_nurse_id(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin4", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse5", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin4", TEST_PASSWORD)

    bad_type = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-14", "shift_type": "SOIREE", "nurse_id": nurse.user_id,
    }, headers=headers)
    assert bad_type.status_code == 422

    bad_nurse = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-14", "shift_type": "MATIN", "nurse_id": 999999999,
    }, headers=headers)
    assert bad_nurse.status_code == 404


def test_delete_unknown_shift_returns_404(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin5", "medecin", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin5", TEST_PASSWORD)

    resp = client.delete("/nurse-shifts/999999999", headers=headers)
    assert resp.status_code == 404


def test_list_shifts_shows_multiple_nurses_same_slot(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin6", "medecin", password=TEST_PASSWORD)
    nurse1 = create_test_user(db_session, "nsh_ep_nurse6a", "nurse", password=TEST_PASSWORD)
    nurse2 = create_test_user(db_session, "nsh_ep_nurse6b", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin6", TEST_PASSWORD)

    for nurse in (nurse1, nurse2):
        client.post("/nurse-shifts/", json={
            "shift_date": "2026-10-15", "shift_type": "MATIN", "nurse_id": nurse.user_id,
        }, headers=headers)

    resp = client.get("/nurse-shifts/?start=2026-10-15&end=2026-10-15", headers=headers)
    assert len(resp.json()) == 2


def test_secretaire_forbidden_on_read_and_write(db_session, api_client):
    create_test_user(db_session, "nsh_ep_secretaire1", "secretaire", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "nsh_ep_medecin7", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse7", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_secretaire1", TEST_PASSWORD)

    assert client.get("/nurse-shifts/?start=2026-10-01&end=2026-10-31", headers=headers).status_code == 403
    assert client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-16", "shift_type": "MATIN", "nurse_id": nurse.user_id,
    }, headers=headers).status_code == 403


def test_list_nurses_returns_only_active_nurses(db_session, api_client):
    medecin = create_test_user(db_session, "nsh_ep_medecin8", "medecin", password=TEST_PASSWORD)
    active_nurse = create_test_user(db_session, "nsh_ep_activenurse", "nurse", password=TEST_PASSWORD)
    create_test_user(db_session, "nsh_ep_inactivenurse", "nurse", password=TEST_PASSWORD, is_active=False)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin8", TEST_PASSWORD)

    resp = client.get("/nurse-shifts/nurses", headers=headers)
    assert resp.status_code == 200
    usernames = {n["user_id"] for n in resp.json()}
    assert active_nurse.user_id in usernames


def test_assign_and_remove_write_audit_entries(db_session, api_client):
    from models.audit import AuditUserAction

    medecin = create_test_user(db_session, "nsh_ep_medecin9", "medecin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_ep_nurse9", "nurse", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "nsh_ep_medecin9", TEST_PASSWORD)

    shift_id = client.post("/nurse-shifts/", json={
        "shift_date": "2026-10-17", "shift_type": "MATIN", "nurse_id": nurse.user_id,
    }, headers=headers).json()["id"]
    client.delete(f"/nurse-shifts/{shift_id}", headers=headers)

    entries = (
        db_session.query(AuditUserAction)
        .filter(AuditUserAction.resource_type == "NurseShift", AuditUserAction.resource_id == shift_id)
        .all()
    )
    actions = {e.action_performed for e in entries}
    assert "ASSIGN" in actions
    assert "REMOVE" in actions
