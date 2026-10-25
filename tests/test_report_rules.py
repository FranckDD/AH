# tests/test_report_rules.py
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from utils.report_rules import (
    anomaly_key, normalize_anomaly, diff_anomalies, should_notify,
    first_seen_map, worked_days, per_worked_day, parse_period,
)


def A(kind, ref, label="x"):
    return normalize_anomaly({"kind": kind, "ref": ref, "label": label})


def test_anomaly_key_basic():
    assert anomaly_key(" cash_gap ", 12) == "cash_gap:12"
    assert anomaly_key("a1", " r7 ") == "a1:r7"


@pytest.mark.parametrize("kind,ref", [("", "1"), ("  ", "1"), ("k", ""), ("k", "  "), ("K", "1"),
                                       ("a b", "1"), ("a:b", "1"), (None, "1"), ("k", None)])
def test_anomaly_key_refuses(kind, ref):
    with pytest.raises(ValueError):
        anomaly_key(kind, ref)


def test_normalize_anomaly():
    n = normalize_anomaly({"kind": "k", "ref": 5, "label": " Ecart ", "detail": {"a": 1}})
    assert n == {"key": "k:5", "kind": "k", "ref": "5", "label": "Ecart", "detail": {"a": 1}}
    assert normalize_anomaly({"kind": "k", "ref": 5, "label": "L", "detail": "txt"})["detail"] == "txt"
    assert normalize_anomaly({"kind": "k", "ref": 5, "label": "L"})["detail"] is None


@pytest.mark.parametrize("label", [None, "", "   "])
def test_normalize_anomaly_label_required(label):
    with pytest.raises(ValueError):
        normalize_anomaly({"kind": "k", "ref": 1, "label": label})


def test_diff_empty_previous_all_new():
    d = diff_anomalies(set(), [A("k", 1), A("k", 2)])
    assert [a["key"] for a in d["new"]] == ["k:1", "k:2"]
    assert d["still_open"] == [] and d["resolved_keys"] == []


def test_diff_resolved_and_still_open():
    d = diff_anomalies({"k:1", "k:2", "k:0"}, [A("k", 1), A("k", 3)])
    assert [a["key"] for a in d["still_open"]] == ["k:1"]
    assert [a["key"] for a in d["new"]] == ["k:3"]
    assert d["resolved_keys"] == ["k:0", "k:2"]


def test_diff_duplicates_collapse_first_wins():
    d = diff_anomalies(set(), [A("k", 1, "first"), A("k", 1, "second")])
    assert len(d["new"]) == 1 and d["new"][0]["label"] == "first"


NOW = datetime(2026, 10, 25, 12, 0)


def test_should_notify_new():
    assert should_notify([A("k", 1)], [], None, NOW) == (True, "nouveau")
    assert should_notify([A("k", 1)], [A("k", 2)], NOW, NOW) == (True, "nouveau")


def test_should_notify_reminder():
    op = [A("k", 2)]
    assert should_notify([], op, None, NOW) == (True, "rappel")
    assert should_notify([], op, NOW - timedelta(days=7), NOW) == (True, "rappel")
    assert should_notify([], op, NOW - timedelta(days=6, hours=23), NOW) == (False, None)


def test_should_notify_nothing():
    assert should_notify([], [], None, NOW) == (False, None)


def test_first_seen_map_three_days_any_order():
    d1, d2, d3 = date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)
    snaps = [
        {"business_date": d3, "keys": ["a", "b", "c"]},
        {"business_date": d1, "keys": ["a"]},
        {"business_date": d2, "keys": {"a", "b"}},
    ]
    assert first_seen_map(snaps) == {"a": d1, "b": d2, "c": d3}
    assert first_seen_map([]) == {}


def test_worked_days():
    assert worked_days([]) == 0
    d = date(2026, 10, 1)
    assert worked_days([d, d, date(2026, 10, 2)]) == 2
    assert worked_days([datetime(2026, 10, 1, 8), datetime(2026, 10, 1, 17), d]) == 1


def test_per_worked_day():
    assert per_worked_day(Decimal("100"), 0) is None
    assert per_worked_day(Decimal("100"), 3) == Decimal("33.33")
    assert per_worked_day(Decimal("200"), 3) == Decimal("66.67")
    assert per_worked_day(Decimal("1.005"), 1) == Decimal("1.01")
    assert isinstance(per_worked_day(Decimal("10"), 4), Decimal)


def test_parse_period_default_today():
    t = date(2026, 10, 25)
    assert parse_period(None, None, t) == (t, t)
    assert parse_period(date(2026, 10, 1), None, t) == (date(2026, 10, 1), t)
    assert parse_period(None, date(2026, 10, 30), t) == (date(2026, 10, 30), date(2026, 10, 30))
    assert parse_period(None, date(2026, 10, 20), t) == (date(2026, 10, 20), date(2026, 10, 20))
    with pytest.raises(ValueError):
        parse_period(date(2026, 10, 26), None, t)


def test_parse_period_errors_and_limits():
    t = date(2026, 10, 25)
    with pytest.raises(ValueError):
        parse_period(date(2026, 10, 5), date(2026, 10, 4), t)
    start = date(2026, 1, 1)
    assert parse_period(start, start + timedelta(days=365), t) == (start, start + timedelta(days=365))
    with pytest.raises(ValueError):
        parse_period(start, start + timedelta(days=366), t)
    with pytest.raises(ValueError):
        parse_period("2026-10-01", t, t)
    with pytest.raises(ValueError):
        parse_period(datetime(2026, 10, 1), t, t)
