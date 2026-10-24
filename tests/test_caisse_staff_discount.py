# tests/test_caisse_staff_discount.py
"""Task 5 - controle serveur de la reduction personnel a la facturation."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from controller.caisse_controller import CaisseController
from repositories.caisse_repo import CaisseRepository
from repositories.staff_discount_repo import StaffDiscountRepository
from models.caisse import Caisse
from models.patient import Patient
from models.pharmacy import Pharmacy
from models.lab import Examen
from models.staff_discount_rule import StaffDiscountRule
from tests.conftest import create_test_user, create_test_patient, auth_headers
import uuid as _uuid
import pytest

PWD = "Correct123!"
MSG = "Réduction personnel incohérente avec les règles en vigueur."


def _only_rule(db, category="medicament", minimum=5000, rate=50, active=True):
    """Desactive toutes les regles existantes (dans la transaction de test)
    puis cree/maj la seule regle voulue."""
    db.query(StaffDiscountRule).update({StaffDiscountRule.is_active: False})
    db.flush()
    rule = StaffDiscountRepository(db).upsert_rule(category, minimum, rate, active, None)
    db.flush()
    return rule


def _patient(db, user, staff=True):
    pid, _ = create_test_patient(db, user)
    p = db.get(Patient, pid)
    p.is_staff = staff
    db.flush()
    return pid


# Prix verrouille au catalogue (2026-10-24) : la secretaire facture au prix
# catalogue. Medicament et examen de test a 1 FCFA, le montant de ligne vient
# de la quantite (line_total = 1 x t) : memes totaux qu'avant.
_CATALOG = {"exam_id": None}


@pytest.fixture(autouse=True)
def _catalog_exam(db_session):
    ex = Examen(code=f"SD-{_uuid.uuid4().hex[:8]}", nom="Examen staff test", categorie="Bio", prix=1)
    db_session.add(ex)
    db_session.flush()
    _CATALOG["exam_id"] = ex.id
    yield


def _med(db, qty=100000):
    m = Pharmacy(drug_name="Medoc staff test", quantity=qty, threshold=1, medication_type="comprime",
                 price=1)
    db.add(m)
    db.flush()
    return m.medication_id


def _payload(patient_id, med_id, totals=(3000.0, 4000.0), discount=None, amount=None):
    # 1re ligne medicament (stock), lignes suivantes examens (spec : 3000 med + 4000 examens)
    items = [{"item_type": "médicament" if i == 0 else "Examens",
              "item_ref_id": med_id if i == 0 else _CATALOG["exam_id"], "unit_price": 1.0,
              "quantity": int(t), "line_total": t} for i, t in enumerate(totals)]
    gross = sum(totals)
    p = {
        "patient_id": patient_id,
        "amount": amount if amount is not None else gross - (discount or 0),
        "advance_amount": 0.0,
        "payment_method": "Especes",
        "transaction_type": "Vente",
        "items": items,
    }
    if discount is not None:
        p["staff_discount_amount"] = discount
    return p


def _client(api_client, db, name):
    user = create_test_user(db, name, "secretaire", password=PWD)
    client = api_client(auth_endpoints, caisse_endpoints)
    return user, client, auth_headers(client, name, PWD)


def test_staff_invoice_with_correct_discount_accepted(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_ok")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["amount"] == "5500.00"
    assert float(body["staff_discount_amount"]) == 1500.0
    assert body["staff_discount_details"]
    assert body["staff_discount_details"][0]["category"] == "medicament"
    tx = db_session.get(Caisse, body["transaction_id"])
    assert float(tx.staff_discount_amount) == 1500.0
    assert tx.staff_discount_details is not None


def test_discount_too_high_rejected(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_high")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=2000.0), headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == MSG


def test_discount_on_non_staff_patient_rejected(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_nonstaff")
    _only_rule(db_session)
    pid = _patient(db_session, user, staff=False)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0), headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == MSG


def test_discount_without_patient_rejected(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_nopatient")
    _only_rule(db_session)
    p = _payload(None, _med(db_session), discount=1500.0)
    p["patient_label"] = "Passant"
    r = client.post("/caisse/", json=p, headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == MSG


def test_missing_discount_when_rule_applies_rejected(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_missing")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session)), headers=h)  # 0 implicite
    assert r.status_code == 400
    assert r.json()["detail"] == MSG


def test_rule_deactivated_before_sync_rejected(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_deact")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    med = _med(db_session)
    # Le poste a calcule 1500 hors ligne, puis l'admin desactive la regle
    _only_rule(db_session, active=False)
    r = client.post("/caisse/", json=_payload(pid, med, discount=1500.0), headers=h)
    assert r.status_code == 400
    assert r.json()["detail"] == MSG


def test_no_matching_rule_stores_zero_and_null_details(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_nomatch")
    _only_rule(db_session, category="consultation")
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session)), headers=h)
    assert r.status_code == 201, r.text
    tx = db_session.get(Caisse, r.json()["transaction_id"])
    assert float(tx.staff_discount_amount) == 0
    assert tx.staff_discount_details is None
    assert r.json()["staff_discount_details"] is None


def test_rounding_edge_accepted(db_session, api_client):
    # 33% de 5001 = 1650.33 ; le client envoie 1650.33 (2 decimales)
    user, client, h = _client(api_client, db_session, "sd5_round")
    _only_rule(db_session, rate=33)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), totals=(5001.0,), discount=1650.33), headers=h)
    assert r.status_code == 201, r.text
    assert float(r.json()["staff_discount_amount"]) == 1650.33
    # et un centime d'ecart est refuse
    r2 = client.post("/caisse/", json=_payload(pid, _med(db_session), totals=(5001.0,), discount=1650.34), headers=h)
    assert r2.status_code == 400
    assert r2.json()["detail"] == MSG


def test_net_amount_mismatch_rejected_with_amount_message(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_netmis")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0, amount=7000.0), headers=h)
    assert r.status_code == 400
    assert "Incohérence montant" in r.json()["detail"]


def test_non_staff_invoice_unchanged(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_regress")
    _only_rule(db_session)
    pid = _patient(db_session, user, staff=False)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session)), headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["amount"] == "7000.00"
    assert float(r.json()["staff_discount_amount"]) == 0
    assert r.json()["staff_discount_details"] is None


def test_cancel_keeps_discount_fields(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_cancel")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0), headers=h)
    assert r.status_code == 201, r.text
    tid = r.json()["transaction_id"]
    c = client.post(f"/caisse/{tid}/cancel", json={"cancel_justification": "test"}, headers=h)
    assert c.status_code == 200
    g = client.get(f"/caisse/{tid}", headers=h).json()
    assert g["status"] == "cancelled"
    assert g["amount"] == "5500.00"
    assert float(g["staff_discount_amount"]) == 1500.0
    assert g["staff_discount_details"]


def test_ticket_data_exposes_staff_discount(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_ticket")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0), headers=h)
    tid = r.json()["transaction_id"]
    ctrl = CaisseController(repo=CaisseRepository(db_session), current_user=user)
    data = ctrl.build_ticket_data(tid)
    assert data["staff_discount"]["amount"] == 1500.0
    assert isinstance(data["staff_discount"]["details"], list)

    r0 = client.post("/caisse/", json=_payload(pid, _med(db_session), totals=(100.0,)), headers=h)
    assert r0.status_code == 201, r0.text
    assert ctrl.build_ticket_data(r0.json()["transaction_id"])["staff_discount"] is None


def test_get_transaction_exposes_staff_fields(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_get")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0), headers=h)
    g = client.get(f"/caisse/{r.json()['transaction_id']}", headers=h).json()
    assert float(g["staff_discount_amount"]) == 1500.0
    assert g["staff_discount_details"][0]["rate_percent"] == 50


# ---------------- Fix round 1 : PUT /caisse/{id} + minors ----------------

def _staff_invoice(db, api_client, name):
    user, client, h = _client(api_client, db, name)
    _only_rule(db)
    pid = _patient(db, user)
    med = _med(db)
    r = client.post("/caisse/", json=_payload(pid, med, discount=1500.0), headers=h)
    assert r.status_code == 201, r.text
    return user, client, h, pid, med, r.json()["transaction_id"]


def _items(med, totals):
    return _payload(None, med, totals=totals)["items"]


REFUSE = "Facture avec réduction personnel"


def _assert_staff_invoice_unchanged(db, tid, med):
    tx = db.get(Caisse, tid)
    db.refresh(tx)
    assert float(tx.amount) == 5500.0
    assert float(tx.staff_discount_amount) == 1500.0
    assert tx.staff_discount_details[0]["category"] == "medicament"
    assert tx.staff_discount_details[0]["base"] == 3000.0
    assert len(tx.items) == 2
    assert sorted(float(i.line_total) for i in tx.items) == [3000.0, 4000.0]


def _put_refused(db, api_client, name, build):
    _, client, h, _, med, tid = _staff_invoice(db, api_client, name)
    stock_before = db.get(Pharmacy, med).quantity
    r = client.put(f"/caisse/{tid}", json=build(db, med), headers=h)
    assert 400 <= r.status_code < 500, r.text
    assert REFUSE in r.json()["detail"]
    _assert_staff_invoice_unchanged(db, tid, med)
    assert db.get(Pharmacy, med).quantity == stock_before


def test_put_staff_invoice_with_correct_net_amount_refused(db_session, api_client):
    _put_refused(db_session, api_client, "sd5_put_net",
                 lambda db, med: {"items": _items(med, (3000.0, 4000.0)), "amount": 5500.0})


def test_put_changing_items_on_staff_invoice_refused(db_session, api_client):
    _put_refused(db_session, api_client, "sd5_put_items",
                 lambda db, med: {"items": _items(med, (6000.0, 1000.0)), "amount": 4000.0})


def test_put_switch_to_non_staff_patient_refused(db_session, api_client):
    user, client, h, _, med, tid = _staff_invoice(db_session, api_client, "sd5_put_pat")
    other = _patient(db_session, user, staff=False)
    r = client.put(f"/caisse/{tid}", json={"patient_id": other}, headers=h)
    assert 400 <= r.status_code < 500, r.text
    assert REFUSE in r.json()["detail"]
    _assert_staff_invoice_unchanged(db_session, tid, med)


def test_put_items_with_wrong_amount_on_staff_invoice_refused(db_session, api_client):
    _put_refused(db_session, api_client, "sd5_put_bad",
                 lambda db, med: {"items": _items(med, (6000.0, 1000.0)), "amount": 7000.0})


def test_put_items_only_on_staff_invoice_refused(db_session, api_client):
    _put_refused(db_session, api_client, "sd5_put_only",
                 lambda db, med: {"items": _items(med, (8000.0, 2000.0))})


def test_put_amount_only_on_staff_invoice_refused(db_session, api_client):
    _put_refused(db_session, api_client, "sd5_put_amt", lambda db, med: {"amount": 1234.0})


def test_put_client_sent_staff_discount_with_items_refused(db_session, api_client):
    _put_refused(db_session, api_client, "sd5_put_cli",
                 lambda db, med: {"staff_discount_amount": 7000.0,
                                  "staff_discount_details": [{"x": 1}],
                                  "items": _items(med, (3000.0, 4000.0))})


def test_put_note_only_on_staff_invoice_still_succeeds(db_session, api_client):
    _, client, h, _, med, tid = _staff_invoice(db_session, api_client, "sd5_put_note")
    r = client.put(f"/caisse/{tid}", json={"note": "n"}, headers=h)
    assert r.status_code == 200, r.text
    # champs reduction envoyes par le client sans items/patient/amount : ignores
    r2 = client.put(f"/caisse/{tid}", json={"staff_discount_amount": 0, "note": "n2"}, headers=h)
    assert r2.status_code == 200, r2.text
    _assert_staff_invoice_unchanged(db_session, tid, med)
    assert db_session.get(Caisse, tid).note == "n2"


def test_put_attach_staff_patient_to_no_discount_invoice_still_recomputes(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_put_attach")
    _only_rule(db_session)
    plain = _patient(db_session, user, staff=False)
    staff = _patient(db_session, user, staff=True)
    med = _med(db_session)
    r = client.post("/caisse/", json=_payload(plain, med), headers=h)
    assert r.status_code == 201, r.text
    tid = r.json()["transaction_id"]
    ok = client.put(f"/caisse/{tid}", json={"patient_id": staff, "amount": 5500.0}, headers=h)
    assert ok.status_code == 200, ok.text
    tx = db_session.get(Caisse, tid)
    db_session.refresh(tx)
    assert float(tx.staff_discount_amount) == 1500.0 and float(tx.amount) == 5500.0

def test_put_non_staff_invoice_unchanged(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_put_regress")
    _only_rule(db_session)
    pid = _patient(db_session, user, staff=False)
    med = _med(db_session)
    r = client.post("/caisse/", json=_payload(pid, med), headers=h)
    tid = r.json()["transaction_id"]
    ok = client.put(f"/caisse/{tid}", json={"items": _items(med, (1000.0, 2000.0)), "amount": 3000.0}, headers=h)
    assert ok.status_code == 200 and ok.json()["amount"] == "3000.00"
    bad = client.put(f"/caisse/{tid}", json={"items": _items(med, (1000.0,)), "amount": 999.0}, headers=h)
    assert bad.status_code == 400 and "Incohérence montant" in bad.json()["detail"]
    amt_only = client.put(f"/caisse/{tid}", json={"amount": 1234.0}, headers=h)
    assert amt_only.status_code == 200 and amt_only.json()["amount"] == "1234.00"


def test_create_mismatch_message_shows_gross_discount_net(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_msg")
    _only_rule(db_session)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), discount=1500.0, amount=7000.0), headers=h)
    d = r.json()["detail"]
    assert "7000.00" in d and "1500.00" in d and "Réduction personnel" in d


def test_create_none_line_total_returns_400(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_none")
    p = _payload(None, _med(db_session), totals=(100.0, 50.0), amount=100.0)
    p["items"][1]["line_total"] = None
    r = client.post("/caisse/", json=p, headers=h)
    assert r.status_code == 400


def test_create_amount_stored_rounded(db_session, api_client):
    user, client, h = _client(api_client, db_session, "sd5_round_amt")
    _only_rule(db_session, rate=33)
    pid = _patient(db_session, user)
    r = client.post("/caisse/", json=_payload(pid, _med(db_session), totals=(5001.0,), discount=1650.33,
                                              amount=3350.669), headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["amount"] == "3350.67"
