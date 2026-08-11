import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jose import jwt as jose_jwt
from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from tests.conftest import override_get_db, create_test_user


def _login(client, username, password):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )


def test_login_success_returns_token_with_correct_role(db_session):
    create_test_user(db_session, "test_login_admin", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "test_login_admin", "Correct123!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = jose_jwt.decode(
        token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
        issuer="ah2-api", audience="ah2-web",
    )
    assert payload["roles"] == ["admin"]


def test_login_wrong_password_returns_401(db_session):
    create_test_user(db_session, "test_login_wrongpass", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "test_login_wrongpass", "WrongPassword!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


def test_login_inactive_account_returns_401(db_session):
    create_test_user(db_session, "test_login_inactive", "admin", password="Correct123!", is_active=False)
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "test_login_inactive", "Correct123!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"


def test_login_unknown_username_returns_401(db_session):
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = _login(client, "does_not_exist_at_all", "Whatever123!")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Identifiants invalides"
