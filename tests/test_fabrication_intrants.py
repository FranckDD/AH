# tests/test_fabrication_intrants.py
"""Fabrication, tache 3 : intrants et achats (routes /fabrication/intrants et /fabrication/purchases).

get_current_user est surcharge avec un vrai utilisateur de la base (pas de limite de connexion).
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from models import AuditUserAction, FabBatch, FabConsumption, FabIntrantPurchase, Pharmacy
from tests.conftest import create_test_user

ROLES = ("ProductionManager", "promoteur", "admin", "medecin", "nurse", "secretaire",
         "StockController", "laborantin")


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    """Vitesse (motif de test_lab_stock_roles.py) : un seul bcrypt.hash reutilise."""
    import tests.conftest as cf
    real = cf.pwd_context
    cache = {}

    class _Ctx:
        def hash(self, pw):
            if pw not in cache:
                cache[pw] = real.hash(pw)
            return cache[pw]

        def __getattr__(self, name):
            return getattr(real, name)

    mp = pytest.MonkeyPatch()
    mp.setattr(cf, "pwd_context", _Ctx())
    yield
    mp.undo()


@pytest.fixture
def env(db_session, api_client):
    users = {r: create_test_user(db_session, _rand(f"t_fi_{r.lower()}"), r) for r in ROLES}
    client = api_client(auth_endpoints, ep)
    return {"db": db_session, "client": client, "users": users}


def _as(env, role):
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    return env["client"]


def _intrant(env, **kw):
    body = {"name": _rand("intr"), "unit": "L"}
    body.update(kw)
    r = _as(env, "ProductionManager").post("/fabrication/intrants", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _purchase(env, intrant_id, qty="60.000", cost="1550.00", **kw):
    body = {"intrant_id": intrant_id, "purchase_date": date.today().isoformat(),
            "quantity": qty, "unit_cost": cost, "supplier": _rand("sup")}
    body.update(kw)
    r = _as(env, "ProductionManager").post("/fabrication/purchases", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _consume(env, purchase_id, qty, restored=False):
    """Pose une consommation directement (le contrat de consommation arrive en tache 4)."""
    db = env["db"]
    prod = Pharmacy(drug_name=_rand("prod"), quantity=0, threshold=0,
                    medication_type="pharmaceutique", forme="Autre")
    db.add(prod)
    db.flush()
    batch = FabBatch(batch_number=_rand("B")[:30], product_id=prod.medication_id,
                     production_date=date.today(), created_by=env["users"]["ProductionManager"].user_id)
    db.add(batch)
    db.flush()
    p = db.get(FabIntrantPurchase, purchase_id)
    p.remaining_qty = p.remaining_qty - Decimal(qty)
    db.add(FabConsumption(batch_id=batch.id, purchase_id=purchase_id, quantity=Decimal(qty),
                          restored_at=None))
    db.flush()


def _stock(env, intrant_id, role="ProductionManager"):
    rows = _as(env, role).get("/fabrication/intrants").json()
    return next(x for x in rows if x["id"] == intrant_id)


def _audits(env, resource_type, resource_id, action):
    return env["db"].query(AuditUserAction).filter_by(
        resource_type=resource_type, resource_id=resource_id, action_performed=action).count()


def test_role_constants():
    assert set(ep.READERS) == {"ProductionManager", "promoteur", "admin"}
    assert set(ep.WRITERS) == {"ProductionManager"}
    assert set(ep.SETTINGS_WRITERS) == {"admin"}


def test_purchase_gives_stock(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    assert Decimal(str(pu["remaining_qty"])) == Decimal("60")
    row = _stock(env, it["id"])
    assert Decimal(str(row["stock"])) == 60
    assert row["below_threshold"] is False
    assert _audits(env, "FabIntrantPurchase", pu["id"], "CREATE") == 1
    assert _audits(env, "FabIntrant", it["id"], "CREATE") == 1


def test_stock_ignores_cancelled_purchases(env):
    it = _intrant(env)
    _purchase(env, it["id"], qty="10")
    p2 = _purchase(env, it["id"], qty="5")
    r = _as(env, "ProductionManager").post(f"/fabrication/purchases/{p2['id']}/cancel",
                                           json={"reason": "erreur de saisie"})
    assert r.status_code == 200, r.text
    assert Decimal(str(_stock(env, it["id"])["stock"])) == 10


def test_update_unconsumed_purchase_ok(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    r = _as(env, "ProductionManager").put(f"/fabrication/purchases/{pu['id']}",
                                          json={"quantity": "40.500", "unit_cost": "100.00"})
    assert r.status_code == 200, r.text
    assert Decimal(str(r.json()["remaining_qty"])) == Decimal("40.5")
    assert Decimal(str(_stock(env, it["id"])["stock"])) == Decimal("40.5")
    assert _audits(env, "FabIntrantPurchase", pu["id"], "UPDATE") == 1


def test_update_consumed_purchase_conflict(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    _consume(env, pu["id"], "10")
    r = _as(env, "ProductionManager").put(f"/fabrication/purchases/{pu['id']}",
                                          json={"quantity": "40"})
    assert r.status_code == 409, r.text


def test_cancel_requires_reason(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    c = _as(env, "ProductionManager")
    for body in ({}, {"reason": ""}, {"reason": "   "}):
        assert c.post(f"/fabrication/purchases/{pu['id']}/cancel", json=body).status_code == 422
    r = c.post(f"/fabrication/purchases/{pu['id']}/cancel", json={"reason": "  doublon  "})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "annule"
    assert r.json()["cancel_reason"] == "doublon"
    assert _audits(env, "FabIntrantPurchase", pu["id"], "CANCEL") == 1
    # deja annule
    assert c.post(f"/fabrication/purchases/{pu['id']}/cancel", json={"reason": "x"}).status_code == 409
    assert c.put(f"/fabrication/purchases/{pu['id']}", json={"supplier": "z"}).status_code == 409


def test_cancel_consumed_purchase_conflict(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    _consume(env, pu["id"], "10")
    r = _as(env, "ProductionManager").post(f"/fabrication/purchases/{pu['id']}/cancel",
                                           json={"reason": "trop tard"})
    assert r.status_code == 409, r.text


@pytest.mark.parametrize("override", [
    {"quantity": "0"}, {"quantity": "-1"}, {"unit_cost": "-0.01"}, {"quantity": "abc"},
    {"quantity": "1.2345"}, {"unit_cost": "1.234"}, {"unexpected": 1},
])
def test_purchase_validation_422(env, override):
    it = _intrant(env)
    body = {"intrant_id": it["id"], "purchase_date": date.today().isoformat(),
            "quantity": "5", "unit_cost": "10"}
    body.update(override)
    r = _as(env, "ProductionManager").post("/fabrication/purchases", json=body)
    assert r.status_code == 422, r.text


def test_purchase_update_validation_422(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    c = _as(env, "ProductionManager")
    assert c.put(f"/fabrication/purchases/{pu['id']}", json={"quantity": "0"}).status_code == 422
    assert c.put(f"/fabrication/purchases/{pu['id']}", json={"unit_cost": "-1"}).status_code == 422
    assert c.put(f"/fabrication/purchases/{pu['id']}", json={}).status_code == 422


def test_purchase_unknown_intrant_404(env):
    r = _as(env, "ProductionManager").post("/fabrication/purchases", json={
        "intrant_id": 999999999, "purchase_date": date.today().isoformat(),
        "quantity": "5", "unit_cost": "10"})
    assert r.status_code == 404, r.text


def test_intrant_validation_and_update(env):
    c = _as(env, "ProductionManager")
    assert c.post("/fabrication/intrants", json={"name": "   ", "unit": "L"}).status_code == 422
    assert c.post("/fabrication/intrants", json={"name": "a", "unit": ""}).status_code == 422
    it = _intrant(env, name="  " + _rand("padded") + "  ")
    assert it["name"] == it["name"].strip()
    r = c.put(f"/fabrication/intrants/{it['id']}", json={"unit": "kg", "is_container": True})
    assert r.status_code == 200, r.text
    assert r.json()["unit"] == "kg" and r.json()["is_container"] is True
    assert _audits(env, "FabIntrant", it["id"], "UPDATE") == 1
    assert c.put("/fabrication/intrants/999999999", json={"unit": "kg"}).status_code == 404
    # le seuil ne passe pas par la creation ni la mise a jour
    assert c.put(f"/fabrication/intrants/{it['id']}", json={"alert_threshold": "5"}).status_code == 422


def test_threshold_admin_only_and_below_threshold(env):
    it = _intrant(env)
    _purchase(env, it["id"], qty="60")
    body = {"value": "200"}
    r = _as(env, "ProductionManager").put(f"/fabrication/intrants/{it['id']}/threshold", json=body)
    assert r.status_code == 403
    r = _as(env, "promoteur").put(f"/fabrication/intrants/{it['id']}/threshold", json=body)
    assert r.status_code == 403
    r = _as(env, "admin").put(f"/fabrication/intrants/{it['id']}/threshold", json=body)
    assert r.status_code == 200, r.text
    assert Decimal(str(r.json()["alert_threshold"])) == 200
    assert _audits(env, "FabIntrant", it["id"], "UPDATE_THRESHOLD") == 1
    row = _stock(env, it["id"], role="admin")
    assert row["below_threshold"] is True
    # seuil negatif refuse
    r = _as(env, "admin").put(f"/fabrication/intrants/{it['id']}/threshold", json={"value": "-1"})
    assert r.status_code == 422
    # seuil sous le stock : plus d'alerte
    _as(env, "admin").put(f"/fabrication/intrants/{it['id']}/threshold", json={"value": "10"})
    assert _stock(env, it["id"])["below_threshold"] is False


def test_threshold_unknown_intrant_404(env):
    r = _as(env, "admin").put("/fabrication/intrants/999999999/threshold", json={"value": "1"})
    assert r.status_code == 404


def test_purchases_list_filter(env):
    it = _intrant(env)
    other = _intrant(env)
    pu = _purchase(env, it["id"])
    _purchase(env, other["id"])
    rows = _as(env, "promoteur").get(f"/fabrication/purchases?intrant_id={it['id']}")
    assert rows.status_code == 200
    assert [x["id"] for x in rows.json()] == [pu["id"]]


def test_editable_intrant_rename_ok(env):
    it = _intrant(env)
    row = _stock(env, it["id"])
    assert row["editable"] is True and row["purchases_count"] == 0
    new_name = _rand("renamed")
    r = _as(env, "ProductionManager").put(f"/fabrication/intrants/{it['id']}",
                                          json={"name": new_name, "unit": "kg", "is_container": True})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == new_name


def test_cancelled_purchase_keeps_intrant_editable(env):
    it = _intrant(env)
    pu = _purchase(env, it["id"])
    _as(env, "ProductionManager").post(f"/fabrication/purchases/{pu['id']}/cancel", json={"reason": "x"})
    row = _stock(env, it["id"])
    assert row["editable"] is True and row["purchases_count"] == 0
    r = _as(env, "ProductionManager").put(f"/fabrication/intrants/{it['id']}", json={"unit": "kg"})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("body", [{"name": "autre nom"}, {"unit": "kg"}, {"is_container": True},
                                  {"name": "x", "is_active": False}])
def test_delivered_intrant_locked_409(env, body):
    it = _intrant(env)
    _purchase(env, it["id"])
    row = _stock(env, it["id"])
    assert row["editable"] is False and row["purchases_count"] == 1
    r = _as(env, "ProductionManager").put(f"/fabrication/intrants/{it['id']}", json=body)
    assert r.status_code == 409, r.text
    assert "deja" in r.json()["detail"]
    again = _stock(env, it["id"])
    assert again["name"] == it["name"] and again["unit"] == "L" and again["is_active"] is True


def test_deactivate_reactivate_before_and_after_delivery(env):
    c = _as(env, "ProductionManager")
    for delivered in (False, True):
        it = _intrant(env)
        if delivered:
            _purchase(env, it["id"])
        r = c.put(f"/fabrication/intrants/{it['id']}", json={"is_active": False})
        assert r.status_code == 200, r.text
        assert r.json()["is_active"] is False
        assert all(x["id"] != it["id"] for x in c.get("/fabrication/intrants").json())
        rows = c.get("/fabrication/intrants?include_inactive=true").json()
        assert any(x["id"] == it["id"] and x["is_active"] is False for x in rows)
        r = c.put(f"/fabrication/intrants/{it['id']}", json={"is_active": True})
        assert r.status_code == 200 and r.json()["is_active"] is True


@pytest.mark.parametrize("role", [r for r in ROLES if r != "ProductionManager"])
def test_activation_writers_only(env, role):
    it = _intrant(env)
    r = _as(env, role).put(f"/fabrication/intrants/{it['id']}", json={"is_active": False})
    assert r.status_code == 403


def test_purchases_date_filter(env):
    it = _intrant(env)
    ids = {d: _purchase(env, it["id"], purchase_date=d)["id"]
           for d in ("2026-01-10", "2026-01-15", "2026-01-20")}
    c = _as(env, "promoteur")

    def got(q):
        r = c.get(f"/fabrication/purchases?intrant_id={it['id']}{q}")
        assert r.status_code == 200, r.text
        return {x["id"] for x in r.json()}
    assert got("&date_from=2026-01-15&date_to=2026-01-20") == {ids["2026-01-15"], ids["2026-01-20"]}
    assert got("&date_from=2026-01-15&date_to=2026-01-15") == {ids["2026-01-15"]}
    assert got("&date_to=2026-01-10") == {ids["2026-01-10"]}
    assert got("") == set(ids.values())
    assert c.get("/fabrication/purchases?date_from=pas-une-date").status_code == 422
    assert c.get("/fabrication/purchases?date_from=2026-02-01&date_to=2026-01-01").status_code == 422


ROUTES = {
    "intrants_list": (ep.READERS, lambda e: ("get", "/fabrication/intrants", None)),
    "purchases_list": (ep.READERS, lambda e: ("get", "/fabrication/purchases", None)),
    "intrants_create": (ep.WRITERS, lambda e: ("post", "/fabrication/intrants",
                                               {"name": _rand("m"), "unit": "L"})),
    "intrants_update": (ep.WRITERS, lambda e: ("put", f"/fabrication/intrants/{e['it']['id']}",
                                               {"is_active": True})),
    "purchases_create": (ep.WRITERS, lambda e: ("post", "/fabrication/purchases", {
        "intrant_id": e["it"]["id"], "purchase_date": date.today().isoformat(),
        "quantity": "1", "unit_cost": "1"})),
    "purchases_update": (ep.WRITERS, lambda e: ("put", f"/fabrication/purchases/{e['pu']['id']}",
                                                {"supplier": "s"})),
    "purchases_cancel": (ep.WRITERS, lambda e: ("post", f"/fabrication/purchases/{e['pu']['id']}/cancel",
                                                {"reason": "r"})),
    "threshold": (ep.SETTINGS_WRITERS, lambda e: ("put", f"/fabrication/intrants/{e['it']['id']}/threshold",
                                                  {"value": "3"})),
}


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    env["it"] = _intrant(env)
    env["pu"] = _purchase(env, env["it"]["id"])
    allowed, build = ROUTES[route]
    method, url, body = build(env)
    client = _as(env, role)
    kw = {} if body is None else {"json": body}
    r = getattr(client, method)(url, **kw)
    if role in allowed:
        assert 200 <= r.status_code < 300, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


def test_unauthenticated_refused(env):
    env["it"] = _intrant(env)
    env["pu"] = _purchase(env, env["it"]["id"])
    app.dependency_overrides.pop(auth_endpoints.get_current_user, None)
    for route in sorted(ROUTES):
        method, url, body = ROUTES[route][1](env)
        kw = {} if body is None else {"json": body}
        r = getattr(env["client"], method)(url, **kw)
        assert r.status_code in (401, 403), (route, r.status_code)
