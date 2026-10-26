"""Releve B : la colonne Details de l'audit des actions etait presque toujours vide."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.labo import lab_endpoints
from models.audit import AuditUserAction
from repositories.audit_repo import AuditRepository
from tests.conftest import create_test_user, auth_headers

PWD = "Correct123!"


def _last(db_session, resource_type, action):
    db_session.expire_all()
    return (db_session.query(AuditUserAction)
            .filter_by(resource_type=resource_type, action_performed=action)
            .order_by(AuditUserAction.action_id.desc()).first())


def test_log_user_action_keeps_details_in_new_values(db_session):
    admin = create_test_user(db_session, "ad_keep", "admin", password=PWD)
    AuditRepository(db_session).log_user_action(admin, "Thing", "UPDATE", resource_id=1, details="Prix 100 -> 150")
    db_session.flush()
    row = _last(db_session, "Thing", "UPDATE")
    assert row.new_values["details"] == "Prix 100 -> 150"


def test_log_user_action_details_do_not_overwrite_new_values(db_session):
    admin = create_test_user(db_session, "ad_keep2", "admin", password=PWD)
    AuditRepository(db_session).log_user_action(admin, "Thing", "UPDATE", new_values={"a": 1}, details="x")
    db_session.flush()
    row = _last(db_session, "Thing", "UPDATE")
    assert row.new_values == {"a": 1, "details": "x"}


def test_user_create_and_update_are_audited_without_password(db_session, api_client):
    create_test_user(db_session, "ad_users", "admin", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    h = auth_headers(client, "ad_users", PWD)
    role_id = client.get("/users/roles", headers=h).json()[0]["id"]
    r = client.post("/users/", json={"username": "ad_new_user", "password": "Abcdef123!", "full_name": "Ad New",
                                      "role_id": role_id, "postgres_role": "app_secretaire"}, headers=h)
    assert r.status_code == 201, r.text
    row = _last(db_session, "User", "CREATE")
    assert row is not None and row.new_values["username"] == "ad_new_user"
    assert "password" not in row.new_values and "password_hash" not in row.new_values

    uid = r.json()["user_id"]
    assert client.put(f"/users/{uid}", json={"contact": "677000000"}, headers=h).status_code == 200
    upd = _last(db_session, "User", "UPDATE")
    assert upd.resource_id == uid and upd.new_values["contact"] == "677000000"


def test_exam_price_change_is_audited_with_old_and_new(db_session, api_client):
    create_test_user(db_session, "ad_exam", "admin", password=PWD)
    client = api_client(auth_endpoints, lab_endpoints)
    h = auth_headers(client, "ad_exam", PWD)
    ex = client.post("/labo/exams", json={"code": "ADX1", "nom": "Audit exam", "categorie": "C", "prix": 1000}, headers=h).json()
    assert client.put(f"/labo/exams/{ex['id']}", json={"prix": 1500}, headers=h).status_code == 200
    row = _last(db_session, "Examen", "UPDATE")
    assert float(row.old_values["prix"]) == 1000 and float(row.new_values["prix"]) == 1500
    assert "1000" in row.new_values["details"] and "1500" in row.new_values["details"]
