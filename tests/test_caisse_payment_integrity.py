# tests/test_caisse_payment_integrity.py
"""Cloture de caisse, tache 7 : tout argent encaisse a une ligne paiement_echelonne.

- POST /caisse/{id}/settle ecrit une ligne 'SOLDE' du reste du, mode normalise de la vente ;
- PUT /caisse/{id} ne change ni advance_amount ni paid_at d'une vente deja encaissee
  (valeur identique acceptee), et normalise payment_method ;
- un versement rejoue avec un mode null n'est pas rejete (422) avant le garde-fou.
"""
import sys
import os
from decimal import Decimal

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from models.paiement_echelonne import PaiementEchelonne
from tests.conftest import create_test_user, auth_headers

PWD = "Correct123!"


def _client(db_session, api_client, username):
    create_test_user(db_session, username, "secretaire", password=PWD)
    client = api_client(auth_endpoints, caisse_endpoints)
    return client, auth_headers(client, username, PWD)


def _sale(client, h, mode="Mobile Money", advance=30.0):
    body = {
        "amount": 100.0, "advance_amount": advance, "payment_method": mode,
        "transaction_type": "Consultation", "patient_label": "Passant integrite",
        "items": [{"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0,
                   "quantity": 1, "line_total": 100.0}],
    }
    resp = client.post("/caisse/", json=body, headers=h)
    assert resp.status_code == 201, resp.text
    return resp.json()["transaction_id"]


def _payments(db_session, tx_id):
    db_session.expire_all()
    return db_session.query(PaiementEchelonne).filter_by(transaction_id=tx_id).order_by(
        PaiementEchelonne.payment_id).all()


def _advance(db_session, tx_id):
    return Decimal(str(db_session.execute(
        text("SELECT advance_amount FROM caisse WHERE transaction_id=:t"), {"t": tx_id}).scalar()))


# --- settle -----------------------------------------------------------------

def test_settle_ecrit_une_ligne_solde(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_settle")
    tx_id = _sale(client, h, mode="Mobile Money", advance=30.0)
    resp = client.post(f"/caisse/{tx_id}/settle", headers=h)
    assert resp.status_code == 200, resp.text
    pays = _payments(db_session, tx_id)
    assert len(pays) == 2
    solde = pays[-1]
    assert solde.payment_type == "SOLDE"
    assert Decimal(str(solde.paid_amount)) == Decimal("70")
    assert solde.payment_method == "autre_mobile"
    assert solde.received_at is not None
    assert sum(Decimal(str(p.paid_amount)) for p in pays) == _advance(db_session, tx_id) == Decimal("100")


def test_settle_vente_deja_soldee_ne_cree_rien(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_settle_full")
    tx_id = _sale(client, h, advance=100.0)
    assert client.post(f"/caisse/{tx_id}/settle", headers=h).status_code == 200
    assert len(_payments(db_session, tx_id)) == 1


# --- PUT --------------------------------------------------------------------

def test_put_ne_peut_pas_changer_advance_amount(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_put_adv")
    tx_id = _sale(client, h, advance=30.0)
    resp = client.put(f"/caisse/{tx_id}", json={"advance_amount": 100.0}, headers=h)
    assert resp.status_code == 400, resp.text
    assert _advance(db_session, tx_id) == Decimal("30")
    assert len(_payments(db_session, tx_id)) == 1


def test_put_ne_peut_pas_changer_paid_at_vente_encaissee(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_put_date")
    tx_id = _sale(client, h, advance=30.0)
    resp = client.put(f"/caisse/{tx_id}", json={"paid_at": "2020-01-01T08:00:00"}, headers=h)
    assert resp.status_code == 400, resp.text


def test_put_valeurs_identiques_et_champs_non_monetaires_acceptes(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_put_same")
    tx_id = _sale(client, h, advance=30.0)
    got = client.get(f"/caisse/{tx_id}", headers=h).json()
    resp = client.put(f"/caisse/{tx_id}",
                      json={"note": "corrigee", "advance_amount": 30.0, "paid_at": got["paid_at"]},
                      headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["note"] == "corrigee"


def test_put_payment_method_normalise(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_put_mode")
    tx_id = _sale(client, h, advance=30.0)
    resp = client.put(f"/caisse/{tx_id}", json={"payment_method": "Virement"}, headers=h)
    assert resp.status_code == 200, resp.text
    stored = db_session.execute(text("SELECT payment_method FROM caisse WHERE transaction_id=:t"),
                                {"t": tx_id}).scalar()
    assert stored == "non_classe"


# --- versement avec mode null -------------------------------------------------

def test_versement_rejoue_mode_null_non_classe(db_session, api_client):
    client, h = _client(db_session, api_client, "pi_inst_null")
    tx_id = _sale(client, h, advance=30.0)
    resp = client.post(f"/caisse/{tx_id}/payment",
                       json={"paid_amount": 10.0, "payment_method": None,
                             "uuid": "dddddddd-1111-2222-3333-000000000001"}, headers=h)
    assert resp.status_code == 201, resp.text
    assert resp.json()["payment_method"] == "non_classe"
    # en ligne, sans uuid : meme regle qu'une vente (stocke non_classe)
    online = client.post(f"/caisse/{tx_id}/payment",
                         json={"paid_amount": 10.0}, headers=h)
    assert online.status_code == 201, online.text
    assert online.json()["payment_method"] == "non_classe"
