"""Nom du patient sur les factures et les demandes de reduction.

Bug : patient_name restait None pour un patient enregistre (Patient n'a pas
de full_name) et le flux de demande de reduction ne lisait que patient_label.
"""
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.discount import discount_endpoints
from conftest import auth_headers, create_test_user, create_test_patient, create_test_transaction
from models.notification import Notification

PWD = "TestPass123!"


def _setup(api_client, db_session, **patient_overrides):
    client = api_client(auth_endpoints, caisse_endpoints, discount_endpoints)
    sec = create_test_user(db_session, "pn_sec", "secretaire", password=PWD)
    mgr = create_test_user(db_session, "pn_mgr", "admin", password=PWD)
    pid, _code = create_test_patient(db_session, sec, first_name="Awa", last_name="Diallo", **patient_overrides)
    return client, sec, mgr, pid


def test_get_and_list_return_registered_patient_full_name(api_client, db_session):
    client, sec, mgr, pid = _setup(api_client, db_session)
    tx = create_test_transaction(db_session, sec, patient_id=pid, note="pn-reg")
    h = auth_headers(client, "pn_sec", PWD)

    r = client.get(f"/caisse/{tx.transaction_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["patient_name"] == "Awa Diallo"

    r = client.get("/caisse/", params={"term": "pn-reg", "per_page": 50}, headers=h)
    row = [x for x in r.json()["data"] if x["transaction_id"] == tx.transaction_id][0]
    assert row["patient_name"] == "Awa Diallo"


def test_walk_in_still_uses_label(api_client, db_session):
    client, sec, mgr, pid = _setup(api_client, db_session)
    tx = create_test_transaction(db_session, sec, patient_label="Passant Kone")
    h = auth_headers(client, "pn_sec", PWD)
    r = client.get(f"/caisse/{tx.transaction_id}", headers=h)
    assert r.json()["patient_name"] == "Passant Kone"
    assert r.json()["patient_label"] == "Passant Kone"


def test_registered_patient_name_wins_over_label(api_client, db_session):
    client, sec, mgr, pid = _setup(api_client, db_session)
    tx = create_test_transaction(db_session, sec, patient_id=pid, patient_label="Ancien libelle")
    h = auth_headers(client, "pn_sec", PWD)
    r = client.get(f"/caisse/{tx.transaction_id}", headers=h)
    assert r.json()["patient_name"] == "Awa Diallo"
    assert r.json()["patient_label"] == "Ancien libelle"


def _invoice(**extra):
    return {
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 2000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 2000, "quantity": 1, "line_total": 2000}],
        **extra,
    }


def _request(client, headers, mgr, **extra):
    r = client.post("/discount-requests", json={"invoice_data": _invoice(**extra), "requested_to": mgr.user_id}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _notif_payload(db_session, req_id):
    for n in db_session.query(Notification).filter(Notification.type == "discount_request").all():
        if n.payload.get("discount_request_id") == req_id:
            return n.payload
    raise AssertionError("notification introuvable")


def test_discount_request_registered_patient_name_everywhere(api_client, db_session):
    client, sec, mgr, pid = _setup(api_client, db_session)
    sh = auth_headers(client, "pn_sec", PWD)
    mh = auth_headers(client, "pn_mgr", PWD)
    req_id = _request(client, sh, mgr, patient_id=pid)

    assert _notif_payload(db_session, req_id)["patient_label"] == "Awa Diallo"

    pending = client.get("/discount-requests/pending", headers=mh).json()
    item = [p for p in pending if p["id"] == req_id][0]
    assert item["patient_label"] == "Awa Diallo"
    assert item["patient_id"] == pid

    hist = client.get("/discount-requests/history", headers=mh).json()
    h_item = [x for x in hist["data"] if x["id"] == req_id][0]
    assert h_item["patient_label"] == "Awa Diallo"
    assert h_item["patient_id"] == pid


def test_discount_request_walk_in_unchanged(api_client, db_session):
    client, sec, mgr, pid = _setup(api_client, db_session)
    sh = auth_headers(client, "pn_sec", PWD)
    mh = auth_headers(client, "pn_mgr", PWD)
    req_id = _request(client, sh, mgr, patient_label="Passant Kone")

    assert _notif_payload(db_session, req_id)["patient_label"] == "Passant Kone"
    item = [p for p in client.get("/discount-requests/pending", headers=mh).json() if p["id"] == req_id][0]
    assert item["patient_label"] == "Passant Kone"
    assert item["patient_id"] is None
    hist = client.get("/discount-requests/history", headers=mh).json()
    assert [x for x in hist["data"] if x["id"] == req_id][0]["patient_label"] == "Passant Kone"
