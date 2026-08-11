import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jose import jwt as jose_jwt

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from tests.conftest import create_test_user, login


def test_valid_token_allows_access_to_me_endpoint(db_session, api_client):
    create_test_user(db_session, "test_token_valid", "admin", password="Correct123!")
    client = api_client(auth_endpoints)
    token = login(client, "test_token_valid", "Correct123!").json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["application_role"]["role_name"] == "admin"


def test_expired_token_returns_401(db_session, api_client):
    user = create_test_user(db_session, "test_token_expired", "admin", password="Correct123!")
    expired_payload = {
        "sub": str(user.user_id),
        "roles": ["admin"],
        "exp": int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)).timestamp()),
        "ver": 0,
        "jti": "test-expired-jti",
        "iss": auth_endpoints.JWT_ISSUER,
        "aud": auth_endpoints.JWT_AUDIENCE,
    }
    token = jose_jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    client = api_client(auth_endpoints)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token expiré"


def test_tampered_signature_returns_401(db_session, api_client):
    user = create_test_user(db_session, "test_token_tampered", "admin", password="Correct123!")
    payload = {
        "sub": str(user.user_id),
        "roles": ["admin"],
        "exp": int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)).timestamp()),
        "ver": 0,
        "jti": "test-tampered-jti",
        "iss": auth_endpoints.JWT_ISSUER,
        "aud": auth_endpoints.JWT_AUDIENCE,
    }
    token = jose_jwt.encode(payload, "wrong-secret-not-the-real-one", algorithm=JWT_ALGORITHM)

    client = api_client(auth_endpoints)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token invalide ou expiré"


def test_logout_revokes_current_token(db_session, api_client):
    create_test_user(db_session, "test_token_logout", "admin", password="Correct123!")
    client = api_client(auth_endpoints)
    token = login(client, "test_token_logout", "Correct123!").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout_resp = client.post("/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    reuse_resp = client.get("/auth/me", headers=headers)

    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["detail"] == "Session invalidée, veuillez vous reconnecter"
