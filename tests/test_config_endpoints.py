# tests/test_config_endpoints.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.admin import config_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from conftest import create_test_user, auth_headers

TEST_PASSWORD = "TestPass123!"


def test_structure_endpoint_never_exposes_ticket_print_token(api_client, db_session):
    """GET /config/structure est PUBLIC (aucune authentification, utilise
    par l'ecran de login) - le jeton d'impression ne doit donc jamais s'y
    trouver, meme s'il est deja renseigne en base."""
    from repositories.config_repo import ConfigRepository
    repo = ConfigRepository(db_session)
    repo.save_config({"name": "Clinique Test", "ticket_print_token": "SECRET_NE_DOIT_JAMAIS_FUITER"})

    client = api_client(config_endpoints)
    r = client.get("/config/structure")
    assert r.status_code == 200
    assert "ticket_print_token" not in r.json()
    assert "SECRET_NE_DOIT_JAMAIS_FUITER" not in str(r.json())


def test_ticket_print_token_endpoint_requires_auth(api_client, db_session):
    client = api_client(config_endpoints)
    r = client.get("/config/ticket-print-token")
    assert r.status_code == 401


def test_ticket_print_token_endpoint_forbidden_for_medecin(api_client, db_session):
    client = api_client(auth_endpoints, config_endpoints)
    create_test_user(db_session, "cfg_medecin1", "medecin", password=TEST_PASSWORD)
    headers = auth_headers(client, "cfg_medecin1", TEST_PASSWORD)
    r = client.get("/config/ticket-print-token", headers=headers)
    assert r.status_code == 403


def test_generate_ticket_token_endpoint_admin_only(api_client, db_session):
    client = api_client(auth_endpoints, config_endpoints)
    create_test_user(db_session, "cfg_secretaire1", "secretaire", password=TEST_PASSWORD)
    headers = auth_headers(client, "cfg_secretaire1", TEST_PASSWORD)
    r = client.post("/config/generate-ticket-token", headers=headers)
    assert r.status_code == 403


def test_generate_then_fetch_ticket_token_roundtrip(api_client, db_session):
    client = api_client(auth_endpoints, config_endpoints)
    create_test_user(db_session, "cfg_admin1", "admin", password=TEST_PASSWORD)
    headers = auth_headers(client, "cfg_admin1", TEST_PASSWORD)

    r = client.post("/config/generate-ticket-token", headers=headers)
    assert r.status_code == 200
    token = r.json()["token"]
    assert len(token) >= 32

    r = client.get("/config/ticket-print-token", headers=headers)
    assert r.status_code == 200
    assert r.json()["token"] == token
