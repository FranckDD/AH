# tests/test_auth_profile.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import create_test_user, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_get_me_includes_profile_fields(db_session, api_client):
    user = create_test_user(db_session, "l7d_getme_profile", "medecin", password=TEST_PASSWORD)
    user.email = "medecin.test@example.com"
    user.contact = "0102030405"
    db_session.flush()

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_getme_profile", TEST_PASSWORD)

    resp = client.get("/auth/me", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Test l7d_getme_profile"
    assert body["email"] == "medecin.test@example.com"
    assert body["contact"] == "0102030405"


def test_update_my_profile_success(db_session, api_client):
    create_test_user(db_session, "l7d_update_profile", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_update_profile", TEST_PASSWORD)

    resp = client.put(
        "/auth/profile",
        json={"full_name": "Nouveau Nom", "email": "nouveau@example.com", "contact": "0611223344"},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Nouveau Nom"
    assert body["email"] == "nouveau@example.com"
    assert body["contact"] == "0611223344"

    get_resp = client.get("/auth/me", headers=headers)
    assert get_resp.json()["full_name"] == "Nouveau Nom"


def test_update_my_profile_partial_leaves_other_fields_unchanged(db_session, api_client):
    user = create_test_user(db_session, "l7d_partial_profile", "secretaire", password=TEST_PASSWORD)
    user.contact = "0600000000"
    db_session.flush()

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_partial_profile", TEST_PASSWORD)

    resp = client.put("/auth/profile", json={"full_name": "Juste Le Nom"}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Juste Le Nom"
    assert body["contact"] == "0600000000"


def test_update_my_profile_duplicate_email_returns_409(db_session, api_client):
    other = create_test_user(db_session, "l7d_other_dupemail", "medecin", password=TEST_PASSWORD)
    other.email = "occupe@example.com"
    db_session.flush()
    create_test_user(db_session, "l7d_self_dupemail", "secretaire", password=TEST_PASSWORD)

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_self_dupemail", TEST_PASSWORD)

    resp = client.put("/auth/profile", json={"email": "occupe@example.com"}, headers=headers)

    assert resp.status_code == 409


def test_update_my_profile_cannot_change_role_or_username(db_session, api_client):
    """SelfProfileUpdate n'a aucun champ role_id/username/is_active/password -
    meme envoyes, ils sont silencieusement ignores par Pydantic (champs
    inconnus rejetes par defaut... verifie qu'ils n'ont AUCUN effet, pas que
    la requete echoue)."""
    user = create_test_user(db_session, "l7d_no_privesc", "secretaire", password=TEST_PASSWORD)
    original_role_id = user.role_id
    db_session.flush()

    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_no_privesc", TEST_PASSWORD)

    resp = client.put(
        "/auth/profile",
        json={"full_name": "Toujours Secretaire", "role_id": 999999, "username": "pirate", "is_active": False},
        headers=headers,
    )

    assert resp.status_code == 200
    get_resp = client.get("/auth/me", headers=headers)
    assert get_resp.json()["username"] == "l7d_no_privesc"
    assert get_resp.json()["application_role"]["role_name"] == "secretaire"


def test_update_my_profile_contact_too_long_returns_clean_500(db_session, api_client):
    """Revue finale chantier 7d (I2) : PUT /auth/profile n'avait aucun
    gestionnaire pour SQLAlchemyError/RuntimeError - un contact trop long
    (contact est String(50)) remontait comme une exception non geree au
    lieu d'un 500 propre avec un message."""
    create_test_user(db_session, "l7d_contact_too_long", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints)
    headers = auth_headers(client, "l7d_contact_too_long", TEST_PASSWORD)

    resp = client.put("/auth/profile", json={"contact": "0" * 100}, headers=headers)

    assert resp.status_code == 500
    assert "detail" in resp.json()
