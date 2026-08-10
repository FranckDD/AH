# tests/test_role_required.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from api_backend.backend_app.routes.auth.auth_endpoints import role_required, get_current_user


class FakeUser:
    def __init__(self, roles):
        self.roles = roles


def make_app(user_roles):
    app = FastAPI()

    def fake_current_user():
        return FakeUser(user_roles)

    app.dependency_overrides[get_current_user] = fake_current_user

    @app.get("/protected", dependencies=[Depends(role_required("admin", "manager"))])
    def protected():
        return {"ok": True}

    return app


def test_manager_role_is_recognized_as_valid_even_without_db_row():
    client = TestClient(make_app(["manager"]))
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_admin_still_allowed():
    client = TestClient(make_app(["admin"]))
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_unrecognized_allowed_role_does_not_leak_through_as_raw_string():
    # role_required("admin", "biologiste") : "biologiste" n'est pas un canonical connu
    # et ne doit plus etre accepte tel quel en minuscules (repli retire).
    app = FastAPI()

    def fake_current_user():
        return FakeUser(["biologiste"])  # un attaquant qui aurait ce role brut en DB

    app.dependency_overrides[get_current_user] = fake_current_user

    @app.get("/protected2", dependencies=[Depends(role_required("admin", "biologiste"))])
    def protected2():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/protected2")
    assert resp.status_code == 403
