# tests/test_lab_stock_expenses.py
"""Task 5 (stock labo) : depenses (agregation SQL) et historique de prix.

Base de dev partagee : les receptions de test sont datees dans les annees 1990
(fenetre sans donnees reelles) et filtrees sur cette fenetre ; tout est annule par
le rollback de db_session.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.lab_stock import lab_stock_endpoints
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.lab_stock_controller import LabStockController
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user

EXP = (date.today() + timedelta(days=200)).isoformat()
WIN = {"from": "1995-01-01", "to": "1995-12-31"}


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    u = {r: create_test_user(db, f"t_lsex_{r.lower()}", r)
         for r in ("laborantin", "StockController", "promoteur", "ToxicoManager", "admin")}
    lab = _ctrl(db, u["laborantin"])
    a = lab.create_product({"name": "TEST_LSEX_A"})
    b = lab.create_product({"name": "TEST_LSEX_B"})
    client = api_client(lab_stock_endpoints)
    return {"db": db, "client": client, "u": u, "a": a, "b": b, "n": iter(range(1000))}


def _rc(env, delivery, supplier, lines, invoice=None):
    """lines : [(product_dict, qty, unit_price)] ; cree via le controleur (StockController)."""
    invoice = invoice or f"TEST_LSEX_F{next(env['n'])}"
    return _ctrl(env["db"], env["u"]["StockController"]).create_receipt({
        "invoice_number": invoice, "supplier": supplier, "delivery_date": delivery,
        "lines": [{"product_id": p["id"], "received_qty": q, "unit_price": pr,
                   "lot_number": "L1", "expiry_date": EXP} for p, q, pr in lines]})


def _get(env, url, role="promoteur", **params):
    _as(env["u"][role], role)
    return env["client"].get(url, params=params)


def _d(v):
    return Decimal(str(v))


def test_totals_by_month_and_supplier(env):
    a, b = env["a"], env["b"]
    _rc(env, "1995-03-10", "TEST_LSEX_S1", [(a, 2, "100"), (b, 1, "50.50")])   # 250.50
    _rc(env, "1995-03-25", "TEST_LSEX_S2", [(a, 1, "1000")])                   # 1000
    _rc(env, "1995-05-02", "TEST_LSEX_S1", [(b, 4, "25")])                     # 100
    r = _get(env, "/lab-stock/expenses", **WIN)
    assert r.status_code == 200, r.text
    j = r.json()
    assert _d(j["total"]) == Decimal("1350.50")
    assert [(m["month"], _d(m["total"])) for m in j["by_month"]] == [
        ("1995-03", Decimal("1250.50")), ("1995-05", Decimal("100.00"))]
    assert [(s["supplier"], _d(s["total"])) for s in j["by_supplier"]] == [
        ("TEST_LSEX_S2", Decimal("1000.00")), ("TEST_LSEX_S1", Decimal("350.50"))]


def test_cancelled_receipt_excluded(env):
    a = env["a"]
    keep = _rc(env, "1995-04-01", "TEST_LSEX_S1", [(a, 1, "100")])
    gone = _rc(env, "1995-04-02", "TEST_LSEX_S1", [(a, 1, "700")])
    _ctrl(env["db"], env["u"]["admin"]).cancel_receipt(gone["id"], "erreur")
    j = _get(env, "/lab-stock/expenses", **WIN).json()
    assert _d(j["total"]) == Decimal("100.00")
    assert [(m["month"], _d(m["total"])) for m in j["by_month"]] == [("1995-04", Decimal("100.00"))]
    assert [(s["supplier"], _d(s["total"])) for s in j["by_supplier"]] == [("TEST_LSEX_S1", Decimal("100.00"))]
    ph = _get(env, f"/lab-stock/products/{a['id']}/price-history").json()
    assert [p["receipt_id"] for p in ph if p["delivery_date"].startswith("1995")] == [keep["id"]]


def test_period_without_data_is_zero(env):
    _rc(env, "1995-04-01", "TEST_LSEX_S1", [(env["a"], 1, "100")])
    j = _get(env, "/lab-stock/expenses", **{"from": "1996-01-01", "to": "1996-12-31"}).json()
    assert _d(j["total"]) == 0 and j["by_month"] == [] and j["by_supplier"] == []


def test_period_bounds_inclusive_by_delivery_date(env):
    a = env["a"]
    _rc(env, "1995-01-01", "TEST_LSEX_S1", [(a, 1, "10")])
    _rc(env, "1995-12-31", "TEST_LSEX_S1", [(a, 1, "20")])
    _rc(env, "1996-01-01", "TEST_LSEX_S1", [(a, 1, "40")])
    assert _d(_get(env, "/lab-stock/expenses", **WIN).json()["total"]) == Decimal("30.00")


def test_supplier_case_and_space_grouped_one_name(env):
    a = env["a"]
    _rc(env, "1995-02-01", "Fourn Casse", [(a, 1, "100")])
    _rc(env, "1995-06-01", "  FOURN casse ", [(a, 1, "200")])
    j = _get(env, "/lab-stock/expenses", **WIN).json()
    assert len(j["by_supplier"]) == 1
    s = j["by_supplier"][0]
    assert _d(s["total"]) == Decimal("300.00")
    assert s["supplier"] == "FOURN casse"  # graphie la plus recente (espaces retires a la saisie)


def test_from_after_to_is_422(env):
    r = _get(env, "/lab-stock/expenses", **{"from": "1995-12-31", "to": "1995-01-01"})
    assert r.status_code == 422


def test_default_period_is_last_12_months(env):
    a = env["a"]
    before = _d(_get(env, "/lab-stock/expenses").json()["total"])
    old = date.today() - timedelta(days=800)
    _rc(env, old.isoformat(), "TEST_LSEX_S1", [(a, 1, "999")])          # hors defaut
    _rc(env, date.today().isoformat(), "TEST_LSEX_S1", [(a, 1, "77")])  # dans le defaut
    after = _get(env, "/lab-stock/expenses").json()
    assert _d(after["total"]) - before == Decimal("77.00")
    assert after["from"] <= date.today().isoformat() and after["to"] >= date.today().isoformat()


def test_price_history_sorted_by_date(env):
    a, b = env["a"], env["b"]
    r2 = _rc(env, "1995-08-01", "TEST_LSEX_S2", [(a, 3, "120")])
    r1 = _rc(env, "1995-02-01", "TEST_LSEX_S1", [(a, 5, "100"), (b, 1, "9")])
    r3 = _rc(env, "1995-11-01", "TEST_LSEX_S1", [(a, 2, "150.50")])
    ph = _get(env, f"/lab-stock/products/{a['id']}/price-history").json()
    assert [(p["receipt_id"], p["delivery_date"], p["supplier"], _d(p["unit_price"]), p["received_qty"])
            for p in ph] == [
        (r1["id"], "1995-02-01", "TEST_LSEX_S1", Decimal("100"), 5),
        (r2["id"], "1995-08-01", "TEST_LSEX_S2", Decimal("120"), 3),
        (r3["id"], "1995-11-01", "TEST_LSEX_S1", Decimal("150.50"), 2)]
    assert _get(env, f"/lab-stock/products/{b['id']}/price-history").json()[0]["receipt_id"] == r1["id"]


def test_price_history_unknown_product_404(env):
    assert _get(env, "/lab-stock/products/2147483000/price-history").status_code == 404


@pytest.mark.parametrize("role,code", [("promoteur", 200), ("ToxicoManager", 200), ("admin", 200),
                                       ("laborantin", 403), ("StockController", 403)])
def test_roles(env, role, code):
    pid = env["a"]["id"]
    assert _get(env, "/lab-stock/expenses", role, **WIN).status_code == code
    assert _get(env, f"/lab-stock/products/{pid}/price-history", role).status_code == code
