# tests/test_cash_closure_schema.py
"""Cloture de caisse, tache 1 : colonnes received_at, tables de cloture, CHECK, unicite, immuabilite, seed."""
import importlib.util
import pathlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from models import (
    CashClosure, CashClosureCorrection, CashClosureLine, CashClosureStart, PaymentMode,
)
from tests.conftest import create_test_retrait, create_test_transaction, create_test_user

MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / "024_cash_closure.py"


def _migration():
    spec = importlib.util.spec_from_file_location("mig_024", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _closure(**kw):
    start = datetime(2030, 1, 1, 0, 0, tzinfo=timezone.utc)
    vals = dict(period_start=start, period_end=start + timedelta(hours=23),
                business_date=start.date(), kind="auto", opening_cash=Decimal("0"),
                expected_cash=Decimal("0"))
    vals.update(kw)
    return CashClosure(**vals)


def _insert(db, obj):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(obj)
            db.flush()


def test_seed_payment_modes(db_session):
    modes = {m.code: m for m in db_session.query(PaymentMode).all()}
    assert {"especes", "orange_money", "mtn_money", "autre_mobile"} <= set(modes)
    assert modes["especes"].is_active is True


def test_received_at_defaults_to_now_on_insert(db_session):
    user = create_test_user(db_session, "t_cc_recv", "secretaire")
    tx = create_test_transaction(db_session, user)
    r = create_test_retrait(db_session, user)
    db_session.execute(text(
        "INSERT INTO paiement_echelonne (transaction_id, paid_amount, payment_method, payment_type, handled_by) "
        "VALUES (:t, 10, 'Especes', 'VERSEMENT', :u)"), {"t": tx.transaction_id, "u": user.user_id})
    now = db_session.execute(text("SELECT now()")).scalar()
    pe = db_session.execute(text(
        "SELECT received_at FROM paiement_echelonne WHERE transaction_id = :t "
        "ORDER BY payment_id DESC LIMIT 1"), {"t": tx.transaction_id}).scalar()
    rt = db_session.execute(text(
        "SELECT received_at FROM caisse_retrait WHERE retrait_id = :r"), {"r": r.retrait_id}).scalar()
    for value in (pe, rt):
        assert value is not None and abs((now - value).total_seconds()) < 60


def test_backfill_uses_correct_timezones(db_session):
    mig = _migration()
    db_session.execute(text("CREATE TEMP TABLE bf_pe (payment_date timestamp, received_at timestamptz)"))
    db_session.execute(text("CREATE TEMP TABLE bf_rt (retrait_at timestamp, received_at timestamptz)"))
    db_session.execute(text("INSERT INTO bf_pe (payment_date) VALUES ('2026-03-10 12:00:00')"))
    db_session.execute(text("INSERT INTO bf_rt (retrait_at) VALUES ('2026-03-10 12:00:00')"))
    db_session.execute(text(mig.BACKFILL_SQL.format(table="bf_pe", expr=mig.PAIEMENT_EXPR)))
    db_session.execute(text(mig.BACKFILL_SQL.format(table="bf_rt", expr=mig.RETRAIT_EXPR)))
    pe = db_session.execute(text("SELECT received_at AT TIME ZONE 'UTC' FROM bf_pe")).scalar()
    rt = db_session.execute(text("SELECT received_at AT TIME ZONE 'UTC' FROM bf_rt")).scalar()
    assert pe == datetime(2026, 3, 10, 11, 0)   # Africa/Lagos = UTC+1
    assert rt == datetime(2026, 3, 10, 12, 0)   # deja en UTC


def test_closure_checks(db_session):
    user = create_test_user(db_session, "t_cc_chk", "secretaire")
    _insert(db_session, _closure(kind="manual", closed_by=user.user_id, counted_cash=Decimal("-1")))
    _insert(db_session, _closure(kind="weekly"))
    start = datetime(2030, 1, 1, tzinfo=timezone.utc)
    _insert(db_session, _closure(period_start=start, period_end=start))
    _insert(db_session, _closure(period_start=start, period_end=start - timedelta(hours=1)))
    _insert(db_session, _closure(kind="manual", closed_by=None))  # manuelle sans auteur


def test_line_and_correction_checks(db_session):
    user = create_test_user(db_session, "t_cc_line", "secretaire")
    c = _closure()
    db_session.add(c)
    db_session.flush()
    _insert(db_session, CashClosureLine(closure_id=c.id, mode_code="especes", source="bogus"))
    _insert(db_session, CashClosureLine(closure_id=c.id, mode_code="especes", source="physical",
                                        counted=Decimal("-5")))
    _insert(db_session, CashClosureCorrection(closure_id=c.id, mode_code="especes",
                                              amount_delta=Decimal("5"), reason="x", status="bogus",
                                              requested_by=user.user_id))
    _insert(db_session, CashClosureCorrection(closure_id=c.id, mode_code="especes",
                                              amount_delta=Decimal("5"), reason="   ",
                                              requested_by=user.user_id))
    db_session.add(CashClosureLine(closure_id=c.id, mode_code="especes", source="physical"))
    db_session.flush()
    _insert(db_session, CashClosureLine(closure_id=c.id, mode_code="especes", source="physical"))


def test_period_end_unique(db_session):
    db_session.add(_closure())
    db_session.flush()
    _insert(db_session, _closure())


def test_closure_is_immutable(db_session):
    c = _closure(counted_cash=Decimal("10"))
    db_session.add(c)
    db_session.flush()
    line = CashClosureLine(closure_id=c.id, mode_code="especes", source="physical")
    db_session.add(line)
    db_session.flush()
    for sql in (f"UPDATE cash_closures SET counted_cash = 99 WHERE id = {c.id}",
                f"DELETE FROM cash_closures WHERE id = {c.id}",
                f"UPDATE cash_closure_lines SET counted = 99 WHERE id = {line.id}",
                f"DELETE FROM cash_closure_lines WHERE id = {line.id}"):
        with pytest.raises(DBAPIError):
            with db_session.begin_nested():
                db_session.execute(text(sql))


def test_correction_status_is_mutable(db_session):
    user = create_test_user(db_session, "t_cc_corr", "admin")
    c = _closure()
    db_session.add(c)
    db_session.flush()
    corr = CashClosureCorrection(closure_id=c.id, mode_code="especes", amount_delta=Decimal("-3"),
                                 reason="erreur de comptage", requested_by=user.user_id)
    db_session.add(corr)
    db_session.flush()
    db_session.execute(text(
        "UPDATE cash_closure_corrections SET status = 'approved', decided_by = :u WHERE id = :i"),
        {"u": user.user_id, "i": corr.id})


def test_closure_start_single_row_and_immutable(db_session):
    if db_session.query(CashClosureStart).count():
        pytest.skip("depart deja pose sur la base de dev (immuable)")
    _insert(db_session, CashClosureStart(id=2, started_at=datetime.now(timezone.utc),
                                         opening_cash=Decimal("0")))
    _insert(db_session, CashClosureStart(id=1, started_at=datetime.now(timezone.utc),
                                         opening_cash=Decimal("-1")))
    db_session.add(CashClosureStart(id=1, started_at=datetime.now(timezone.utc),
                                    opening_cash=Decimal("500")))
    db_session.flush()
    with pytest.raises(DBAPIError):
        with db_session.begin_nested():
            db_session.execute(text("UPDATE cash_closure_start SET opening_cash = 1"))
    with pytest.raises(DBAPIError):
        with db_session.begin_nested():
            db_session.execute(text("DELETE FROM cash_closure_start"))
