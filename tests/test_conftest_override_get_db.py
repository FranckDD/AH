# tests/test_conftest_override_get_db.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app import database
from tests.conftest import override_get_db


def test_health_endpoint_uses_the_transactional_test_session(db_session):
    """
    Demontre que override_get_db() branche correctement la session de
    test dans une vraie route FastAPI appelee via TestClient. /health
    est la route la plus simple du projet (aucune auth, aucune logique
    metier) - ideale pour valider le mecanisme de surcharge isolement,
    avant de l'utiliser pour de vrais tests metier (2d-1 a 2d-4).
    """
    override_get_db(app, database, db_session)
    try:
        client = TestClient(app)
        resp = client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["database"] == "connected"
