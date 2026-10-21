# tests/test_stock_incidents.py
"""Task 3 : avaries sur le stock en rayon (appels directs du controleur)."""
from datetime import date

import pytest

from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from models.stock_reception import StockIncident
from models.notification import Notification
from models.audit import AuditUserAction
from repositories.stock_repo import StockRepository
from repositories.notification_repo import NotificationRepository
from repositories.audit_repo import AuditRepository
from controller.stock_controller import StockController, StockConflictError
from tests.conftest import create_test_user


def _ctrl(db, user):
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _product(db, qty=10, threshold=5, name="TEST_INC_PROD"):
    p = Pharmacy(drug_name=name, quantity=qty, threshold=threshold, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def users(db_session):
    return {
        "assistant": create_test_user(db_session, "t_inc_assist", "Assistant"),
        "assistant2": create_test_user(db_session, "t_inc_assist2", "Assistant"),
        "controller": create_test_user(db_session, "t_inc_ctrl", "StockController"),
        "admin": create_test_user(db_session, "t_inc_admin", "admin"),
    }


def _inc(db, user, product, kind="endommage", qty=3, reason="carton ecrase", d=None):
    return _ctrl(db, user).create_incident({
        "product_id": product.medication_id, "kind": kind, "quantity": qty, "reason": reason,
        "incident_date": d or date.today()})


def _stock(db, p):
    db.expire_all()
    return db.get(Pharmacy, p.medication_id).quantity


def test_create_incident_no_stock_change_and_notifies(db_session, users):
    p = _product(db_session, qty=10)
    out = _inc(db_session, users["assistant"], p, qty=3)
    assert out["status"] == "a_controler" and out["quantity"] == 3 and out["kind"] == "endommage"
    assert out["product_name"] == "TEST_INC_PROD"
    assert _stock(db_session, p) == 10
    q = db_session.query(Notification).filter_by(type="stock_to_check")
    n = q.filter_by(recipient_user_id=users["controller"].user_id).one()
    assert n.payload["incident_id"] == out["id"] and n.payload["kind"] == "endommage"
    assert n.payload["product_name"] == "TEST_INC_PROD" and n.payload["quantity"] == 3
    assert n.payload["created_by_name"] == users["assistant"].full_name
    assert q.filter_by(recipient_user_id=users["admin"].user_id).count() == 1
    assert q.filter_by(recipient_user_id=users["assistant"].user_id).count() == 0
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockIncident", resource_id=out["id"],
                                                       action_performed="CREATE").count() == 1


@pytest.mark.parametrize("patch", [
    {"kind": "inconnu"}, {"quantity": 0}, {"quantity": -2}, {"quantity": "x"}, {"reason": "  "},
    {"reason": None}, {"incident_date": None}, {"incident_date": "garbage"}, {"product_id": 987654321},
])
def test_create_incident_validation(db_session, users, patch):
    p = _product(db_session)
    data = {"product_id": p.medication_id, "kind": "perdu", "quantity": 1, "reason": "r",
            "incident_date": date.today()}
    data.update(patch)
    before = db_session.query(StockIncident).count()
    with pytest.raises(ValueError):
        _ctrl(db_session, users["assistant"]).create_incident(data)
    assert db_session.query(StockIncident).count() == before


@pytest.mark.parametrize("kind", ["endommage", "perdu", "defectueux"])
def test_validate_removes_stock(db_session, users, kind):
    p = _product(db_session, qty=10, threshold=5)
    i = _inc(db_session, users["assistant"], p, kind=kind, qty=6)
    out = _ctrl(db_session, users["controller"]).validate_incident(i["id"])
    assert out["status"] == "valide" and out["controlled_by"] == users["controller"].user_id
    db_session.expire_all()
    prod = db_session.get(Pharmacy, p.medication_id)
    assert prod.quantity == 4 and prod.stock_status != "normal"
    mv = db_session.query(StockMovement).filter_by(medication_id=p.medication_id,
                                                   movement_type=f"avarie_{kind}").one()
    assert mv.change_qty == -6
    inc = db_session.get(StockIncident, i["id"])
    assert inc.controlled_by == users["controller"].user_id and inc.controlled_at is not None
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockIncident", resource_id=i["id"],
                                                       action_performed="VALIDATE").count() == 1
    nd = db_session.query(Notification).filter_by(recipient_user_id=users["assistant"].user_id,
                                                  type="stock_decided").one()
    assert nd.payload["status"] == "valide"


def test_validate_conflict_when_stock_dropped_since_creation(db_session, users):
    p = _product(db_session, qty=5)
    i = _inc(db_session, users["assistant"], p, qty=4)
    StockRepository(db_session).apply_stock_delta(p.medication_id, -3, "VENTE", "vente", users["assistant"])
    db_session.commit()  # la vente est validee (comme le fait le code caisse) avant la validation
    assert _stock(db_session, p) == 2
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["controller"]).validate_incident(i["id"])
    assert _stock(db_session, p) == 2
    assert db_session.get(StockIncident, i["id"]).status == "a_controler"
    assert db_session.query(StockMovement).filter(
        StockMovement.medication_id == p.medication_id,
        StockMovement.movement_type.like("avarie_%")).count() == 0
    assert db_session.query(Notification).filter_by(recipient_user_id=users["assistant"].user_id,
                                                    type="stock_decided").count() == 0


def test_author_cannot_validate_or_reject(db_session, users):
    p = _product(db_session, qty=10)
    i = _inc(db_session, users["admin"], p)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["admin"]).validate_incident(i["id"])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["admin"]).reject_incident(i["id"], "non")
    i2 = _inc(db_session, users["controller"], p)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["controller"]).validate_incident(i2["id"])
    assert _stock(db_session, p) == 10


def test_non_checker_cannot_validate(db_session, users):
    p = _product(db_session, qty=10)
    i = _inc(db_session, users["assistant"], p)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["assistant2"]).validate_incident(i["id"])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["assistant2"]).reject_incident(i["id"], "x")
    assert _stock(db_session, p) == 10


def test_admin_can_validate_other_authors(db_session, users):
    p = _product(db_session, qty=10)
    i = _inc(db_session, users["assistant"], p, qty=2)
    assert _ctrl(db_session, users["admin"]).validate_incident(i["id"])["status"] == "valide"
    assert _stock(db_session, p) == 8


def test_reject_incident(db_session, users):
    p = _product(db_session, qty=10)
    i = _inc(db_session, users["assistant"], p)
    c = _ctrl(db_session, users["controller"])
    with pytest.raises(ValueError):
        c.reject_incident(i["id"], "  ")
    with pytest.raises(ValueError):
        c.reject_incident(i["id"], None)
    out = c.reject_incident(i["id"], "pas constate")
    assert out["status"] == "rejete" and out["reject_reason"] == "pas constate"
    assert _stock(db_session, p) == 10
    nd = db_session.query(Notification).filter_by(recipient_user_id=users["assistant"].user_id,
                                                  type="stock_decided").one()
    assert nd.payload["status"] == "rejete" and nd.payload["reason"] == "pas constate"


def test_decided_incident_is_final(db_session, users):
    p = _product(db_session, qty=10)
    i = _inc(db_session, users["assistant"], p, qty=2)
    c = _ctrl(db_session, users["controller"])
    c.validate_incident(i["id"])
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin"]).validate_incident(i["id"])
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin"]).reject_incident(i["id"], "trop tard")
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["assistant"]).cancel_incident(i["id"])
    assert _stock(db_session, p) == 8


def test_cancel_incident(db_session, users):
    p = _product(db_session, qty=10)
    i = _inc(db_session, users["assistant"], p)
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["controller"]).cancel_incident(i["id"])
    out = _ctrl(db_session, users["assistant"]).cancel_incident(i["id"])
    assert out["status"] == "rejete" and out["reject_reason"] == "annulé par l'auteur"
    i2 = _inc(db_session, users["assistant"], p)
    assert _ctrl(db_session, users["admin"]).cancel_incident(i2["id"])["status"] == "rejete"
    assert _stock(db_session, p) == 10
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["assistant"]).cancel_incident(i["id"])


def test_unknown_incident(db_session, users):
    c = _ctrl(db_session, users["controller"])
    for fn in (lambda: c.validate_incident(987654321), lambda: c.reject_incident(987654321, "x"),
               lambda: c.cancel_incident(987654321)):
        with pytest.raises(ValueError):
            fn()


def test_list_incidents(db_session, users):
    p = _product(db_session)
    a = _inc(db_session, users["assistant"], p)
    b = _inc(db_session, users["assistant2"], p)
    _ctrl(db_session, users["controller"]).reject_incident(b["id"], "non")
    c = _ctrl(db_session, users["controller"])
    ids = {x["id"] for x in c.list_incidents()}
    assert {a["id"], b["id"]} <= ids
    assert {x["id"] for x in c.list_incidents("a_controler")} >= {a["id"]}
    assert b["id"] not in {x["id"] for x in c.list_incidents("a_controler")}
    assert [x["id"] for x in _ctrl(db_session, users["assistant"]).list_incidents(None, True)] == [a["id"]]
    assert c.list_incidents(None, True) == []


def test_date_string_normalized(db_session, users):
    p = _product(db_session)
    assert _inc(db_session, users["assistant"], p, d="2026-03-04")["incident_date"] == date(2026, 3, 4)
