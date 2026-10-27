# tests/test_pharmacy_barcode.py
"""Code-barres des produits : attribution par la base et recherche par code."""
import re
from unittest.mock import MagicMock

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.pharmacy import pharmacy_endpoints
from models.pharmacy import Pharmacy
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("admin", "Assistant", "secretaire", "StockController", "nurse")


@pytest.fixture(scope="module", autouse=True)
def _no_redis_no_celery():
    mp = pytest.MonkeyPatch()
    mp.setattr("controller.pharmacy_controller.task_check_low_stock_alert", MagicMock())
    mp.setattr("controller.pharmacy_controller.redis_client", MagicMock(get=MagicMock(return_value=None)))
    mp.setattr("controller.patient_controller.redis_client", MagicMock())
    yield
    mp.undo()


@pytest.fixture
def env(db_session, api_client):
    for r in ROLES:
        create_test_user(db_session, f"t_bc_{r.lower()}", r, password=PWD)
    client = api_client(auth_endpoints, pharmacy_endpoints)

    class _Heads(dict):
        def __missing__(self, role):
            self[role] = auth_headers(client, f"t_bc_{role.lower()}", PWD)
            return self[role]

    return {"db": db_session, "client": client, "h": _Heads()}


def _body(name="TEST_BC_PROD"):
    return {"drug_name": name, "quantity": 0, "threshold": 5,
            "medication_type": "pharmaceutique", "forme": "Autre", "price": 3}


def _create(env, name="TEST_BC_PROD", extra=None):
    body = _body(name)
    body.update(extra or {})
    r = env["client"].post("/pharmacy/", json=body, headers=env["h"]["admin"])
    assert r.status_code == 201, r.text
    return r.json()


def test_new_products_get_distinct_barcodes(env):
    a = _create(env)
    b = _create(env)
    assert a["drug_name"] == b["drug_name"]
    assert a["barcode"] != b["barcode"]
    for code in (a["barcode"], b["barcode"]):
        assert re.fullmatch(r"1\d{7}", code)


def test_product_created_outside_pharmacy_repo_gets_barcode(env):
    p = Pharmacy(drug_name="TEST_BC_DIRECT", quantity=1, threshold=0,
                 medication_type="pharmaceutique", forme="Autre", price=1, stock_status="normal")
    env["db"].add(p)
    env["db"].flush()
    env["db"].refresh(p)
    assert re.fullmatch(r"1\d{7}", p.barcode)


def test_by_barcode_returns_product_and_404_for_unknown(env):
    created = _create(env)
    r = env["client"].get(f"/pharmacy/by-barcode/{created['barcode']}", headers=env["h"]["admin"])
    assert r.status_code == 200, r.text
    assert r.json()["medication_id"] == created["medication_id"]
    assert r.json()["barcode"] == created["barcode"]
    r = env["client"].get("/pharmacy/by-barcode/99999999", headers=env["h"]["admin"])
    assert r.status_code == 404


@pytest.mark.parametrize("role,expected", [
    ("secretaire", 200), ("Assistant", 200), ("admin", 200),
    ("StockController", 403), ("nurse", 403),
])
def test_by_barcode_allowed_for_secretaire_and_denied_for_other_roles(env, role, expected):
    created = _create(env)
    r = env["client"].get(f"/pharmacy/by-barcode/{created['barcode']}", headers=env["h"][role])
    assert r.status_code == expected


def test_put_cannot_change_barcode(env):
    created = _create(env)
    r = env["client"].put(f"/pharmacy/{created['medication_id']}",
                          json={"price": 9, "barcode": "10000001"}, headers=env["h"]["admin"])
    assert r.status_code == 200, r.text
    assert r.json()["barcode"] == created["barcode"]
    env["db"].expire_all()
    assert env["db"].get(Pharmacy, created["medication_id"]).barcode == created["barcode"]


def test_post_ignores_barcode_in_payload(env):
    created = _create(env, extra={"barcode": "19999999"})
    assert created["barcode"] != "19999999"
    assert re.fullmatch(r"1\d{7}", created["barcode"])
