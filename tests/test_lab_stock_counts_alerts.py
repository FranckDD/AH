# tests/test_lab_stock_counts_alerts.py
"""Task 4 (stock labo) : comptage, alertes (seuil, peremption, rappel) et historique."""
from datetime import date, datetime, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.lab_stock import lab_stock_endpoints
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.lab_stock_controller import LabStockController, LabStockCountConflictError
from models.lab_stock import LabStockCountLine, LabStockMovement, LabStockProduct, LabStockRequest
from models.notification import Notification
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user

TODAY = date.today()


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    u = {
        "lab": create_test_user(db, "t_lsca_lab", "laborantin"),
        "ctl": create_test_user(db, "t_lsca_ctl", "StockController"),
        "promo": create_test_user(db, "t_lsca_promo", "promoteur"),
        "admin": create_test_user(db, "t_lsca_admin", "admin"),
    }
    lab = _ctrl(db, u["lab"])
    a = lab.create_product({"name": "TEST_LSCA_A", "alert_threshold": 5})
    b = lab.create_product({"name": "TEST_LSCA_B", "alert_threshold": 0})
    client = api_client(lab_stock_endpoints)
    return {"db": db, "client": client, "u": u, "a": a, "b": b, "lab": lab}


def _qty(db, pid):
    db.expire_all()
    return db.get(LabStockProduct, pid).quantity


def _receive(env, pid, qty, expiry, invoice):
    return _ctrl(env["db"], env["u"]["ctl"]).create_receipt({
        "invoice_number": invoice, "supplier": "TEST_LSCA_S", "delivery_date": TODAY.isoformat(),
        "lines": [{"product_id": pid, "received_qty": qty, "unit_price": "10", "lot_number": "LOTX",
                   "expiry_date": expiry.isoformat()}]})


def _count(env, lines):
    _as(env["u"]["lab"], "laborantin")
    return env["client"].post("/lab-stock/counts", json={"lines": lines})


def _notifs(db, type_, uid=None):
    db.expire_all()
    q = db.query(Notification).filter(Notification.type == type_)
    if uid is not None:
        q = q.filter(Notification.recipient_user_id == uid)
    return q.all()


def _open_req(db, pid):
    db.expire_all()
    return db.query(LabStockRequest).filter(LabStockRequest.product_id == pid,
                                            LabStockRequest.status.in_(("a_commander", "commande"))).one_or_none()


def test_count_sets_stock_traces_delta_and_last_counted(env):
    db, a, b = env["db"], env["a"], env["b"]
    _receive(env, a["id"], 10, TODAY + timedelta(days=300), "TEST_LSCA_F1")
    r = _count(env, [{"product_id": a["id"], "previous_qty": 10, "counted_qty": 7},
                     {"product_id": b["id"], "previous_qty": 0, "counted_qty": 0}])
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["conflicts"] == [] and len(out["applied"]) == 2
    assert _qty(db, a["id"]) == 7 and _qty(db, b["id"]) == 0
    mv = db.query(LabStockMovement).filter_by(ref_type="count", ref_id=out["count_id"]).all()
    assert sorted((m.product_id, m.change_qty, m.quantity_after) for m in mv) == sorted(
        [(a["id"], -3, 7), (b["id"], 0, 0)])
    assert db.get(LabStockProduct, a["id"]).last_counted_at is not None
    assert db.get(LabStockProduct, b["id"]).last_counted_at is not None
    assert db.query(LabStockCountLine).filter_by(count_id=out["count_id"]).count() == 2
    # historique avec noms
    hist = env["client"].get("/lab-stock/movements", params={"product_id": a["id"]}).json()
    assert [h["movement_type"] for h in hist] == ["comptage", "reception"]
    assert hist[0]["product_name"] == "TEST_LSCA_A" and hist[0]["created_by_name"] == env["u"]["lab"].full_name


def test_stale_line_conflicts_others_applied(env):
    db, a, b = env["db"], env["a"], env["b"]
    _receive(env, a["id"], 10, TODAY + timedelta(days=300), "TEST_LSCA_F2")
    r = _count(env, [{"product_id": a["id"], "previous_qty": 0, "counted_qty": 2},
                     {"product_id": b["id"], "previous_qty": 0, "counted_qty": 4}])
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["conflicts"] == [{"product_id": a["id"], "name": "TEST_LSCA_A", "expected": 0, "actual": 10}]
    assert [x["product_id"] for x in out["applied"]] == [b["id"]]
    assert _qty(db, a["id"]) == 10 and _qty(db, b["id"]) == 4
    assert db.query(LabStockCountLine).filter_by(count_id=out["count_id"]).count() == 1


def test_reception_then_concurrent_count_all_conflict_409(env):
    """Ecran de comptage charge (stock 0), reception (+6), puis envoi : 409, stock = reception."""
    db, a = env["db"], env["a"]
    loaded = _qty(db, a["id"])
    _receive(env, a["id"], 6, TODAY + timedelta(days=300), "TEST_LSCA_F3")
    r = _count(env, [{"product_id": a["id"], "previous_qty": loaded, "counted_qty": 1}])
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["conflicts"][0]["actual"] == 6
    assert _qty(db, a["id"]) == 6
    assert db.query(LabStockMovement).filter_by(product_id=a["id"], movement_type="comptage").count() == 0


def test_disabled_or_unknown_product_refused(env):
    db, b = env["db"], env["b"]
    env["lab"].update_product(b["id"], {"is_active": False})
    assert _count(env, [{"product_id": b["id"], "previous_qty": 0, "counted_qty": 1}]).status_code == 422
    assert _count(env, [{"product_id": 99999999, "previous_qty": 0, "counted_qty": 1}]).status_code == 422
    assert _count(env, [{"product_id": env["a"]["id"], "previous_qty": 0, "counted_qty": -1}]).status_code == 422
    dup = {"product_id": env["a"]["id"], "previous_qty": 0, "counted_qty": 1}
    assert _count(env, [dup, dup]).status_code == 422


def test_below_threshold_creates_one_seuil_request_no_duplicate(env):
    db, a, u = env["db"], env["a"], env["u"]
    _receive(env, a["id"], 20, TODAY + timedelta(days=300), "TEST_LSCA_F4")
    assert _open_req(db, a["id"]) is None
    assert _count(env, [{"product_id": a["id"], "previous_qty": 20, "counted_qty": 3}]).status_code == 200
    req = _open_req(db, a["id"])
    assert req.origin == "seuil" and req.status == "a_commander"
    low = [n for n in _notifs(db, "lab_stock_low", u["promo"].user_id) if n.payload.get("product_id") == a["id"]]
    assert len(low) == 1
    assert _count(env, [{"product_id": a["id"], "previous_qty": 3, "counted_qty": 2}]).status_code == 200
    low = [n for n in _notifs(db, "lab_stock_low", u["promo"].user_id) if n.payload.get("product_id") == a["id"]]
    assert len(low) == 1
    assert db.query(LabStockRequest).filter_by(product_id=a["id"]).count() == 1


def test_rise_above_threshold_closes_only_uncommanded_seuil(env):
    db, a, b, u = env["db"], env["a"], env["b"], env["u"]
    # seuil a_commander -> annule
    assert _count(env, [{"product_id": a["id"], "previous_qty": 0, "counted_qty": 1}]).status_code == 200
    req = _open_req(db, a["id"])
    assert req.origin == "seuil"
    assert _count(env, [{"product_id": a["id"], "previous_qty": 1, "counted_qty": 9}]).status_code == 200
    db.expire_all()
    closed = db.get(LabStockRequest, req.id)
    assert closed.status == "annule" and closed.cancel_reason == "stock remonté"
    # seuil deja commandee -> intacte
    assert _count(env, [{"product_id": a["id"], "previous_qty": 9, "counted_qty": 2}]).status_code == 200
    req2 = _open_req(db, a["id"])
    _ctrl(db, u["admin"]).mark_ordered(req2.id, (TODAY + timedelta(days=3)).isoformat())
    assert _count(env, [{"product_id": a["id"], "previous_qty": 2, "counted_qty": 9}]).status_code == 200
    assert _open_req(db, a["id"]).status == "commande"
    # signalement -> intact
    sig = env["lab"].signal(b["id"], "bientot_fini")
    assert _count(env, [{"product_id": b["id"], "previous_qty": 0, "counted_qty": 5}]).status_code == 200
    assert _open_req(db, b["id"]).id == sig["id"]


def test_threshold_zero_stock_zero_no_false_low(env):
    db, b = env["db"], env["b"]
    alerts = _ctrl(db, env["u"]["lab"]).get_alerts(TODAY)
    assert b["id"] not in [x["product_id"] for x in alerts["low"]]
    env["lab"].signal(b["id"], "fini")
    alerts = _ctrl(db, env["u"]["lab"]).get_alerts(TODAY)
    assert b["id"] in [x["product_id"] for x in alerts["low"]]
    # seuil 5, stock 0 : liste meme sans demande
    assert env["a"]["id"] in [x["product_id"] for x in alerts["low"]]


def test_expiring_lots_and_dedup(env):
    db, a, b, u = env["db"], env["a"], env["b"], env["u"]
    soon = _receive(env, a["id"], 4, TODAY + timedelta(days=60), "TEST_LSCA_F5")
    far = _receive(env, a["id"], 4, TODAY + timedelta(days=61), "TEST_LSCA_F6")
    nostock = _receive(env, b["id"], 2, TODAY + timedelta(days=10), "TEST_LSCA_F7")
    # lot du produit b : stock remis a 0 -> absent
    _count(env, [{"product_id": b["id"], "previous_qty": 2, "counted_qty": 0}])
    ctrl = _ctrl(db, u["lab"])
    exp = {e["receipt_id"]: e for e in ctrl.get_alerts(TODAY)["expiring"]}
    assert soon["id"] in exp and exp[soon["id"]]["days_left"] == 60
    assert far["id"] not in exp and nostock["id"] not in exp
    # deja perime : days_left negatif
    exp = {e["receipt_id"]: e for e in ctrl.get_alerts(TODAY + timedelta(days=65))["expiring"]}
    assert exp[soon["id"]]["days_left"] == -5 and far["id"] in exp
    line_id = exp[soon["id"]]["receipt_line_id"]
    mine = [n for n in _notifs(db, "lab_stock_expiry", u["promo"].user_id)
            if n.payload.get("receipt_line_id") == line_id]
    assert len(mine) == 1
    # lue puis relecture : pas de nouvelle notification
    mine[0].status = "read"
    db.flush()
    ctrl.get_alerts(TODAY)
    _as(u["promo"], "promoteur")
    assert env["client"].get("/lab-stock/alerts").status_code == 200
    assert len([n for n in _notifs(db, "lab_stock_expiry", u["promo"].user_id)
                if n.payload.get("receipt_line_id") == line_id]) == 1
    # produit desactive -> absent
    env["lab"].update_product(a["id"], {"is_active": False})
    assert soon["id"] not in [e["receipt_id"] for e in ctrl.get_alerts(TODAY)["expiring"]]


def test_reminder_due_after_7_days_weekly_dedup(env):
    db, a, u = env["db"], env["a"], env["u"]
    assert _count(env, [{"product_id": a["id"], "previous_qty": 0, "counted_qty": 8}]).status_code == 200
    ctrl = _ctrl(db, u["lab"])
    st = ctrl.get_alerts(TODAY)["count_status"]
    assert st["reminder_due"] is False and st["days_since"] == 0
    later = datetime.utcnow().date() + timedelta(days=7)
    assert ctrl.get_alerts(later - timedelta(days=1))["count_status"]["reminder_due"] is False
    st = ctrl.get_alerts(later)["count_status"]
    assert st["reminder_due"] is True and st["days_since"] == 7
    ctrl.get_alerts(later)
    rem = _notifs(db, "lab_stock_count_reminder", u["lab"].user_id)
    assert len(rem) == 1 and rem[0].status == "unread"
    # le comptage efface le rappel
    _count(env, [{"product_id": a["id"], "previous_qty": 8, "counted_qty": 8}])
    assert all(n.status == "read" for n in _notifs(db, "lab_stock_count_reminder", u["lab"].user_id))
    _as(u["lab"], "laborantin")
    r = env["client"].get("/lab-stock/counts/status")
    assert r.status_code == 200 and r.json()["reminder_due"] is False


def test_never_counted(env, monkeypatch):
    db = env["db"]
    ctrl = _ctrl(db, env["u"]["lab"])
    monkeypatch.setattr(ctrl.repo, "last_count_at", lambda: None)
    st = ctrl.get_alerts(TODAY)["count_status"]
    assert st == {"last_counted_at": None, "days_since": None, "reminder_due": True}
    monkeypatch.setattr(ctrl.repo, "active_product_count", lambda: 0)
    assert ctrl.get_alerts(TODAY)["count_status"]["reminder_due"] is False


def test_notification_failure_does_not_break_read(env, monkeypatch):
    db = env["db"]
    _receive(env, env["a"]["id"], 3, TODAY + timedelta(days=5), "TEST_LSCA_F8")
    ctrl = _ctrl(db, env["u"]["lab"])

    def boom(*a, **k):
        raise RuntimeError("panne")
    monkeypatch.setattr(ctrl.notification_repo, "create", boom)
    out = ctrl.get_alerts(TODAY)
    assert env["a"]["id"] in [e["product_id"] for e in out["expiring"]]


def test_count_conflict_error_class(env):
    with pytest.raises(LabStockCountConflictError):
        _receive(env, env["a"]["id"], 1, TODAY + timedelta(days=300), "TEST_LSCA_F9")
        _ctrl(env["db"], env["u"]["lab"]).submit_count(
            [{"product_id": env["a"]["id"], "previous_qty": 0, "counted_qty": 0}])
