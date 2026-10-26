# tests/test_caisse_kpi_cache.py
# Defaut 6b (2026-10-26) : le cache Redis des KPI caisse (caisse:kpis:{from}:{to},
# 5 min) n'etait jamais vide a l'enregistrement d'une facture ou d'un paiement :
# les tuiles restaient figees jusqu'a 5 minutes. Chaque ecriture doit vider
# toutes les cles caisse:kpis:* (et caisse:distrib:*), garder l'invalidation de
# caisse:daily_total, et ne jamais bloquer une vente si Redis est indisponible.
import sys
import os
import fnmatch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

import controller.caisse_controller as caisse_controller_module
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from controller.discount_request_controller import DiscountRequestController
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.notification_repo import NotificationRepository
from repositories.caisse_repo import CaisseRepository
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, *keys):
        n = 0
        for k in keys:
            n += 1 if self.store.pop(k, None) is not None else 0
        return n

    def scan_iter(self, match=None, count=None):
        return [k for k in list(self.store) if match is None or fnmatch.fnmatch(k, match)]

    def incr(self, key):
        self.store[key] = int(self.store.get(key) or 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        return True


class DownRedis:
    def __getattr__(self, name):
        def _boom(*a, **k):
            raise ConnectionError("redis down")
        return _boom


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(caisse_controller_module, "redis_client", fake)
    return fake


def _invoice(patient_id, amount=100.0, advance=40.0):
    return {
        "patient_id": patient_id,
        "amount": amount,
        "advance_amount": advance,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [{"item_type": "Service", "item_ref_id": 1, "unit_price": amount, "quantity": 1, "line_total": amount}],
    }


def _seed_stale(fake):
    fake.store["caisse:kpis:2026-01-01:2026-01-01"] = '{"stale": true}'
    fake.store["caisse:kpis:2026-01-01:2026-01-31"] = '{"stale": true}'
    fake.store["caisse:distrib:2026-01-01:2026-01-01"] = '{"stale": true}'
    fake.store["caisse:daily_total:2026-01-01"] = "1"
    fake.store["patient:stats:global"] = "keep"


def _assert_cleared(fake):
    assert not [k for k in fake.store if k.startswith("caisse:kpis:")]
    assert not [k for k in fake.store if k.startswith("caisse:distrib:")]
    assert fake.store.get("patient:stats:global") == "keep", "seules les cles caisse sont videes"


def test_vente_vide_le_cache_kpi_et_la_lecture_suivante_recalcule(db_session, api_client, fake_redis):
    user = create_test_user(db_session, "kpi_cache_sec", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "kpi_cache_sec", TEST_PASSWORD)

    today = str(caisse_controller_module.business_today())
    params = {"date_from": today, "date_to": today}
    avant = client.get("/caisse/dashboard/caisse/kpis", params=params, headers=headers)
    assert avant.status_code == 200
    assert f"caisse:kpis:{today}:{today}" in fake_redis.store, "la premiere lecture met en cache"
    _seed_stale(fake_redis)

    resp = client.post("/caisse/", json=_invoice(patient_id), headers=headers)
    assert resp.status_code == 201
    _assert_cleared(fake_redis)
    assert f"caisse:daily_total:{today}" not in fake_redis.store

    apres = client.get("/caisse/dashboard/caisse/kpis", params=params, headers=headers)
    assert apres.status_code == 200
    assert apres.json()["total_transactions"] == avant.json()["total_transactions"] + 1


def test_paiement_et_annulation_vident_le_cache_kpi(db_session, api_client, fake_redis):
    user = create_test_user(db_session, "kpi_cache_sec2", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "kpi_cache_sec2", TEST_PASSWORD)
    tx_id = client.post("/caisse/", json=_invoice(patient_id), headers=headers).json()["transaction_id"]

    _seed_stale(fake_redis)
    pay = client.post(f"/caisse/{tx_id}/payment", json={"paid_amount": 10.0, "payment_method": "Especes"}, headers=headers)
    assert pay.status_code in (200, 201), pay.text
    _assert_cleared(fake_redis)

    _seed_stale(fake_redis)
    cancel = client.post(f"/caisse/{tx_id}/cancel", json={"cancel_justification": "erreur de saisie"}, headers=headers)
    assert cancel.status_code == 200, cancel.text
    _assert_cleared(fake_redis)


def test_redis_indisponible_ne_bloque_pas_la_vente(db_session, api_client, monkeypatch):
    monkeypatch.setattr(caisse_controller_module, "redis_client", DownRedis())
    user = create_test_user(db_session, "kpi_cache_sec3", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "kpi_cache_sec3", TEST_PASSWORD)
    resp = client.post("/caisse/", json=_invoice(patient_id), headers=headers)
    assert resp.status_code == 201


def test_demande_de_reduction_vide_le_cache_kpi(db_session, fake_redis):
    secretaire = create_test_user(db_session, "kpi_cache_dr_sec", "secretaire")
    manager = create_test_user(db_session, "kpi_cache_dr_mgr", "admin")
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session),
        caisse_repo=CaisseRepository(db_session),
        notification_repo=NotificationRepository(db_session),
        current_user=secretaire,
    )
    _seed_stale(fake_redis)
    ctrl.create_request({
        "payment_method": "Espèces", "transaction_type": "Consultation",
        "amount": 5000, "advance_amount": 0,
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 5000, "quantity": 1, "line_total": 5000}],
    }, requested_to=manager.user_id)
    _assert_cleared(fake_redis)


# --- Revue : rejeu idempotent d'un versement (meme uuid client, meme facture) ---
def _payments(db_session, tx_id):
    from models.paiement_echelonne import PaiementEchelonne
    db_session.expire_all()
    return db_session.query(PaiementEchelonne).filter_by(transaction_id=tx_id).all()


def _advance(db_session, tx_id):
    from models.caisse import Caisse
    db_session.expire_all()
    return float(db_session.get(Caisse, tx_id).advance_amount)


def test_rejeu_d_un_solde_complet_est_idempotent(db_session, api_client, fake_redis):
    import uuid as _uuid
    user = create_test_user(db_session, "replay_sec1", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "replay_sec1", TEST_PASSWORD)
    tx_id = client.post("/caisse/", json=_invoice(patient_id, 100.0, 40.0), headers=headers).json()["transaction_id"]
    body = {"paid_amount": 60.0, "payment_method": "Especes", "payment_type": "SOLDE", "uuid": str(_uuid.uuid4())}

    first = client.post(f"/caisse/{tx_id}/payment", json=body, headers=headers)
    assert first.status_code == 201, first.text
    rows_before = len(_payments(db_session, tx_id))  # l'avance de creation compte deja une ligne
    _seed_stale(fake_redis)
    again = client.post(f"/caisse/{tx_id}/payment", json=body, headers=headers)
    assert again.status_code == 201, again.text
    assert again.json()["payment_id"] == first.json()["payment_id"]
    assert len(_payments(db_session, tx_id)) == rows_before
    assert _advance(db_session, tx_id) == 100.0
    _assert_cleared(fake_redis)


def test_rejeu_d_un_versement_est_idempotent(db_session, api_client, fake_redis):
    import uuid as _uuid
    user = create_test_user(db_session, "replay_sec2", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "replay_sec2", TEST_PASSWORD)
    tx_id = client.post("/caisse/", json=_invoice(patient_id, 100.0, 0.0), headers=headers).json()["transaction_id"]
    body = {"paid_amount": 30.0, "payment_method": "Especes", "uuid": str(_uuid.uuid4())}

    assert client.post(f"/caisse/{tx_id}/payment", json=body, headers=headers).status_code == 201
    assert client.post(f"/caisse/{tx_id}/payment", json=body, headers=headers).status_code == 201
    assert len(_payments(db_session, tx_id)) == 1
    assert _advance(db_session, tx_id) == 30.0


def test_meme_uuid_sur_une_autre_facture_reste_refuse(db_session, api_client, fake_redis):
    import uuid as _uuid
    user = create_test_user(db_session, "replay_sec3", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "replay_sec3", TEST_PASSWORD)
    tx1 = client.post("/caisse/", json=_invoice(patient_id, 100.0, 0.0), headers=headers).json()["transaction_id"]
    tx2 = client.post("/caisse/", json=_invoice(patient_id, 100.0, 0.0), headers=headers).json()["transaction_id"]
    body = {"paid_amount": 10.0, "payment_method": "Especes", "uuid": str(_uuid.uuid4())}
    assert client.post(f"/caisse/{tx1}/payment", json=body, headers=headers).status_code == 201
    other = client.post(f"/caisse/{tx2}/payment", json=body, headers=headers)
    assert other.status_code >= 400
    assert _advance(db_session, tx2) == 0.0
