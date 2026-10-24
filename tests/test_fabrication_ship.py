# tests/test_fabrication_ship.py
"""Fabrication, tache 5 : bilan fige, expedition, raccord au circuit lot -> reception existant.

Tout tourne dans la transaction de test (db_session) : rien ne reste en base.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.stock_controller import StockController
from models import AuditUserAction, FabBatch, FabSettings, Pharmacy
from models.stock_reception import ProductionLot
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_repo import StockRepository
from tests.conftest import create_test_user
from utils.fabrication_rules import compute_bilan


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _as(user):
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _user(db, role):
    u = create_test_user(db, _rand("t_fs"), role)
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


def _finished(env, good, damaged=0, rejected=0):
    """Lot termine : 100 contenants a 50, 10 de liquide a 1500 (cout 20000)."""
    pc = _purchase(env, _intrant(env, True), "500", "50.00")
    pl = _purchase(env, _intrant(env, False), "100", "1500.00")
    r = _post(env, "/fabrication/batches", {"product_id": _product(env["db"]),
                                            "production_date": date.today().isoformat()})
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    r = env["c"].put(f"/fabrication/batches/{bid}", json={"consumptions": [
        {"purchase_id": pc, "quantity": "100"}, {"purchase_id": pl, "quantity": "10"}]})
    assert r.status_code == 200, r.text
    assert _post(env, f"/fabrication/batches/{bid}/start").status_code == 200
    r = _post(env, f"/fabrication/batches/{bid}/finish",
              {"qty_good": good, "qty_damaged": damaged, "qty_rejected": rejected})
    assert r.status_code == 200, r.text
    return r.json()


def _ship(env, bid, **extra):
    body = {"delivery_date": date.today().isoformat()}
    body.update(extra)
    return _post(env, f"/fabrication/batches/{bid}/ship", body)


# ---------------- regle pure ----------------
def test_bilan_compares_unrounded_pct():
    # 2001 / 100000 = 2.001 % : arrondi a 2.00 mais strictement hors tolerance 2
    b = compute_bilan(100000, 97999, 0, 0, Decimal("2"))
    assert b["missing"] == 2001
    assert b["out_of_tolerance"] is True
    assert compute_bilan(100000, 98000, 0, 0, Decimal("2"))["out_of_tolerance"] is False


# ---------------- expedition ----------------
def test_ship_within_tolerance_freezes_everything(env):
    b = _finished(env, 98, damaged=1)  # manque 1 %
    exp = date.today() + timedelta(days=365)
    r = _ship(env, b["id"], expiry_date=exp.isoformat())
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "expedie"
    assert out["expected_qty"] == 100 and out["found_qty"] == 99 and out["missing_qty"] == 1
    assert Decimal(str(out["missing_pct"])) == Decimal("1.00")
    assert Decimal(str(out["tolerance_applied"])) == Decimal("2.00")
    assert out["out_of_tolerance"] is False
    assert Decimal(str(out["total_cost"])) == Decimal("20000.00")
    assert Decimal(str(out["unit_cost"])) == Decimal("204.08")
    assert out["expedited_at"] is not None and out["expedited_by"] == env["user"].user_id
    assert "consumptions" in out
    lot = env["db"].get(ProductionLot, out["production_lot_id"])
    assert lot.status == "produit"
    assert lot.product_id == b["product_id"]
    assert lot.quantity_produced == 98
    assert lot.producer == (env["user"].full_name or env["user"].username)
    assert lot.expiry_date == exp and lot.delivery_date == date.today()
    assert lot.lot_number.startswith(f"LOT-{date.today():%Y%m%d}-")
    # fiche du lot : numero du lot de production et nom du produit fini
    detail = env["c"].get(f"/fabrication/batches/{b['id']}").json()
    assert detail["production_lot_number"] == lot.lot_number
    assert detail["product_name"] == env["db"].get(Pharmacy, b["product_id"]).drug_name
    assert env["db"].query(AuditUserAction).filter_by(
        resource_type="FabBatch", resource_id=b["id"], action_performed="SHIP").count() == 1
    assert env["db"].query(AuditUserAction).filter_by(
        resource_type="ProductionLot", resource_id=lot.id, action_performed="CREATE").count() == 1


@pytest.mark.parametrize("just", [None, "", "   "])
def test_ship_out_of_tolerance_requires_justification(env, just):
    b = _finished(env, 95)  # manque 5 %
    extra = {} if just is None else {"justification": just}
    r = _ship(env, b["id"], **extra)
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "justification_required" and detail["message"]
    env["db"].expire_all()
    row = env["db"].get(FabBatch, b["id"])
    assert row.status == "termine" and row.production_lot_id is None


def test_ship_out_of_tolerance_with_justification(env):
    b = _finished(env, 95)
    r = _ship(env, b["id"], justification="  casse au transport  ")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["out_of_tolerance"] is True and out["justification"] == "casse au transport"
    # changer la tolerance globale ne touche pas un lot expedie
    _as(_user(env["db"], "admin"))
    r = env["c"].put("/fabrication/settings", json={"tolerance_pct": "10.00", "stale_days": 7})
    assert r.status_code == 200, r.text
    g = env["c"].get(f"/fabrication/batches/{b['id']}").json()
    assert Decimal(str(g["tolerance_applied"])) == Decimal("2.00")
    assert g["out_of_tolerance"] is True


def test_unshipped_batch_has_no_production_lot_number(env):
    b = _finished(env, 98)
    detail = env["c"].get(f"/fabrication/batches/{b['id']}").json()
    assert detail["production_lot_number"] is None
    assert detail["product_name"] == env["db"].get(Pharmacy, b["product_id"]).drug_name


def test_ship_uses_current_tolerance(env):
    b = _finished(env, 95)
    env["db"].get(FabSettings, 1).tolerance_pct = Decimal("6.00")
    env["db"].flush()
    r = _ship(env, b["id"])
    assert r.status_code == 200, r.text
    assert Decimal(str(r.json()["tolerance_applied"])) == Decimal("6.00")
    assert r.json()["out_of_tolerance"] is False


def test_ship_zero_good_422(env):
    b = _finished(env, 0, damaged=99)
    assert _ship(env, b["id"], justification="x").status_code == 422


def test_ship_requires_delivery_date(env):
    b = _finished(env, 99)
    assert _post(env, f"/fabrication/batches/{b['id']}/ship", {}).status_code == 422


def test_expedie_is_frozen(env):
    b = _finished(env, 99)
    assert _ship(env, b["id"]).status_code == 200
    bid = b["id"]
    assert _ship(env, bid).status_code == 409
    assert _post(env, f"/fabrication/batches/{bid}/reopen").status_code == 409
    assert _post(env, f"/fabrication/batches/{bid}/cancel", {"reason": "x"}).status_code == 409
    assert _post(env, f"/fabrication/batches/{bid}/start").status_code == 409
    assert _post(env, f"/fabrication/batches/{bid}/finish", {"qty_good": 1}).status_code == 409
    assert env["c"].put(f"/fabrication/batches/{bid}", json={"producer_name": "x"}).status_code == 409
    assert env["db"].query(ProductionLot).filter_by(product_id=b["product_id"]).count() == 1


def test_ship_from_non_termine_409(env):
    r = _post(env, "/fabrication/batches", {"product_id": _product(env["db"]),
                                            "production_date": date.today().isoformat()})
    assert _ship(env, r.json()["id"]).status_code == 409
    assert _ship(env, 999999999).status_code == 404


def test_ship_role_guard(env):
    b = _finished(env, 99)
    for role in ("admin", "promoteur"):
        _as(_user(env["db"], role))
        assert _ship(env, b["id"]).status_code == 403


# ---------------- sorties declarees ----------------
def _fctrl(env):
    from controller.fabrication_controller import FabricationController
    from repositories.fabrication_repo import FabricationRepository
    db = env["db"]
    return FabricationController(FabricationRepository(db), AuditRepository(db), env["user"])


def test_ship_deducts_active_outputs(env):
    b = _finished(env, 100)
    ctrl = _fctrl(env)
    ctrl.declare_output(b["id"], "echantillon", 12)
    ctrl.declare_output(b["id"], "autre", 3, "don")
    r = _ship(env, b["id"])
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["qty_outputs"] == 15 and out["qty_shipped"] == 85
    lot = env["db"].get(ProductionLot, out["production_lot_id"])
    assert lot.quantity_produced == 85
    # bilan et cout inchanges : calcules sur les 100 bonnes
    assert out["expected_qty"] == 100 and out["found_qty"] == 100 and out["missing_qty"] == 0
    assert out["out_of_tolerance"] is False
    assert Decimal(str(out["total_cost"])) == Decimal("20000.00")
    assert Decimal(str(out["unit_cost"])) == Decimal("200.00")
    audit = env["db"].query(AuditUserAction).filter_by(
        resource_type="FabBatch", resource_id=b["id"], action_performed="SHIP").one()
    assert audit.new_values["qty_shipped"] == 85
    lot_audit = env["db"].query(AuditUserAction).filter_by(
        resource_type="ProductionLot", resource_id=lot.id, action_performed="CREATE").one()
    assert lot_audit.new_values["quantity_produced"] == 85


def test_ship_without_output_unchanged(env):
    b = _finished(env, 100)
    out = _ship(env, b["id"]).json()
    assert out["qty_outputs"] == 0 and out["qty_shipped"] == 100
    assert env["db"].get(ProductionLot, out["production_lot_id"]).quantity_produced == 100
    assert Decimal(str(out["unit_cost"])) == Decimal("200.00")


def test_ship_cancelled_output_not_deducted(env):
    b = _finished(env, 100)
    ctrl = _fctrl(env)
    o = ctrl.declare_output(b["id"], "echantillon", 12)
    ctrl.cancel_output(b["id"], o["id"], "erreur")
    ctrl.declare_output(b["id"], "echantillon", 2)
    out = _ship(env, b["id"]).json()
    assert env["db"].get(ProductionLot, out["production_lot_id"]).quantity_produced == 98


def test_ship_all_bottles_out_refused(env):
    b = _finished(env, 100)
    _fctrl(env).declare_output(b["id"], "echantillon", 100)
    before = env["db"].query(ProductionLot).filter_by(product_id=b["product_id"]).count()
    r = _ship(env, b["id"])
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == "Toutes les bouteilles sont sorties : rien a expedier."
    env["db"].expire_all()
    row = env["db"].get(FabBatch, b["id"])
    assert row.status == "termine" and row.production_lot_id is None
    assert env["db"].query(ProductionLot).filter_by(product_id=b["product_id"]).count() == before == 0


def test_ship_zero_good_message_unchanged(env):
    b = _finished(env, 0, damaged=99)
    r = _ship(env, b["id"], justification="x")
    assert r.status_code == 422 and r.json()["detail"] == "Aucune bouteille bonne : rien a expedier."


def test_bilan_same_with_or_without_outputs(env):
    a = _finished(env, 95)
    b = _finished(env, 95)
    _fctrl(env).declare_output(b["id"], "echantillon", 10)
    oa = _ship(env, a["id"], justification="casse").json()
    ob = _ship(env, b["id"], justification="casse").json()
    for k in ("expected_qty", "found_qty", "missing_qty", "missing_pct", "tolerance_applied",
              "out_of_tolerance", "total_cost", "unit_cost"):
        assert oa[k] == ob[k], k
    assert oa["missing_qty"] == 5 and oa["out_of_tolerance"] is True
    assert ob["qty_shipped"] == 85 and oa["qty_shipped"] == 95


def test_reopen_refused_with_active_output_then_allowed(env):
    b = _finished(env, 100)
    ctrl = _fctrl(env)
    o = ctrl.declare_output(b["id"], "echantillon", 5)
    r = _post(env, f"/fabrication/batches/{b['id']}/reopen")
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "Annulez d'abord les sorties declarees."
    env["db"].expire_all()
    assert env["db"].get(FabBatch, b["id"]).status == "termine"
    ctrl.cancel_output(b["id"], o["id"], "erreur")
    r = _post(env, f"/fabrication/batches/{b['id']}/reopen")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "en_production"


# ---------------- reglages ----------------
def test_settings_get_and_put_guards(env):
    for role in ("ProductionManager", "promoteur", "admin"):
        _as(_user(env["db"], role))
        r = env["c"].get("/fabrication/settings")
        assert r.status_code == 200, r.text
        assert {"tolerance_pct", "stale_days"} <= set(r.json())
    body = {"tolerance_pct": "3.50", "stale_days": 10}
    for role in ("ProductionManager", "promoteur"):
        _as(_user(env["db"], role))
        assert env["c"].put("/fabrication/settings", json=body).status_code == 403
    admin = _user(env["db"], "admin")
    _as(admin)
    r = env["c"].put("/fabrication/settings", json=body)
    assert r.status_code == 200, r.text
    assert Decimal(str(r.json()["tolerance_pct"])) == Decimal("3.50") and r.json()["stale_days"] == 10
    assert r.json()["updated_by"] == admin.user_id
    for bad in ({"tolerance_pct": "-1", "stale_days": 7}, {"tolerance_pct": "2", "stale_days": 0},
                {"tolerance_pct": "2", "stale_days": -3}, {"tolerance_pct": "2"}):
        assert env["c"].put("/fabrication/settings", json=bad).status_code == 422


# ---------------- non-regression du circuit existant ----------------
def test_existing_circuit_receives_shipped_lot(env):
    b = _finished(env, 97, damaged=2)
    out = _ship(env, b["id"]).json()
    db = env["db"]
    pid = b["product_id"]
    before = db.get(Pharmacy, pid).quantity

    def ctrl(u):
        return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), u)

    author = create_test_user(db, _rand("t_fs_as"), "Assistant")
    checker = create_test_user(db, _rand("t_fs_sc"), "StockController")
    lot = ctrl(author).mark_lot_delivered(out["production_lot_id"], date.today())
    assert lot["status"] == "livre"
    rec = ctrl(author).create_receipt({"origin": "fabrication", "production_lot_id": lot["id"],
                                       "received_date": date.today(), "lines": [{"qty_good": 97}]})
    assert rec["lines"][0]["qty_expected"] == 97
    ctrl(checker).validate_receipt(rec["id"])
    db.expire_all()
    assert db.get(ProductionLot, lot["id"]).status == "recu"
    assert db.get(Pharmacy, pid).quantity == before + 97
