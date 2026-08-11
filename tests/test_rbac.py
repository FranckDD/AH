# tests/test_rbac.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from tests.conftest import override_get_db, create_test_user


def _login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


def _override_both(session):
    override_get_db(app, auth_endpoints, session)
    override_get_db(app, users_endpoint, session)


def test_admin_role_can_list_users(db_session):
    create_test_user(db_session, "test_rbac_admin", "admin", password="Correct123!")
    _override_both(db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_rbac_admin", "Correct123!").json()["access_token"]
        resp = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200


def test_secretaire_role_forbidden_from_admin_route(db_session):
    create_test_user(db_session, "test_rbac_secretaire", "secretaire", password="Correct123!")
    _override_both(db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_rbac_secretaire", "Correct123!").json()["access_token"]
        resp = client.get("/users/", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_unauthenticated_request_returns_401(db_session):
    _override_both(db_session)
    try:
        client = TestClient(app)
        resp = client.get("/users/")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
