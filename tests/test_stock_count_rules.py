# tests/test_stock_count_rules.py
"""Regles pures du comptage physique : validation des lignes et statut de frequence."""
from datetime import datetime, timedelta

import pytest

from utils.stock_count_rules import frequency_status, gap_kind, parse_counted_at, validate_counts

IDS = {1, 2, 3}


def test_valid_lines_cleaned():
    out = validate_counts([{"product_id": 2, "counted_qty": 0},
                           {"product_id": 1, "counted_qty": 7, "observation": "  casse  "},
                           {"product_id": 3, "counted_qty": 10_000_000, "observation": "   "}], IDS)
    assert out == [{"product_id": 2, "counted_qty": 0, "observation": None, "counted_at": None},
                   {"product_id": 1, "counted_qty": 7, "observation": "casse", "counted_at": None},
                   {"product_id": 3, "counted_qty": 10_000_000, "observation": None, "counted_at": None}]


def test_integral_float_accepted_as_int():
    out = validate_counts([{"product_id": 1, "counted_qty": 2.0}], IDS)
    assert out[0]["counted_qty"] == 2 and type(out[0]["counted_qty"]) is int


@pytest.mark.parametrize("qty", [True, False, 2.5, "2", None, -1, 10_000_001, float("nan"), float("inf")])
def test_bad_quantities_refused(qty):
    with pytest.raises(ValueError):
        validate_counts([{"product_id": 1, "counted_qty": qty}], IDS)


def test_missing_quantity_refused():
    with pytest.raises(ValueError):
        validate_counts([{"product_id": 1}], IDS)


def test_duplicate_refused():
    with pytest.raises(ValueError, match="double"):
        validate_counts([{"product_id": 1, "counted_qty": 1}, {"product_id": 1, "counted_qty": 2}], IDS)


@pytest.mark.parametrize("pid", [99, None, True, "1"])
def test_unknown_or_bad_product_refused(pid):
    with pytest.raises(ValueError):
        validate_counts([{"product_id": pid, "counted_qty": 1}], IDS)


@pytest.mark.parametrize("lines", [[], None, "x", [None], [1]])
def test_empty_or_malformed_list_refused(lines):
    with pytest.raises(ValueError):
        validate_counts(lines, IDS)


def test_observation_limits():
    assert validate_counts([{"product_id": 1, "counted_qty": 1, "observation": "a" * 1000}], IDS)
    with pytest.raises(ValueError):
        validate_counts([{"product_id": 1, "counted_qty": 1, "observation": "a" * 1001}], IDS)
    with pytest.raises(ValueError):
        validate_counts([{"product_id": 1, "counted_qty": 1, "observation": 12}], IDS)


NOW = datetime(2026, 10, 25, 12, 0, 0)


def test_frequency_never():
    assert frequency_status(None, NOW, 30) == ("jamais_compte", None)


@pytest.mark.parametrize("days,expected", [(0, "a_jour"), (29, "a_jour"), (30, "a_jour"), (31, "en_retard")])
def test_frequency_boundaries(days, expected):
    assert frequency_status(NOW - timedelta(days=days), NOW, 30) == (expected, days)


def test_frequency_floors_partial_days():
    # 30 jours et 23 h : 30 jours entiers -> encore a jour
    assert frequency_status(NOW - timedelta(days=30, hours=23), NOW, 30) == ("a_jour", 30)
    assert frequency_status(NOW - timedelta(days=31, minutes=1), NOW, 30) == ("en_retard", 31)


def test_frequency_interval_one():
    assert frequency_status(NOW - timedelta(days=1), NOW, 1) == ("a_jour", 1)
    assert frequency_status(NOW - timedelta(days=2), NOW, 1) == ("en_retard", 2)


def test_frequency_future_clamped():
    assert frequency_status(NOW + timedelta(hours=2), NOW, 30) == ("a_jour", 0)


def test_gap_kind():
    assert (gap_kind(3), gap_kind(-1), gap_kind(0)) == ("plus", "moins", "aucun")


def test_parse_counted_at():
    assert parse_counted_at(None) is None and parse_counted_at("  ") is None
    assert parse_counted_at("2026-10-25T09:30:00+01:00") == datetime(2026, 10, 25, 8, 30)
    assert parse_counted_at("2026-10-25T08:30:00Z") == datetime(2026, 10, 25, 8, 30)
    assert parse_counted_at("2026-10-25T08:30:00") == datetime(2026, 10, 25, 8, 30)
    out = validate_counts([{"product_id": 1, "counted_qty": 1, "counted_at": "2026-10-25T08:30:00Z"}], IDS)
    assert out[0]["counted_at"] == datetime(2026, 10, 25, 8, 30)


@pytest.mark.parametrize("bad", ["hier", "2026-13-01T00:00:00", 12, True, "2026-10-25T08:30:00+00:00" + " " * 30 + "x"])
def test_parse_counted_at_invalid(bad):
    with pytest.raises(ValueError):
        parse_counted_at(bad)
