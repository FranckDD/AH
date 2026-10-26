"""Releve B : aucun controle ne bloquait un retrait en especes superieur a l'argent de la caisse."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uuid as uuidlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.retrait import retrait_endpoints
from controller.cash_closure_controller import get_cash_closure_controller
from tests.conftest import create_test_user, auth_headers
from tests.cash_closure_isolation import clean_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")

PWD = "Correct123!"


def _env(db_session, api_client, opening=100):
    admin = create_test_user(db_session, "rcg_admin", "admin", password=PWD)
    sec = create_test_user(db_session, "rcg_sec", "secretaire", password=PWD)
    start_at = datetime.now(timezone.utc) - timedelta(hours=2)
    get_cash_closure_controller(db_session, admin, clock=lambda: start_at).set_start(Decimal(opening), start_at)
    client = api_client(auth_endpoints, retrait_endpoints)
    return client, auth_headers(client, "rcg_sec", PWD)


def _post(client, headers, amount, mode="especes", **extra):
    return client.post("/retrait/", json={"amount": amount, "justification": "Test", "payment_method": mode, **extra}, headers=headers)


def test_cash_withdrawal_above_cash_in_till_is_refused(db_session, api_client):
    client, h = _env(db_session, api_client, opening=100)
    r = _post(client, h, 500)
    assert r.status_code == 422, r.text
    assert "caisse" in r.json()["detail"].lower()


def test_cash_withdrawal_within_cash_is_accepted_and_reduces_the_till(db_session, api_client):
    client, h = _env(db_session, api_client, opening=100)
    assert _post(client, h, 60).status_code == 201
    assert _post(client, h, 60).status_code == 422   # il ne reste que 40


def test_mobile_money_withdrawal_is_not_limited_by_cash(db_session, api_client):
    client, h = _env(db_session, api_client, opening=100)
    assert _post(client, h, 5000, mode="orange_money").status_code == 201


def test_offline_replay_with_uuid_is_never_refused(db_session, api_client):
    client, h = _env(db_session, api_client, opening=100)
    assert _post(client, h, 5000, uuid=str(uuidlib.uuid4())).status_code == 201


def test_no_check_when_register_has_no_start(db_session, api_client):
    from tests.cash_closure_isolation import reset_register
    admin = create_test_user(db_session, "rcg_admin2", "admin", password=PWD)
    sec = create_test_user(db_session, "rcg_sec2", "secretaire", password=PWD)
    reset_register(db_session)
    client = api_client(auth_endpoints, retrait_endpoints)
    h = auth_headers(client, "rcg_sec2", PWD)
    assert _post(client, h, 5000).status_code == 201


def test_precheck_endpoint_tells_over_cash_without_revealing_the_figure(db_session, api_client):
    client, h = _env(db_session, api_client, opening=100)
    over = client.get("/retrait/cash-check", params={"amount": 500, "payment_method": "especes"}, headers=h).json()
    ok = client.get("/retrait/cash-check", params={"amount": 50, "payment_method": "especes"}, headers=h).json()
    assert over == {"over_cash": True} and ok == {"over_cash": False}
