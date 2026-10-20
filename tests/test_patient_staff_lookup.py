# tests/test_patient_staff_lookup.py
"""Task 4b (reduction personnel) : GET /patients/staff-lookup (admin,
promoteur) - recherche minimale, 5 champs seulement."""
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from models.patient import Patient
from tests.conftest import auth_headers, create_test_patient, create_test_user

PASSWORD = "TestPass123!"
FIELDS = {"patient_id", "code_patient", "first_name", "last_name", "is_staff"}


def _setup(db_session, api_client, role="promoteur", login="lk_user"):
    user = create_test_user(db_session, login, role, password=PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    return client, auth_headers(client, login, PASSWORD), user


def _mk(db_session, user, first, last, staff=False):
    pid, code = create_test_patient(db_session, user, first_name=first, last_name=last)
    if staff:
        db_session.query(Patient).filter_by(patient_id=pid).update({"is_staff": True})
        db_session.flush()
    return pid, code


def test_promoteur_and_admin_can_search_by_name_and_code(db_session, api_client):
    client, headers, user = _setup(db_session, api_client, "promoteur", "lk_promo")
    pid, code = _mk(db_session, user, "Zyglorbax", "Quuxington")
    for q in ("zyglor", "QUUXING", code):
        resp = client.get("/patients/staff-lookup", params={"q": q}, headers=headers)
        assert resp.status_code == 200, resp.text
        assert pid in [r["patient_id"] for r in resp.json()], q
    create_test_user(db_session, "lk_admin", "admin", password=PASSWORD)
    headers_a = auth_headers(client, "lk_admin", PASSWORD)
    resp = client.get("/patients/staff-lookup", params={"q": "zyglor"}, headers=headers_a)
    assert resp.status_code == 200
    assert pid in [r["patient_id"] for r in resp.json()]


def test_only_staff_lists_only_flagged_patients_sorted_by_last_name(db_session, api_client):
    client, headers, user = _setup(db_session, api_client)
    b, _ = _mk(db_session, user, "Pers", "Bbbstaff", staff=True)
    a, _ = _mk(db_session, user, "Pers", "Aaastaff", staff=True)
    n, _ = _mk(db_session, user, "Pers", "Cccnotstaff")
    resp = client.get("/patients/staff-lookup", params={"only_staff": True, "limit": 50}, headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    ids = [r["patient_id"] for r in rows]
    assert n not in ids
    assert all(r["is_staff"] for r in rows)
    assert ids.index(a) < ids.index(b)
    assert [r["last_name"] for r in rows] == sorted(r["last_name"] for r in rows)
    # q combine avec only_staff
    resp = client.get("/patients/staff-lookup", params={"only_staff": True, "q": "Aaastaff"}, headers=headers)
    assert [r["patient_id"] for r in resp.json()] == [a]


def test_response_has_exactly_the_five_fields(db_session, api_client):
    client, headers, user = _setup(db_session, api_client)
    _mk(db_session, user, "Fieldsy", "Fieldsson")
    rows = client.get("/patients/staff-lookup", params={"q": "Fieldsy"}, headers=headers).json()
    assert rows
    for r in rows:
        assert set(r.keys()) == FIELDS


def test_secretaire_medecin_toxicomanager_get_403(db_session, api_client):
    client, _, _ = _setup(db_session, api_client, "admin", "lk_creator")
    for role in ("secretaire", "medecin", "ToxicoManager"):
        login = f"lk_{role}"
        create_test_user(db_session, login, role, password=PASSWORD)
        headers = auth_headers(client, login, PASSWORD)
        resp = client.get("/patients/staff-lookup", params={"q": "abc"}, headers=headers)
        assert resp.status_code == 403, f"{role}: {resp.status_code}"


def test_soft_deleted_patient_excluded(db_session, api_client):
    client, headers, user = _setup(db_session, api_client)
    pid, _ = _mk(db_session, user, "Ghostly", "Deletedson", staff=True)
    db_session.query(Patient).filter_by(patient_id=pid).update({"is_deleted": True})
    db_session.flush()
    assert client.get("/patients/staff-lookup", params={"q": "Ghostly"}, headers=headers).json() == []
    rows = client.get("/patients/staff-lookup", params={"only_staff": True, "limit": 50}, headers=headers).json()
    assert pid not in [r["patient_id"] for r in rows]


def test_no_q_and_not_only_staff_returns_422(db_session, api_client):
    client, headers, _ = _setup(db_session, api_client)
    assert client.get("/patients/staff-lookup", headers=headers).status_code == 422
    assert client.get("/patients/staff-lookup", params={"only_staff": False}, headers=headers).status_code == 422


def test_q_shorter_than_2_returns_422(db_session, api_client):
    client, headers, _ = _setup(db_session, api_client)
    assert client.get("/patients/staff-lookup", params={"q": "a"}, headers=headers).status_code == 422


def test_limit_bounds(db_session, api_client):
    client, headers, _ = _setup(db_session, api_client)
    for lim in (0, 51):
        resp = client.get("/patients/staff-lookup", params={"q": "ab", "limit": lim}, headers=headers)
        assert resp.status_code == 422, lim


def test_staff_lookup_not_swallowed_by_patient_id_route(db_session, api_client):
    client, headers, user = _setup(db_session, api_client, "admin", "lk_swallow")
    pid, _ = _mk(db_session, user, "Swallow", "Checker")
    resp = client.get("/patients/staff-lookup", params={"q": "Swallow"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    # GET /patients/{id} reste servi par le routeur principal
    detail = client.get(f"/patients/{pid}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["patient_id"] == pid
    secr = create_test_user(db_session, "lk_secr_detail", "secretaire", password=PASSWORD)
    headers_s = auth_headers(client, "lk_secr_detail", PASSWORD)
    assert client.get(f"/patients/{pid}", headers=headers_s).status_code == 200


def test_promoteur_still_forbidden_on_other_patient_routes(db_session, api_client):
    client, headers, user = _setup(db_session, api_client, "promoteur", "lk_promo403")
    pid, _ = _mk(db_session, user, "Closed", "Door")
    assert client.get("/patients/", headers=headers).status_code == 403
    assert client.get(f"/patients/{pid}", headers=headers).status_code == 403
