# tests/test_lab_stock_receipts.py
"""Task 3 (stock labo) : reception (saisie + validation en une fois) et annulation admin."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.lab_stock import lab_stock_endpoints
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.lab_stock_controller import LabStockConflictError, LabStockController
from models.lab_stock import LabStockMovement, LabStockProduct, LabStockReceipt, LabStockRequest
from models.notification import Notification
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user

EXP = (date.today() + timedelta(days=200)).isoformat()
TODAY = date.today().isoformat()


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    u = {
        "lab": create_test_user(db, "t_lsrc_lab", "laborantin"),
        "ctl": create_test_user(db, "t_lsrc_ctl", "StockController"),
        "promo": create_test_user(db, "t_lsrc_promo", "promoteur"),
        "admin": create_test_user(db, "t_lsrc_admin", "admin"),
    }
    lab = _ctrl(db, u["lab"])
    a = lab.create_product({"name": "TEST_LSRC_A", "alert_threshold": 10})
    b = lab.create_product({"name": "TEST_LSRC_B", "alert_threshold": 0})
    client = api_client(lab_stock_endpoints)
    return {"db": db, "client": client, "u": u, "a": a, "b": b}


def _line(pid, qty=5, price="1500", **kw):
    d = {"product_id": pid, "received_qty": qty, "unit_price": price, "lot_number": "LOT1", "expiry_date": EXP}
    d.update(kw)
    return d


def _body(lines, invoice="TEST_LSRC_F1", supplier="Fourn X"):
    return {"invoice_number": invoice, "supplier": supplier, "delivery_date": TODAY, "lines": lines}


def _post(env, body, who="ctl", role="StockController"):
    _as(env["u"][who], role)
    return env["client"].post("/lab-stock/receipts", json=body)


def _qty(db, pid):
    db.expire_all()
    return db.get(LabStockProduct, pid).quantity


def test_receipt_increases_stock_and_movements(env):
    db, a, b = env["db"], env["a"], env["b"]
    r = _post(env, _body([_line(a["id"], 4, "1500"), _line(b["id"], 3, "250.50")]))
    assert r.status_code == 201, r.text
    rc = r.json()
    assert Decimal(str(rc["total_amount"])) == Decimal("6751.50")
    assert {Decimal(str(l["line_total"])) for l in rc["lines"]} == {Decimal("6000.00"), Decimal("751.50")}
    assert rc["created_by_name"] == env["u"]["ctl"].full_name
    assert _qty(db, a["id"]) == 4 and _qty(db, b["id"]) == 3
    mv = db.query(LabStockMovement).filter_by(ref_type="receipt", ref_id=rc["id"]).all()
    assert sorted((m.product_id, m.change_qty, m.movement_type) for m in mv) == sorted(
        [(a["id"], 4, "reception"), (b["id"], 3, "reception")])
    # lecture
    _as(env["u"]["lab"], "laborantin")
    assert env["client"].get(f"/lab-stock/receipts/{rc['id']}").json()["id"] == rc["id"]
    lst = env["client"].get("/lab-stock/receipts", params={"supplier": "fourn x", "from": TODAY}).json()
    assert [x["id"] for x in lst] == [rc["id"]]


def test_totals_supplied_ignored(env):
    # via HTTP : champ total inconnu -> 422 (extra=forbid)
    bad = _body([dict(_line(env["a"]["id"]), line_total=1)])
    assert _post(env, bad).status_code == 422
    bad = dict(_body([_line(env["a"]["id"])]), total_amount=1)
    assert _post(env, bad).status_code == 422
    # via controleur : les totaux fournis sont ignores
    body = dict(_body([dict(_line(env["a"]["id"], 2, "100"), line_total=1)]), total_amount=1)
    out = _ctrl(env["db"], env["u"]["ctl"]).create_receipt(body)
    assert out["total_amount"] == Decimal("200.00") and out["lines"][0]["line_total"] == Decimal("200.00")


def test_partial_delivery_closes_and_creates_seuil(env):
    db, a, u = env["db"], env["a"], env["u"]
    req = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    rc = _post(env, _body([_line(a["id"], 4)])).json()
    db.expire_all()
    old = db.get(LabStockRequest, req["id"])
    assert old.status == "recu" and old.closed_by_receipt_id == rc["id"] and old.closed_at is not None
    new = db.query(LabStockRequest).filter(LabStockRequest.product_id == a["id"],
                                           LabStockRequest.status == "a_commander").one()
    assert new.origin == "seuil"
    n = db.query(Notification).filter_by(recipient_user_id=u["lab"].user_id, type="lab_stock_received").all()
    assert len(n) == 1 and n[0].payload["receipt_id"] == rc["id"]


def test_above_threshold_no_new_request(env):
    db, a = env["db"], env["a"]
    _ctrl(db, env["u"]["lab"]).signal(a["id"], "fini")
    _post(env, _body([_line(a["id"], 50), _line(env["b"]["id"], 1)]))
    db.expire_all()
    open_ = db.query(LabStockRequest).filter(
        LabStockRequest.product_id.in_([a["id"], env["b"]["id"]]),
        LabStockRequest.status.in_(("a_commander", "commande"))).all()
    assert open_ == []  # seuil 0 + stock > 0 : pas de demande non plus


def test_duplicate_invoice_409_and_double_submit(env):
    db, a = env["db"], env["a"]
    assert _post(env, _body([_line(a["id"], 5)])).status_code == 201
    r = _post(env, _body([_line(a["id"], 5)], invoice="  test_lsrc_f1 ", supplier="FOURN x"))
    assert r.status_code == 409
    assert _post(env, _body([_line(a["id"], 5)])).status_code == 409  # double soumission
    assert _qty(db, a["id"]) == 5
    assert db.query(LabStockReceipt).filter(LabStockReceipt.invoice_number.ilike("test_lsrc_f1%")).count() == 1


def test_invalid_lines_422(env):
    db, a = env["db"], env["a"]
    cases = [
        [_line(a["id"]), _line(a["id"])],
        [_line(a["id"], lot_number="  ")],
        [_line(a["id"], expiry_date="")],
        [_line(a["id"], qty=0)],
        [_line(a["id"], price="-1")],
        [_line(999_999_999)],
        [],
    ]
    for lines in cases:
        r = _post(env, _body(lines))
        assert r.status_code == 422, (lines, r.status_code, r.text)
    _ctrl(db, env["u"]["lab"]).update_product(env["b"]["id"], {"is_active": False})
    assert _post(env, _body([_line(env["b"]["id"])])).status_code == 422
    assert _qty(db, a["id"]) == 0


def test_cancel_receipt(env):
    db, a, u = env["db"], env["a"], env["u"]
    req = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    rc = _post(env, _body([_line(a["id"], 20)])).json()
    url = f"/lab-stock/receipts/{rc['id']}/cancel"
    _as(u["promo"], "promoteur")
    assert env["client"].post(url, json={"reason": "x"}).status_code == 403
    with pytest.raises(PermissionError):
        _ctrl(db, u["ctl"]).cancel_receipt(rc["id"], "x")
    _as(u["admin"], "admin")
    assert env["client"].post(url, json={"reason": "  "}).status_code == 422
    r = env["client"].post(url, json={"reason": "erreur de saisie"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "annule" and r.json()["cancelled_by_name"] == u["admin"].full_name
    assert _qty(db, a["id"]) == 0
    assert db.get(LabStockRequest, req["id"]).status == "a_commander"
    mv = db.query(LabStockMovement).filter_by(ref_id=rc["id"], movement_type="annulation_reception").one()
    assert mv.change_qty == -20
    assert env["client"].post(url, json={"reason": "bis"}).status_code == 409
    # facture de nouveau acceptee
    assert _post(env, _body([_line(a["id"], 3)])).status_code == 201


def test_cancel_insufficient_stock_writes_nothing(env):
    db, a, b, u = env["db"], env["a"], env["b"], env["u"]
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 5), _line(b["id"], 5)]))
    p = db.get(LabStockProduct, b["id"])
    LabStockRepository(db).apply_delta(b["id"], -3, "comptage", "count", None, u["lab"])
    db.commit()
    with pytest.raises(LabStockConflictError):
        _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "x")
    assert _qty(db, a["id"]) == 5 and _qty(db, b["id"]) == 2
    assert db.get(LabStockReceipt, rc["id"]).status == "valide"
    assert p is not None


def test_cancel_leaves_other_open_request(env):
    db, a, u = env["db"], env["a"], env["u"]
    first = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 50)]))
    second = _ctrl(db, u["lab"]).signal(a["id"], "bientot_fini")
    assert second["id"] != first["id"]
    _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "x")
    db.expire_all()
    assert db.get(LabStockRequest, first["id"]).status == "recu"
    assert db.get(LabStockRequest, second["id"]).status == "a_commander"


# ---------------- revue Task 3 ----------------
def _mv_count(db, pid):
    return db.query(LabStockMovement).filter_by(product_id=pid).count()


def test_race_duplicate_without_precheck_is_409(env, monkeypatch):
    db, a = env["db"], env["a"]
    assert _post(env, _body([_line(a["id"], 5)])).status_code == 201
    mv_before = _mv_count(db, a["id"])
    monkeypatch.setattr(LabStockRepository, "valid_receipt_exists", lambda self, s, i: False)
    r = _post(env, _body([_line(a["id"], 7)], invoice=" TEST_LSRC_F1 ", supplier="fourn x"))
    assert r.status_code == 409, r.text
    assert _qty(db, a["id"]) == 5 and _mv_count(db, a["id"]) == mv_before
    assert db.query(LabStockReceipt).filter(LabStockReceipt.invoice_number.ilike("test_lsrc_f1")).count() == 1


def test_other_integrity_error_is_not_duplicate(env, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    def boom(self, *a, **k):
        raise IntegrityError("x", {}, Exception("violates check constraint lab_stock_x"))
    monkeypatch.setattr(LabStockRepository, "apply_delta", boom)
    with pytest.raises(IntegrityError):
        _ctrl(env["db"], env["u"]["ctl"]).create_receipt(_body([_line(env["a"]["id"])]))


def test_delivery_date_tolerance(env):
    a = env["a"]["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    later = (date.today() + timedelta(days=2)).isoformat()
    assert _post(env, dict(_body([_line(a)], invoice="TEST_LSRC_T1"), delivery_date=tomorrow)).status_code == 201
    assert _post(env, dict(_body([_line(a)], invoice="TEST_LSRC_T2"), delivery_date=later)).status_code == 422


def test_seuil_after_cancel_and_audit(env):
    from models.audit import AuditUserAction
    db, b, u = env["db"], env["b"], env["u"]
    db.get(LabStockProduct, b["id"]).alert_threshold = 2
    db.flush()
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(b["id"], 5)]))
    assert db.query(LabStockRequest).filter_by(product_id=b["id"]).count() == 0
    _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "erreur")
    req = db.query(LabStockRequest).filter_by(product_id=b["id"], status="a_commander").one()
    assert req.origin == "seuil"
    rows = {x.action_performed: x for x in db.query(AuditUserAction).filter_by(
        resource_type="LabStockReceipt", resource_id=rc["id"]).all()}
    assert set(rows) == {"CREATE", "CANCEL"}
    assert rows["CREATE"].new_values["total_amount"] == "7500.00"
    assert rows["CANCEL"].new_values["removed"] == {str(b["id"]): 5}
    assert rows["CANCEL"].new_values["reopened_request_ids"] == []


def test_low_notification_payload_and_dedupe(env):
    db, a, u = env["db"], env["a"], env["u"]
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 3)]))
    req = db.query(LabStockRequest).filter_by(product_id=a["id"], status="a_commander").one()
    n = db.query(Notification).filter_by(recipient_user_id=u["promo"].user_id, type="lab_stock_low").all()
    n = [x for x in n if x.payload.get("request_id") == req.id]
    assert len(n) == 1
    assert n[0].payload == {"request_id": req.id, "product_id": a["id"], "product_name": "TEST_LSRC_A",
                            "quantity": 3, "alert_threshold": 10}
    # re-evaluation : nouvelle reception -> demande close + nouvelle ; meme demande re-evaluee -> pas de doublon
    c = _ctrl(db, u["ctl"])
    c._ensure_threshold_request(db.get(LabStockProduct, a["id"]), 3)
    c._notify_managers("lab_stock_low", "request_id", req.id, dict(n[0].payload))
    db.flush()
    again = [x for x in db.query(Notification).filter_by(
        recipient_user_id=u["promo"].user_id, type="lab_stock_low").all() if x.payload.get("request_id") == req.id]
    assert len(again) == 1
    assert rc


def test_line_limit_and_price_decimals(env):
    db, u = env["db"], env["u"]
    lines = [_line(10_000_000 + i) for i in range(201)]
    assert _post(env, _body(lines)).status_code == 422
    with pytest.raises(ValueError):
        _ctrl(db, u["ctl"]).create_receipt(_body(lines))
    assert _post(env, _body([_line(env["a"]["id"], price="1.005")])).status_code == 422
    with pytest.raises(ValueError):
        _ctrl(db, u["ctl"]).create_receipt(_body([_line(env["a"]["id"], price="1.005")]))
    assert _qty(db, env["a"]["id"]) == 0


def test_cancel_insufficient_stock_no_movement_requests_unchanged(env):
    db, a, b, u = env["db"], env["a"], env["b"], env["u"]
    req = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 50), _line(b["id"], 5)]))
    LabStockRepository(db).apply_delta(b["id"], -3, "comptage", "count", None, u["lab"])
    db.commit()
    before = {r.id: (r.status, r.closed_by_receipt_id) for r in db.query(LabStockRequest).filter(
        LabStockRequest.product_id.in_([a["id"], b["id"]])).all()}
    with pytest.raises(LabStockConflictError):
        _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "x")
    db.expire_all()
    assert db.query(LabStockMovement).filter_by(movement_type="annulation_reception", ref_id=rc["id"]).count() == 0
    after = {r.id: (r.status, r.closed_by_receipt_id) for r in db.query(LabStockRequest).filter(
        LabStockRequest.product_id.in_([a["id"], b["id"]])).all()}
    assert after == before and before[req["id"]] == ("recu", rc["id"])
    assert _qty(db, a["id"]) == 50 and _qty(db, b["id"]) == 2


def test_cancel_reopens_ordered_request_as_commande(env):
    from models.audit import AuditUserAction
    db, a, u = env["db"], env["a"], env["u"]
    req = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    _ctrl(db, u["promo"]).mark_ordered(req["id"], EXP)
    db.expire_all()
    before = db.get(LabStockRequest, req["id"])
    snap = (before.ordered_by, before.ordered_at, before.expected_date)
    assert before.status == "commande" and all(v is not None for v in snap)
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 20)]))
    db.expire_all()
    closed = db.get(LabStockRequest, req["id"])
    assert closed.status == "recu" and (closed.ordered_by, closed.ordered_at, closed.expected_date) == snap
    _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "erreur")
    db.expire_all()
    r = db.get(LabStockRequest, req["id"])
    assert r.status == "commande"
    assert (r.ordered_by, r.ordered_at, r.expected_date) == snap
    assert r.closed_by_receipt_id is None and r.closed_at is None
    row = db.query(AuditUserAction).filter_by(resource_type="LabStockReceipt", resource_id=rc["id"],
                                              action_performed="CANCEL").one()
    assert row.new_values["reopened_request_ids"] == [req["id"]]
    assert row.new_values["reopened"] == [{"id": req["id"], "status": "commande"}]


def test_cancel_reopens_never_ordered_request_as_a_commander(env):
    from models.audit import AuditUserAction
    db, a, u = env["db"], env["a"], env["u"]
    req = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 20)]))
    _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "erreur")
    db.expire_all()
    r = db.get(LabStockRequest, req["id"])
    assert r.status == "a_commander" and r.ordered_at is None and r.ordered_by is None
    assert r.closed_by_receipt_id is None and r.closed_at is None
    row = db.query(AuditUserAction).filter_by(resource_type="LabStockReceipt", resource_id=rc["id"],
                                              action_performed="CANCEL").one()
    assert row.new_values["reopened"] == [{"id": req["id"], "status": "a_commander"}]


def test_cancel_does_not_duplicate_when_other_open_request(env):
    db, a, u = env["db"], env["a"], env["u"]
    first = _ctrl(db, u["lab"]).signal(a["id"], "fini")
    _ctrl(db, u["promo"]).mark_ordered(first["id"], EXP)
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 50)]))
    second = _ctrl(db, u["lab"]).signal(a["id"], "bientot_fini")
    _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "x")
    db.expire_all()
    assert db.get(LabStockRequest, first["id"]).status == "recu"
    open_ = db.query(LabStockRequest).filter(
        LabStockRequest.product_id == a["id"],
        LabStockRequest.status.in_(("a_commander", "commande"))).all()
    assert [x.id for x in open_] == [second["id"]]


def test_cancel_receipt_marks_received_notifications_read(env):
    db, a, u = env["db"], env["a"], env["u"]
    _ctrl(db, u["lab"]).signal(a["id"], "fini")
    rc = _ctrl(db, u["ctl"]).create_receipt(_body([_line(a["id"], 5)], invoice="TEST_LSRC_NOTIF"))
    mine = lambda: [n for n in db.query(Notification).filter_by(type="lab_stock_received").all()
                    if isinstance(n.payload, dict) and n.payload.get("receipt_id") == rc["id"]]
    assert mine() and all(n.status == "unread" for n in mine())
    _ctrl(db, u["admin"]).cancel_receipt(rc["id"], "erreur")
    db.expire_all()
    assert all(n.status == "read" and n.read_at is not None for n in mine())
