# tests/test_stock_schema.py
"""Schema fabrication / reception / avaries du stock (migration 019)."""
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from models.pharmacy import Pharmacy
from models.application_role import ApplicationRole
from models.stock_reception import (
    ProductionLot, StockReceipt, StockReceiptLine, StockIncident,
    StockAdjustmentRequest,
)
from tests.conftest import create_test_user


@pytest.fixture
def ctx(db_session):
    user = create_test_user(db_session, "stock_schema_user", "admin")
    product = Pharmacy(drug_name="Produit schema test", quantity=10, threshold=1,
                       medication_type="Autre")
    db_session.add(product)
    db_session.flush()
    return db_session, user, product


def _lot(user, product, **kw):
    base = dict(lot_number="LOT-20261020-001", product_id=product.medication_id,
                quantity_produced=100, production_date=date(2026, 10, 20),
                created_by=user.user_id)
    base.update(kw)
    return ProductionLot(**base)


def _receipt(user, **kw):
    base = dict(receipt_number="REC-20261020-001", origin="fournisseur",
                received_date=date(2026, 10, 20), created_by=user.user_id)
    base.update(kw)
    return StockReceipt(**base)


def _line(receipt_id, product, **kw):
    base = dict(receipt_id=receipt_id, product_id=product.medication_id, qty_good=1)
    base.update(kw)
    return StockReceiptLine(**base)


def _inc(u, p, **kw):
    base = dict(product_id=p.medication_id, kind="perdu", quantity=1, reason="x",
                incident_date=date(2026, 10, 20), created_by=u.user_id)
    base.update(kw)
    return StockIncident(**base)


def _req(u, p, **kw):
    base = dict(product_id=p.medication_id, kind="correction", quantity=1, reason="x",
                requested_by=u.user_id)
    base.update(kw)
    return StockAdjustmentRequest(**base)


def _rejects(session, obj, constraint):
    """L'insertion doit echouer, et pour la bonne raison (nom de contrainte)."""
    with pytest.raises(IntegrityError) as exc:
        with session.begin_nested():
            session.add(obj)
            session.flush()
    assert constraint in str(exc.value), f"attendu {constraint}, obtenu: {exc.value}"


def test_defaults_and_valid_rows_accepted(ctx):
    s, u, p = ctx
    lot = _lot(u, p)
    s.add(lot)
    s.flush()
    assert lot.status == "produit"
    r = _receipt(u)
    s.add(r)
    s.flush()
    assert r.status == "a_controler"
    s.add(_line(r.id, p, qty_good=3))
    s.flush()


@pytest.mark.parametrize("make, constraint", [
    (lambda u, p: _lot(u, p, status="inconnu"), "production_lots_status_check"),
    (lambda u, p: _receipt(u, origin="autre"), "stock_receipts_origin_check"),
    (lambda u, p: _receipt(u, status="inconnu"), "stock_receipts_status_check"),
    (lambda u, p: _inc(u, p, kind="inconnu"), "stock_incidents_kind_check"),
    (lambda u, p: _inc(u, p, status="inconnu"), "stock_incidents_status_check"),
    (lambda u, p: _req(u, p, kind="inconnu"), "stock_adjustment_requests_kind_check"),
    (lambda u, p: _req(u, p, status="inconnu"), "stock_adjustment_requests_status_check"),
])
def test_unknown_status_or_kind_rejected(ctx, make, constraint):
    s, u, p = ctx
    _rejects(s, make(u, p), constraint)


def test_quantity_checks(ctx):
    s, u, p = ctx
    _rejects(s, _lot(u, p, quantity_produced=0), "production_lots_quantity_check")
    r = _receipt(u)
    s.add(r)
    s.flush()
    _rejects(s, _line(r.id, p, qty_good=-1), "stock_receipt_lines_qty_good_check")
    _rejects(s, _line(r.id, p, qty_damaged=-1), "stock_receipt_lines_qty_damaged_check")
    _rejects(s, _line(r.id, p, qty_lost=-1), "stock_receipt_lines_qty_lost_check")
    _rejects(s, _line(r.id, p, qty_defective=-1), "stock_receipt_lines_qty_defective_check")
    _rejects(s, _inc(u, p, quantity=0), "stock_incidents_quantity_check")
    _rejects(s, _req(u, p, quantity=-1), "stock_adjustment_requests_quantity_check")


def test_null_product_rejected(ctx):
    s, u, p = ctx
    r = _receipt(u)
    s.add(r)
    s.flush()
    for obj in (_line(r.id, p, product_id=None), _inc(u, p, product_id=None),
                _req(u, p, product_id=None)):
        _rejects(s, obj, 'column "product_id"')


def test_origin_lot_coherence(ctx):
    s, u, p = ctx
    lot = _lot(u, p)
    s.add(lot)
    s.flush()
    _rejects(s, _receipt(u, origin="fabrication", production_lot_id=None),
             "stock_receipts_origin_lot_check")
    _rejects(s, _receipt(u, origin="fournisseur", production_lot_id=lot.id),
             "stock_receipts_origin_lot_check")
    ok = _receipt(u, origin="fabrication", production_lot_id=lot.id)
    s.add(ok)
    s.flush()


def test_numbers_unique(ctx):
    s, u, p = ctx
    s.add(_lot(u, p))
    s.add(_receipt(u))
    s.flush()
    _rejects(s, _lot(u, p), "production_lots_lot_number_key")
    _rejects(s, _receipt(u), "stock_receipts_receipt_number_key")


def test_receipt_delete_cascades_to_lines(ctx):
    s, u, p = ctx
    r = _receipt(u)
    s.add(r)
    s.flush()
    s.add(_line(r.id, p, qty_good=2))
    s.flush()
    rid = r.id
    s.execute(text("DELETE FROM stock_receipts WHERE id = :i"), {"i": rid})
    n = s.execute(text("SELECT count(*) FROM stock_receipt_lines WHERE receipt_id = :i"),
                  {"i": rid}).scalar()
    assert n == 0


def test_adjustment_quantity_rules(ctx):
    s, u, p = ctx
    _rejects(s, _req(u, p, kind="reapprovisionnement", quantity=0),
             "stock_adjustment_requests_reappro_qty_check")
    ok = _req(u, p, quantity=0)
    s.add(ok)
    s.flush()
    assert ok.status == "en_attente"


def test_stockcontroller_role_row_exists(db_session):
    role = db_session.query(ApplicationRole).filter_by(role_name="StockController").one_or_none()
    assert role is not None


def test_timestamps_have_server_default():
    from models.stock_reception import ProductionLot as L, StockAdjustmentRequest as A
    assert L.__table__.c.created_at.server_default is not None
    assert A.__table__.c.requested_at.server_default is not None
