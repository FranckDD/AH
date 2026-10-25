# tests/test_report_schema.py
"""Rapports / controle quotidien, tache 1 : tables daily_controls et report_settings."""
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from models import DailyControl, ReportSettings


def _refused(db, obj):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(obj)
            db.flush()


def _exec_refused(db, sql, params=None):
    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.execute(text(sql), params or {})


def test_valid_creation_and_defaults(db_session):
    c = DailyControl(business_date=date(2099, 1, 1))
    db_session.add(c)
    db_session.flush()
    db_session.refresh(c)
    assert c.anomalies == []
    assert c.new_count == 0 and c.open_count == 0
    assert c.computed_at is not None
    assert c.notified_at is None and c.reminder_sent_at is None
    assert c.recomputed is False


def test_anomalies_roundtrip(db_session):
    items = [{"key": "k1", "kind": "x", "ref": 1, "label": "l", "detail": "d",
              "first_seen": "2099-01-02"}]
    c = DailyControl(business_date=date(2099, 1, 2), anomalies=items, new_count=1, open_count=1)
    db_session.add(c)
    db_session.flush()
    db_session.expire(c)
    assert c.anomalies == items


def test_duplicate_business_date_refused(db_session):
    db_session.add(DailyControl(business_date=date(2099, 1, 3)))
    db_session.flush()
    _refused(db_session, DailyControl(business_date=date(2099, 1, 3)))


def test_anomalies_must_be_array(db_session):
    _refused(db_session, DailyControl(business_date=date(2099, 1, 4), anomalies={"a": 1}))


def test_negative_counts_refused(db_session):
    _refused(db_session, DailyControl(business_date=date(2099, 1, 5), new_count=-1))
    _refused(db_session, DailyControl(business_date=date(2099, 1, 6), open_count=-1))


def test_business_date_index_exists(db_session):
    names = {r[0] for r in db_session.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'daily_controls'"))}
    assert "idx_daily_controls_business_date" in names


def test_settings_seeded_single_row(db_session):
    rows = db_session.query(ReportSettings).all()
    assert len(rows) == 1 and rows[0].id == 1
    s = rows[0]
    # la valeur peut avoir ete modifiee en dev : on verifie les bornes, pas le defaut
    assert 1 <= s.cancelled_sales_threshold <= 1000
    assert 1 <= s.adjustment_pending_days <= 365
    assert s.updated_at is not None


def test_settings_defaults_when_column_omitted(db_session):
    defaults = {r[0]: r[1] for r in db_session.execute(text(
        "SELECT column_name, column_default FROM information_schema.columns "
        "WHERE table_name = 'report_settings'"))}
    assert defaults["cancelled_sales_threshold"] == "3"
    assert defaults["adjustment_pending_days"] == "3"


@pytest.mark.parametrize("col,bad", [
    ("cancelled_sales_threshold", 0), ("cancelled_sales_threshold", 1001),
    ("adjustment_pending_days", 0), ("adjustment_pending_days", 366),
])
def test_threshold_bounds_refused(db_session, col, bad):
    _exec_refused(db_session, f"UPDATE report_settings SET {col} = :v WHERE id = 1", {"v": bad})


def test_settings_second_row_refused(db_session):
    _exec_refused(db_session, "INSERT INTO report_settings (id) VALUES (2)")
