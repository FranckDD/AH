# tests/test_stock_count_schema.py
"""Comptage du stock, tache 1 : tables, CHECK, unicite, index partiel, immuabilite, reglage."""
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from models import Pharmacy, StockCount, StockCountLine, StockCountSettings
from tests.conftest import create_test_user


def _product(db, name="t_sc_prod"):
    p = Pharmacy(drug_name=name, quantity=10, medication_type="Autre")
    db.add(p)
    db.flush()
    return p


def _count(db, user, **kw):
    c = StockCount(started_by=user.user_id, **kw)
    db.add(c)
    db.flush()
    return c


def _line(count, product, **kw):
    vals = dict(count_id=count.id, product_id=product.medication_id,
                counted_qty=5, previous_qty=10, difference=-5,
                counted_at=datetime(2026, 10, 25, 8, 0))  # obligatoire depuis 027
    vals.update(kw)
    return StockCountLine(**vals)


def _refused(db, obj, exc=IntegrityError):
    with pytest.raises(exc):
        with db.begin_nested():
            db.add(obj)
            db.flush()


def _exec_refused(db, sql, params=None):
    with pytest.raises(DBAPIError) as ei:
        with db.begin_nested():
            db.execute(text(sql), params or {})
    return ei.value


def test_valid_creation_and_defaults(db_session):
    user = create_test_user(db_session, "t_sc_ok", "StockController")
    count = _count(db_session, user)
    assert count.status == "en_cours" and count.scope == "tous"
    assert count.started_at is not None and count.submitted_at is None
    line = _line(count, _product(db_session))
    db_session.add(line)
    db_session.flush()
    assert line.movements_during == 0 and line.observation is None
    assert line.adjustment_request_id is None


def test_negative_counted_qty_refused(db_session):
    user = create_test_user(db_session, "t_sc_neg", "StockController")
    count = _count(db_session, user)
    _refused(db_session, _line(count, _product(db_session), counted_qty=-1))


def test_unknown_status_and_scope_refused(db_session):
    user = create_test_user(db_session, "t_sc_enum", "StockController")
    _refused(db_session, StockCount(started_by=user.user_id, status="inconnu"))
    _refused(db_session, StockCount(started_by=user.user_id, scope="inconnue"))


def test_interval_bounds_refused(db_session):
    for bad in (0, 366):
        _exec_refused(db_session, "UPDATE stock_count_settings SET interval_days = :v WHERE id = 1",
                      {"v": bad})


def test_duplicate_count_product_refused(db_session):
    user = create_test_user(db_session, "t_sc_dup", "StockController")
    count = _count(db_session, user)
    prod = _product(db_session)
    db_session.add(_line(count, prod))
    db_session.flush()
    _refused(db_session, _line(count, prod))


def test_one_open_count_per_user(db_session):
    u1 = create_test_user(db_session, "t_sc_u1", "StockController")
    u2 = create_test_user(db_session, "t_sc_u2", "StockController")
    _count(db_session, u1)
    _refused(db_session, StockCount(started_by=u1.user_id))
    other = _count(db_session, u2)
    assert other.id is not None


def test_new_open_count_allowed_after_previous_closed(db_session):
    user = create_test_user(db_session, "t_sc_again", "StockController")
    first = _count(db_session, user)
    db_session.execute(text("UPDATE stock_counts SET status = 'abandonne' WHERE id = :i"),
                       {"i": first.id})
    second = _count(db_session, user)
    assert second.id != first.id


def test_line_update_and_delete_refused(db_session):
    user = create_test_user(db_session, "t_sc_imm", "StockController")
    count = _count(db_session, user)
    line = _line(count, _product(db_session))
    db_session.add(line)
    db_session.flush()
    err = _exec_refused(db_session, "UPDATE stock_count_lines SET counted_qty = 1 WHERE id = :i",
                        {"i": line.id})
    assert "immutable" in str(err)
    _exec_refused(db_session, "DELETE FROM stock_count_lines WHERE id = :i", {"i": line.id})


@pytest.mark.parametrize("final", ["valide", "abandonne"])
def test_closed_count_update_and_delete_refused(db_session, final):
    user = create_test_user(db_session, "t_sc_" + final, "StockController")
    count = _count(db_session, user)
    db_session.execute(text("UPDATE stock_counts SET status = :s WHERE id = :i"),
                       {"s": final, "i": count.id})
    _exec_refused(db_session, "UPDATE stock_counts SET scope = 'selection' WHERE id = :i",
                  {"i": count.id})
    _exec_refused(db_session, "UPDATE stock_counts SET status = 'en_cours' WHERE id = :i",
                  {"i": count.id})
    _exec_refused(db_session, "DELETE FROM stock_counts WHERE id = :i", {"i": count.id})


def test_transition_en_cours_to_valide_allowed(db_session):
    user = create_test_user(db_session, "t_sc_trans", "StockController")
    count = _count(db_session, user)
    db_session.execute(text(
        "UPDATE stock_counts SET status = 'valide', submitted_at = now() WHERE id = :i"),
        {"i": count.id})
    status = db_session.execute(text("SELECT status FROM stock_counts WHERE id = :i"),
                                {"i": count.id}).scalar()
    assert status == "valide"


def test_open_count_can_be_deleted(db_session):
    user = create_test_user(db_session, "t_sc_del", "StockController")
    count = _count(db_session, user)
    db_session.execute(text("DELETE FROM stock_counts WHERE id = :i"), {"i": count.id})
    assert db_session.execute(text("SELECT count(*) FROM stock_counts WHERE id = :i"),
                              {"i": count.id}).scalar() == 0


def test_settings_single_row_and_seed(db_session):
    rows = db_session.query(StockCountSettings).all()
    assert len(rows) == 1 and rows[0].id == 1 and rows[0].interval_days == 30
    _exec_refused(db_session, "INSERT INTO stock_count_settings (id, interval_days) VALUES (2, 30)")
