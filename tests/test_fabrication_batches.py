# tests/test_fabrication_batches.py
"""Fabrication, tache 4 : lots, consommations et transitions jusqu'a termine.

Les tests HTTP tournent dans la transaction de test (db_session).
Le test de concurrence utilise deux vraies sessions sur des donnees commitees,
supprimees en fin de test.
"""
import threading
import time
import uuid
from datetime import date
from decimal import Decimal

import pytest

from api_backend.backend_app.database import SessionLocal
from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.fabrication_controller import FabricationController
from models import (AuditUserAction, FabBatch, FabConsumption, FabIntrant, FabIntrantPurchase,
                    Pharmacy, User)
from repositories.audit_repo import AuditRepository
from repositories.fabrication_repo import FabricationRepository
from tests.conftest import create_test_user


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def env(db_session, api_client):
    user = create_test_user(db_session, _rand("t_fb_pm"), "ProductionManager")
    user.roles = [normalize_role_name("ProductionManager")]
    client = api_client(auth_endpoints, ep)
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    return {"db": db_session, "c": client, "user": user}


def _product(db):
    p = Pharmacy(drug_name=_rand("prod"), quantity=0, threshold=0,
                 medication_type="Naturel", forme="Autre")
    db.add(p)
    db.flush()
    return p.medication_id


def _intrant(env, container=False):
    r = env["c"].post("/fabrication/intrants", json={"name": _rand("intr"), "unit": "u",
                                                     "is_container": container})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _purchase(env, intrant_id, qty="100", cost="10.00"):
    r = env["c"].post("/fabrication/purchases", json={
        "intrant_id": intrant_id, "purchase_date": date.today().isoformat(),
        "quantity": qty, "unit_cost": cost, "supplier": _rand("sup")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _batch(env, items=None):
    r = env["c"].post("/fabrication/batches", json={
        "product_id": _product(env["db"]), "production_date": date.today().isoformat()})
    assert r.status_code == 201, r.text
    b = r.json()
    if items is not None:
        r = env["c"].put(f"/fabrication/batches/{b['id']}", json={"consumptions": items})
        assert r.status_code == 200, r.text
        b = r.json()
    return b


def _ready(env, bottles="120", liquid="60.000"):
    """Lot pret a demarrer : un contenant + un liquide. Retourne (batch, achat contenant, achat liquide)."""
    pc = _purchase(env, _intrant(env, container=True), qty="500", cost="50.00")
    pl = _purchase(env, _intrant(env), qty="100", cost="1550.00")
    b = _batch(env, [{"purchase_id": pc, "quantity": bottles}, {"purchase_id": pl, "quantity": liquid}])
    return b, pc, pl


def _remaining(env, pid):
    env["db"].expire_all()
    return env["db"].get(FabIntrantPurchase, pid).remaining_qty


def _audits(env, bid, action):
    return env["db"].query(AuditUserAction).filter_by(
        resource_type="FabBatch", resource_id=bid, action_performed=action).count()


def test_batches_date_filter(env):
    ids = {}
    for d in ("2026-03-10", "2026-03-15", "2026-03-20"):
        r = env["c"].post("/fabrication/batches", json={"product_id": _product(env["db"]),
                                                        "production_date": d})
        assert r.status_code == 201, r.text
        ids[d] = r.json()["id"]

    def got(q):
        r = env["c"].get(f"/fabrication/batches?{q}")
        assert r.status_code == 200, r.text
        return {x["id"] for x in r.json()} & set(ids.values())
    assert got("date_from=2026-03-15&date_to=2026-03-20") == {ids["2026-03-15"], ids["2026-03-20"]}
    assert got("date_from=2026-03-10&date_to=2026-03-10") == {ids["2026-03-10"]}
    assert got("status=brouillon&date_from=2026-03-11") == {ids["2026-03-15"], ids["2026-03-20"]}
    assert env["c"].get("/fabrication/batches?date_to=31-03-2026").status_code == 422
    assert env["c"].get("/fabrication/batches?date_from=2026-03-20&date_to=2026-03-10").status_code == 422


# ---------------- creation / numerotation ----------------
def test_create_numbers_successive(env):
    b1 = _batch(env)
    b2 = _batch(env)
    year = date.today().year
    assert b1["status"] == "brouillon"
    assert b1["batch_number"].startswith(f"FAB-{year}-")
    n1 = int(b1["batch_number"][-4:])
    assert b2["batch_number"] == f"FAB-{year}-{n1 + 1:04d}"
    assert _audits(env, b1["id"], "CREATE") == 1


def test_create_unknown_product_404(env):
    r = env["c"].post("/fabrication/batches", json={"product_id": 999999999,
                                                    "production_date": date.today().isoformat()})
    assert r.status_code == 404, r.text


def test_list_and_get(env):
    b, _, _ = _ready(env)
    rows = env["c"].get("/fabrication/batches").json()
    assert b["id"] in [x["id"] for x in rows]
    g = env["c"].get(f"/fabrication/batches/{b['id']}").json()
    assert len(g["consumptions"]) == 2
    c0 = g["consumptions"][0]
    for k in ("intrant_name", "purchase_id", "supplier", "purchase_date", "unit_cost", "line_cost"):
        assert k in c0
    # 120 x 50 + 60 x 1550
    assert Decimal(str(g["cost_so_far"])) == Decimal("99000.00")
    assert env["c"].get("/fabrication/batches/999999999").status_code == 404


# ---------------- demarrage ----------------
def test_start_without_consumption_422(env):
    b = _batch(env)
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 422


def test_start_zero_container_422(env):
    pl = _purchase(env, _intrant(env))
    b = _batch(env, [{"purchase_id": pl, "quantity": "5"}])
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 422
    assert _remaining(env, pl) == Decimal("100")


def test_start_two_containers_422(env):
    p1 = _purchase(env, _intrant(env, container=True))
    p2 = _purchase(env, _intrant(env, container=True))
    b = _batch(env, [{"purchase_id": p1, "quantity": "10"}, {"purchase_id": p2, "quantity": "10"}])
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 422
    assert _remaining(env, p1) == Decimal("100")


def test_start_fractional_container_422(env):
    pc = _purchase(env, _intrant(env, container=True))
    b = _batch(env, [{"purchase_id": pc, "quantity": "10.5"}])
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 422


def test_start_over_remaining_422(env):
    pc = _purchase(env, _intrant(env, container=True))
    pl = _purchase(env, _intrant(env), qty="10")
    b = _batch(env, [{"purchase_id": pc, "quantity": "10"}, {"purchase_id": pl, "quantity": "10.001"}])
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 422
    assert _remaining(env, pl) == Decimal("10")
    assert _remaining(env, pc) == Decimal("100")


def test_start_cancelled_purchase_refused(env):
    pc = _purchase(env, _intrant(env, container=True))
    pl = _purchase(env, _intrant(env))
    r = env["c"].post(f"/fabrication/purchases/{pl}/cancel", json={"reason": "x"})
    assert r.status_code == 200
    r = env["c"].put(f"/fabrication/batches/{_batch(env)['id']}",
                     json={"consumptions": [{"purchase_id": pc, "quantity": "1"},
                                            {"purchase_id": pl, "quantity": "1"}]})
    assert r.status_code in (409, 422)


def test_start_ok_reserves_stock(env):
    b, pc, pl = _ready(env)
    r = env["c"].post(f"/fabrication/batches/{b['id']}/start")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "en_production"
    assert out["started_at"] is not None
    assert out["expected_qty"] == 120
    assert _remaining(env, pc) == Decimal("380")
    assert _remaining(env, pl) == Decimal("40")
    cons = env["db"].query(FabConsumption).filter_by(batch_id=b["id"]).all()
    assert all(c.restored_at is None for c in cons)
    snaps = {c.purchase_id: c.unit_cost_snapshot for c in cons}
    assert snaps == {pc: Decimal("50.00"), pl: Decimal("1550.00")}
    assert _audits(env, b["id"], "START") == 1
    # le lot demarre ne repart pas
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 409


def test_decimal_exact(env):
    pc = _purchase(env, _intrant(env, container=True))
    pl = _purchase(env, _intrant(env), qty="1")
    b1 = _batch(env, [{"purchase_id": pc, "quantity": "1"}, {"purchase_id": pl, "quantity": "0.1"}])
    b2 = _batch(env, [{"purchase_id": pc, "quantity": "1"}, {"purchase_id": pl, "quantity": "0.2"}])
    for b in (b1, b2):
        assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 200
    rem = _remaining(env, pl)
    assert rem == Decimal("0.700") and str(rem) == "0.700"
    used = sum(c.quantity for c in env["db"].query(FabConsumption).filter_by(purchase_id=pl))
    assert str(used) == "0.300"


def test_two_batches_same_purchase_no_overconsume(env):
    pc = _purchase(env, _intrant(env, container=True))
    pl = _purchase(env, _intrant(env), qty="10")
    b1 = _batch(env, [{"purchase_id": pc, "quantity": "1"}, {"purchase_id": pl, "quantity": "7"}])
    b2 = _batch(env, [{"purchase_id": pc, "quantity": "1"}, {"purchase_id": pl, "quantity": "7"}])
    assert env["c"].post(f"/fabrication/batches/{b1['id']}/start").status_code == 200
    r = env["c"].post(f"/fabrication/batches/{b2['id']}/start")
    assert r.status_code in (409, 422), r.text
    assert _remaining(env, pl) == Decimal("3")
    assert env["c"].get(f"/fabrication/batches/{b2['id']}").json()["status"] == "brouillon"


# ---------------- edition ----------------
def test_edit_non_draft_409(env):
    b, pc, _ = _ready(env)
    env["c"].post(f"/fabrication/batches/{b['id']}/start")
    r = env["c"].put(f"/fabrication/batches/{b['id']}",
                     json={"consumptions": [{"purchase_id": pc, "quantity": "1"}]})
    assert r.status_code == 409
    assert env["c"].put(f"/fabrication/batches/{b['id']}", json={"producer_name": "x"}).status_code == 409


def test_edit_draft_validation(env):
    b = _batch(env)
    pc = _purchase(env, _intrant(env, container=True))
    c = env["c"]
    for items in ([{"purchase_id": pc, "quantity": "0"}], [{"purchase_id": pc, "quantity": "-1"}],
                  [{"purchase_id": pc, "quantity": "1.0001"}],
                  [{"purchase_id": pc, "quantity": "1"}, {"purchase_id": pc, "quantity": "2"}]):
        assert c.put(f"/fabrication/batches/{b['id']}", json={"consumptions": items}).status_code == 422
    r = c.put(f"/fabrication/batches/{b['id']}",
              json={"consumptions": [{"purchase_id": 999999999, "quantity": "1"}]})
    assert r.status_code == 404
    r = c.put(f"/fabrication/batches/{b['id']}", json={"product_id": 999999999})
    assert r.status_code == 404
    r = c.put(f"/fabrication/batches/{b['id']}", json={"producer_name": "  someone  "})
    assert r.status_code == 200 and r.json()["producer_name"] == "someone"
    assert _audits(env, b["id"], "UPDATE") == 1


# ---------------- fin ----------------
def _started(env):
    b, pc, pl = _ready(env)
    assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 200
    return b, pc, pl


def test_finish_requires_qty_good(env):
    b, _, _ = _started(env)
    r = env["c"].post(f"/fabrication/batches/{b['id']}/finish", json={"qty_damaged": 1})
    assert r.status_code == 422


@pytest.mark.parametrize("field", ["qty_good", "qty_damaged", "qty_rejected", "liquid_lost"])
def test_finish_negative_422(env, field):
    b, _, _ = _started(env)
    body = {"qty_good": 100, field: -1}
    assert env["c"].post(f"/fabrication/batches/{b['id']}/finish", json=body).status_code == 422


def test_finish_found_over_expected_422(env):
    b, _, _ = _started(env)
    r = env["c"].post(f"/fabrication/batches/{b['id']}/finish",
                      json={"qty_good": 118, "qty_damaged": 2, "qty_rejected": 1})
    assert r.status_code == 422


def test_finish_from_draft_409(env):
    b, _, _ = _ready(env)
    assert env["c"].post(f"/fabrication/batches/{b['id']}/finish", json={"qty_good": 1}).status_code == 409


def test_finish_ok_and_reopen(env):
    b, _, _ = _started(env)
    r = env["c"].post(f"/fabrication/batches/{b['id']}/finish",
                      json={"qty_good": 112, "qty_damaged": 3, "qty_rejected": 2, "liquid_lost": "0.500"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "termine" and out["finished_at"] is not None
    assert out["found_qty"] == 117 and out["missing_qty"] == 3
    assert Decimal(str(out["missing_pct"])) == Decimal("2.50")
    assert _audits(env, b["id"], "FINISH") == 1
    r = env["c"].post(f"/fabrication/batches/{b['id']}/reopen")
    assert r.status_code == 200 and r.json()["status"] == "en_production"
    assert _audits(env, b["id"], "REOPEN") == 1


def test_reopen_refused_from_expedie_and_draft(env):
    b, _, _ = _ready(env)
    assert env["c"].post(f"/fabrication/batches/{b['id']}/reopen").status_code == 409
    row = env["db"].get(FabBatch, b["id"])
    row.status = "expedie"
    env["db"].commit()  # savepoint du test : survit au rollback d'un refus
    assert env["c"].post(f"/fabrication/batches/{b['id']}/reopen").status_code == 409
    assert env["c"].post(f"/fabrication/batches/{b['id']}/cancel", json={"reason": "x"}).status_code == 409


# ---------------- annulation ----------------
def test_cancel_in_production_restores(env):
    b, pc, pl = _started(env)
    c = env["c"]
    assert c.post(f"/fabrication/batches/{b['id']}/cancel", json={"reason": "  "}).status_code == 422
    r = c.post(f"/fabrication/batches/{b['id']}/cancel", json={"reason": "panne"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "annule" and r.json()["cancel_reason"] == "panne"
    assert _remaining(env, pc) == Decimal("500")
    assert _remaining(env, pl) == Decimal("100")
    cons = env["db"].query(FabConsumption).filter_by(batch_id=b["id"]).all()
    assert cons and all(x.restored_at is not None for x in cons)
    assert _audits(env, b["id"], "CANCEL") == 1
    # l'achat redevient modifiable
    assert c.put(f"/fabrication/purchases/{pl}", json={"supplier": "z"}).status_code == 200
    assert c.post(f"/fabrication/batches/{b['id']}/cancel", json={"reason": "x"}).status_code == 409


def test_cancel_draft_does_not_touch_stock(env):
    b, pc, pl = _ready(env)
    r = env["c"].post(f"/fabrication/batches/{b['id']}/cancel", json={"reason": "abandon"})
    assert r.status_code == 200
    assert _remaining(env, pl) == Decimal("100")


def test_readers_and_others(env, db_session):
    b = _batch(env)
    for role, code in (("promoteur", 200), ("admin", 200), ("medecin", 403)):
        u = create_test_user(db_session, _rand("t_fb_r"), role)
        u.roles = [normalize_role_name(role)]
        app.dependency_overrides[auth_endpoints.get_current_user] = lambda u=u: u
        assert env["c"].get(f"/fabrication/batches/{b['id']}").status_code == code
        assert env["c"].post(f"/fabrication/batches/{b['id']}/start").status_code == 403


# ---------------- concurrence reelle (deux sessions) ----------------
def test_concurrent_start_locks_purchase():
    """Session A tient le verrou et decremente ; B (autre thread) attend puis voit le restant decremente."""
    s0 = SessionLocal()
    sa = None
    ids = {}
    try:
        user = s0.query(User).filter(User.is_active.is_(True)).order_by(User.user_id).first()
        assert user is not None
        prod = Pharmacy(drug_name=_rand("prod"), quantity=0, threshold=0,
                        medication_type="pharmaceutique", forme="Autre")
        ic = FabIntrant(name=_rand("ic"), unit="u", is_container=True)
        il = FabIntrant(name=_rand("il"), unit="L")
        s0.add_all([prod, ic, il])
        s0.flush()
        pc = FabIntrantPurchase(intrant_id=ic.id, purchase_date=date.today(), quantity=Decimal("50"),
                                unit_cost=Decimal("1"), remaining_qty=Decimal("50"), created_by=user.user_id)
        pl = FabIntrantPurchase(intrant_id=il.id, purchase_date=date.today(), quantity=Decimal("10"),
                                unit_cost=Decimal("1"), remaining_qty=Decimal("10"), created_by=user.user_id)
        s0.add_all([pc, pl])
        s0.flush()
        b2 = FabBatch(batch_number=_rand("CC")[:30], product_id=prod.medication_id,
                      production_date=date.today(), created_by=user.user_id)
        s0.add(b2)
        s0.flush()
        s0.add_all([FabConsumption(batch_id=b2.id, purchase_id=pc.id, quantity=Decimal("1")),
                    FabConsumption(batch_id=b2.id, purchase_id=pl.id, quantity=Decimal("7"))])
        s0.commit()
        ids = {"prod": prod.medication_id, "ic": ic.id, "il": il.id, "pc": pc.id, "pl": pl.id, "b2": b2.id}

        # Session A : verrou + decrement non commite (comme un start en cours)
        sa = SessionLocal()
        ra = FabricationRepository(sa)
        locked = ra.lock_purchase(ids["pl"])
        locked.remaining_qty = locked.remaining_qty - Decimal("7")
        sa.flush()

        result = {}

        def run_b():
            sb = SessionLocal()
            try:
                u = sb.get(User, user.user_id)
                ctrl = FabricationController(FabricationRepository(sb), AuditRepository(sb), u)
                try:
                    result["out"] = ctrl.start_batch(ids["b2"])
                except Exception as e:  # noqa: BLE001
                    result["err"] = e
            finally:
                sb.close()

        t = threading.Thread(target=run_b)
        t.start()
        time.sleep(1.0)
        blocked = t.is_alive()
        sa.commit()
        t.join(timeout=15)
        assert blocked, ("B doit attendre le verrou de A", result)
        assert not t.is_alive()
        assert "out" not in result, result
        assert isinstance(result["err"], ValueError), result

        s0.expire_all()
        assert s0.get(FabIntrantPurchase, ids["pl"]).remaining_qty == Decimal("3")
        assert s0.get(FabIntrantPurchase, ids["pc"]).remaining_qty == Decimal("50")
        assert s0.get(FabBatch, ids["b2"]).status == "brouillon"
    finally:
        if sa is not None:
            sa.rollback()
            sa.close()
        s0.rollback()
        if ids:
            s0.query(AuditUserAction).filter(AuditUserAction.resource_type == "FabBatch",
                                             AuditUserAction.resource_id == ids["b2"]).delete()
            s0.query(FabConsumption).filter(FabConsumption.batch_id == ids["b2"]).delete()
            s0.query(FabBatch).filter(FabBatch.id == ids["b2"]).delete()
            s0.query(FabIntrantPurchase).filter(FabIntrantPurchase.id.in_([ids["pc"], ids["pl"]])).delete()
            s0.query(FabIntrant).filter(FabIntrant.id.in_([ids["ic"], ids["il"]])).delete()
            s0.query(Pharmacy).filter(Pharmacy.medication_id == ids["prod"]).delete()
            s0.commit()
        s0.close()


# ---------------- produit fabricable / intrant desactive ----------------
def test_create_batch_non_natural_product_422(env):
    ph = Pharmacy(drug_name=_rand("pharma"), quantity=0, threshold=0,
                  medication_type="Pharmaceutique", forme="Autre")
    env["db"].add(ph)
    env["db"].flush()
    r = env["c"].post("/fabrication/batches", json={"product_id": ph.medication_id,
                                                    "production_date": date.today().isoformat()})
    assert r.status_code == 422, r.text
    assert "non fabricable" in r.text


def test_update_draft_to_non_natural_product_422(env):
    b = _batch(env)
    ph = Pharmacy(drug_name=_rand("pharma"), quantity=0, threshold=0,
                  medication_type="pharmaceutique", forme="Autre")
    env["db"].add(ph)
    env["db"].flush()
    r = env["c"].put(f"/fabrication/batches/{b['id']}", json={"product_id": ph.medication_id})
    assert r.status_code == 422, r.text
    r = env["c"].put(f"/fabrication/batches/{b['id']}", json={"product_id": 999999999})
    assert r.status_code == 404


def test_draft_refuses_inactive_intrant_purchase(env):
    iid = _intrant(env, container=True)
    pc = _purchase(env, iid)
    assert env["c"].put(f"/fabrication/intrants/{iid}", json={"is_active": False}).status_code == 200
    r = env["c"].put(f"/fabrication/batches/{_batch(env)['id']}",
                     json={"consumptions": [{"purchase_id": pc, "quantity": "1"}]})
    assert r.status_code == 409, r.text
    assert "desactive" in r.text


def test_start_refuses_intrant_deactivated_after_draft(env):
    pc = _purchase(env, _intrant(env, container=True))
    pl = _purchase(env, _intrant(env))
    b = _batch(env, [{"purchase_id": pc, "quantity": "10"}, {"purchase_id": pl, "quantity": "5"}])
    liq = env["db"].get(FabIntrantPurchase, pl).intrant_id
    assert env["c"].put(f"/fabrication/intrants/{liq}", json={"is_active": False}).status_code == 200
    r = env["c"].post(f"/fabrication/batches/{b['id']}/start")
    assert r.status_code == 409, r.text
    assert _remaining(env, pl) == Decimal("100") and _remaining(env, pc) == Decimal("100")


def test_cancel_still_restores_after_intrant_deactivated(env):
    b, pc, pl = _started(env)
    liq = env["db"].get(FabIntrantPurchase, pl).intrant_id
    assert env["c"].put(f"/fabrication/intrants/{liq}", json={"is_active": False}).status_code == 200
    r = env["c"].post(f"/fabrication/batches/{b['id']}/cancel", json={"reason": "x"})
    assert r.status_code == 200, r.text
    assert _remaining(env, pl) == Decimal("100")


def test_purchases_list_exposes_intrant_active(env):
    iid = _intrant(env)
    _purchase(env, iid)
    assert env["c"].put(f"/fabrication/intrants/{iid}", json={"is_active": False}).status_code == 200
    rows = [p for p in env["c"].get("/fabrication/purchases").json() if p["intrant_id"] == iid]
    assert rows and rows[0]["intrant_active"] is False


def test_list_batches_has_product_name_even_if_not_fabricable(env):
    ph = Pharmacy(drug_name=_rand("pharma"), quantity=0, threshold=0,
                  medication_type="Pharmaceutique", forme="Autre")
    env["db"].add(ph)
    env["db"].flush()
    fb = FabBatch(batch_number=_rand("PN")[:30], product_id=ph.medication_id,
                  production_date=date.today(), created_by=env["user"].user_id)
    env["db"].add(fb)
    env["db"].flush()
    rows = env["c"].get("/fabrication/batches").json()
    row = next(r for r in rows if r["id"] == fb.id)
    assert row["product_name"] == ph.drug_name
