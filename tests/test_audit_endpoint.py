# tests/test_audit_endpoint.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.audit import audit_endpoint
from tests.conftest import create_test_user, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_toxicomanager_can_list_audit_access(db_session, api_client):
    """Registre L4a : /audit n'autorisait que admin/manager, alors que
    ToxicoManager a deja une entree de menu vers les logs (MainLayout.vue)
    et que role_required() reconnait deja ce role ailleurs (labo, toxico)."""
    create_test_user(db_session, "l4a_toxicomanager_audit", "ToxicoManager", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, audit_endpoint)
    headers = auth_headers(client, "l4a_toxicomanager_audit", TEST_PASSWORD)

    resp = client.get("/audit/access?page=1&per_page=1", headers=headers)

    assert resp.status_code == 200


def test_medecin_still_forbidden_from_audit(db_session, api_client):
    """Garde-fou : l'elargissement a ToxicoManager ne doit pas elargir
    /audit a d'autres roles non prevus."""
    create_test_user(db_session, "l4a_medecin_audit", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, audit_endpoint)
    headers = auth_headers(client, "l4a_medecin_audit", TEST_PASSWORD)

    resp = client.get("/audit/access?page=1&per_page=1", headers=headers)

    assert resp.status_code == 403
