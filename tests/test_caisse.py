# tests/test_caisse.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from tests.conftest import create_test_user, create_test_patient, create_test_transaction, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_create", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_create", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "amount": 100.0,
        "advance_amount": 100.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "100.00"
    assert body["advance_amount"] == "100.00"
    assert body["patient_id"] == patient_id
    assert body["transaction_id"]
    assert len(body["items"]) == 1


def test_create_transaction_partial_payment_amount_due_bug(db_session, api_client):
    """
    Documente un bug reel sur HEAD (SUIVI-AVANCEMENT.md registre a
    creer) : api_backend/backend_app/routes/caisse/mapping.py::
    normalize_caisse_data calcule amount_due = amount + advance_amount
    (au lieu de amount - advance_amount) et amount_paid = amount seul
    (au lieu de advance_amount). Constate par execution reelle : avec
    amount=100 et advance_amount=30, amount_due vaut 130 (attendu 70)
    et amount_paid vaut 100 (attendu 30). Ce bug est independant des
    KPIs de tableau de bord (get_caisse_kpis), qui calculent
    correctement remaining_due = total_factured - total_paid (voir
    test_dashboard_kpis_date_scoped_exact_values).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_partial", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_partial", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "amount": 100.0,
        "advance_amount": 30.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "100.00"
    assert body["advance_amount"] == "30.00"
    assert body["amount_due"] == "130.00"
    assert body["amount_paid"] == "100.00"


def test_create_transaction_missing_required_field_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_missing", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_missing", TEST_PASSWORD)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "items": [],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 400
    assert "transaction_type" in resp.json()["detail"]


def test_create_transaction_amount_mismatch_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_mismatch", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_mismatch", TEST_PASSWORD)

    payload = {
        "amount": 999.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 400
    assert "Incohérence" in resp.json()["detail"]


def test_create_transaction_invalid_consultation_reference_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_badconsult", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_badconsult", TEST_PASSWORD)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Consultation", "item_ref_id": 999999999, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 400
    assert "Aucune consultation" in resp.json()["detail"]


def test_create_transaction_forbidden_for_medecin(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_medecin_create", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_medecin_create", TEST_PASSWORD)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [
            {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
        ],
    }
    resp = client.post("/caisse/", json=payload, headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_create_transaction_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, caisse_endpoints)

    payload = {
        "amount": 100.0,
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [],
    }
    resp = client.post("/caisse/", json=payload)

    assert resp.status_code == 401
