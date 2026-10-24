# tests/test_payment_modes.py
"""Liste officielle des modes de paiement a l'ecriture (cloture de caisse, tache 6).

- retrait neuf sans mode -> 422 ; mode ancien normalise, jamais rejete ;
- vente et paiement echelonne : meme normalisation ;
- mode desactive par l'admin -> nouvelle ecriture refusee (422), anciens paiements lisibles.
"""
import sys
import os

import pytest
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.retrait import retrait_endpoints
from models.paiement_echelonne import PaiementEchelonne
from models.retrait import CaisseRetrait
from tests.conftest import create_test_user, create_test_transaction, auth_headers

PWD = "Correct123!"


def _client(db_session, api_client, username):
    create_test_user(db_session, username, "secretaire", password=PWD)
    client = api_client(auth_endpoints, retrait_endpoints, caisse_endpoints)
    return client, auth_headers(client, username, PWD)


def _retrait(client, headers, **extra):
    body = {"amount": 10.0, "justification": "Test mode", **extra}
    return client.post("/retrait/", json=body, headers=headers)


def _stored_retrait_mode(db_session, retrait_id):
    return db_session.get(CaisseRetrait, retrait_id).payment_method


def _sale_payload(mode, advance=50.0):
    return {
        "amount": 100.0, "advance_amount": advance, "payment_method": mode,
        "transaction_type": "Consultation", "patient_label": "Passant mode",
        "items": [{"item_type": "Service", "item_ref_id": 1, "unit_price": 100.0,
                   "quantity": 1, "line_total": 100.0}],
    }


def _deactivate(db_session, code):
    db_session.execute(text("UPDATE payment_modes SET is_active = false WHERE code = :c"), {"c": code})
    db_session.flush()


# --- Retraits --------------------------------------------------------------

def test_retrait_sans_mode_refuse_422(db_session, api_client):
    client, h = _client(db_session, api_client, "pm_retrait_nomode")
    assert _retrait(client, h).status_code == 422
    assert _retrait(client, h, payment_method=None).status_code == 422
    assert _retrait(client, h, payment_method="").status_code == 422
    assert _retrait(client, h, payment_method="   ").status_code == 422


@pytest.mark.parametrize("code", ["especes", "orange_money", "mtn_money", "autre_mobile"])
def test_retrait_code_officiel_stocke(db_session, api_client, code):
    client, h = _client(db_session, api_client, f"pm_retrait_{code}")
    resp = _retrait(client, h, payment_method=code)
    assert resp.status_code == 201
    assert _stored_retrait_mode(db_session, resp.json()["retrait_id"]) == code
    assert resp.json()["payment_method"] == code


@pytest.mark.parametrize("raw, expected", [
    ("Virement", "non_classe"),
    ("Mobile Money", "autre_mobile"),
    ("Chèque", "non_classe"),
    ("Cash", "especes"),
    ("Espèces", "especes"),
    ("MTN Money", "mtn_money"),
])
def test_retrait_mode_ancien_normalise_jamais_rejete(db_session, api_client, raw, expected):
    client, h = _client(db_session, api_client, f"pm_retrait_old_{expected}_{len(raw)}")
    resp = _retrait(client, h, payment_method=raw)
    assert resp.status_code == 201, resp.text
    assert _stored_retrait_mode(db_session, resp.json()["retrait_id"]) == expected


def test_retrait_mode_desactive_refuse_422(db_session, api_client):
    client, h = _client(db_session, api_client, "pm_retrait_inactive")
    _deactivate(db_session, "autre_mobile")
    assert _retrait(client, h, payment_method="autre_mobile").status_code == 422
    # non_classe (seau des valeurs anciennes) reste toujours accepte
    assert _retrait(client, h, payment_method="Virement").status_code == 201


def test_ancien_retrait_sans_mode_garde_son_affichage(db_session, api_client):
    """Lignes anciennes (null) : le mapping d'affichage 'Espèces' est conserve."""
    user = create_test_user(db_session, "pm_retrait_legacy", "secretaire", password=PWD)
    old = CaisseRetrait(amount=5, justification="ancien", handled_by=user.user_id, payment_method=None)
    db_session.add(old)
    db_session.flush()
    client = api_client(auth_endpoints, retrait_endpoints)
    h = auth_headers(client, "pm_retrait_legacy", PWD)
    resp = client.get(f"/retrait/{old.retrait_id}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["payment_method"] == "Espèces"


# --- Ventes et paiements echelonnes ---------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Especes", "especes"),
    ("Mobile Money", "autre_mobile"),
    ("Virement", "non_classe"),
    ("orange_money", "orange_money"),
])
def test_vente_mode_normalise(db_session, api_client, raw, expected):
    client, h = _client(db_session, api_client, f"pm_sale_{expected}_{len(raw)}")
    resp = client.post("/caisse/", json=_sale_payload(raw), headers=h)
    assert resp.status_code == 201, resp.text
    tx_id = resp.json()["transaction_id"]
    stored = db_session.execute(text("SELECT payment_method FROM caisse WHERE transaction_id=:t"),
                                {"t": tx_id}).scalar()
    assert stored == expected
    pay = db_session.query(PaiementEchelonne).filter_by(transaction_id=tx_id).one()
    assert pay.payment_method == expected


@pytest.mark.parametrize("raw, expected", [
    ("Mobile Money", "autre_mobile"),
    ("Virement", "non_classe"),
    ("MTN Money", "mtn_money"),
])
def test_paiement_echelonne_mode_normalise(db_session, api_client, raw, expected):
    user = create_test_user(db_session, f"pm_inst_{expected}", "secretaire", password=PWD)
    client = api_client(auth_endpoints, caisse_endpoints)
    h = auth_headers(client, f"pm_inst_{expected}", PWD)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=10.0)
    resp = client.post(f"/caisse/{tx.transaction_id}/payment",
                       json={"paid_amount": 20.0, "payment_method": raw}, headers=h)
    assert resp.status_code == 201, resp.text
    assert resp.json()["payment_method"] == expected


def test_mode_desactive_vente_et_versement_refuses_ancien_paiement_lisible(db_session, api_client):
    client, h = _client(db_session, api_client, "pm_sale_inactive")
    # Ancien paiement dans ce mode, avant desactivation
    ok = client.post("/caisse/", json=_sale_payload("mtn_money", advance=30.0), headers=h)
    assert ok.status_code == 201
    tx_id = ok.json()["transaction_id"]

    _deactivate(db_session, "mtn_money")

    assert client.post("/caisse/", json=_sale_payload("MTN Money"), headers=h).status_code == 422
    inst = client.post(f"/caisse/{tx_id}/payment",
                       json={"paid_amount": 10.0, "payment_method": "mtn_money"}, headers=h)
    assert inst.status_code == 422

    # L'ancien paiement reste lisible
    got = client.get(f"/caisse/{tx_id}", headers=h)
    assert got.status_code == 200
    assert got.json()["payment_method"] == "mtn_money"
    stored = db_session.query(PaiementEchelonne).filter_by(transaction_id=tx_id).one()
    assert stored.payment_method == "mtn_money"


# --- Rejeu depuis la file hors ligne (uuid client) : jamais refuse pour le mode ---

def test_retrait_rejoue_sans_mode_stocke_non_classe(db_session, api_client):
    client, h = _client(db_session, api_client, "pm_replay_nomode")
    resp = _retrait(client, h, uuid="cccccccc-1111-2222-3333-000000000001")
    assert resp.status_code == 201, resp.text
    assert _stored_retrait_mode(db_session, resp.json()["retrait_id"]) == "non_classe"
    # meme envoi sans uuid (operation en ligne) : refuse
    assert _retrait(client, h).status_code == 422


def test_retrait_rejoue_mode_desactive_accepte(db_session, api_client):
    client, h = _client(db_session, api_client, "pm_replay_inactive_r")
    _deactivate(db_session, "orange_money")
    resp = _retrait(client, h, payment_method="orange_money",
                    uuid="cccccccc-1111-2222-3333-000000000002")
    assert resp.status_code == 201, resp.text
    assert _stored_retrait_mode(db_session, resp.json()["retrait_id"]) == "orange_money"
    assert _retrait(client, h, payment_method="orange_money").status_code == 422


def test_vente_et_versement_rejoues_mode_desactive_acceptes(db_session, api_client):
    client, h = _client(db_session, api_client, "pm_replay_inactive_s")
    _deactivate(db_session, "mtn_money")
    # en ligne : refuse
    assert client.post("/caisse/", json=_sale_payload("mtn_money"), headers=h).status_code == 422
    # rejeu : accepte, code garde tel quel
    sale = client.post("/caisse/", json={**_sale_payload("mtn_money", advance=20.0),
                                          "uuid": "cccccccc-1111-2222-3333-000000000003"}, headers=h)
    assert sale.status_code == 201, sale.text
    assert sale.json()["payment_method"] == "mtn_money"
    tx_id = sale.json()["transaction_id"]
    online = client.post(f"/caisse/{tx_id}/payment",
                         json={"paid_amount": 10.0, "payment_method": "mtn_money"}, headers=h)
    assert online.status_code == 422
    inst = client.post(f"/caisse/{tx_id}/payment",
                       json={"paid_amount": 10.0, "payment_method": "",
                             "uuid": "cccccccc-1111-2222-3333-000000000004"}, headers=h)
    assert inst.status_code == 201, inst.text
    assert inst.json()["payment_method"] == "non_classe"
    inst2 = client.post(f"/caisse/{tx_id}/payment",
                        json={"paid_amount": 10.0, "payment_method": "mtn_money",
                              "uuid": "cccccccc-1111-2222-3333-000000000005"}, headers=h)
    assert inst2.status_code == 201, inst2.text
    assert inst2.json()["payment_method"] == "mtn_money"


def test_demande_de_remise_mode_desactive_422(db_session, api_client):
    from api_backend.backend_app.routes.discount import discount_endpoints
    create_test_user(db_session, "pm_disc_sec", "secretaire", password=PWD)
    mgr = create_test_user(db_session, "pm_disc_mgr", "admin", password=PWD)
    client = api_client(auth_endpoints, discount_endpoints)
    h = auth_headers(client, "pm_disc_sec", PWD)
    _deactivate(db_session, "autre_mobile")
    invoice = {**_sale_payload("Mobile Money", advance=0)}
    resp = client.post("/discount-requests", json={"invoice_data": invoice, "requested_to": mgr.user_id},
                       headers=h)
    assert resp.status_code == 422, resp.text
    ok = client.post("/discount-requests",
                     json={"invoice_data": {**invoice, "payment_method": "Especes"},
                           "requested_to": mgr.user_id}, headers=h)
    assert ok.status_code == 201, ok.text
