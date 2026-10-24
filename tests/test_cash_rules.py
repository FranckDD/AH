# tests/test_cash_rules.py
"""Regles pures de la cloture de caisse (pas de base de donnees)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from utils.cash_rules import (
    closing_time_for, compute_line, normalize_mode, overdue_days,
    require_comment_if_gap,
)

UTC = timezone.utc


@pytest.mark.parametrize("raw,expected", [
    ("Espèces", "especes"), ("Especes", "especes"), ("especes", "especes"),
    ("ESPÈCES", "especes"), ("Cash", "especes"), ("  cash ", "especes"),
    ("Mobile Money", "autre_mobile"), ("mobile money", "autre_mobile"),
    ("MTN Money", "mtn_money"), ("mtn_money", "mtn_money"),
    ("Orange Money", "orange_money"), ("orange money", "orange_money"),
    ("Virement", "non_classe"), ("Chèque", "non_classe"),
    ("Cheque", "non_classe"), ("Bitcoin", "non_classe"),
    ("", None), ("   ", None), (None, None),
])
def test_normalize_mode(raw, expected):
    assert normalize_mode(raw) == expected


def test_closing_time_is_22h_utc():
    t = closing_time_for(date(2026, 10, 23))
    assert t.tzinfo is not None
    assert t.astimezone(UTC) == datetime(2026, 10, 23, 22, 0, tzinfo=UTC)


def test_overdue_none_before_23h():
    last = datetime(2026, 10, 22, 22, 0, tzinfo=UTC)  # 22 oct 23:00 local
    now = datetime(2026, 10, 23, 21, 59, tzinfo=UTC)  # 22:59 local
    assert overdue_days(last, now) == []


def test_overdue_exactly_23h_is_inclusive():
    last = datetime(2026, 10, 22, 22, 0, tzinfo=UTC)
    now = datetime(2026, 10, 23, 22, 0, tzinfo=UTC)
    assert overdue_days(last, now) == [date(2026, 10, 23)]


def test_overdue_three_day_outage():
    last = datetime(2026, 10, 20, 22, 0, tzinfo=UTC)  # 20 oct 23:00 local
    now = datetime(2026, 10, 23, 23, 30, tzinfo=UTC)
    assert overdue_days(last, now) == [
        date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)]


def test_overdue_day_already_covered_is_skipped():
    # derniere cloture manuelle le 23 a 23:10 local : le 23 n'est pas du
    last = datetime(2026, 10, 23, 22, 10, tzinfo=UTC)
    now = datetime(2026, 10, 24, 5, 0, tzinfo=UTC)
    assert overdue_days(last, now) == []


def test_overdue_uses_local_date_not_utc():
    # 23:30 local le 23 = 22:30 UTC le 23 ; 00:30 local le 24 = 23:30 UTC le 23
    last = datetime(2026, 10, 22, 22, 0, tzinfo=UTC)
    now = datetime(2026, 10, 23, 23, 30, tzinfo=UTC)
    assert overdue_days(last, now) == [date(2026, 10, 23)]


def test_overdue_accepts_other_timezones():
    last = datetime(2026, 10, 22, 23, 0, tzinfo=timezone(timedelta(hours=1)))
    now = datetime(2026, 10, 23, 17, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert overdue_days(last, now) == [date(2026, 10, 23)]


def test_compute_line_especes():
    r = compute_line("especes", Decimal("100"), Decimal("50"), Decimal("30"),
                     Decimal("120"))
    assert r["expected"] == Decimal("120")
    assert r["difference"] == Decimal("0")


def test_compute_line_mobile_ignores_opening():
    r = compute_line("orange_money", Decimal("999"), Decimal("50"),
                     Decimal("30"), Decimal("20"))
    assert r["expected"] == Decimal("20")
    assert r["difference"] == Decimal("0")


def test_compute_line_gap_negative():
    r = compute_line("especes", Decimal("100"), Decimal("50"), Decimal("30"),
                     Decimal("115"))
    assert r["difference"] == Decimal("-5")


def test_compute_line_no_count_gives_none_difference():
    r = compute_line("mtn_money", Decimal("0"), Decimal("10"), Decimal("0"),
                     None)
    assert r["expected"] == Decimal("10")
    assert r["difference"] is None


def test_compute_line_decimal_exact():
    r = compute_line("especes", Decimal("0"), Decimal("0.1"), Decimal("0"),
                     Decimal("0.3"))
    r2 = compute_line("especes", Decimal("0.1"), Decimal("0.2"), Decimal("0"),
                      Decimal("0.3"))
    assert r2["expected"] == Decimal("0.3")
    assert r2["difference"] == Decimal("0")
    assert r["difference"] == Decimal("0.2")
    assert isinstance(r2["expected"], Decimal)


def test_comment_required_for_nonzero_gap():
    with pytest.raises(ValueError):
        require_comment_if_gap([{"mode": "especes", "difference": Decimal("-5"),
                                 "comment": None}])
    with pytest.raises(ValueError):
        require_comment_if_gap([{"mode": "especes", "difference": Decimal("5"),
                                 "comment": "   "}])


def test_comment_accepted_when_present_or_gap_zero():
    require_comment_if_gap([
        {"mode": "especes", "difference": Decimal("-5"), "comment": "billet dechire"},
        {"mode": "mtn_money", "difference": Decimal("0"), "comment": None},
        {"mode": "orange_money", "difference": None, "comment": None},
    ])
