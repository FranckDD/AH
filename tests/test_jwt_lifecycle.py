# tests/test_jwt_lifecycle.py
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock, patch
from jose import jwt as jose_jwt
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from api_backend.backend_app.config import JWT_SECRET, JWT_ALGORITHM
from api_backend.backend_app.routes.auth import auth_endpoints as auth_mod


def make_fake_user(user_id=1, token_version=0):
    user = MagicMock()
    user.user_id = user_id
    user.token_version = token_version
    user.application_role = None
    return user


def build_app_with_fake_user(fake_user):
    app = FastAPI()

    @app.get("/protected")
    def protected(current_user=Depends(auth_mod.get_current_user)):
        return {"user_id": current_user.user_id}

    fake_ctrl = MagicMock()
    fake_ctrl.user_repo.get_user_by_id.return_value = fake_user

    patcher = patch.object(auth_mod, "AuthController", return_value=fake_ctrl)
    patcher.start()
    return app, patcher


def make_token(sub, ver, iss="ah2-api", aud="ah2-web", exp_delta=600):
    payload = {"sub": str(sub), "roles": [], "exp": int(time.time()) + exp_delta}
    if ver is not None:
        payload["ver"] = ver
    if iss is not None:
        payload["iss"] = iss
    if aud is not None:
        payload["aud"] = aud
    return jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_matching_token_version_is_accepted():
    fake_user = make_fake_user(user_id=1, token_version=2)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=2)
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
    finally:
        patcher.stop()


def test_stale_token_version_is_rejected():
    fake_user = make_fake_user(user_id=1, token_version=3)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=2)  # ancien token, version depassee (logout entre-temps)
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        patcher.stop()


def test_wrong_audience_is_rejected():
    fake_user = make_fake_user(user_id=1, token_version=0)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=0, aud="autre-app")
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        patcher.stop()


def test_wrong_issuer_is_rejected():
    fake_user = make_fake_user(user_id=1, token_version=0)
    app, patcher = build_app_with_fake_user(fake_user)
    try:
        token = make_token(sub=1, ver=0, iss="autre-service")
        client = TestClient(app)
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
    finally:
        patcher.stop()
