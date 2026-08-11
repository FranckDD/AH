import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jose import jwt as jose_jwt
from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from tests.conftest import override_get_db, create_test_user

JWT_ISSUER = "ah2-api"
JWT_AUDIENCE = "ah2-web"


def _login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


def test_valid_token_allows_access_to_me_endpoint(db_session):
    create_test_user(db_session, "test_token_valid", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_token_valid", "Correct123!").json()["access_token"]
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["application_role"]["role_name"] == "admin"


def test_expired_token_returns_401(db_session):
    user = create_test_user(db_session, "test_token_expired", "admin", password="Correct123!")
    expired_payload = {
        "sub": str(user.user_id),
        "roles": ["admin"],
        "exp": int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).timestamp()),
        "ver": 0,
        "jti": "test-expired-jti",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jose_jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token expiré"


def test_tampered_signature_returns_401(db_session):
    user = create_test_user(db_session, "test_token_tampered", "admin", password="Correct123!")
    payload = {
        "sub": str(user.user_id),
        "roles": ["admin"],
        "exp": int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).timestamp()),
        "ver": 0,
        "jti": "test-tampered-jti",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jose_jwt.encode(payload, "wrong-secret-not-the-real-one", algorithm=JWT_ALGORITHM)

    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token invalide ou expiré"


def test_logout_revokes_current_token(db_session):
    create_test_user(db_session, "test_token_logout", "admin", password="Correct123!")
    override_get_db(app, auth_endpoints, db_session)
    try:
        client = TestClient(app)
        token = _login(client, "test_token_logout", "Correct123!").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        logout_resp = client.post("/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        reuse_resp = client.get("/auth/me", headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["detail"] == "Session invalidée, veuillez vous reconnecter"
