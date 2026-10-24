# tests/test_cash_closure_endpoints.py
"""Cloture de caisse, tache 5 : endpoints HTTP (comptage a l'aveugle, revelation, garde
double onglet, depart, corrections, modes de paiement, rattrapage).

Horloge injectee (dependance get_clock du routeur) : tout se passe en 2030, jamais sur
l'horloge reelle ; l'etat de caisse est isole par clean_register.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.cash_closure import cash_closure_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.cash_closure_controller import get_cash_closure_controller
from models.cash_closure import CashClosure, CashClosureCorrection
from models.notification import Notification
from tests.conftest import create_test_transaction, create_test_user
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")


UTC = timezone.utc
TZ = ZoneInfo("Africa/Douala")
DAY0 = datetime(2030, 5, 6, 8, 0, tzinfo=TZ)
FORBIDDEN = ("expected", "entries", "exits", "opening")


@pytest.fixture
def env(db_session, api_client):
    users = {}
    for r in ("admin", "promoteur", "secretaire"):
        u = create_test_user(db_session, f"t_ccep_{r}", r)
        u.roles = [normalize_role_name(r)]
        users[r] = u
    client = api_client(auth_endpoints, ep)
    CLOCK.at = DAY0
    app.dependency_overrides[ep.get_clock] = lambda: CLOCK
    return db_session, client, users


class _Clock:
    at = DAY0

    def __call__(self):
        return self.at


CLOCK = _Clock()


def _as(user):
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _start(db, admin, opening=0, now=DAY0 + timedelta(hours=4)):
    """Depart a DAY0, puis l'horloge avance a `now`."""
    get_cash_closure_controller(db, admin, clock=lambda: DAY0).set_start(Decimal(opening))
    CLOCK.at = now


def _sale(db, user, amount, mode="Especes"):
    tx = create_test_transaction(
        db, user, amount=amount, advance_amount=amount, payment_method=mode,
        items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": amount,
                "quantity": 1, "line_total": amount}])
    db.execute(text("UPDATE paiement_echelonne SET received_at = :r WHERE transaction_id = :t"),
               {"r": DAY0 + timedelta(hours=1), "t": tx.transaction_id})
    db.commit()
    return tx


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


def _body(status, especes="0.00", comment=None, last=None):
    counts = [{"mode": m["code"], "counted": especes if m["code"] == "especes" else "0.00"}
              for m in status["modes"]]
    for c in counts:
        if c["mode"] == "especes" and comment:
            c["comment"] = comment
    return {"counts": counts, "last_closed_at": last if last is not None else status["last_closed_at"]}


def _line(detail, mode):
    return next(l for l in detail["lines"] if l["mode"] == mode)


def test_status_is_blind_then_submit_reveals(env):
    db, c, u = env
    _start(db, u["admin"], opening=100)
    _sale(db, u["secretaire"], 500)
    _as(u["secretaire"])
    r = c.get("/cash-closure/status")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["configured"] is True and s["last_closed_at"] is None
    bad = [k for k in _keys(s) if any(w in k.lower() for w in FORBIDDEN)]
    assert not bad, bad
    # avant validation : aucune cloture lisible, aucune notification pour la secretaire
    assert c.get("/cash-closure").json() == []
    assert db.query(Notification).filter_by(type="cash_closure",
                                            recipient_user_id=u["secretaire"].user_id).count() == 0

    r = c.post("/cash-closure", json=_body(s, especes="600.00"))
    assert r.status_code == 201, r.text
    d = r.json()
    esp = _line(d, "especes")
    assert esp["expected"] == "600.00" and esp["counted"] == "600.00" and esp["difference"] == "0.00"
    assert esp["opening"] == "100.00" and esp["entries"] == "500.00"
    assert d["expected_cash"] == "600.00"
    # revelation : lisible apres validation
    g = c.get(f"/cash-closure/{d['id']}")
    assert g.status_code == 200 and _line(g.json(), "especes")["expected"] == "600.00"
    assert [x["id"] for x in c.get("/cash-closure").json()] == [d["id"]]
    # notifications reellement creees par HTTP (fabrique cablee) pour promoteur et admin
    for role in ("promoteur", "admin"):
        n = db.query(Notification).filter_by(type="cash_closure",
                                             recipient_user_id=u[role].user_id).one()
        assert n.payload["closure_id"] == d["id"]
    assert db.query(Notification).filter_by(type="cash_closure",
                                            recipient_user_id=u["secretaire"].user_id).count() == 0
    s2 = c.get("/cash-closure/status").json()
    assert datetime.fromisoformat(s2["last_closed_at"]) == datetime.fromisoformat(d["period_end"])


def test_no_mutation_route_on_closures(env):
    db, c, u = env
    for r in app.routes:
        p = getattr(r, "path", "")
        if p == "/cash-closure" or (p.startswith("/cash-closure/") and "corrections" not in p):
            assert set(r.methods or ()) <= {"GET", "POST", "HEAD"}, (p, r.methods)
    _start(db, u["admin"])
    _as(u["secretaire"])
    s = c.get("/cash-closure/status").json()
    d = c.post("/cash-closure", json=_body(s)).json()
    for m in ("PUT", "PATCH", "DELETE"):
        assert c.request(m, f"/cash-closure/{d['id']}", json={}).status_code in (404, 405)
    _as(u["admin"])
    for m in ("PUT", "PATCH", "DELETE"):
        assert c.request(m, f"/cash-closure/{d['id']}", json={}).status_code in (404, 405)


def test_double_tab_guard(env):
    db, c, u = env
    _start(db, u["admin"])
    _as(u["secretaire"])
    s = c.get("/cash-closure/status").json()
    stale = _body(s)
    assert c.post("/cash-closure", json=stale).status_code == 201
    r = c.post("/cash-closure", json=stale)  # second onglet : last_closed_at encore null
    assert r.status_code == 409 and "entre-temps" in r.json()["detail"]
    CLOCK.at = DAY0 + timedelta(hours=5)
    fresh = c.get("/cash-closure/status").json()
    # meme instant ecrit dans un autre fuseau : accepte
    other_tz = datetime.fromisoformat(fresh["last_closed_at"]).astimezone(
        timezone(timedelta(hours=5))).isoformat()
    assert c.post("/cash-closure", json=_body(fresh, last=other_tz)).status_code == 201
    CLOCK.at = DAY0 + timedelta(hours=6)
    later = c.get("/cash-closure/status").json()
    for bad in ("pas une date", "2030-01-01T10:00:00"):
        assert c.post("/cash-closure", json=_body(later, last=bad)).status_code == 422
    body = _body(later)
    del body["last_closed_at"]
    assert c.post("/cash-closure", json=body).status_code == 422  # champ obligatoire
    assert db.query(CashClosure).count() == 2


def test_strict_counts_schema(env):
    db, c, u = env
    _start(db, u["admin"])
    _as(u["secretaire"])
    s = c.get("/cash-closure/status").json()
    b = _body(s)
    b["counts"][0]["counted"] = 0  # nombre, pas chaine
    assert c.post("/cash-closure", json=b).status_code == 422
    b = _body(s)
    b["extra"] = 1
    assert c.post("/cash-closure", json=b).status_code == 422
    b = _body(s)
    b["counts"][0]["x"] = 1
    assert c.post("/cash-closure", json=b).status_code == 422
    assert db.query(CashClosure).count() == 0


def test_start_admin_once(env):
    db, c, u = env
    _as(u["admin"])
    assert c.get("/cash-closure/status").json()["configured"] is False
    assert c.post("/cash-closure/start", json={"opening_cash": 250}).status_code == 422
    assert c.post("/cash-closure/start", json={"opening_cash": "250", "x": 1}).status_code == 422
    r = c.post("/cash-closure/start", json={"opening_cash": "250.00"})
    assert r.status_code == 201, r.text
    assert r.json()["opening_cash"] == "250.00"
    assert c.post("/cash-closure/start", json={"opening_cash": "1.00"}).status_code == 409
    assert c.get("/cash-closure/status").json()["configured"] is True
    _as(u["promoteur"])
    assert c.post("/cash-closure/start", json={"opening_cash": "1.00"}).status_code == 403


def test_corrections_flow(env):
    db, c, u = env
    _start(db, u["admin"])
    _sale(db, u["secretaire"], 300)
    _as(u["secretaire"])
    s = c.get("/cash-closure/status").json()
    d = c.post("/cash-closure", json=_body(s, especes="250.00", comment="manque")).json()
    url = f"/cash-closure/{d['id']}/corrections"
    for bad in ({"mode_code": "especes", "amount_delta": "0", "reason": "x"},
                {"mode_code": "especes", "amount_delta": "10", "reason": "   "},
                {"mode_code": "especes", "amount_delta": 10, "reason": "x"},
                {"mode_code": "inconnu", "amount_delta": "10", "reason": "x"},
                {"mode_code": "especes", "amount_delta": "1.234", "reason": "x"}):
        assert c.post(url, json=bad).status_code == 422, bad
    assert c.post("/cash-closure/987654321/corrections",
                  json={"mode_code": "especes", "amount_delta": "50", "reason": "x"}).status_code == 404
    r = c.post(url, json={"mode_code": "especes", "amount_delta": "50.00", "reason": "billet retrouve"})
    assert r.status_code == 201, r.text
    corr = r.json()
    assert corr["status"] == "pending" and corr["amount_delta"] == "50.00"
    assert corr["requested_by"] == u["secretaire"].user_id

    _as(u["promoteur"])
    pend = c.get("/cash-closure/corrections", params={"status": "pending"}).json()
    assert corr["id"] in [x["id"] for x in pend]
    assert c.get("/cash-closure/corrections", params={"status": "nope"}).status_code == 422
    r = c.post(f"/cash-closure/corrections/{corr['id']}/decide", json={"approve": True})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert r.json()["decided_by"] == u["promoteur"].user_id
    _as(u["admin"])
    assert c.post(f"/cash-closure/corrections/{corr['id']}/decide",
                  json={"approve": False}).status_code == 409
    assert c.post("/cash-closure/corrections/987654321/decide",
                  json={"approve": False}).status_code == 404
    # la cloture elle-meme n'a pas bouge
    g = c.get(f"/cash-closure/{d['id']}").json()
    assert _line(g, "especes")["counted"] == "250.00" and g["counted_cash"] == "250.00"
    assert db.query(CashClosureCorrection).filter_by(closure_id=d["id"]).count() == 1


def test_payment_modes_admin_write(env):
    db, c, u = env
    _as(u["admin"])
    # Regle 6 : aucune creation de code (liste officielle fixe)
    assert c.post("/payment-modes", json={"code": "wave", "label": "Wave"}).status_code == 405
    assert c.put("/payment-modes/autre_mobile", json={"is_active": False}).status_code == 200
    r = c.put("/payment-modes/orange_money", json={"label": "Orange", "sort_order": 7})
    assert r.status_code == 200 and r.json()["label"] == "Orange"
    assert c.put("/payment-modes/especes", json={"is_active": False}).status_code == 422
    assert c.put("/payment-modes/inconnu", json={"label": "x"}).status_code == 404
    assert c.put("/payment-modes/mtn_money", json={"code": "wave2"}).status_code == 422
    assert c.delete("/payment-modes/mtn_money").status_code == 405
    allm = {m["code"]: m for m in c.get("/payment-modes").json()}
    assert allm["autre_mobile"]["is_active"] is False
    _as(u["secretaire"])
    codes = [m["code"] for m in c.get("/cash-closure/status").json()["modes"]]
    assert "autre_mobile" not in codes and "orange_money" in codes
    assert c.put("/payment-modes/orange_money", json={"label": "x"}).status_code == 403


def test_catchup(env):
    db, c, u = env
    _start(db, u["admin"], now=DAY0 + timedelta(days=3, hours=2))
    _as(u["secretaire"])
    assert len(c.get("/cash-closure/status").json()["overdue_days"]) == 3
    r = c.post("/cash-closure/catchup")
    assert r.status_code == 200, r.text
    out = r.json()
    assert [x["business_date"] for x in out] == [str((DAY0 + timedelta(days=i)).date()) for i in range(3)]
    assert all(x["kind"] == "auto" for x in out)
    assert isinstance(out[0]["expected_cash"], str)
    assert c.post("/cash-closure/catchup").json() == []
    assert c.get("/cash-closure/status").json()["overdue_days"] == []


def test_gap_probe_capped_over_http(env):
    db, c, u = env
    _start(db, u["admin"])
    _sale(db, u["secretaire"], 700)
    _as(u["secretaire"])
    s = c.get("/cash-closure/status").json()
    for _ in range(3):
        r = c.post("/cash-closure", json=_body(s, especes="650.00"))
        assert r.status_code == 422, r.text
        assert "700" not in r.text and "650" not in r.text
    r = c.post("/cash-closure", json=_body(s, especes="650.00"))
    assert r.status_code == 201, r.text
    assert _line(r.json(), "especes")["comment"] == "commentaire non fourni"
    n = db.query(Notification).filter_by(type="cash_closure", recipient_user_id=u["admin"].user_id).one()
    assert n.payload["comment_missing"] is True and n.payload["anomaly"] is True


def test_int_path_params_bounded(env):
    db, c, u = env
    _as(u["admin"])
    for url in ("/cash-closure/2147483648", "/cash-closure/0", "/cash-closure/-1"):
        assert c.get(url).status_code == 422, url
    assert c.post("/cash-closure/corrections/2147483648/decide", json={"approve": True}).status_code == 422
    _as(u["secretaire"])
    assert c.post("/cash-closure/2147483648/corrections",
                  json={"mode_code": "especes", "amount_delta": "1", "reason": "x"}).status_code == 422


def test_correction_applied_to_next_closure_over_http(env):
    db, c, u = env
    _start(db, u["admin"])
    _as(u["secretaire"])
    first = c.post("/cash-closure", json=_body(c.get("/cash-closure/status").json())).json()
    corr = c.post(f"/cash-closure/{first['id']}/corrections",
                  json={"mode_code": "especes", "amount_delta": "75.00", "reason": "oubli"}).json()
    CLOCK.at = DAY0 + timedelta(hours=5)
    _as(u["promoteur"])
    assert c.post(f"/cash-closure/corrections/{corr['id']}/decide", json={"approve": True}).status_code == 200
    CLOCK.at = DAY0 + timedelta(hours=6)
    _as(u["secretaire"])
    s = c.get("/cash-closure/status").json()
    assert not [k for k in _keys(s) if any(w in k.lower() for w in FORBIDDEN)]
    d = c.post("/cash-closure", json=_body(s, especes="75.00")).json()
    esp = _line(d, "especes")
    assert esp["entries"] == "75.00" and esp["expected"] == "75.00" and esp["difference"] == "0.00"
    assert [x["id"] for x in d["corrections_applied"]] == [corr["id"]]
    assert d["corrections_applied"][0]["amount_delta"] == "75.00"
    assert c.get(f"/cash-closure/{first['id']}").json()["corrections_applied"] == []


def test_detail_has_cancellations_and_corrections_over_http(env):
    db, c, u = env
    _start(db, u["admin"])
    tx = _sale(db, u["secretaire"], 300)
    db.execute(text("UPDATE caisse SET status='cancelled', cancelled_at=:c, cancelled_by=:u,"
                    " cancel_justification='erreur' WHERE transaction_id=:t"),
               {"c": (DAY0 + timedelta(hours=2)).astimezone(UTC).replace(tzinfo=None),
                "u": u["secretaire"].user_id, "t": tx.transaction_id})
    db.commit()
    _as(u["secretaire"])
    d = c.post("/cash-closure", json=_body(c.get("/cash-closure/status").json())).json()
    x = d["cancellations"][0]
    assert x["transaction_id"] == tx.transaction_id and x["amount"] == "300.00"
    assert x["justification"] == "erreur" and x["cancelled_by"] == u["secretaire"].user_id
    g = c.get(f"/cash-closure/{d['id']}").json()
    assert g["cancellations"] == d["cancellations"] and g["corrections_applied"] == []
    assert c.get("/cash-closure").json()[0]["cancellations"] == d["cancellations"]
