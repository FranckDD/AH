import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "Correct123!"


def test_update_user_duplicate_email_returns_409_not_500(db_session, api_client):
    """Registre L3f (chantier 7d) : UserController.update_user attrapait
    IntegrityError dans son 'except SQLAlchemyError' generique (IntegrityError
    est une sous-classe de SQLAlchemyError), le convertissant en RuntimeError
    avant meme de sortir du controller - le bloc 'except IntegrityError' de
    cet endpoint n'a donc jamais pu s'executer. Un email deja pris par un
    autre compte renvoyait un 500 generique au lieu d'un 409 propre."""
    admin = create_test_user(db_session, "l7d_admin_dupemail", "admin", password=TEST_PASSWORD)
    admin.email = "deja.pris@example.com"
    db_session.flush()
    target = create_test_user(db_session, "l7d_target_dupemail", "secretaire", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "l7d_admin_dupemail", TEST_PASSWORD)

    resp = client.put(f"/users/{target.user_id}", json={"email": "deja.pris@example.com"}, headers=headers)

    assert resp.status_code == 409


def test_update_user_sets_is_head_nurse_without_breaking_other_fields(db_session, api_client):
    """Review Focus : le nouveau champ doit voyager de bout en bout sans
    casser un champ deja whiteliste (is_active reste modifiable dans le
    meme appel)."""
    admin = create_test_user(db_session, "nsh_admin_headnurse", "admin", password=TEST_PASSWORD)
    nurse = create_test_user(db_session, "nsh_target_headnurse", "nurse", password=TEST_PASSWORD)

    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "nsh_admin_headnurse", TEST_PASSWORD)

    resp = client.put(f"/users/{nurse.user_id}", json={
        "is_head_nurse": True,
        "is_active": True,
    }, headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_head_nurse"] is True
    assert body["is_active"] is True


def test_create_user_with_head_nurse_checked_persists_flag(db_session, api_client):
    """Finding Important 1 (revue finale planning-rotation-infirmiers) :
    UserController.create_user passait une whitelist explicite de kwargs a
    user_repo.create_user(...) qui omettait is_head_nurse, meme si UserCreate
    l'accepte et que le frontend l'envoie a la creation - la coche etait
    silencieusement ignoree. Verifie que POST /users/ avec is_head_nurse=True
    renvoie bien is_head_nurse=True."""
    admin = create_test_user(db_session, "nsh_admin_createheadnurse", "admin", password=TEST_PASSWORD)

    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "nsh_admin_createheadnurse", TEST_PASSWORD)

    resp = client.post("/users/", json={
        "username": "nsh_new_headnurse",
        "password": "NewNursePass123!",
        "full_name": "Nouvelle Infirmiere Cheffe",
        "is_head_nurse": True,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_head_nurse"] is True


# --- Chantier psychologues : drapeau sees_own_toxico_only -------------------

def _admin_client(db_session, api_client, name):
    create_test_user(db_session, name, "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, users_endpoint)
    return client, auth_headers(client, name, TEST_PASSWORD)


def test_create_psychologist_with_sees_own_toxico_only_persists_flag(db_session, api_client):
    client, headers = _admin_client(db_session, api_client, "pv_admin_create")
    resp = client.post("/users/", json={
        "username": "pv_new_psy",
        "password": "NewPsyPass123!",
        "full_name": "Psy Limitee",
        "sees_own_toxico_only": True,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sees_own_toxico_only"] is True
    got = client.get(f"/users/{body['user_id']}", headers=headers)
    assert got.status_code == 200, got.text
    assert got.json()["sees_own_toxico_only"] is True


def test_update_user_sets_and_clears_sees_own_toxico_only(db_session, api_client):
    client, headers = _admin_client(db_session, api_client, "pv_admin_update")
    psy = create_test_user(db_session, "pv_target_update", "Psychologist", password=TEST_PASSWORD)
    r1 = client.put(f"/users/{psy.user_id}", json={"sees_own_toxico_only": True}, headers=headers)
    assert r1.status_code == 200, r1.text
    assert r1.json()["sees_own_toxico_only"] is True
    assert r1.json()["is_active"] is True
    r2 = client.put(f"/users/{psy.user_id}", json={"sees_own_toxico_only": False}, headers=headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["sees_own_toxico_only"] is False
    assert r2.json()["is_active"] is True


def test_list_users_returns_the_flag(db_session, api_client):
    client, headers = _admin_client(db_session, api_client, "pv_admin_list")
    psy = create_test_user(db_session, "pv_listed_psy", "Psychologist", password=TEST_PASSWORD)
    psy.sees_own_toxico_only = True
    db_session.flush()
    resp = client.get("/users/", params={"search": "pv_listed_psy"}, headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    items = payload["data"]
    row = next(u for u in items if u["username"] == "pv_listed_psy")
    assert row["sees_own_toxico_only"] is True


def test_flag_defaults_to_false_on_create_without_it(db_session, api_client):
    client, headers = _admin_client(db_session, api_client, "pv_admin_default")
    resp = client.post("/users/", json={
        "username": "pv_default_user",
        "password": "NewPsyPass123!",
        "full_name": "Sans drapeau",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["sees_own_toxico_only"] is False


def test_flag_is_in_audit_snapshot(db_session):
    user = create_test_user(db_session, "pv_audit_user", "Psychologist", password=TEST_PASSWORD)
    user.sees_own_toxico_only = True
    assert "sees_own_toxico_only" in users_endpoint._USER_AUDIT_FIELDS
    assert users_endpoint._user_snapshot(user)["sees_own_toxico_only"] is True


def test_self_profile_cannot_set_the_flag(db_session, api_client):
    psy = create_test_user(db_session, "pv_self_psy", "Psychologist", password=TEST_PASSWORD)
    psy.sees_own_toxico_only = True
    db_session.flush()
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "pv_self_psy", TEST_PASSWORD)
    resp = client.put("/auth/profile", json={"full_name": "X", "sees_own_toxico_only": False}, headers=headers)
    assert resp.status_code == 200, resp.text
    db_session.refresh(psy)
    assert psy.sees_own_toxico_only is True


def test_auth_me_exposes_the_flag(db_session, api_client):
    psy = create_test_user(db_session, "pv_me_psy", "Psychologist", password=TEST_PASSWORD)
    psy.sees_own_toxico_only = True
    db_session.flush()
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "pv_me_psy", TEST_PASSWORD)
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["sees_own_toxico_only"] is True
