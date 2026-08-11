import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jose import jwt as jose_jwt

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from tests.conftest import create_test_user, login


def test_login_success_returns_token_with_correct_role(db_session, api_client):
    create_test_user(db_session, "test_login_admin", "admin", password="Correct123!")
    client = api_client(auth_endpoints)
    resp = login(client, "test_login_admin", "Correct123!")

    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = jose_jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        issuer=auth_endpoints.JWT_ISSUER, audience=auth_endpoints.JWT_AUDIENCE,
    )
    assert payload["roles"] == ["admin"]


def test_login_wrong_password_returns_401(db_session, api_client):
    create_test_user(db_session, "test_login_wrongpass", "admin", password="Correct123!")
    client = api_client(auth_endpoints)
    resp = login(client, "test_login_wrongpass", "WrongPassword!")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


def test_login_inactive_account_returns_401(db_session, api_client):
    create_test_user(db_session, "test_login_inactive", "admin", password="Correct123!", is_active=False)
    client = api_client(auth_endpoints)
    resp = login(client, "test_login_inactive", "Correct123!")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


def test_login_unknown_username_returns_401(db_session, api_client):
    client = api_client(auth_endpoints)
    resp = login(client, "does_not_exist_at_all", "Whatever123!")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"
