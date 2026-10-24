# tests/test_business_time.py
import sys
import os
from datetime import datetime, date, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import utils.business_time as bt


def _utc(y, m, d, hh, mm):
    return lambda: datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


def test_business_now_is_douala_naive_from_utc_clock():
    now = bt.business_now(_utc(2026, 10, 23, 23, 30))
    assert now == datetime(2026, 10, 24, 0, 30)
    assert now.tzinfo is None


def test_business_today_rolls_over_at_douala_midnight():
    assert bt.business_today(_utc(2026, 10, 23, 23, 30)) == date(2026, 10, 24)
    assert bt.business_today(_utc(2026, 10, 23, 22, 59)) == date(2026, 10, 23)


def test_default_clock_is_patchable(monkeypatch):
    monkeypatch.setattr(bt, "_utc_clock", _utc(2026, 1, 1, 23, 15))
    assert bt.business_today() == date(2026, 1, 2)
    assert bt.business_now() == datetime(2026, 1, 2, 0, 15)


def test_default_clock_independent_of_process_tz():
    # L'horloge par defaut est aware UTC, donc TZ du processus sans effet.
    assert bt._utc_clock().tzinfo is not None
