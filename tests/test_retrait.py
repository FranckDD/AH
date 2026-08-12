# tests/test_retrait.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.retrait import retrait_endpoints
from tests.conftest import create_test_user, create_test_retrait, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_retrait_success(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_create", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_create", TEST_PASSWORD)

    resp = client.post(
        "/retrait/",
        json={"amount": 60.0, "justification": "Achat fournitures bureau", "category": "Fournitures", "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == 60.0
    assert body["justification"] == "Achat fournitures bureau"
    assert body["status"] == "active"
    assert body["retrait_id"]


def test_create_retrait_negative_amount_returns_422(db_session, api_client):
    create_test_user(db_session, "test_retrait_secretaire_negative", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_negative", TEST_PASSWORD)

    resp = client.post("/retrait/", json={"amount": -5.0, "justification": "x"}, headers=headers)

    assert resp.status_code == 422


def test_get_retrait_success(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_get", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user, amount=42.0, justification="Retrait specifique")
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_get", TEST_PASSWORD)

    resp = client.get(f"/retrait/{retrait.retrait_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["retrait_id"] == retrait.retrait_id
    assert resp.json()["amount"] == 42.0


def test_get_retrait_not_found(db_session, api_client):
    create_test_user(db_session, "test_retrait_secretaire_get404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_get404", TEST_PASSWORD)

    resp = client.get("/retrait/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_retraits(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_list", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user, justification="Zzuniquelistjustif2d4")
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_list", TEST_PASSWORD)

    resp = client.get("/retrait/?per_page=200", headers=headers)

    assert resp.status_code == 200
    ids = [r["retrait_id"] for r in resp.json()["data"]]
    assert retrait.retrait_id in ids


def test_search_retraits_by_term(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_search", "secretaire", password=TEST_PASSWORD)
    create_test_retrait(db_session, user, justification="Zzuniquesearchjustif2d4")
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_search", TEST_PASSWORD)

    resp = client.get("/retrait/search?term=Zzuniquesearchjustif2d4", headers=headers)

    assert resp.status_code == 200
    justifications = [r["justification"] for r in resp.json()["data"]]
    assert "Zzuniquesearchjustif2d4" in justifications


def test_total_retraits(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_total", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_total", TEST_PASSWORD)

    before = client.get("/retrait/total", headers=headers).json()
    create_test_retrait(db_session, user, amount=33.0)
    after = client.get("/retrait/total", headers=headers).json()

    assert after == before + 33.0


def test_cancel_retrait_success(db_session, api_client):
    user = create_test_user(db_session, "test_retrait_secretaire_cancel", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_cancel", TEST_PASSWORD)

    resp = client.post(
        f"/retrait/{retrait.retrait_id}/cancel",
        json={"cancel_justification": "Erreur de saisie"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Retrait annulé avec succès"

    get_resp = client.get(f"/retrait/{retrait.retrait_id}", headers=headers)
    assert get_resp.json()["status"] == "cancelled"


def test_cancel_retrait_already_cancelled_returns_400(db_session, api_client):
    """
    Contraste avec test_cancel_transaction_already_cancelled_is_idempotent
    (tests/test_caisse.py) : ici, annuler un retrait deja annule est
    explicitement refuse (400), alors qu'annuler une transaction caisse
    deja annulee reussit silencieusement (200) - incoherence de
    comportement entre les deux modules.
    """
    user = create_test_user(db_session, "test_retrait_secretaire_doublecancel", "secretaire", password=TEST_PASSWORD)
    retrait = create_test_retrait(db_session, user)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_secretaire_doublecancel", TEST_PASSWORD)

    first = client.post(f"/retrait/{retrait.retrait_id}/cancel", json={"cancel_justification": "Premiere annulation"}, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/retrait/{retrait.retrait_id}/cancel", json={"cancel_justification": "Deuxieme annulation"}, headers=headers)
    assert second.status_code == 400
    assert "déjà annulé" in second.json()["detail"]


def test_retrait_forbidden_for_medecin(db_session, api_client):
    create_test_user(db_session, "test_retrait_medecin", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_medecin", TEST_PASSWORD)

    resp = client.get("/retrait/", headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_retrait_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, retrait_endpoints)

    resp = client.get("/retrait/")

    assert resp.status_code == 401
