# tests/test_stock_products_lookup.py
"""Task 9 (fix) : GET /stock/products - liste minimale {id, name} pour les filtres."""
import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.stock import stock_endpoints
from models.pharmacy import Pharmacy
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ALLOWED = ("StockController", "admin", "Assistant")
DENIED = ("secretaire", "ToxicoManager", "medecin")


def _product(db, name):
    p = Pharmacy(drug_name=name, quantity=7, threshold=5, medication_type="pharmaceutique",
                 forme="Autre", price=1000, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def env(db_session, api_client):
    for r in ALLOWED + DENIED:
        create_test_user(db_session, f"t_lk_{r.lower()}", r, password=PWD)
    b = _product(db_session, "TEST_LK_B")
    a = _product(db_session, "TEST_LK_A")
    client = api_client(auth_endpoints, stock_endpoints)
    return {"client": client, "a": a, "b": b}


# Une connexion par test : /auth/login est limite a 5/minute (limiter remis a zero par test).
@pytest.mark.parametrize("role", ALLOWED)
def test_lookup_allowed_shape_and_order(env, role):
    c = env["client"]
    resp = c.get("/stock/products", headers=auth_headers(c, f"t_lk_{role.lower()}", PWD))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert all(set(x.keys()) == {"id", "name"} for x in body)
    ids = [x["id"] for x in body]
    assert ids.index(env["a"].medication_id) < ids.index(env["b"].medication_id)
    assert {"id": env["a"].medication_id, "name": "TEST_LK_A"} in body


@pytest.mark.parametrize("role", DENIED)
def test_lookup_denied(env, role):
    c = env["client"]
    resp = c.get("/stock/products", headers=auth_headers(c, f"t_lk_{role.lower()}", PWD))
    assert resp.status_code == 403, resp.text


def test_lookup_unauthenticated(env):
    assert env["client"].get("/stock/products").status_code in (401, 403)
