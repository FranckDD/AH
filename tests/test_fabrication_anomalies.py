# tests/test_fabrication_anomalies.py
"""Fabrication, tache 6 : anomalies, resume, cout par produit, tracabilite (lecture seule).

Tout tourne dans la transaction de test (db_session) : rien ne reste en base.
Les assertions filtrent sur les objets crees par le test (la base peut contenir d'autres lignes).
"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from models import FabBatch, FabIntrant, FabSettings, Pharmacy
from models.stock_reception import ProductionLot, StockReceipt, StockReceiptLine
from tests.conftest import create_test_user


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _as(user):
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _user(db, role):
    u = create_test_user(db, _rand("t_fa"), role)
    u.roles = [normalize_role_name(role)]
    return u


@pytest.fixture
def env(db_session, api_client):
    user = _user(db_session, "ProductionManager")
    client = api_client(auth_endpoints, ep)
    _as(user)
    s = db_session.get(FabSettings, 1)
    if s is None:
        s = FabSettings(id=1, tolerance_pct=Decimal("2.00"), stale_days=7)
        db_session.add(s)
    else:
        s.tolerance_pct = Decimal("2.00")
        s.stale_days = 7
    db_session.flush()
    return {"db": db_session, "c": client, "user": user}


def _product(db):
    p = Pharmacy(drug_name=_rand("prod"), quantity=10, threshold=0,
                 medication_type="Naturel", forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p.medication_id


def _post(env, url, body=None):
    return env["c"].post(url, json=body) if body is not None else env["c"].post(url)


def _intrant(env, container):
    r = _post(env, "/fabrication/intrants", {"name": _rand("i"), "unit": "u", "is_container": container})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _purchase(env, iid, qty, cost):
    r = _post(env, "/fabrication/purchases", {"intrant_id": iid, "purchase_date": date.today().isoformat(),
                                             "quantity": qty, "unit_cost": cost})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _batch(env, product_id=None, liq_cost="1500.00", started=True):
    """Lot brouillon (ou demarre) : 100 contenants a 50, 10 de liquide."""
    pc = _purchase(env, _intrant(env, True), "500", "50.00")
    pl = _purchase(env, _intrant(env, False), "100", liq_cost)
    r = _post(env, "/fabrication/batches", {"product_id": product_id or _product(env["db"]),
                                            "production_date": date.today().isoformat()})
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    r = env["c"].put(f"/fabrication/batches/{bid}", json={"consumptions": [
        {"purchase_id": pc, "quantity": "100"}, {"purchase_id": pl, "quantity": "10"}]})
    assert r.status_code == 200, r.text
    if started:
        assert _post(env, f"/fabrication/batches/{bid}/start").status_code == 200
    return r.json()


def _finish(env, bid, good, damaged=0, rejected=0):
    r = _post(env, f"/fabrication/batches/{bid}/finish",
              {"qty_good": good, "qty_damaged": damaged, "qty_rejected": rejected})
    assert r.status_code == 200, r.text
    return r.json()


def _ship(env, bid, **extra):
    body = {"delivery_date": date.today().isoformat()}
    body.update(extra)
    r = _post(env, f"/fabrication/batches/{bid}/ship", body)
    assert r.status_code == 200, r.text
    return r.json()


def _mine(env, kind, ref):
    r = env["c"].get("/fabrication/anomalies")
    assert r.status_code == 200, r.text
    return [a for a in r.json() if a["kind"] == kind and a["ref"] == ref]


def _backdate(env, bid, days):
    b = env["db"].get(FabBatch, bid)
    b.started_at = datetime.utcnow() - timedelta(days=days)
    env["db"].flush()


def _refs(env):
    return {a["ref"] for a in env["c"].get("/fabrication/anomalies").json()}


# ---------------- etat sain ----------------
def test_healthy_state_no_anomaly(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    out = _ship(env, b["id"])
    assert b["batch_number"] not in _refs(env)
    iid = _intrant(env, False)
    _purchase(env, iid, "10", "1.00")
    env["db"].get(FabIntrant, iid).alert_threshold = Decimal("5")
    env["db"].flush()
    assert env["db"].get(FabIntrant, iid).name not in _refs(env)
    assert out["status"] == "expedie"


# ---------------- hors_tolerance ----------------
def test_hors_tolerance_shipped(env):
    b = _batch(env)
    _finish(env, b["id"], 95)
    _ship(env, b["id"], justification="casse")
    found = _mine(env, "hors_tolerance", b["batch_number"])
    assert len(found) == 1
    d = found[0]["detail"]
    assert d["batch_id"] == b["id"] and d["status"] == "expedie"
    assert Decimal(str(d["missing_pct"])) == Decimal("5.00")


def test_hors_tolerance_finished_not_shipped(env):
    b = _batch(env)
    _finish(env, b["id"], 95)
    assert len(_mine(env, "hors_tolerance", b["batch_number"])) == 1


def test_within_tolerance_no_hors_tolerance(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    assert _mine(env, "hors_tolerance", b["batch_number"]) == []


# ---------------- intrant_sous_seuil ----------------
def test_intrant_sous_seuil_strict(env):
    iid = _intrant(env, False)
    _purchase(env, iid, "3", "1.00")
    row = env["db"].get(FabIntrant, iid)
    row.alert_threshold = Decimal("5")
    env["db"].flush()
    found = _mine(env, "intrant_sous_seuil", row.name)
    assert len(found) == 1
    d = found[0]["detail"]
    assert d["intrant_id"] == iid and Decimal(str(d["stock"])) == Decimal("3")
    assert Decimal(str(d["alert_threshold"])) == Decimal("5")
    row.alert_threshold = Decimal("3")
    env["db"].flush()
    assert _mine(env, "intrant_sous_seuil", row.name) == []


def test_inactive_intrant_ignored(env):
    iid = _intrant(env, False)
    row = env["db"].get(FabIntrant, iid)
    row.alert_threshold = Decimal("5")
    row.is_active = False
    env["db"].flush()
    assert _mine(env, "intrant_sous_seuil", row.name) == []


# ---------------- lot_trop_long ----------------
def test_lot_trop_long_en_production(env):
    b = _batch(env)
    assert _mine(env, "lot_trop_long", b["batch_number"]) == []
    _backdate(env, b["id"], 8)
    found = _mine(env, "lot_trop_long", b["batch_number"])
    assert len(found) == 1 and found[0]["detail"]["status"] == "en_production"
    assert found[0]["detail"]["days"] >= 8


def test_lot_trop_long_termine(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    _backdate(env, b["id"], 30)
    assert len(_mine(env, "lot_trop_long", b["batch_number"])) == 1


def test_lot_trop_long_respects_stale_days(env):
    b = _batch(env)
    _backdate(env, b["id"], 8)
    env["db"].get(FabSettings, 1).stale_days = 10
    env["db"].flush()
    assert _mine(env, "lot_trop_long", b["batch_number"]) == []


def test_lot_trop_long_never_for_shipped_or_cancelled(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    _ship(env, b["id"])
    _backdate(env, b["id"], 60)
    assert _mine(env, "lot_trop_long", b["batch_number"]) == []
    c = _batch(env)
    assert _post(env, f"/fabrication/batches/{c['id']}/cancel", {"reason": "x"}).status_code == 200
    _backdate(env, c["id"], 60)
    assert _mine(env, "lot_trop_long", c["batch_number"]) == []


# ---------------- ecart_expedie_recu ----------------
def _receipt(env, lot_id, product_id, good, status="valide"):
    db = env["db"]
    r = StockReceipt(receipt_number=_rand("REC")[:30], origin="fabrication", production_lot_id=lot_id,
                     received_date=date.today(), status=status, created_by=env["user"].user_id)
    db.add(r)
    db.flush()
    db.add(StockReceiptLine(receipt_id=r.id, product_id=product_id, qty_expected=99, qty_good=good))
    db.flush()
    return r


def test_ecart_expedie_recu(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    out = _ship(env, b["id"])
    assert _mine(env, "ecart_expedie_recu", b["batch_number"]) == []  # pas de reception
    rec = _receipt(env, out["production_lot_id"], b["product_id"], 90, status="a_controler")
    assert _mine(env, "ecart_expedie_recu", b["batch_number"]) == []  # non validee : ignoree
    rec.status = "valide"
    env["db"].flush()
    found = _mine(env, "ecart_expedie_recu", b["batch_number"])
    assert len(found) == 1
    d = found[0]["detail"]
    assert d["qty_good"] == 99 and d["received_good"] == 90 and d["gap"] == 9
    env["db"].refresh(rec)
    assert rec.status == "valide" and rec.lines[0].qty_good == 90  # reception intacte


def test_no_ecart_when_received_matches(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    out = _ship(env, b["id"])
    _receipt(env, out["production_lot_id"], b["product_id"], 99)
    assert _mine(env, "ecart_expedie_recu", b["batch_number"]) == []


def test_ecart_ignores_other_products_lines(env):
    """Une reception melangeant deux produits : seules les lignes du produit du lot comptent."""
    b = _batch(env)
    _finish(env, b["id"], 99)
    out = _ship(env, b["id"])
    other = _product(env["db"])
    rec = _receipt(env, out["production_lot_id"], b["product_id"], 90)
    env["db"].add(StockReceiptLine(receipt_id=rec.id, product_id=other, qty_expected=50, qty_good=50))
    env["db"].flush()
    found = _mine(env, "ecart_expedie_recu", b["batch_number"])
    assert len(found) == 1 and found[0]["detail"]["received_good"] == 90  # l'autre produit ne masque pas l'ecart
    # et inversement : le produit du lot recu en totalite + un autre produit ne cree pas d'ecart
    rec.lines[0].qty_good = 99
    env["db"].flush()
    assert _mine(env, "ecart_expedie_recu", b["batch_number"]) == []


def _declare(env, bid, qty):
    from controller.fabrication_controller import FabricationController
    from repositories.audit_repo import AuditRepository
    from repositories.fabrication_repo import FabricationRepository
    db = env["db"]
    FabricationController(FabricationRepository(db), AuditRepository(db), env["user"]).declare_output(
        bid, "echantillon", qty)


def test_ecart_uses_shipped_quantity_after_outputs(env):
    b = _batch(env)
    _finish(env, b["id"], 100)
    _declare(env, b["id"], 15)
    out = _ship(env, b["id"])
    rec = _receipt(env, out["production_lot_id"], b["product_id"], 85)
    assert _mine(env, "ecart_expedie_recu", b["batch_number"]) == []  # 85 expedie, 85 recu
    rec.lines[0].qty_good = 80
    env["db"].flush()
    found = _mine(env, "ecart_expedie_recu", b["batch_number"])
    assert len(found) == 1
    d = found[0]["detail"]
    assert d["expedie"] == 85 and d["received_good"] == 80 and d["gap"] == 5
    assert d["qty_good"] == 100


def test_ecart_reads_frozen_production_lot_quantity(env):
    """La quantite expediee est celle du lot de production, pas qty_good modifie apres coup."""
    b = _batch(env)
    _finish(env, b["id"], 100)
    out = _ship(env, b["id"])
    _receipt(env, out["production_lot_id"], b["product_id"], 100)
    env["db"].get(FabBatch, b["id"]).qty_good = 120  # alteration hors circuit
    env["db"].flush()
    assert _mine(env, "ecart_expedie_recu", b["batch_number"]) == []


# ---------------- cout par produit ----------------
def test_cost_by_product(env):
    pid = _product(env["db"])
    r = env["c"].get(f"/fabrication/products/{pid}/cost")
    assert r.status_code == 200, r.text
    assert r.json() == {"last_unit_cost": None, "average_unit_cost": None, "batches": 0}
    b1 = _batch(env, pid)                       # cout 20000
    _finish(env, b1["id"], 100)
    assert env["c"].get(f"/fabrication/products/{pid}/cost").json()["batches"] == 0  # non expedie
    o1 = _ship(env, b1["id"])                   # 200.00
    b2 = _batch(env, pid, liq_cost="2500.00")   # 30000 / 100 = 300.00
    _finish(env, b2["id"], 100)
    o2 = _ship(env, b2["id"])
    assert Decimal(str(o1["unit_cost"])) == Decimal("200.00")
    assert Decimal(str(o2["unit_cost"])) == Decimal("300.00")
    r = env["c"].get(f"/fabrication/products/{pid}/cost").json()
    assert r["batches"] == 2
    assert Decimal(str(r["average_unit_cost"])) == Decimal("250.00")
    assert Decimal(str(r["last_unit_cost"])) == Decimal("300.00")


# ---------------- tracabilite ----------------
def test_trace_production_lot(env):
    b = _batch(env)
    _finish(env, b["id"], 99)
    out = _ship(env, b["id"])
    r = env["c"].get(f"/fabrication/trace/production-lot/{out['production_lot_id']}")
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["batch"]["id"] == b["id"] and t["batch"]["batch_number"] == b["batch_number"]
    assert len(t["consumptions"]) == 2
    assert {"intrant_name", "supplier", "purchase_date", "unit_cost"} <= set(t["consumptions"][0])


def test_trace_non_fabrication_lot_404(env):
    db = env["db"]
    lot = ProductionLot(lot_number=_rand("LOT")[:30], product_id=_product(db), quantity_produced=5,
                        production_date=date.today(), status="produit", created_by=env["user"].user_id)
    db.add(lot)
    db.flush()
    assert env["c"].get(f"/fabrication/trace/production-lot/{lot.id}").status_code == 404
    assert env["c"].get("/fabrication/trace/production-lot/999999999").status_code == 404


# ---------------- resume ----------------
def test_summary(env):
    b = _batch(env, started=False)
    r = env["c"].get("/fabrication/summary")
    assert r.status_code == 200, r.text
    s = r.json()
    assert set(s["counts_by_status"]) == {"brouillon", "en_production", "termine", "expedie", "annule"}
    assert s["counts_by_status"]["brouillon"] >= 1
    assert any(x["id"] == b["id"] for x in s["recent_batches"])
    before = s["anomalies_count"]
    _post(env, f"/fabrication/batches/{b['id']}/start")
    _backdate(env, b["id"], 9)
    assert env["c"].get("/fabrication/summary").json()["anomalies_count"] == before + 1


# ---------------- roles ----------------
@pytest.mark.parametrize("role,code", [("ProductionManager", 200), ("promoteur", 200), ("admin", 200),
                                       ("secretaire", 403), ("medecin", 403)])
def test_read_roles(env, role, code):
    _as(_user(env["db"], role))
    for url in ("/fabrication/anomalies", "/fabrication/summary", "/fabrication/products/1/cost"):
        assert env["c"].get(url).status_code == code, url
