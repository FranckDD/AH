# tests/test_stockcontroller_deny.py
"""Regle R8 : le role StockController n'atteint plus les routes "authentifie seulement"
hors de son perimetre (garde NEGATIVE deny_roles), sans gener les autres roles."""
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.appointment import appointment_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from api_backend.backend_app.routes.notifications import notification_endpoints
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
MODULES = (auth_endpoints, users_endpoint, appointment_endpoints, lab_endpoints, notification_endpoints)


def test_stockcontroller_denied_on_out_of_scope_routes(db_session, api_client):
    create_test_user(db_session, "t_deny_ctrl", "StockController", password=PWD)
    client = api_client(*MODULES)
    h = auth_headers(client, "t_deny_ctrl", PWD)
    for path in ("/appointments/", "/users/roles", "/users/specialties", "/users/doctors",
                 "/users/managers", "/labo/exams/1/params"):
        r = client.get(path, headers=h)
        assert r.status_code == 403, (path, r.status_code, r.text)
    # perimetre conserve
    assert client.get("/auth/me", headers=h).status_code == 200
    assert client.get("/notifications", headers=h).status_code == 200


def test_secretaire_still_allowed(db_session, api_client):
    create_test_user(db_session, "t_deny_secr", "secretaire", password=PWD)
    client = api_client(*MODULES)
    h = auth_headers(client, "t_deny_secr", PWD)
    for path in ("/appointments/", "/users/roles", "/users/doctors", "/labo/exams/1/params"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, (path, r.status_code, r.text)
