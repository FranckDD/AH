# tests/test_rbac.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from tests.conftest import create_test_user, login


def test_admin_role_can_list_users(db_session, api_client):
    create_test_user(db_session, "test_rbac_admin", "admin", password="Correct123!")
    client = api_client(auth_endpoints, users_endpoint)
    token = login(client, "test_rbac_admin", "Correct123!").json()["access_token"]
    resp = client.get("/users/?search=test_rbac_admin", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "test_rbac_admin" in usernames


def test_secretaire_role_forbidden_from_admin_route(db_session, api_client):
    create_test_user(db_session, "test_rbac_secretaire", "secretaire", password="Correct123!")
    client = api_client(auth_endpoints, users_endpoint)
    token = login(client, "test_rbac_secretaire", "Correct123!").json()["access_token"]
    resp = client.get("/users/", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_unauthenticated_request_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, users_endpoint)
    resp = client.get("/users/")

    assert resp.status_code == 401
