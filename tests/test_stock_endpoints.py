# tests/test_stock_endpoints.py
"""Task 5 : routeur /stock par vrais appels HTTP (droits, cablage reel, erreurs, mouvements)."""
from datetime import date, datetime, timedelta

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.stock import stock_endpoints
from controller.stock_controller import StockController
from models.notification import Notification
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from models.stock_reception import ProductionLot
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_repo import StockRepository
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("admin", "Assistant", "StockController", "secretaire", "ToxicoManager", "medecin")
TODAY = date.today().isoformat()


def _ctrl(db, user):
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _product(db, qty=100, name="TEST_EP_PROD"):
    p = Pharmacy(drug_name=name, quantity=qty, threshold=5, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    """Vitesse : env cree 8 comptes par test (183 tests) et chaque bcrypt.hash coute
    ~0,25 s. Un hash bcrypt reste valide pour tout verify() : on calcule UNE fois le
    hash de PWD et on le reutilise. Le login (verify reel) et toutes les assertions
    sont inchanges ; seul create_test_user (tests/conftest.py) est concerne."""
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
    users = {r: create_test_user(db_session, f"t_ep_{r.lower()}", r, password=PWD) for r in ROLES}
    users["author"] = create_test_user(db_session, "t_ep_author", "Assistant", password=PWD)
    users["author_sec"] = create_test_user(db_session, "t_ep_author_sec", "secretaire", password=PWD)
    client = api_client(auth_endpoints, stock_endpoints)
    return {"db": db_session, "client": client, "users": users, "product": _product(db_session)}


def _h(env, key):
    return auth_headers(env["client"], f"t_ep_{key.lower()}", PWD)


# ---------- fabriques d'objets (via le controleur, auteur choisi) ----------
def _lot(env, author, delivered=False):
    c = _ctrl(env["db"], author)
    lot = c.create_lot({"product_id": env["product"].medication_id, "quantity_produced": 20,
                        "production_date": date.today()})
    if delivered:
        lot = c.mark_lot_delivered(lot["id"])
    return lot


def _receipt(env, author):
    return _ctrl(env["db"], author).create_receipt({
        "origin": "fournisseur", "supplier": "ACME", "received_date": date.today(),
        "lines": [{"product_id": env["product"].medication_id, "qty_expected": 10, "qty_good": 10}]})


def _incident(env, author, qty=2):
    return _ctrl(env["db"], author).create_incident({
        "product_id": env["product"].medication_id, "kind": "endommage", "quantity": qty,
        "reason": "casse", "incident_date": date.today()})


def _adjust(env, author, kind="reapprovisionnement", qty=5):
    return _ctrl(env["db"], author).create_adjustment_request({
        "product_id": env["product"].medication_id, "kind": kind, "quantity": qty, "reason": "manque"})


CREATORS = ("Assistant", "admin")


def _author_for(env, role, creators=CREATORS, fallback="author"):
    u = env["users"]
    return u[role] if role in creators else u[fallback]


def _receipt_body(env):
    return {"origin": "fournisseur", "supplier": "ACME", "received_date": TODAY,
            "lines": [{"product_id": env["product"].medication_id, "qty_expected": 5, "qty_good": 5}]}


def _incident_body(env, qty=1):
    return {"product_id": env["product"].medication_id, "kind": "perdu", "quantity": qty,
            "reason": "egare", "incident_date": TODAY}


# route -> (allowed roles, builder(env, role) -> (method, url, json))
ROUTES = {
    "lot_create": (CREATORS, lambda e, r: ("post", "/stock/lots", {
        "product_id": e["product"].medication_id, "quantity_produced": 10, "production_date": TODAY})),
    "lot_list": (CREATORS + ("StockController",), lambda e, r: ("get", "/stock/lots", None)),
    "lot_deliver": (CREATORS, lambda e, r: (
        "post", f"/stock/lots/{_lot(e, _author_for(e, r))['id']}/deliver", {})),
    "lot_cancel": (CREATORS, lambda e, r: (
        "post", f"/stock/lots/{_lot(e, _author_for(e, r))['id']}/cancel", None)),
    "receipt_create": (CREATORS, lambda e, r: ("post", "/stock/receipts", _receipt_body(e))),
    "receipt_list": (CREATORS + ("StockController",), lambda e, r: ("get", "/stock/receipts", None)),
    "receipt_get": (CREATORS + ("StockController",), lambda e, r: (
        "get", f"/stock/receipts/{_receipt(e, _author_for(e, r))['id']}", None)),
    "receipt_lines": (("StockController", "admin"), lambda e, r: _lines_call(e)),
    "receipt_validate": (("StockController", "admin"), lambda e, r: (
        "post", f"/stock/receipts/{_receipt(e, e['users']['author'])['id']}/validate", None)),
    "receipt_reject": (("StockController", "admin"), lambda e, r: (
        "post", f"/stock/receipts/{_receipt(e, e['users']['author'])['id']}/reject", {"reason": "faux"})),
    "receipt_cancel": (CREATORS, lambda e, r: (
        "post", f"/stock/receipts/{_receipt(e, _author_for(e, r))['id']}/cancel", None)),
    "incident_create": (CREATORS, lambda e, r: ("post", "/stock/incidents", _incident_body(e))),
    "incident_list": (CREATORS + ("StockController",), lambda e, r: ("get", "/stock/incidents", None)),
    "incident_validate": (("StockController", "admin"), lambda e, r: (
        "post", f"/stock/incidents/{_incident(e, e['users']['author'])['id']}/validate", None)),
    "incident_reject": (("StockController", "admin"), lambda e, r: (
        "post", f"/stock/incidents/{_incident(e, e['users']['author'])['id']}/reject", {"reason": "non"})),
    "incident_cancel": (CREATORS, lambda e, r: (
        "post", f"/stock/incidents/{_incident(e, _author_for(e, r))['id']}/cancel", None)),
    "adj_create": (("secretaire",), lambda e, r: ("post", "/stock/adjustment-requests", {
        "product_id": e["product"].medication_id, "kind": "correction", "quantity": 7, "reason": "inventaire"})),
    "adj_list": (("secretaire", "admin"), lambda e, r: ("get", "/stock/adjustment-requests", None)),
    "adj_cancel": (("secretaire",), lambda e, r: (
        "post", f"/stock/adjustment-requests/"
                f"{_adjust(e, _author_for(e, r, ('secretaire',), 'author_sec'))['id']}/cancel", None)),
    "adj_approve": (("admin",), lambda e, r: (
        "post", f"/stock/adjustment-requests/{_adjust(e, e['users']['author_sec'])['id']}/approve", None)),
    "adj_reject": (("admin",), lambda e, r: (
        "post", f"/stock/adjustment-requests/{_adjust(e, e['users']['author_sec'])['id']}/reject",
        {"note": "non justifie"})),
    "movements": (("StockController", "admin", "Assistant"), lambda e, r: ("get", "/stock/movements", None)),
}


def _lines_call(e):
    rec = _receipt(e, e["users"]["author"])
    return ("put", f"/stock/receipts/{rec['id']}/lines",
            {"lines": [{"id": rec["lines"][0]["id"], "qty_good": 8, "qty_damaged": 2}]})


def _call(client, method, url, body, headers):
    kw = {"headers": headers}
    if body is not None:
        kw["json"] = body
    return getattr(client, method)(url, **kw)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    allowed, build = ROUTES[route]
    method, url, body = build(env, role)
    r = _call(env["client"], method, url, body, _h(env, role))
    if role in allowed:
        assert 200 <= r.status_code < 300, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_unauthenticated_refused(env, route):
    method, url, body = ROUTES[route][1](env, "admin")
    r = _call(env["client"], method, url, body, {})
    assert r.status_code in (401, 403)


# ---------- (b) cablage reel des notifications ----------
def _notifs(db, user, type_):
    return db.query(Notification).filter_by(recipient_user_id=user.user_id, type=type_).all()


def test_receipt_creation_notifies_checkers_and_decision_notifies_author(env):
    db, u, c = env["db"], env["users"], env["client"]
    r = c.post("/stock/receipts", json=_receipt_body(env), headers=_h(env, "Assistant"))
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert [n.payload["receipt_id"] for n in _notifs(db, u["StockController"], "stock_to_check")] == [rid]
    assert len(_notifs(db, u["admin"], "stock_to_check")) == 1
    assert _notifs(db, u["Assistant"], "stock_to_check") == []
    assert c.post(f"/stock/receipts/{rid}/validate", headers=_h(env, "StockController")).status_code == 200
    dec = _notifs(db, u["Assistant"], "stock_decided")
    assert len(dec) == 1 and dec[0].payload["id"] == rid and dec[0].payload["status"] == "valide"


def test_incident_creation_notifies_and_decision_notifies_author(env):
    db, u, c = env["db"], env["users"], env["client"]
    r = c.post("/stock/incidents", json=_incident_body(env), headers=_h(env, "Assistant"))
    assert r.status_code == 201, r.text
    iid = r.json()["id"]
    assert [n.payload["incident_id"] for n in _notifs(db, u["StockController"], "stock_to_check")] == [iid]
    assert len(_notifs(db, u["admin"], "stock_to_check")) == 1
    assert c.post(f"/stock/incidents/{iid}/reject", json={"reason": "faux"},
                  headers=_h(env, "admin")).status_code == 200
    dec = _notifs(db, u["Assistant"], "stock_decided")
    assert len(dec) == 1 and dec[0].payload["status"] == "rejete" and dec[0].payload["reason"] == "faux"


def test_adjustment_request_notifies_admins_only_and_decision_notifies_author(env):
    db, u, c = env["db"], env["users"], env["client"]
    r = c.post("/stock/adjustment-requests", json={
        "product_id": env["product"].medication_id, "kind": "reapprovisionnement", "quantity": 5,
        "reason": "rupture"}, headers=_h(env, "secretaire"))
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert [n.payload["request_id"] for n in _notifs(db, u["admin"], "stock_adjustment_request")] == [aid]
    assert _notifs(db, u["StockController"], "stock_adjustment_request") == []
    r = c.post(f"/stock/adjustment-requests/{aid}/approve", headers=_h(env, "admin"))
    assert r.status_code == 200, r.text
    assert r.json()["stock_before"] == 100 and r.json()["stock_after"] == 105
    dec = _notifs(db, u["secretaire"], "stock_decided")
    assert len(dec) == 1 and dec[0].payload["status"] == "approuve"


# ---------- (c) erreurs ----------
def test_author_cannot_validate_even_admin(env):
    c = env["client"]
    rid = c.post("/stock/receipts", json=_receipt_body(env), headers=_h(env, "admin")).json()["id"]
    r = c.post(f"/stock/receipts/{rid}/validate", headers=_h(env, "admin"))
    assert r.status_code == 403 and "saisie" in r.json()["detail"]
    iid = c.post("/stock/incidents", json=_incident_body(env), headers=_h(env, "admin")).json()["id"]
    assert c.post(f"/stock/incidents/{iid}/validate", headers=_h(env, "admin")).status_code == 403


def test_double_validation_409_and_insufficient_stock_409(env):
    c = env["client"]
    rec = _receipt(env, env["users"]["author"])
    h = _h(env, "StockController")
    assert c.post(f"/stock/receipts/{rec['id']}/validate", headers=h).status_code == 200
    r = c.post(f"/stock/receipts/{rec['id']}/validate", headers=h)
    assert r.status_code == 409 and "déjà" in r.json()["detail"]
    inc = _incident(env, env["users"]["author"], qty=500)
    r = c.post(f"/stock/incidents/{inc['id']}/validate", headers=h)
    assert r.status_code == 409 and "insuffisant" in r.json()["detail"]


@pytest.mark.parametrize("url,body", [
    ("/stock/incidents", {"quantity": 1_000_001}),
    ("/stock/incidents", {"quantity": -1}),
    ("/stock/incidents", {"quantity": "abc"}),
    ("/stock/incidents", {"kind": "vole"}),
    ("/stock/incidents", {"reason": "   "}),
    ("/stock/incidents", {"incident_date": "20/10/2026"}),
    ("/stock/lots", {"quantity_produced": 10_000_000}),
    ("/stock/receipts", {"origin": "cadeau"}),
    ("/stock/receipts", {"lines": [{"product_id": 1, "qty_good": 2_000_000}]}),
])
def test_invalid_payloads_422(env, url, body):
    base = {"/stock/incidents": _incident_body(env), "/stock/receipts": _receipt_body(env),
            "/stock/lots": {"product_id": env["product"].medication_id, "quantity_produced": 1,
                            "production_date": TODAY}}[url]
    r = env["client"].post(url, json={**base, **body}, headers=_h(env, "admin"))
    assert r.status_code == 422, r.text


def test_reject_with_empty_reason_422(env):
    rec = _receipt(env, env["users"]["author"])
    r = env["client"].post(f"/stock/receipts/{rec['id']}/reject", json={"reason": "  "},
                           headers=_h(env, "admin"))
    assert r.status_code == 422


def test_controller_caps_oversize_quantity(env):
    # un rollback du controleur annule aussi les objets de fixture non commites :
    # on cree d'abord tout ce qui est necessaire, puis un seul echec attendu par controleur.
    adj = _adjust(env, env["users"]["author_sec"])
    with pytest.raises(ValueError):
        _ctrl(env["db"], env["users"]["admin"]).reject_adjustment(adj["id"], 123)
    from controller.stock_controller import _int
    with pytest.raises(ValueError):
        _int(1_000_001, "quantity")
    assert _int(1_000_000, "quantity") == 1_000_000


@pytest.mark.parametrize("method,url,body,role", [
    ("get", "/stock/receipts/99999999", None, "admin"),
    ("post", "/stock/receipts/99999999/validate", None, "admin"),
    ("post", "/stock/receipts/99999999/cancel", None, "admin"),
    ("post", "/stock/incidents/99999999/validate", None, "admin"),
    ("post", "/stock/lots/99999999/deliver", {}, "admin"),
    ("post", "/stock/lots/99999999/cancel", None, "admin"),
    ("post", "/stock/adjustment-requests/99999999/approve", None, "admin"),
    ("post", "/stock/adjustment-requests/99999999/cancel", None, "secretaire"),
])
def test_unknown_id_404(env, method, url, body, role):
    r = _call(env["client"], method, url, body, _h(env, role))
    assert r.status_code == 404, r.text


# ---------- (d) mouvements ----------
def test_movements_history_filters_and_pagination(env):
    db, c = env["db"], env["client"]
    p = env["product"]
    db.add(StockMovement(medication_id=p.medication_id, change_qty=-3, movement_type="VENTE",
                         note="vente test", created_by="t_ep", created_at=datetime.utcnow() - timedelta(minutes=5)))
    db.flush()
    rec = _receipt(env, env["users"]["author"])
    _ctrl(db, env["users"]["StockController"]).validate_receipt(rec["id"])
    h = _h(env, "StockController")
    r = c.get(f"/stock/movements?product_id={p.medication_id}", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2 and body["page"] == 1 and body["per_page"] == 50
    types = [i["movement_type"] for i in body["items"]]
    assert types == ["reception", "VENTE"]  # plus recent d'abord
    item = body["items"][1]
    assert item["product_name"] == "TEST_EP_PROD" and item["change_qty"] == -3
    assert set(item) >= {"movement_id", "product_id", "product_name", "movement_type", "change_qty",
                         "note", "created_by", "created_at"}
    r = c.get(f"/stock/movements?product_id={p.medication_id}&movement_type=VENTE", headers=h).json()
    assert r["total"] == 1 and r["items"][0]["movement_type"] == "VENTE"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = c.get(f"/stock/movements?product_id={p.medication_id}&date_from={tomorrow}", headers=h).json()
    assert r["total"] == 0
    r = c.get(f"/stock/movements?product_id={p.medication_id}&date_from={TODAY}&date_to={TODAY}",
              headers=h).json()
    assert r["total"] == 2
    r = c.get(f"/stock/movements?product_id={p.medication_id}&per_page=1&page=2", headers=h).json()
    assert r["total"] == 2 and len(r["items"]) == 1 and r["items"][0]["movement_type"] == "VENTE"
    assert c.get("/stock/movements?per_page=201", headers=h).status_code == 422
    assert c.get("/stock/movements?page=0", headers=h).status_code == 422


# ---------- (e) P4 : l'Assistant ne voit que ses saisies ----------
def test_assistant_sees_only_own_receipts_and_incidents(env):
    u, c = env["users"], env["client"]
    mine = _receipt(env, u["Assistant"])
    other = _receipt(env, u["author"])
    _incident(env, u["Assistant"])
    other_inc = _incident(env, u["author"])
    h = _h(env, "Assistant")
    ids = [x["id"] for x in c.get("/stock/receipts?mine_only=false", headers=h).json()]
    assert mine["id"] in ids and other["id"] not in ids
    assert all(x["created_by"] == u["Assistant"].user_id for x in c.get("/stock/receipts", headers=h).json())
    inc_ids = [x["id"] for x in c.get("/stock/incidents", headers=h).json()]
    assert other_inc["id"] not in inc_ids and len(inc_ids) >= 1
    assert c.get(f"/stock/receipts/{other['id']}", headers=h).status_code == 403
    assert c.get(f"/stock/receipts/{mine['id']}", headers=h).status_code == 200
    ids = [x["id"] for x in c.get("/stock/receipts", headers=_h(env, "StockController")).json()]
    assert mine["id"] in ids and other["id"] in ids


def test_secretaire_sees_only_own_adjustments_admin_sees_all(env):
    u, c = env["users"], env["client"]
    mine = _adjust(env, u["secretaire"])
    other = _adjust(env, u["author_sec"])
    ids = [x["id"] for x in c.get("/stock/adjustment-requests?mine_only=false",
                                  headers=_h(env, "secretaire")).json()]
    assert mine["id"] in ids and other["id"] not in ids
    ids = [x["id"] for x in c.get("/stock/adjustment-requests", headers=_h(env, "admin")).json()]
    assert mine["id"] in ids and other["id"] in ids


# ---------- (f) parcours complet ----------
def test_full_journey_lot_to_validated_receipt(env):
    db, c = env["db"], env["client"]
    p = env["product"]
    ha, hc = _h(env, "Assistant"), _h(env, "StockController")
    r = c.post("/stock/lots", json={"product_id": p.medication_id, "quantity_produced": 30,
                                    "production_date": TODAY, "producer": "Atelier"}, headers=ha)
    assert r.status_code == 201, r.text
    lot_id = r.json()["id"]
    assert r.json()["status"] == "produit"
    r = c.post(f"/stock/lots/{lot_id}/deliver", json={"delivery_date": TODAY}, headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "livre"
    assert lot_id in [x["id"] for x in c.get("/stock/lots?status=livre", headers=hc).json()]
    r = c.post("/stock/receipts", json={"origin": "fabrication", "production_lot_id": lot_id,
                                        "received_date": TODAY, "lines": [{"qty_good": 30}]}, headers=ha)
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["lines"][0]["qty_expected"] == 30 and rec["lines"][0]["product_id"] == p.medication_id
    r = c.put(f"/stock/receipts/{rec['id']}/lines",
              json={"lines": [{"id": rec["lines"][0]["id"], "qty_good": 27, "qty_damaged": 3}]}, headers=hc)
    assert r.status_code == 200, r.text
    r = c.post(f"/stock/receipts/{rec['id']}/validate", headers=hc)
    assert r.status_code == 200 and r.json()["status"] == "valide"
    db.expire_all()
    assert db.get(Pharmacy, p.medication_id).quantity == 127
    assert db.get(ProductionLot, lot_id).status == "recu"


def test_secretaire_adjustment_correction_approved_by_admin(env):
    db, c = env["db"], env["client"]
    p = env["product"]
    r = c.post("/stock/adjustment-requests", json={"product_id": p.medication_id, "kind": "correction",
                                                   "quantity": 42, "reason": "inventaire"},
               headers=_h(env, "secretaire"))
    assert r.status_code == 201, r.text
    r = c.post(f"/stock/adjustment-requests/{r.json()['id']}/approve", headers=_h(env, "admin"))
    assert r.status_code == 200 and r.json()["status"] == "approuve"
    db.expire_all()
    assert db.get(Pharmacy, p.medication_id).quantity == 42
