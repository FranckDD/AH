# tests/test_stock_adjustment_requests.py
"""Task 4 : demandes d'ajustement de la secretaire (approbation admin)."""
import pytest

from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from models.stock_reception import StockAdjustmentRequest
from models.notification import Notification
from models.audit import AuditUserAction
from repositories.stock_repo import StockRepository
from repositories.notification_repo import NotificationRepository
from repositories.audit_repo import AuditRepository
from controller.stock_controller import StockController, StockConflictError
from tests.conftest import create_test_user


def _ctrl(db, user):
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _product(db, qty=10, threshold=5, name="TEST_ADJ_PROD"):
    p = Pharmacy(drug_name=name, quantity=qty, threshold=threshold, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def users(db_session):
    return {
        "sec": create_test_user(db_session, "t_adj_sec", "secretaire"),
        "sec2": create_test_user(db_session, "t_adj_sec2", "secretaire"),
        "admin": create_test_user(db_session, "t_adj_admin", "admin"),
        "admin2": create_test_user(db_session, "t_adj_admin2", "admin"),
        "controller": create_test_user(db_session, "t_adj_ctrl", "StockController"),
        "assistant": create_test_user(db_session, "t_adj_assist", "Assistant"),
    }


def _stock(db, p):
    db.expire_all()
    return db.get(Pharmacy, p.medication_id).quantity


def _req(db, user, p, kind="reapprovisionnement", qty=5, reason="livraison recue"):
    return _ctrl(db, user).create_adjustment_request(
        {"product_id": p.medication_id, "kind": kind, "quantity": qty, "reason": reason})


def test_create_no_stock_change_and_notifies_admins(db_session, users):
    p = _product(db_session, qty=10)
    out = _req(db_session, users["sec"], p, qty=5)
    assert out["status"] == "en_attente" and out["kind"] == "reapprovisionnement" and out["quantity"] == 5
    assert out["product_name"] == "TEST_ADJ_PROD" and out["requested_by"] == users["sec"].user_id
    assert _stock(db_session, p) == 10
    q = db_session.query(Notification).filter_by(type="stock_adjustment_request")
    for k in ("admin", "admin2"):
        n = q.filter_by(recipient_user_id=users[k].user_id).one()
        assert n.payload == {"request_id": out["id"], "product_name": "TEST_ADJ_PROD",
                             "kind": "reapprovisionnement", "quantity": 5,
                             "requested_by_name": users["sec"].full_name}
    assert q.filter_by(recipient_user_id=users["controller"].user_id).count() == 0
    assert q.filter_by(recipient_user_id=users["sec"].user_id).count() == 0
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockAdjustmentRequest",
                                                       resource_id=out["id"],
                                                       action_performed="CREATE").count() == 1


@pytest.mark.parametrize("who", ["admin", "controller", "assistant"])
def test_only_secretaire_can_create(db_session, users, who):
    p = _product(db_session)
    before = db_session.query(StockAdjustmentRequest).count()
    with pytest.raises(PermissionError):
        _req(db_session, users[who], p)
    assert db_session.query(StockAdjustmentRequest).count() == before


@pytest.mark.parametrize("patch", [
    {"kind": "inconnu"}, {"kind": None},
    {"kind": "reapprovisionnement", "quantity": 0}, {"kind": "reapprovisionnement", "quantity": -1},
    {"kind": "correction", "quantity": -1}, {"quantity": "x"}, {"quantity": 1.5},
    {"reason": "  "}, {"reason": None}, {"product_id": 987654321}, {"product_id": None},
])
def test_create_validation(db_session, users, patch):
    p = _product(db_session)
    data = {"product_id": p.medication_id, "kind": "reapprovisionnement", "quantity": 3, "reason": "r"}
    data.update(patch)
    before = db_session.query(StockAdjustmentRequest).count()
    with pytest.raises(ValueError):
        _ctrl(db_session, users["sec"]).create_adjustment_request(data)
    assert db_session.query(StockAdjustmentRequest).count() == before


def test_correction_zero_quantity_allowed_at_creation(db_session, users):
    p = _product(db_session)
    assert _req(db_session, users["sec"], p, kind="correction", qty=0)["quantity"] == 0


def test_approve_reapprovisionnement(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    out = _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    assert out["status"] == "approuve" and out["decided_by"] == users["admin"].user_id
    assert out["stock_before"] == 10 and out["stock_after"] == 15 and out["decided_at"] is not None
    assert _stock(db_session, p) == 15
    mv = db_session.query(StockMovement).filter_by(medication_id=p.medication_id, movement_type="renew").one()
    assert mv.change_qty == 5
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockAdjustmentRequest",
                                                       resource_id=r["id"],
                                                       action_performed="APPROVE").count() == 1
    nd = db_session.query(Notification).filter_by(recipient_user_id=users["sec"].user_id,
                                                  type="stock_decided").one()
    assert nd.payload["kind"] == "adjustment" and nd.payload["id"] == r["id"]
    assert nd.payload["number"] == f"AJU-{r['id']}" and nd.payload["status"] == "approuve"


def test_approve_correction_up_and_down(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, kind="correction", qty=14)
    out = _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    assert (out["stock_before"], out["stock_after"]) == (10, 14) and _stock(db_session, p) == 14
    r2 = _req(db_session, users["sec"], p, kind="correction", qty=3)
    _ctrl(db_session, users["admin2"]).approve_adjustment(r2["id"])
    assert _stock(db_session, p) == 3
    mvs = db_session.query(StockMovement).filter_by(medication_id=p.medication_id, movement_type="update")
    assert sorted(m.change_qty for m in mvs) == [-11, 4]


def test_correction_delta_computed_at_approval_time(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, kind="correction", qty=8)
    StockRepository(db_session).apply_stock_delta(p.medication_id, -4, "VENTE", "vente", users["sec"])
    db_session.commit()  # vente intermediaire validee
    assert _stock(db_session, p) == 6
    out = _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    assert (out["stock_before"], out["stock_after"]) == (6, 8)
    assert _stock(db_session, p) == 8
    mv = db_session.query(StockMovement).filter_by(medication_id=p.medication_id, movement_type="update").one()
    assert mv.change_qty == 2


def test_correction_same_quantity_logs_zero_movement(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, kind="correction", qty=10)
    out = _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    assert out["status"] == "approuve" and (out["stock_before"], out["stock_after"]) == (10, 10)
    mv = db_session.query(StockMovement).filter_by(medication_id=p.medication_id, movement_type="update").one()
    assert mv.change_qty == 0
    assert _stock(db_session, p) == 10


def test_correction_to_zero_updates_status(db_session, users):
    p = _product(db_session, qty=10, threshold=5)
    r = _req(db_session, users["sec"], p, kind="correction", qty=0)
    _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    db_session.expire_all()
    prod = db_session.get(Pharmacy, p.medication_id)
    assert prod.quantity == 0 and prod.stock_status != "normal"


@pytest.mark.parametrize("who", ["controller", "assistant", "sec", "sec2"])
def test_non_admin_cannot_approve_or_reject(db_session, users, who):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users[who]).approve_adjustment(r["id"])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users[who]).reject_adjustment(r["id"], "non")
    assert _stock(db_session, p) == 10
    assert db_session.get(StockAdjustmentRequest, r["id"]).status == "en_attente"
    assert db_session.query(StockMovement).filter_by(medication_id=p.medication_id,
                                                     movement_type="renew").count() == 0


def test_requester_cannot_decide_own_request(db_session, users):
    """Cas hypothetique (role change) : un admin demandeur ne peut pas decider sa demande."""
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    db_session.get(StockAdjustmentRequest, r["id"]).requested_by = users["admin"].user_id
    db_session.commit()  # le rollback du controleur ne doit pas annuler cette mise en place
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["admin"]).reject_adjustment(r["id"], "non")
    assert _stock(db_session, p) == 10


def test_reject(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    c = _ctrl(db_session, users["admin"])
    with pytest.raises(ValueError):
        c.reject_adjustment(r["id"], "  ")
    with pytest.raises(ValueError):
        c.reject_adjustment(r["id"], None)
    out = c.reject_adjustment(r["id"], "quantite incoherente")
    assert out["status"] == "refuse" and out["decision_note"] == "quantite incoherente"
    assert out["decided_by"] == users["admin"].user_id
    assert _stock(db_session, p) == 10
    assert db_session.query(StockMovement).filter_by(medication_id=p.medication_id).count() == 0
    nd = db_session.query(Notification).filter_by(recipient_user_id=users["sec"].user_id,
                                                  type="stock_decided").one()
    assert nd.payload["status"] == "refuse" and nd.payload["reason"] == "quantite incoherente"
    assert nd.payload["number"] == f"AJU-{r['id']}"


def test_decided_request_is_final(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin2"]).approve_adjustment(r["id"])
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin2"]).reject_adjustment(r["id"], "trop tard")
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["sec"]).cancel_adjustment(r["id"])
    assert _stock(db_session, p) == 15
    assert db_session.query(StockMovement).filter_by(medication_id=p.medication_id,
                                                     movement_type="renew").count() == 1


def test_rejected_request_cannot_be_approved(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    _ctrl(db_session, users["admin"]).reject_adjustment(r["id"], "non")
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin2"]).approve_adjustment(r["id"])
    assert _stock(db_session, p) == 10


def test_cancel(db_session, users):
    p = _product(db_session, qty=10)
    r = _req(db_session, users["sec"], p, qty=5)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["sec2"]).cancel_adjustment(r["id"])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["admin"]).cancel_adjustment(r["id"])
    out = _ctrl(db_session, users["sec"]).cancel_adjustment(r["id"])
    assert out["status"] == "annule"
    assert _stock(db_session, p) == 10
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin"]).approve_adjustment(r["id"])
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["sec"]).cancel_adjustment(r["id"])
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockAdjustmentRequest",
                                                       resource_id=r["id"],
                                                       action_performed="CANCEL").count() == 1


def test_unknown_request(db_session, users):
    for fn in (lambda: _ctrl(db_session, users["admin"]).approve_adjustment(987654321),
               lambda: _ctrl(db_session, users["admin"]).reject_adjustment(987654321, "x"),
               lambda: _ctrl(db_session, users["sec"]).cancel_adjustment(987654321)):
        with pytest.raises(ValueError):
            fn()


def test_list_requests(db_session, users):
    p = _product(db_session)
    a = _req(db_session, users["sec"], p)
    b = _req(db_session, users["sec2"], p)
    _ctrl(db_session, users["admin"]).reject_adjustment(b["id"], "non")
    c = _ctrl(db_session, users["admin"])
    assert {a["id"], b["id"]} <= {x["id"] for x in c.list_adjustment_requests()}
    pend = {x["id"] for x in c.list_adjustment_requests("en_attente")}
    assert a["id"] in pend and b["id"] not in pend
    assert [x["id"] for x in _ctrl(db_session, users["sec"]).list_adjustment_requests(None, True)] == [a["id"]]
    assert c.list_adjustment_requests(None, True) == []


def test_dict_exposes_current_quantity(db_session, users):
    """Task 9 (fix) : la file admin affiche le stock actuel du produit."""
    p = _product(db_session, qty=12, name="TEST_ADJ_CURQ")
    out = _req(db_session, users["sec"], p, qty=3)
    assert out["current_quantity"] == 12
    listed = [r for r in _ctrl(db_session, users["admin"]).list_adjustment_requests("en_attente")
              if r["id"] == out["id"]]
    assert listed and listed[0]["current_quantity"] == 12
