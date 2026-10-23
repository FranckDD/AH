"""Regles pures de la Fabrication (sans base de donnees)."""
from decimal import Decimal

import pytest

from utils.fabrication_rules import (
    TRANSITIONS,
    compute_bilan,
    compute_cost,
    next_batch_number,
)


def test_bilan_missing_and_pct():
    b = compute_bilan(120, 112, 3, 2, Decimal("2"))
    assert b["expected"] == 120
    assert b["found"] == 117
    assert b["missing"] == 3
    assert b["missing_pct"] == Decimal("2.50")
    assert b["out_of_tolerance"] is True


def test_bilan_at_tolerance_is_ok():
    b = compute_bilan(120, 112, 3, 2, Decimal("2.5"))
    assert b["out_of_tolerance"] is False


def test_bilan_no_missing():
    b = compute_bilan(120, 118, 1, 1, Decimal("2"))
    assert b["missing"] == 0
    assert b["missing_pct"] == Decimal("0.00")
    assert b["out_of_tolerance"] is False


def test_bilan_found_exceeds_expected():
    with pytest.raises(ValueError):
        compute_bilan(10, 8, 2, 1, Decimal("2"))


@pytest.mark.parametrize("expected", [0, -5])
def test_bilan_expected_not_positive(expected):
    with pytest.raises(ValueError):
        compute_bilan(expected, 0, 0, 0, Decimal("2"))


def test_cost_exact_decimal():
    total, unit = compute_cost(
        [(Decimal("0.1"), Decimal("10")), (Decimal("0.2"), Decimal("10"))], 3
    )
    assert total == Decimal("3.00")
    assert unit == Decimal("1.00")


def test_cost_no_good_bottle():
    total, unit = compute_cost([(Decimal("1"), Decimal("5"))], 0)
    assert total == Decimal("5.00")
    assert unit is None


def test_cost_empty():
    assert compute_cost([], 4) == (Decimal("0.00"), Decimal("0.00"))


def test_batch_number_first():
    assert next_batch_number(None, 2026) == "FAB-2026-0001"


def test_batch_number_same_year():
    assert next_batch_number("FAB-2026-0009", 2026) == "FAB-2026-0010"


def test_batch_number_new_year():
    assert next_batch_number("FAB-2025-0042", 2026) == "FAB-2026-0001"


@pytest.mark.parametrize("bad", ["", "XYZ", "FAB-2026-1", "FAB-26-0001", "FAB-2026-00AB"])
def test_batch_number_bad_format(bad):
    with pytest.raises(ValueError):
        next_batch_number(bad, 2026)


def test_transitions_allowed():
    assert TRANSITIONS == {
        "brouillon": {"en_production", "annule"},
        "en_production": {"termine", "annule"},
        "termine": {"en_production", "expedie", "annule"},
        "expedie": set(),
        "annule": set(),
    }


def test_transitions_forbidden_absent():
    statuses = list(TRANSITIONS)
    allowed = {
        ("brouillon", "en_production"), ("brouillon", "annule"),
        ("en_production", "termine"), ("en_production", "annule"),
        ("termine", "en_production"), ("termine", "expedie"), ("termine", "annule"),
    }
    for a in statuses:
        for b in statuses:
            if (a, b) not in allowed:
                assert b not in TRANSITIONS[a], (a, b)


def test_next_batch_number_rejects_trailing_newline():
    with pytest.raises(ValueError):
        next_batch_number("FAB-2026-0001\n", 2026)


def test_next_batch_number_past_9999():
    assert next_batch_number("FAB-2026-9999", 2026) == "FAB-2026-10000"
    assert next_batch_number("FAB-2026-10000", 2026) == "FAB-2026-10001"
