# tests/test_caisse.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from controller.caisse_controller import CaisseController
from repositories.caisse_repo import CaisseRepository
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
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


def test_create_transaction_partial_payment_computes_amount_due_and_paid_correctly(db_session, api_client):
    """
    Registre F1, corrige : amount_due = amount - advance_amount,
    amount_paid = advance_amount (mapping.py::normalize_caisse_data).
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
    assert body["amount_due"] == "70.00"
    assert body["amount_paid"] == "30.00"


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
    assert "ne correspond pas" in resp.json()["detail"]


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


def test_get_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_get", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=150.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 150.0, "quantity": 1, "line_total": 150.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_get", TEST_PASSWORD)

    resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["transaction_id"] == tx.transaction_id
    assert resp.json()["amount"] == "150.00"


def test_get_transaction_not_found(db_session, api_client):
    create_test_user(db_session, "test_caisse_secretaire_get404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_get404", TEST_PASSWORD)

    resp = client.get("/caisse/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_transactions_search_by_term(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_search", "secretaire", password=TEST_PASSWORD)
    create_test_transaction(db_session, user, transaction_type="Zzuniquetransactiontype2d4")
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_search", TEST_PASSWORD)

    resp = client.get("/caisse/?term=Zzuniquetransactiontype2d4", headers=headers)

    assert resp.status_code == 200
    types = [tx["transaction_type"] for tx in resp.json()["data"]]
    assert "Zzuniquetransactiontype2d4" in types


def test_list_transactions_filter_by_status(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_statusfilter", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, transaction_type="Zzstatusfilter2d4")
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_statusfilter", TEST_PASSWORD)

    resp_active = client.get("/caisse/?term=Zzstatusfilter2d4&status=active", headers=headers)
    assert resp_active.status_code == 200
    assert any(t["transaction_id"] == tx.transaction_id for t in resp_active.json()["data"])

    resp_cancelled = client.get("/caisse/?term=Zzstatusfilter2d4&status=cancelled", headers=headers)
    assert resp_cancelled.status_code == 200
    assert not any(t["transaction_id"] == tx.transaction_id for t in resp_cancelled.json()["data"])


def test_list_transactions_filter_by_date_range(db_session, api_client):
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_caisse_secretaire_daterange", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(
        db_session, user, transaction_type="Zzdaterange2d4",
        paid_at=date_cls(2030, 1, 15),
    )
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_daterange", TEST_PASSWORD)

    resp = client.get("/caisse/?date_from=2030-01-01&date_to=2030-01-31", headers=headers)
    assert resp.status_code == 200
    assert any(t["transaction_id"] == tx.transaction_id for t in resp.json()["data"])

    resp_excl = client.get("/caisse/?date_from=2030-02-01&date_to=2030-02-28", headers=headers)
    assert resp_excl.status_code == 200
    assert not any(t["transaction_id"] == tx.transaction_id for t in resp_excl.json()["data"])


def test_list_for_patient(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_forpatient", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, last_name="CaissePatient2d4")
    tx = create_test_transaction(db_session, user, patient_id=patient_id)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_forpatient", TEST_PASSWORD)

    resp = client.get(f"/caisse/patient/{patient_id}", headers=headers)

    assert resp.status_code == 200
    ids = [t["transaction_id"] for t in resp.json()]
    assert tx.transaction_id in ids


def test_update_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_update", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_update", TEST_PASSWORD)

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"note": "Note mise a jour"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["note"] == "Note mise a jour"


def test_update_transaction_partial_payload_keeps_existing_items(db_session, api_client):
    """
    Registre F6, corrige : un PUT partiel qui omet "items" ne touche plus
    aux lignes existantes ni au stock. "items" absent = inchange ;
    "items": [] explicite = vide intentionnellement.
    """
    user = create_test_user(db_session, "test_caisse_secretaire_keepitems", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_keepitems", TEST_PASSWORD)

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"note": "Partial update"}, headers=headers)

    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1
    assert resp.json()["note"] == "Partial update"

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert len(get_resp.json()["items"]) == 1


def test_update_transaction_explicit_empty_items_clears_lines(db_session, api_client):
    """Registre F6 : "items": [] explicite reste un vidage intentionnel."""
    user = create_test_user(db_session, "test_caisse_secretaire_clearitems", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=100.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_clearitems", TEST_PASSWORD)

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"items": [], "advance_amount": 100.0}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_update_transaction_refused_after_cancel(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_updatecancelled", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_updatecancelled", TEST_PASSWORD)

    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Test annulation"}, headers=headers)
    assert cancel_resp.status_code == 200

    resp = client.put(f"/caisse/{tx.transaction_id}", json={"note": "Ne devrait pas marcher"}, headers=headers)

    assert resp.status_code == 400
    assert "annulée" in resp.json()["detail"]


def test_update_transaction_not_found(db_session, api_client):
    create_test_user(db_session, "test_caisse_secretaire_update404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_update404", TEST_PASSWORD)

    resp = client.put("/caisse/999999999", json={"note": "x"}, headers=headers)

    assert resp.status_code == 400


def test_delete_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_delete", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_delete", TEST_PASSWORD)

    delete_resp = client.delete(f"/caisse/{tx.transaction_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_transaction_nonexistent_returns_404(db_session, api_client):
    """Registre F2, corrige : DELETE sur un id inexistant renvoie 404."""
    create_test_user(db_session, "test_caisse_secretaire_delete404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_delete404", TEST_PASSWORD)

    resp = client.delete("/caisse/999999999", headers=headers)

    assert resp.status_code == 404


def test_add_installment_payment_success(db_session, api_client):
    """Registre F3, corrige : POST /caisse/{id}/payment renvoie le versement cree, pas {}."""
    user = create_test_user(db_session, "test_caisse_secretaire_payment", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_payment", TEST_PASSWORD)

    resp = client.post(
        f"/caisse/{tx.transaction_id}/payment",
        json={"paid_amount": 20.0, "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["transaction_id"] == tx.transaction_id
    assert body["paid_amount"] == 20.0
    assert body["payment_method"] == "Especes"
    assert body["payment_id"]

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.json()["advance_amount"] == "50.00"


def test_add_installment_payment_exceeds_remaining_returns_400(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_paymentexceed", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_paymentexceed", TEST_PASSWORD)

    resp = client.post(
        f"/caisse/{tx.transaction_id}/payment",
        json={"paid_amount": 100.0, "payment_method": "Especes"},
        headers=headers,
    )

    assert resp.status_code == 400
    assert "Montant trop élevé" in resp.json()["detail"]


def test_settle_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_settle", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=30.0)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_settle", TEST_PASSWORD)

    resp = client.post(f"/caisse/{tx.transaction_id}/settle", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["advance_amount"] == "100.00"


def test_cancel_transaction_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_cancel", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_cancel", TEST_PASSWORD)

    resp = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Erreur de saisie"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Annulé"

    get_resp = client.get(f"/caisse/{tx.transaction_id}", headers=headers)
    assert get_resp.json()["status"] == "cancelled"
    assert get_resp.json()["cancel_justification"] == "Erreur de saisie"


def test_cancel_transaction_restores_pharmacy_stock(db_session):
    """Retour terrain 2026-09-28 (question explicite de l'utilisateur) :
    CaisseRepository.cancel_transaction() restaure deja le stock
    pharmacie pour les lignes 'médicament'/'carnet' (voir
    repositories/caisse_repo.py) mais ce chemin n'etait jamais couvert
    par un test - item_type='Service' est utilise partout ailleurs dans
    ce fichier (voir create_test_transaction) precisement pour eviter
    toute dependance a une vraie ligne Pharmacy."""
    user = create_test_user(db_session, "test_caisse_secretaire_stock_cancel", "secretaire", password=TEST_PASSWORD)

    med = Pharmacy(drug_name="Paracetamol 500mg", quantity=10, threshold=5, medication_type="comprime")
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)

    tx = create_test_transaction(db_session, user, items=[
        {
            "item_type": "médicament",
            "item_ref_id": med.medication_id,
            "unit_price": 500.0,
            "quantity": 3,
            "line_total": 1500.0,
        }
    ])

    db_session.refresh(med)
    assert med.quantity == 7  # create_transaction deduit deja le stock a la vente (10 - 3)

    ctrl = CaisseController(repo=CaisseRepository(db_session), current_user=user)
    ctrl.cancel_transaction(tx.transaction_id, "Erreur de saisie")

    db_session.refresh(med)
    assert med.quantity == 10  # stock restaure a son niveau d'avant-vente

    movement = (
        db_session.query(StockMovement)
        .filter_by(medication_id=med.medication_id, movement_type="ANNULATION_VENTE")
        .first()
    )
    assert movement is not None
    assert movement.change_qty == 3


def test_cancel_transaction_already_cancelled_returns_400(db_session, api_client):
    """
    Registre F5, corrige : annuler une transaction caisse deja annulee
    est maintenant refusee (400), comme pour un retrait
    (test_cancel_retrait_already_cancelled_returns_400, tests/test_retrait.py).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_doublecancel", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_doublecancel", TEST_PASSWORD)

    first = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Premiere annulation"}, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Deuxieme annulation"}, headers=headers)
    assert second.status_code == 400
    assert "déjà annulée" in second.json()["detail"]


def test_daily_total_reflects_created_transaction(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dailytotal", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dailytotal", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    before = client.get(f"/caisse/daily_total?for_date={today}", headers=headers).json()
    create_test_transaction(db_session, user, amount=77.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 77.0, "quantity": 1, "line_total": 77.0}
    ])
    after = client.get(f"/caisse/daily_total?for_date={today}", headers=headers).json()

    assert after == before + 77.0


def test_total_transactions_reflects_created_transaction(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_total", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_total", TEST_PASSWORD)

    before = client.get("/caisse/total", headers=headers).json()
    create_test_transaction(db_session, user, amount=88.0, advance_amount=0.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 88.0, "quantity": 1, "line_total": 88.0}
    ])
    after = client.get("/caisse/total", headers=headers).json()

    assert after == before + 88.0


def test_total_payments_reflects_advance_amount(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_totalpay", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_totalpay", TEST_PASSWORD)

    before = client.get("/caisse/total_payments", headers=headers).json()
    create_test_transaction(db_session, user, amount=100.0, advance_amount=25.0)
    after = client.get("/caisse/total_payments", headers=headers).json()

    assert after == before + 25.0


def test_total_remaining_due_default_filters_active_status(db_session, api_client):
    """
    Documente une incoherence sur HEAD : total_remaining_due filtre
    implicitement status='active' meme sans parametre status
    (repositories/caisse_repo.py::get_total_remaining_due fait
    "query.filter(Caisse.status == (status or 'active'))"), alors que
    total/total_payments ne filtrent par statut que si explicitement
    demande. Une transaction annulee avec un solde restant du n'est
    donc jamais comptee ici, sans que l'appelant sans filtre explicite
    ne s'y attende forcement. (SUIVI-AVANCEMENT.md registre F4)
    """
    user = create_test_user(db_session, "test_caisse_secretaire_remaining", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_remaining", TEST_PASSWORD)

    before = client.get("/caisse/total_remaining_due?status=active", headers=headers).json()
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0)
    after_active = client.get("/caisse/total_remaining_due?status=active", headers=headers).json()
    assert after_active == before + 60.0

    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Test annulation"}, headers=headers)
    assert cancel_resp.status_code == 200
    after_cancel = client.get("/caisse/total_remaining_due?status=active", headers=headers).json()
    assert after_cancel == before


def test_dashboard_kpis_date_scoped_exact_values(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dashkpis", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dashkpis", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    before = client.get(f"/caisse/dashboard/caisse/kpis?date_from={today}&date_to={today}", headers=headers).json()

    create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])

    resp = client.get(f"/caisse/dashboard/caisse/kpis?date_from={today}&date_to={today}", headers=headers)

    assert resp.status_code == 200
    after = resp.json()
    assert after["total_paid"] == before["total_paid"] + 40.0
    assert after["total_factured"] == before["total_factured"] + 100.0
    assert after["remaining_due"] == before["remaining_due"] + 60.0
    assert after["total_transactions"] == before["total_transactions"] + 1


def test_dashboard_unpaid_list(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dashunpaid", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0, items=[
        {"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}
    ])
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dashunpaid", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    resp = client.get(f"/caisse/dashboard/caisse/unpaid?date_from={today}&date_to={today}", headers=headers)

    assert resp.status_code == 200
    ids = [t["transaction_id"] for t in resp.json()]
    assert tx.transaction_id in ids


def test_dashboard_payment_distribution(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_caisse_secretaire_dashdistrib", "secretaire", password=TEST_PASSWORD)
    create_test_transaction(
        db_session, user, amount=100.0, advance_amount=40.0, payment_method="Zzuniquepaymentmethod2d4",
        items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}],
    )
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_dashdistrib", TEST_PASSWORD)
    today = date_cls.today().isoformat()

    resp = client.get(f"/caisse/dashboard/caisse/payment_distribution?date_from={today}&date_to={today}", headers=headers)

    assert resp.status_code == 200
    distribution = {item["method"]: item["total"] for item in resp.json()["distribution"]}
    assert distribution.get("Zzuniquepaymentmethod2d4") == 40.0


def test_download_invoice_pdf_success(db_session, api_client):
    user = create_test_user(db_session, "test_caisse_secretaire_pdf", "secretaire", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_pdf", TEST_PASSWORD)

    resp = client.get(f"/caisse/{tx.transaction_id}/invoice/download", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000


def test_invoice_pdf_reflete_le_nom_etablissement_configure(db_session, api_client):
    """Chantier exports (2026-09-23) : avant ce chantier, la facture
    utilisait un nom/logo code en dur ('AH2 Sante'), ignorant totalement
    OrganizationConfig - ce test verifie que ce n'est plus le cas."""
    from api_backend.backend_app.routes.admin import config_endpoints

    admin = create_test_user(db_session, "invoice_pdf_admin", "admin", password=TEST_PASSWORD)
    tx = create_test_transaction(db_session, admin)
    db_session.flush()

    client = api_client(auth_endpoints, caisse_endpoints, config_endpoints)
    headers = auth_headers(client, "invoice_pdf_admin", TEST_PASSWORD)

    resp_config = client.post("/config/structure", data={"name": "Clinique Facture Test 2026"}, headers=headers)
    assert resp_config.status_code == 200, resp_config.text

    resp = client.get(f"/caisse/{tx.transaction_id}/invoice/download", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000


def test_download_invoice_pdf_not_found(db_session, api_client):
    create_test_user(db_session, "test_caisse_secretaire_pdf404", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_pdf404", TEST_PASSWORD)

    resp = client.get("/caisse/999999999/invoice/download", headers=headers)

    assert resp.status_code == 404


def test_total_remaining_due_without_status_includes_all_statuses(db_session, api_client):
    """
    Registre F4, corrige : sans parametre status explicite,
    get_total_remaining_due() ne doit plus filtrer implicitement
    status='active', comme ses deux voisins (total, total_payments).
    """
    user = create_test_user(db_session, "test_caisse_secretaire_remaining_nofilter", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_secretaire_remaining_nofilter", TEST_PASSWORD)

    before = client.get("/caisse/total_remaining_due", headers=headers).json()
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0)
    cancel_resp = client.post(f"/caisse/{tx.transaction_id}/cancel", json={"cancel_justification": "Test annulation"}, headers=headers)
    assert cancel_resp.status_code == 200

    after = client.get("/caisse/total_remaining_due", headers=headers).json()
    assert after == before + 60.0


def test_ticket_endpoint_returns_404_for_unknown_transaction(api_client, db_session):
    client = api_client(auth_endpoints, caisse_endpoints)
    create_test_user(db_session, "tk_sec1", "secretaire", password=TEST_PASSWORD)
    headers = auth_headers(client, "tk_sec1", TEST_PASSWORD)
    r = client.get("/caisse/999999/ticket", headers=headers)
    assert r.status_code == 404
