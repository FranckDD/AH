# tests/test_caisse_delete_roles.py
"""DELETE /caisse/{id} : suppression definitive reservee a l'admin."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from tests.conftest import create_test_user, create_test_transaction, auth_headers

TEST_PASSWORD = "Correct123!"


def _setup(db_session, api_client, username, role):
    user = create_test_user(db_session, username, role, password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    return client, tx, auth_headers(client, username, TEST_PASSWORD)


def test_secretaire_cannot_delete_transaction(db_session, api_client):
    client, tx, headers = _setup(db_session, api_client, "test_del_roles_secr", "secretaire")

    resp = client.delete(f"/caisse/{tx.transaction_id}", headers=headers)

    assert resp.status_code == 403
    assert client.get(f"/caisse/{tx.transaction_id}", headers=headers).status_code == 200


def test_admin_can_delete_transaction(db_session, api_client):
    client, tx, headers = _setup(db_session, api_client, "test_del_roles_admin", "admin")

    assert client.delete(f"/caisse/{tx.transaction_id}", headers=headers).status_code == 204
    assert client.get(f"/caisse/{tx.transaction_id}", headers=headers).status_code == 404


def test_admin_cannot_delete_pending_approval_transaction(db_session, api_client):
    client, tx, headers = _setup(db_session, api_client, "test_del_roles_pending", "admin")
    tx.status = "pending_approval"
    db_session.flush()

    resp = client.delete(f"/caisse/{tx.transaction_id}", headers=headers)

    assert resp.status_code == 404
    assert "en attente de validation" in resp.json()["detail"]
    assert client.get(f"/caisse/{tx.transaction_id}", headers=headers).status_code == 200


def test_unauthenticated_delete_is_401(db_session, api_client):
    client, tx, _ = _setup(db_session, api_client, "test_del_roles_anon", "admin")

    assert client.delete(f"/caisse/{tx.transaction_id}").status_code == 401


@pytest.mark.parametrize("role", ["medecin", "nurse"])
def test_other_roles_cannot_delete_transaction(db_session, api_client, role):
    client, tx, headers = _setup(db_session, api_client, f"test_del_roles_{role}", role)

    assert client.delete(f"/caisse/{tx.transaction_id}", headers=headers).status_code == 403
