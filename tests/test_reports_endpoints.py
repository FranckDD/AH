# tests/test_reports_endpoints.py
"""Rapports (tache 6) : parcours HTTP sur l'application reelle et la vraie fabrique, et
strictesse des entrees. Un seul scenario d'erreur par test (toute erreur du controleur
annule la transaction de test). Jour de test passe et isole : 2021-02-03.
"""
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.reports import reports_endpoints as ep
from models.cash_closure import CashClosure, CashClosureLine
from models.fabrication import FabBatchOutput
from models.stock_count import StockCount, StockCountLine
from repositories.cash_closure_repo import CashClosureRepository
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401
from tests.conftest import create_test_transaction, create_test_user
from tests.test_report_products import _batch, _product, _r

DLA = ZoneInfo("Africa/Douala")
D = date(2021, 2, 3)
DS = D.isoformat()
Q = f"?date_from={DS}&date_to={DS}"
SECTIONS = {"period", "money", "products", "production", "growth", "control"}


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    users = {r: create_test_user(db, _r(f"rpe_{r}"), r) for r in ("promoteur", "admin")}
    users["promoteur"].roles = ["promoteur"]
    users["admin"].roles = ["admin"]
    client = api_client(auth_endpoints, ep)

    def as_(role):
        app.dependency_overrides[auth_endpoints.get_current_user] = lambda: users[role]
        return client
    return {"db": db, "users": users, "as": as_}


def _seed(db, u):
    p = _product(db, name="000_RPE_" + _r())
    # vente : 3 x 100 payee le jour D (paid_at local naif), avance encaissee le jour D
    items = [{"item_type": "Médicament", "item_ref_id": p.medication_id, "unit_price": 100,
              "quantity": 3, "line_total": 300}]
    tx = create_test_transaction(db, u, amount=300, advance_amount=300, items=items)
    db.execute(text("UPDATE caisse SET paid_at=:p WHERE transaction_id=:t"),
               {"p": datetime(2021, 2, 3, 10, 0), "t": tx.transaction_id})
    db.execute(text("UPDATE paiement_echelonne SET received_at=:r WHERE transaction_id=:t"),
               {"r": datetime(2021, 2, 3, 10, 0, tzinfo=DLA), "t": tx.transaction_id})
    # cloture du jour D avec un ecart especes de -20
    c = CashClosure(period_start=datetime(2021, 2, 3, 0, 0, tzinfo=DLA),
                    period_end=datetime(2021, 2, 3, 22, 0, tzinfo=DLA), business_date=D,
                    kind="manual", closed_by=u.user_id, opening_cash=Decimal(0),
                    expected_cash=Decimal("300"), counted_cash=Decimal("280"),
                    difference=Decimal("-20"))
    CashClosureRepository(db).insert_closure(c, [CashClosureLine(
        mode_code="especes", source="physical", opening=0, entries=300, exits=0, expected=300,
        counted=280, difference=-20, comment="caisse")])
    # comptage valide
    sc = StockCount(scope="selection", status="valide", started_by=u.user_id,
                    started_at=datetime(2021, 2, 3, 9, 0), submitted_at=datetime(2021, 2, 3, 9, 30))
    db.add(sc)
    db.flush()
    db.add(StockCountLine(count_id=sc.id, product_id=p.medication_id, counted_qty=1000,
                          previous_qty=1000, difference=0, counted_at=datetime(2021, 2, 3, 9, 10)))
    # sortie 'autre' declaree le jour D (UTC naif)
    nat = _product(db, mtype="Naturel")
    b = _batch(db, u, nat, qty_good=50, finished_at=datetime(2021, 2, 3, 8, 0))
    out = FabBatchOutput(batch_id=b.id, reason="autre", quantity=4, status="active", note="x",
                         declared_by=u.user_id, declared_at=datetime(2021, 2, 3, 9, 0))
    db.add(out)
    db.flush()
    db.expire_all()
    return p, out


@pytest.mark.usefixtures("clean_register")
@pytest.mark.parametrize("role", ["promoteur", "admin"])
def test_full_flow_over_http(env, role):
    p, out = _seed(env["db"], env["users"]["promoteur"])
    c = env["as"](role)

    r = c.get("/reports/overview" + Q)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == SECTIONS
    assert body["period"] == {"from": DS, "to": DS}
    assert body["money"]["collected"]["total"] == "300.00"
    gaps = body["money"]["cash_gaps"]["days"]
    assert [g["difference"] for g in gaps if g["business_date"] == DS] == ["-20.00"]
    assert body["products"]["sold_vs_received"]["sold"] == 3
    assert body["products"]["stock_count"]["id"] == "stock_count"
    assert body["production"]["bottles"]["outputs"]["autre"] == 4
    assert body["control"]["period"] == {"from": DS, "to": DS}
    for section in ("money", "products", "production", "growth"):
        for card in body[section].values():
            assert {"id", "title_key", "period", "source"} <= set(card), (section, card)

    r = c.get("/reports/daily-control" + Q)
    assert r.status_code == 200, r.text
    kinds = {(i["kind"], str(i["ref"])) for i in r.json()["items"]}
    assert ("ecart_caisse", f"{DS}:especes") in kinds
    assert ("sortie_autre", str(out.id)) in kinds

    r = c.get("/reports/products-sold" + Q + "&q=000_RPE_&item_type=Medicament&sort=amount_desc"
              "&limit=10&offset=0")
    assert r.status_code == 200, r.text
    t = r.json()
    rows = [i for i in t["items"] if i["product_id"] == p.medication_id]
    assert rows and rows[0]["quantity"] == 3 and rows[0]["amount"] == "300.00"
    assert t["limit"] == 10 and t["offset"] == 0


def test_settings_admin_writes_and_reads_back(env):
    c = env["as"]("admin")
    r = c.put("/reports/settings", json={"cancelled_sales_threshold": 7, "adjustment_pending_days": 11})
    assert r.status_code == 200, r.text
    g = c.get("/reports/settings").json()
    assert (g["cancelled_sales_threshold"], g["adjustment_pending_days"]) == (7, 11)
    g = env["as"]("promoteur").get("/reports/settings").json()
    assert g["cancelled_sales_threshold"] == 7


def test_settings_promoteur_forbidden(env):
    r = env["as"]("promoteur").put("/reports/settings",
                                   json={"cancelled_sales_threshold": 7, "adjustment_pending_days": 11})
    assert r.status_code == 403


def test_overview_defaults_to_today(env):
    r = env["as"]("promoteur").get("/reports/overview")
    assert r.status_code == 200, r.text
    assert r.json()["period"]["from"] == r.json()["period"]["to"]


@pytest.mark.parametrize("path", ["/reports/overview", "/reports/daily-control", "/reports/products-sold"])
@pytest.mark.parametrize("qs", [
    "?date_from=2021-02-04&date_to=2021-02-03",       # inversee
    "?date_from=2021-01-01&date_to=2022-01-02",       # 367 jours
    "?date_from=03/02/2021",                           # non ISO
    "?date_from=2021-02-30",                           # jour inexistant
])
def test_bad_period_422(env, path, qs):
    r = env["as"]("promoteur").get(path + qs)
    assert r.status_code == 422, r.text


def test_reversed_period_french_message(env):
    r = env["as"]("promoteur").get("/reports/overview?date_from=2021-02-04&date_to=2021-02-03")
    assert r.status_code == 422 and "precede" in r.json()["detail"]


@pytest.mark.parametrize("qs", [
    "limit=0", "limit=201", "offset=-1", "q=" + "a" * 101, "item_type=Bogus", "sort=bogus",
])
def test_products_sold_bad_params_422(env, qs):
    r = env["as"]("promoteur").get(f"/reports/products-sold{Q}&{qs}")
    assert r.status_code == 422, r.text


def test_products_sold_limit_200_ok(env):
    r = env["as"]("promoteur").get(f"/reports/products-sold{Q}&limit=200")
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("body", [
    {"cancelled_sales_threshold": "3", "adjustment_pending_days": 3},
    {"cancelled_sales_threshold": 3.0, "adjustment_pending_days": 3},
    {"cancelled_sales_threshold": True, "adjustment_pending_days": 3},
    {"cancelled_sales_threshold": 0, "adjustment_pending_days": 3},
    {"cancelled_sales_threshold": 1001, "adjustment_pending_days": 3},
    {"cancelled_sales_threshold": 3, "adjustment_pending_days": 366},
    {"cancelled_sales_threshold": 3, "adjustment_pending_days": 0},
    {"cancelled_sales_threshold": 3, "adjustment_pending_days": "3"},
    {"cancelled_sales_threshold": 3, "adjustment_pending_days": False},
    {"cancelled_sales_threshold": 3},
    {"cancelled_sales_threshold": 3, "adjustment_pending_days": 3, "extra": 1},
])
def test_settings_strict_body_422(env, body):
    r = env["as"]("admin").put("/reports/settings", json=body)
    assert r.status_code == 422, r.text


def test_unexpected_error_is_generic_500(env, monkeypatch):
    from controller.reports_controller import ReportsController

    def boom(self):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(ReportsController, "get_settings", boom)
    c = env["as"]("admin")
    r = c.get("/reports/settings")
    assert r.status_code == 500
    assert "secret" not in r.text and "Traceback" not in r.text


def test_period_uses_controller_clock_near_douala_midnight(env):
    # 00:10 a Douala le 2021-02-04 = 23:10 UTC le 2021-02-03 : une horloge UTC dirait le 3
    from datetime import timezone
    from controller.reports_controller import get_reports_controller
    at = datetime(2021, 2, 4, 0, 10, tzinfo=DLA)
    assert at.astimezone(timezone.utc).date() == date(2021, 2, 3)
    db, user = env["db"], env["users"]["promoteur"]
    client = env["as"]("promoteur")
    app.dependency_overrides[ep.get_controller] = lambda: get_reports_controller(db, user, clock=lambda: at)
    try:
        r = client.get("/reports/daily-control")
    finally:
        app.dependency_overrides.pop(ep.get_controller, None)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period"] == {"from": "2021-02-04", "to": "2021-02-04"}
    assert body["recomputed"] == []  # le 4 est "aujourd'hui" pour la meme horloge
