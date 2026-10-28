# tests/test_caisse_offline_paid_at.py
"""Chantier 8, correctif tache 7 : heure d'une vente / d'un versement rejoues depuis la file hors ligne."""
import sys
import os
import uuid as uuidlib
from datetime import datetime, date, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from repositories.caisse_repo import CaisseRepository
from utils import business_time
from utils.business_time import resolve_client_time, ClientTimeError
from tests.conftest import create_test_user, create_test_patient, auth_headers

PWD = "Correct123!"
# 2026-10-28 12:00 UTC = 13:00 a Douala
NOW_UTC = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    monkeypatch.setattr(business_time, "_utc_clock", lambda: NOW_UTC)


@pytest.fixture
def ctx(db_session, api_client):
    user = create_test_user(db_session, "t_offline_paid_at", "secretaire", password=PWD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "t_offline_paid_at", PWD)
    return client, headers, patient_id


def _payload(patient_id, amount=100.0, **extra):
    p = {
        "patient_id": patient_id, "amount": amount, "advance_amount": amount,
        "payment_method": "Especes", "transaction_type": "Consultation",
        "items": [{"item_type": "Service", "item_ref_id": 1, "unit_price": amount,
                   "quantity": 1, "line_total": amount}],
        "uuid": str(uuidlib.uuid4()),
    }
    p.update(extra)
    return p


def _post(ctx, **extra):
    client, headers, patient_id = ctx
    return client.post("/caisse/", json=_payload(patient_id, **extra), headers=headers)


def _paid_at(resp):
    assert resp.status_code == 201, resp.text
    return datetime.fromisoformat(resp.json()["paid_at"])


def test_utc_z_string_is_converted_to_douala(ctx):
    assert _paid_at(_post(ctx, paid_at="2026-10-28T09:00:00.000Z")) == datetime(2026, 10, 28, 10, 0)


def test_explicit_offset_is_converted(ctx):
    assert _paid_at(_post(ctx, paid_at="2026-10-28T09:00:00+00:00")) == datetime(2026, 10, 28, 10, 0)


def test_naive_string_is_taken_as_douala_time(ctx):
    assert _paid_at(_post(ctx, paid_at="2026-10-28T09:00:00")) == datetime(2026, 10, 28, 9, 0)


def test_invalid_string_is_422_with_french_message(ctx):
    r = _post(ctx, paid_at="pas une date")
    assert r.status_code == 422
    assert "invalide" in r.json()["detail"]


def test_future_time_falls_back_to_server_time(ctx):
    # 13:00 Douala maintenant ; 14:00 Douala (= 13:00Z) est dans le futur
    assert _paid_at(_post(ctx, paid_at="2026-10-28T13:00:00Z")) == datetime(2026, 10, 28, 13, 0)


def test_within_future_tolerance_is_kept(ctx):
    assert _paid_at(_post(ctx, paid_at="2026-10-28T12:03:00Z")) == datetime(2026, 10, 28, 13, 3)


def test_older_than_7_days_falls_back_to_server_time(ctx):
    assert _paid_at(_post(ctx, paid_at="2026-10-20T08:00:00Z")) == datetime(2026, 10, 28, 13, 0)


def test_six_days_old_is_kept(ctx):
    assert _paid_at(_post(ctx, paid_at="2026-10-22T08:00:00Z")) == datetime(2026, 10, 22, 9, 0)


def test_absent_uses_business_now(ctx):
    assert _paid_at(_post(ctx)) == datetime(2026, 10, 28, 13, 0)


def test_out_of_bounds_logs_warning_without_personal_data(ctx, caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="utils.business_time"):
        r = _post(ctx, paid_at="2026-10-01T08:00:00Z")
    assert r.status_code == 201
    msgs = [m.getMessage() for m in caplog.records if m.name == "utils.business_time"]
    assert len(msgs) == 1 and r.json()["uuid"] in msgs[0] and "t_offline_paid_at" not in msgs[0]


def test_sale_lands_in_the_right_business_day_late_evening(ctx, db_session):
    """23:30 Douala = 22:30 UTC : meme jour des deux cotes."""
    repo = CaisseRepository(db_session)
    d = date(2026, 10, 27)
    before = repo.get_daily_total(d)
    _paid_at(_post(ctx, amount=777.0, paid_at="2026-10-27T22:30:00Z"))
    assert repo.get_daily_total(d) == before + 777.0


def test_sale_after_midnight_douala_belongs_to_next_day(ctx, db_session):
    """00:30 Douala le 28 = 23:30 UTC le 27 : le jour metier est le 28."""
    repo = CaisseRepository(db_session)
    d27, d28 = date(2026, 10, 27), date(2026, 10, 28)
    b27, b28 = repo.get_daily_total(d27), repo.get_daily_total(d28)
    got = _paid_at(_post(ctx, amount=555.0, paid_at="2026-10-27T23:30:00Z"))
    assert got == datetime(2026, 10, 28, 0, 30)
    assert repo.get_daily_total(d27) == b27
    assert repo.get_daily_total(d28) == b28 + 555.0


def test_installment_payment_date_converted(ctx):
    client, headers, patient_id = ctx
    tx = client.post("/caisse/", json=_payload(patient_id, amount=200.0, advance_amount=50.0), headers=headers).json()
    r = client.post(f"/caisse/{tx['transaction_id']}/payment",
                    json={"paid_amount": 40.0, "payment_method": "Especes",
                          "uuid": str(uuidlib.uuid4()), "payment_date": "2026-10-28T09:00:00.000Z"},
                    headers=headers)
    assert r.status_code == 201, r.text
    assert datetime.fromisoformat(r.json()["payment_date"]) == datetime(2026, 10, 28, 10, 0)


def test_installment_invalid_payment_date_is_422(ctx):
    client, headers, patient_id = ctx
    tx = client.post("/caisse/", json=_payload(patient_id, amount=200.0, advance_amount=50.0), headers=headers).json()
    r = client.post(f"/caisse/{tx['transaction_id']}/payment",
                    json={"paid_amount": 40.0, "payment_method": "Especes", "payment_date": "xx"},
                    headers=headers)
    assert r.status_code == 422


def test_resolve_client_time_unit():
    assert resolve_client_time(None) == datetime(2026, 10, 28, 13, 0)
    assert resolve_client_time("") == datetime(2026, 10, 28, 13, 0)
    with pytest.raises(ClientTimeError):
        resolve_client_time("2026-13-45")
