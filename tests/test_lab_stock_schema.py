# tests/test_lab_stock_schema.py
"""Schema du stock labo (migration 021)."""
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models.lab_stock import (
    LabStockProduct, LabStockReceipt, LabStockReceiptLine, LabStockMovement,
    LabStockRequest, LabStockCount, LabStockCountLine,
)
from tests.conftest import create_test_user


@pytest.fixture
def ctx(db_session):
    user = create_test_user(db_session, "lab_stock_schema_user", "admin")
    return db_session, user


def _product(user, name="Reactif A", **kw):
    return LabStockProduct(name=name, created_by=user.user_id, **kw)


def _receipt(user, **kw):
    base = dict(invoice_number="F-001", supplier="Fournisseur X",
                delivery_date=date(2026, 10, 21), total_amount=0,
                created_by=user.user_id)
    base.update(kw)
    return LabStockReceipt(**base)


def _bad(session, obj, constraint):
    """L'insertion doit echouer, pour la bonne raison (nom de contrainte/index)."""
    with pytest.raises(IntegrityError) as exc:
        with session.begin_nested():
            session.add(obj)
            session.flush()
    assert constraint in str(exc.value), f"attendu {constraint}, obtenu: {exc.value}"


def test_constants():
    from utils.lab_stock_rules import EXPIRY_WARNING_DAYS, COUNT_REMINDER_DAYS
    assert EXPIRY_WARNING_DAYS == 60
    assert COUNT_REMINDER_DAYS == 7


def test_product_defaults(ctx):
    s, u = ctx
    p = _product(u)
    s.add(p)
    s.flush()
    assert p.quantity == 0 and p.alert_threshold == 0 and p.is_active is True


def test_product_negative_quantity_refused(ctx):
    s, u = ctx
    _bad(s, _product(u, name="Neg qty", quantity=-1), "lab_stock_products_quantity_check")


def test_product_negative_threshold_refused(ctx):
    s, u = ctx
    _bad(s, _product(u, name="Neg thr", alert_threshold=-1), "lab_stock_products_threshold_check")


def test_active_name_unique_case_insensitive(ctx):
    s, u = ctx
    s.add(_product(u, name="Tubes EDTA"))
    s.flush()
    _bad(s, _product(u, name="tubes edta"), "uq_lab_stock_products_name_active")


def test_inactive_product_allows_recreation(ctx):
    s, u = ctx
    s.add(_product(u, name="Gants", is_active=False))
    s.flush()
    s.add(_product(u, name="GANTS"))
    s.flush()


def test_receipt_status_check(ctx):
    s, u = ctx
    _bad(s, _receipt(u, status="autre"), "lab_stock_receipts_status_check")


def test_receipt_negative_total_refused(ctx):
    s, u = ctx
    _bad(s, _receipt(u, total_amount=-1), "lab_stock_receipts_total_check")


def test_receipt_duplicate_invoice_refused_while_valid(ctx):
    s, u = ctx
    s.add(_receipt(u))
    s.flush()
    _bad(s, _receipt(u, supplier="fournisseur x", invoice_number="f-001"),
         "uq_lab_stock_receipts_supplier_invoice")


def test_receipt_duplicate_invoice_allowed_if_first_cancelled(ctx):
    s, u = ctx
    s.add(_receipt(u, status="annule"))
    s.flush()
    s.add(_receipt(u))
    s.flush()


def _line_ctx(s, u):
    p = _product(u, name="Produit ligne")
    r = _receipt(u)
    s.add_all([p, r])
    s.flush()
    return p, r


def _line(p, r, **kw):
    base = dict(receipt_id=r.id, product_id=p.id, received_qty=5, unit_price=10,
                line_total=50, lot_number="L1", expiry_date=date(2027, 1, 1))
    base.update(kw)
    return LabStockReceiptLine(**base)


def test_line_received_qty_zero_refused(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    _bad(s, _line(p, r, received_qty=0), "lab_stock_receipt_lines_received_check")


def test_line_negative_values_refused(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    _bad(s, _line(p, r, unit_price=-1), "lab_stock_receipt_lines_price_check")


def test_line_negative_ordered_refused(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    _bad(s, _line(p, r, ordered_qty=-1), "lab_stock_receipt_lines_ordered_check")


def test_line_lot_required(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    _bad(s, _line(p, r, lot_number=None), "lot_number")


def test_line_expiry_required(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    _bad(s, _line(p, r, expiry_date=None), "expiry_date")


def test_line_negative_total_refused(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    _bad(s, _line(p, r, line_total=-1), "lab_stock_receipt_lines_total_check")


def test_receipt_delete_cascades_lines(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    s.add(_line(p, r))
    s.flush()
    rid = r.id
    s.execute(text("DELETE FROM lab_stock_receipts WHERE id = :i"), {"i": rid})
    n = s.execute(text("SELECT count(*) FROM lab_stock_receipt_lines WHERE receipt_id = :i"),
                  {"i": rid}).scalar()
    assert n == 0


def _count_ctx(s, u):
    p = _product(u, name="Produit comptage")
    c = LabStockCount(counted_by=u.user_id)
    s.add_all([p, c])
    s.flush()
    return p, c


def test_count_line_negative_previous_refused(ctx):
    s, u = ctx
    p, c = _count_ctx(s, u)
    _bad(s, LabStockCountLine(count_id=c.id, product_id=p.id, previous_qty=-1, counted_qty=0),
         "lab_stock_count_lines_previous_check")


def test_count_line_negative_counted_refused(ctx):
    s, u = ctx
    p, c = _count_ctx(s, u)
    _bad(s, LabStockCountLine(count_id=c.id, product_id=p.id, previous_qty=0, counted_qty=-1),
         "lab_stock_count_lines_counted_check")


def test_count_delete_cascades_lines(ctx):
    s, u = ctx
    p, c = _count_ctx(s, u)
    s.add(LabStockCountLine(count_id=c.id, product_id=p.id, previous_qty=1, counted_qty=2))
    s.flush()
    cid = c.id
    s.execute(text("DELETE FROM lab_stock_counts WHERE id = :i"), {"i": cid})
    n = s.execute(text("SELECT count(*) FROM lab_stock_count_lines WHERE count_id = :i"),
                  {"i": cid}).scalar()
    assert n == 0


def test_line_valid_inserts(ctx):
    s, u = ctx
    p, r = _line_ctx(s, u)
    s.add(_line(p, r, ordered_qty=None))
    s.flush()


def test_movement_type_and_negative_after_refused(ctx):
    s, u = ctx
    p = _product(u, name="Produit mvt")
    s.add(p)
    s.flush()
    _bad(s, LabStockMovement(product_id=p.id, change_qty=1, movement_type="autre",
                             quantity_after=1, created_by=u.user_id),
         "lab_stock_movements_type_check")
    p = _product(u, name="Produit mvt 2")
    s.add(p)
    s.flush()
    _bad(s, LabStockMovement(product_id=p.id, change_qty=-1, movement_type="comptage",
                             quantity_after=-1, created_by=u.user_id),
         "lab_stock_movements_after_check")


def test_request_origin_status_level_checks(ctx):
    s, u = ctx
    p = _product(u, name="Produit dem")
    s.add(p)
    s.flush()
    pid = p.id
    _bad(s, LabStockRequest(product_id=pid, origin="autre"), "lab_stock_requests_origin_check")
    p = _product(u, name="Produit dem 2")
    s.add(p)
    s.flush()
    _bad(s, LabStockRequest(product_id=p.id, origin="seuil", status="autre"),
         "lab_stock_requests_status_check")
    p = _product(u, name="Produit dem 3")
    s.add(p)
    s.flush()
    _bad(s, LabStockRequest(product_id=p.id, origin="signalement", level="autre"),
         "lab_stock_requests_level_check")


def test_one_open_request_per_product(ctx):
    s, u = ctx
    p = _product(u, name="Produit unique")
    s.add(p)
    s.flush()
    s.add(LabStockRequest(product_id=p.id, origin="seuil"))
    s.flush()
    _bad(s, LabStockRequest(product_id=p.id, origin="signalement", level="fini",
                            status="commande"), "uq_lab_stock_requests_open_product")


def test_new_request_allowed_after_closed(ctx):
    s, u = ctx
    p = _product(u, name="Produit clos")
    s.add(p)
    s.flush()
    s.add(LabStockRequest(product_id=p.id, origin="seuil", status="recu"))
    s.add(LabStockRequest(product_id=p.id, origin="seuil", status="annule"))
    s.flush()
    s.add(LabStockRequest(product_id=p.id, origin="seuil"))
    s.flush()
