# tests/test_stock_receipts.py
"""Task 2 : lots de fabrication et receptions controlees (appels directs du controleur)."""
import re
from datetime import date, timedelta

import pytest

from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from models.stock_reception import ProductionLot, StockReceipt
from models.notification import Notification
from models.audit import AuditUserAction
from repositories.stock_repo import StockRepository
from repositories.notification_repo import NotificationRepository
from repositories.audit_repo import AuditRepository
from controller.stock_controller import StockController, StockConflictError
from tests.conftest import create_test_user


def _ctrl(db, user):
    return StockController(StockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _product(db, qty=10, threshold=5, expiry=None, name="TEST_STOCK_PROD"):
    p = Pharmacy(drug_name=name, quantity=qty, threshold=threshold, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal", expiry_date=expiry)
    p.update_stock_status()
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def users(db_session):
    return {
        "assistant": create_test_user(db_session, "t_stk_assist", "Assistant"),
        "assistant2": create_test_user(db_session, "t_stk_assist2", "Assistant"),
        "controller": create_test_user(db_session, "t_stk_ctrl", "StockController"),
        "admin": create_test_user(db_session, "t_stk_admin", "admin"),
    }


def _lot(db, user, product, status_to="livre", qty=50, expiry=None):
    c = _ctrl(db, user)
    lot = c.create_lot({"product_id": product.medication_id, "quantity_produced": qty,
                        "production_date": date.today(), "expiry_date": expiry, "producer": "Atelier"})
    if status_to in ("livre", "recu"):
        lot = c.mark_lot_delivered(lot["id"], date.today())
    if status_to == "annule":
        lot = c.cancel_lot(lot["id"])
    return lot


def _fourn_receipt(db, user, lines):
    return _ctrl(db, user).create_receipt({"origin": "fournisseur", "supplier": "Fourn", "delivery_ref": "BL1",
                                           "received_date": date.today(), "lines": lines})


# (a)
def test_lot_numbering_increments_same_day(db_session, users):
    p = _product(db_session)
    c = _ctrl(db_session, users["assistant"])
    a = c.create_lot({"product_id": p.medication_id, "quantity_produced": 5, "production_date": date.today()})
    b = c.create_lot({"product_id": p.medication_id, "quantity_produced": 5, "production_date": date.today()})
    prefix = f"LOT-{date.today():%Y%m%d}-"
    assert re.fullmatch(re.escape(prefix) + r"\d{3}", a["lot_number"])
    assert int(b["lot_number"][-3:]) == int(a["lot_number"][-3:]) + 1
    assert a["status"] == "produit"
    assert any(l["id"] == a["id"] for l in c.list_lots("produit"))


# (b)
@pytest.mark.parametrize("status", ["produit", "recu", "annule"])
def test_fabrication_receipt_requires_delivered_lot(db_session, users, status):
    p = _product(db_session)
    if status == "recu":
        lot = _lot(db_session, users["assistant"], p, "livre")
        db_session.query(ProductionLot).filter_by(id=lot["id"]).update({"status": "recu"})
        db_session.flush()
    else:
        lot = _lot(db_session, users["assistant"], p, status)
    with pytest.raises(ValueError):
        _ctrl(db_session, users["assistant"]).create_receipt({
            "origin": "fabrication", "production_lot_id": lot["id"], "received_date": date.today(),
            "lines": [{"qty_good": 1}]})


def test_fabrication_receipt_prefilled_from_lot(db_session, users):
    p = _product(db_session)
    exp = date.today() + timedelta(days=200)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=40, expiry=exp)
    r = _ctrl(db_session, users["assistant"]).create_receipt({
        "origin": "fabrication", "production_lot_id": lot["id"], "received_date": date.today(),
        "lines": [{"qty_good": 38, "qty_damaged": 2}]})
    assert re.fullmatch(rf"REC-{date.today():%Y%m%d}-\d{{3}}", r["receipt_number"])
    assert r["status"] == "a_controler"
    assert len(r["lines"]) == 1
    line = r["lines"][0]
    assert line["product_id"] == p.medication_id
    assert line["qty_expected"] == 40
    assert line["lot_number"] == lot["lot_number"]
    assert line["expiry_date"] == exp
    with pytest.raises(ValueError):
        _ctrl(db_session, users["assistant"]).create_receipt({
            "origin": "fabrication", "production_lot_id": lot["id"], "received_date": date.today(),
            "lines": [{"qty_good": 1}, {"qty_good": 1}]})


# (c)
def test_supplier_receipt_multi_lines_and_rules(db_session, users):
    p1, p2 = _product(db_session, name="TSP1"), _product(db_session, name="TSP2")
    r = _fourn_receipt(db_session, users["assistant"], [
        {"product_id": p1.medication_id, "qty_expected": 10, "qty_good": 8, "qty_lost": 2},
        {"product_id": p2.medication_id, "qty_good": 5}])
    assert len(r["lines"]) == 2
    assert {l["product_name"] for l in r["lines"]} == {"TSP1", "TSP2"}
    with pytest.raises(ValueError):
        _fourn_receipt(db_session, users["assistant"], [
            {"product_id": p1.medication_id, "qty_expected": 5, "qty_good": 5, "qty_damaged": 1}])
    with pytest.raises(ValueError):
        _fourn_receipt(db_session, users["assistant"], [{"product_id": p1.medication_id, "qty_good": 0}])
    with pytest.raises(ValueError):
        _fourn_receipt(db_session, users["assistant"], [])


# (d)
def test_validate_receipt_applies_stock(db_session, users):
    near = date.today() + timedelta(days=30)
    far = date.today() + timedelta(days=400)
    p = _product(db_session, qty=10, threshold=5, expiry=far)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=20, expiry=near)
    r = _ctrl(db_session, users["assistant"]).create_receipt({
        "origin": "fabrication", "production_lot_id": lot["id"], "received_date": date.today(),
        "lines": [{"qty_good": 15, "qty_damaged": 3, "qty_defective": 2}]})
    out = _ctrl(db_session, users["controller"]).validate_receipt(r["id"])
    assert out["status"] == "valide"
    db_session.expire_all()
    prod = db_session.get(Pharmacy, p.medication_id)
    assert prod.quantity == 25
    assert prod.stock_status == "normal"
    assert prod.expiry_date.date() == near
    mvts = db_session.query(StockMovement).filter_by(medication_id=p.medication_id,
                                                     movement_type="reception").all()
    assert len(mvts) == 1 and mvts[0].change_qty == 15
    assert r["receipt_number"] in mvts[0].note and "3" in mvts[0].note and "2" in mvts[0].note
    assert db_session.get(ProductionLot, lot["id"]).status == "recu"
    rec = db_session.get(StockReceipt, r["id"])
    assert rec.controlled_by == users["controller"].user_id and rec.controlled_at is not None
    assert db_session.query(AuditUserAction).filter_by(resource_type="StockReceipt", resource_id=r["id"],
                                                       action_performed="VALIDATE").count() == 1
    assert db_session.query(Notification).filter_by(recipient_user_id=users["assistant"].user_id,
                                                    type="stock_decided").count() == 1


# (e)
def test_validate_receipt_all_zero_good(db_session, users):
    p = _product(db_session, qty=7)
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_damaged": 4}])
    out = _ctrl(db_session, users["controller"]).validate_receipt(r["id"])
    assert out["status"] == "valide"
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 7
    assert db_session.query(StockMovement).filter_by(medication_id=p.medication_id,
                                                     movement_type="reception").count() == 0


# (f) -- sequential double validation (see report: a second connection cannot see the
# test's uncommitted rows, so the real-concurrency path is covered by the FOR UPDATE +
# re-check-after-lock in StockController.validate_receipt, reviewed in code).
def test_double_validation_applies_once(db_session, users):
    p = _product(db_session, qty=10)
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 5}])
    _ctrl(db_session, users["controller"]).validate_receipt(r["id"])
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin"]).validate_receipt(r["id"])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 15
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["admin"]).reject_receipt(r["id"], "trop tard")


# (g)
def test_author_cannot_validate(db_session, users):
    p = _product(db_session, qty=10)
    r = _fourn_receipt(db_session, users["admin"], [{"product_id": p.medication_id, "qty_good": 5}])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["admin"]).validate_receipt(r["id"])
    r2 = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 5}])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["assistant2"]).validate_receipt(r2["id"])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 10


# (h)
def test_reject_receipt(db_session, users):
    p = _product(db_session, qty=10)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=5)
    r = _ctrl(db_session, users["assistant"]).create_receipt({
        "origin": "fabrication", "production_lot_id": lot["id"], "received_date": date.today(),
        "lines": [{"qty_good": 5}]})
    c = _ctrl(db_session, users["controller"])
    with pytest.raises(ValueError):
        c.reject_receipt(r["id"], "  ")
    out = c.reject_receipt(r["id"], "carton abime")
    assert out["status"] == "rejete" and out["reject_reason"] == "carton abime"
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 10
    assert db_session.get(ProductionLot, lot["id"]).status == "livre"
    # lot with only a rejected receipt can still be cancelled
    assert _ctrl(db_session, users["assistant"]).cancel_lot(lot["id"])["status"] == "annule"


def test_cancel_lot_refused_with_active_receipt(db_session, users):
    p = _product(db_session)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=5)
    _ctrl(db_session, users["assistant"]).create_receipt({
        "origin": "fabrication", "production_lot_id": lot["id"], "received_date": date.today(),
        "lines": [{"qty_good": 5}]})
    with pytest.raises(StockConflictError):
        _ctrl(db_session, users["assistant"]).cancel_lot(lot["id"])


# (i)
def test_update_receipt_lines(db_session, users):
    p = _product(db_session, qty=0)
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 5}])
    line_id = r["lines"][0]["id"]
    c = _ctrl(db_session, users["controller"])
    out = c.update_receipt_lines(r["id"], [{"id": line_id, "qty_good": 3, "qty_damaged": 2}])
    assert out["lines"][0]["qty_good"] == 3 and out["lines"][0]["qty_damaged"] == 2
    audit = db_session.query(AuditUserAction).filter_by(resource_type="StockReceipt", resource_id=r["id"],
                                                        action_performed="UPDATE_LINES").one()
    assert "5" in str(audit.old_values) and "3" in str(audit.new_values)
    c.validate_receipt(r["id"])
    with pytest.raises(StockConflictError):
        c.update_receipt_lines(r["id"], [{"id": line_id, "qty_good": 1}])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 3


# (j)
def test_cancel_receipt_permissions(db_session, users):
    p = _product(db_session)
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 5}])
    with pytest.raises(PermissionError):
        _ctrl(db_session, users["controller"]).cancel_receipt(r["id"])
    out = _ctrl(db_session, users["assistant"]).cancel_receipt(r["id"])
    assert out["status"] == "rejete" and out["reject_reason"] == "annulé par l'auteur"
    r2 = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 5}])
    assert _ctrl(db_session, users["admin"]).cancel_receipt(r2["id"])["status"] == "rejete"


# (k)
def test_stock_to_check_notifications(db_session, users):
    p = _product(db_session)
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 5}])
    q = db_session.query(Notification).filter_by(type="stock_to_check")
    ctrl_n = q.filter_by(recipient_user_id=users["controller"].user_id).one()
    assert ctrl_n.payload["receipt_id"] == r["id"]
    assert ctrl_n.payload["receipt_number"] == r["receipt_number"]
    assert ctrl_n.payload["created_by_name"] == users["assistant"].full_name
    assert q.filter_by(recipient_user_id=users["admin"].user_id).count() == 1
    assert q.filter_by(recipient_user_id=users["assistant"].user_id).count() == 0
    mine = _ctrl(db_session, users["assistant"]).list_receipts(None, True)
    assert [x["id"] for x in mine] == [r["id"]]
    assert _ctrl(db_session, users["controller"]).list_receipts(None, True) == []


# ---------------- fix round 1 ----------------
def _fab(db, user, lot_id, **line):
    return _ctrl(db, user).create_receipt({"origin": "fabrication", "production_lot_id": lot_id,
                                           "received_date": date.today(), "lines": [line or {"qty_good": 5}]})


def test_second_receipt_same_lot_refused_while_pending(db_session, users):
    p = _product(db_session)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=5)
    _fab(db_session, users["assistant"], lot["id"])
    with pytest.raises(ValueError):
        _fab(db_session, users["assistant2"], lot["id"])


def test_second_receipt_same_lot_refused_after_validation(db_session, users):
    p = _product(db_session)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=5)
    r = _fab(db_session, users["assistant"], lot["id"])
    _ctrl(db_session, users["controller"]).validate_receipt(r["id"])
    with pytest.raises(ValueError):
        _fab(db_session, users["assistant"], lot["id"])


def test_receipt_allowed_again_after_rejection(db_session, users):
    p = _product(db_session)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=5)
    r = _fab(db_session, users["assistant"], lot["id"])
    _ctrl(db_session, users["controller"]).reject_receipt(r["id"], "erreur")
    r2 = _fab(db_session, users["assistant"], lot["id"])
    assert r2["status"] == "a_controler"


def test_bypass_two_receipts_same_lot_stock_applied_once(db_session, users):
    from models.stock_reception import StockReceiptLine
    p = _product(db_session, qty=10)
    lot = _lot(db_session, users["assistant"], p, "livre", qty=50)
    ids = []
    for n in ("REC-19990101-901", "REC-19990101-902"):
        rec = StockReceipt(receipt_number=n, origin="fabrication", production_lot_id=lot["id"],
                           received_date=date.today(), status="a_controler",
                           created_by=users["assistant"].user_id,
                           lines=[StockReceiptLine(product_id=p.medication_id, qty_expected=50, qty_good=50)])
        db_session.add(rec)
        db_session.flush()
        ids.append(rec.id)
    c = _ctrl(db_session, users["controller"])
    c.validate_receipt(ids[0])
    with pytest.raises(StockConflictError):
        c.validate_receipt(ids[1])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 60
    assert db_session.get(StockReceipt, ids[1]).status == "a_controler"


def test_numbering_past_999(db_session, users):
    p = _product(db_session)
    stem = f"LOT-{date.today():%Y%m%d}-"
    for n in ("999", "1000"):
        db_session.add(ProductionLot(lot_number=stem + n, product_id=p.medication_id, quantity_produced=1,
                                     production_date=date.today(), status="produit",
                                     created_by=users["assistant"].user_id))
    db_session.flush()
    lot = _ctrl(db_session, users["assistant"]).create_lot(
        {"product_id": p.medication_id, "quantity_produced": 1, "production_date": date.today()})
    assert lot["lot_number"] == stem + "1001"


def test_date_fields_normalized(db_session, users):
    p = _product(db_session)
    c = _ctrl(db_session, users["assistant"])
    lot = c.create_lot({"product_id": p.medication_id, "quantity_produced": 1,
                        "production_date": date.today().isoformat(), "expiry_date": "2030-01-31"})
    assert lot["expiry_date"] == date(2030, 1, 31) and lot["production_date"] == date.today()
    for bad in ("31/01/2030", 20300131, "garbage"):
        with pytest.raises(ValueError):
            c.create_lot({"product_id": p.medication_id, "quantity_produced": 1,
                          "production_date": date.today(), "expiry_date": bad})
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 1,
                                                         "expiry_date": "2031-02-01"}])
    assert r["lines"][0]["expiry_date"] == date(2031, 2, 1)
    with pytest.raises(ValueError):
        _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 1,
                                                         "expiry_date": "bad"}])


def test_unknown_product_line_writes_nothing(db_session, users):
    before = db_session.query(StockReceipt).count()
    with pytest.raises(ValueError):
        _fourn_receipt(db_session, users["assistant"], [{"product_id": 987654321, "qty_good": 1}])
    assert db_session.query(StockReceipt).count() == before


def test_two_lines_same_product(db_session, users):
    p = _product(db_session, qty=10)
    r = _fourn_receipt(db_session, users["assistant"], [{"product_id": p.medication_id, "qty_good": 3},
                                                       {"product_id": p.medication_id, "qty_good": 4}])
    _ctrl(db_session, users["controller"]).validate_receipt(r["id"])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 17
    assert db_session.query(StockMovement).filter_by(medication_id=p.medication_id,
                                                     movement_type="reception").count() == 2


# R9 : une correction ne peut que REDUIRE ou REDISTRIBUER, jamais ajouter
def _r9_receipt(db, users, qty_good=5, qty_expected=None):
    p = _product(db, qty=0)
    line = {"product_id": p.medication_id, "qty_good": qty_good}
    if qty_expected is not None:
        line["qty_expected"] = qty_expected
    r = _fourn_receipt(db, users["assistant"], [line])
    return p, r, r["lines"][0]["id"], _ctrl(db, users["controller"])


def test_r9_correction_cannot_raise_line_total(db_session, users):
    p, r, lid, c = _r9_receipt(db_session, users, qty_good=5, qty_expected=1000)
    with pytest.raises(ValueError):
        c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 900}])
    with pytest.raises(ValueError):
        c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 5, "qty_damaged": 1}])


def test_r9_correction_cannot_add_line(db_session, users):
    p, r, lid, c = _r9_receipt(db_session, users)
    with pytest.raises(ValueError):
        c.update_receipt_lines(r["id"], [{"id": lid + 999999, "qty_good": 1}])
    with pytest.raises(ValueError):
        c.update_receipt_lines(r["id"], [{"product_id": p.medication_id, "qty_good": 1}])


def test_r9_redistribute_and_reduce_accepted(db_session, users):
    p, r, lid, c = _r9_receipt(db_session, users, qty_good=5)
    out = c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 2, "qty_damaged": 2, "qty_lost": 1}])
    assert out["lines"][0]["qty_good"] == 2
    out = c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 1, "qty_damaged": 0, "qty_lost": 0}])
    assert out["lines"][0]["qty_good"] == 1


def test_r9_successive_corrections_never_exceed_original(db_session, users):
    p, r, lid, c = _r9_receipt(db_session, users, qty_good=5)
    c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 3}])
    with pytest.raises(ValueError):
        c.update_receipt_lines(r["id"], [{"id": lid, "qty_good": 5}])
    c.validate_receipt(r["id"])
    db_session.expire_all()
    assert db_session.get(Pharmacy, p.medication_id).quantity == 3
