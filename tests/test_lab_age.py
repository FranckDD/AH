import re
from datetime import date

import pytest

from utils.lab_age import (
    age_from_external, age_in_days, format_age, parse_external_age,
)

CASES = {
    0: "0 jour", 1: "1 jour", 6: "6 jours", 7: "1 semaine",
    13: "1 semaine 6 jours", 14: "2 semaines", 17: "2 semaines 3 jours",
    27: "3 semaines 6 jours", 28: "4 semaines", 29: "4 semaines 1 jour",
    30: "1 mois", 31: "1 mois", 45: "1 mois 2 semaines",
    59: "1 mois 4 semaines", 60: "2 mois", 61: "2 mois", 100: "3 mois 1 semaine",
    364: "11 mois 4 semaines", 365: "1 an", 540: "1 an 5 mois", 548: "1 an 6 mois",
    1000: "2 ans 8 mois", 716: "1 an 11 mois", 1081: "2 ans 11 mois", 1811: "4 ans 11 mois",
    1825: "4 ans 11 mois", 1826: "5 ans", 1827: "5 ans", 3652: "9 ans",
}


@pytest.mark.parametrize("days,expected", CASES.items())
def test_format_age(days, expected):
    assert format_age(days) == expected


def test_format_negative():
    with pytest.raises(ValueError):
        format_age(-1)


def test_age_in_days():
    assert age_in_days(date(2024, 5, 1), date(2024, 5, 1)) == 0
    assert age_in_days(date(2024, 2, 29), date(2025, 2, 28)) == 365
    assert age_in_days(date(2024, 2, 29), date(2025, 3, 1)) == 366
    assert age_in_days(date(2023, 3, 1), date(2024, 3, 1)) == 366
    assert age_in_days(date(2024, 3, 1), date(2025, 3, 1)) == 365
    assert age_in_days(date(2000, 1, 1), date(2004, 1, 1)) == 1461
    with pytest.raises(ValueError):
        age_in_days(date(2025, 1, 2), date(2025, 1, 1))


def test_external_conversions():
    assert age_from_external(5, "jours") == 5
    assert age_from_external(3, "semaines") == 21
    assert age_from_external(1, "mois") == 30
    assert age_from_external(6, "mois") == 183
    assert age_from_external(12, "mois") == 365
    assert age_from_external(1, "ans") == 365
    assert age_from_external(4, "ans") == 1461
    assert age_from_external(0, "ans") == 0
    assert age_from_external(130, "ans") == round(365.25 * 130)


@pytest.mark.parametrize("value,unit", [
    (-1, "jours"), (1, "heures"), (131, "ans"), (47501, "jours"),
    (7000, "semaines"), (1600, "mois"), (1.5, "ans"), ("3", "ans"), (True, "ans"),
])
def test_external_rejects(value, unit):
    with pytest.raises(ValueError):
        age_from_external(value, unit)


def test_parse_external():
    assert parse_external_age({"age_days": 12}) == 12
    assert parse_external_age({"age_days": "12"}) == 12
    assert parse_external_age({"age_days": 12, "age": 40}) == 12
    assert parse_external_age({"age": 40}) == 14610
    assert parse_external_age({"age": "1"}) == 365
    assert parse_external_age({"age": 0}) == 0
    assert parse_external_age({}) is None
    assert parse_external_age({"age": "abc"}) is None
    assert parse_external_age({"age": -3}) is None
    assert parse_external_age({"age_days": -3}) is None
    assert parse_external_age({"age_days": None, "age": None}) is None
    assert parse_external_age({"age": 200}) is None
    assert parse_external_age({"age_days": float("nan")}) is None
    assert parse_external_age({"age": True}) is None
    assert parse_external_age(None) is None


def _approx_days(text):
    total = 0.0
    for n, unit in re.findall(r"(\d+) (jours?|semaines?|mois|ans?)", text):
        n = int(n)
        total += n * {"jour": 1, "jours": 1, "semaine": 7, "semaines": 7,
                      "mois": 30.4375, "an": 365.25, "ans": 365.25}[unit]
    return total


def test_never_zero_years_and_monotone():
    prev = -1.0
    for d in range(0, 1826):
        text = format_age(d)
        assert not text.startswith("0 an")
        val = _approx_days(text)
        assert val >= prev, (d, text)
        prev = val
    for d in range(1826, 47501, 37):
        assert format_age(d).endswith(" ans")


def test_label_never_reaches_5_years_before_the_under_5_norm_ends():
    """Le libelle imprime et select_range (bornes en jours) doivent changer de tranche le meme jour."""
    for d in range(365, 1826):
        assert not re.match(r"[5-9]\d* ans|\d{2,} ans", format_age(d)), d
    assert format_age(1826) == "5 ans"


# --- Fixture partagee avec le port JavaScript (ah2-admin-web/src/utils/labAge.js, test labAgePregnancy.test.mjs) ---
import json
from pathlib import Path

from utils.lab_age import gestational_from_dpa

_SHARED = json.loads((Path(__file__).parent / "fixtures" / "lab_age_cases.json").read_text(encoding="utf-8"))


def test_shared_fixture_format_age():
    assert len(_SHARED["format_age"]) > 1000
    for days, label in _SHARED["format_age"].items():
        assert format_age(int(days)) == label, days


def test_shared_fixture_age_from_external():
    for value, unit, expected in _SHARED["age_from_external"]:
        if expected is None:
            with pytest.raises(ValueError):
                age_from_external(value, unit)
        else:
            assert age_from_external(value, unit) == expected, (value, unit)


def test_shared_fixture_age_in_days():
    for birth, ref, expected in _SHARED["age_in_days"]:
        if expected is None:
            with pytest.raises(ValueError):
                age_in_days(date.fromisoformat(birth), date.fromisoformat(ref))
        else:
            assert age_in_days(date.fromisoformat(birth), date.fromisoformat(ref)) == expected


def test_shared_fixture_sa_from_dpa():
    for dpa, ref, expected in _SHARED["sa_from_dpa"]:
        assert gestational_from_dpa(date.fromisoformat(dpa), date.fromisoformat(ref)) == expected


def test_sa_from_dpa_rules():
    ref = date(2026, 10, 31)
    assert gestational_from_dpa(date(2027, 1, 1), ref) == 40 - 62 // 7
    assert gestational_from_dpa(ref, ref) == 40
    # Hors fenetre [-4 semaines, +46 semaines] : aucune proposition (pas de valeur ecretee trompeuse)
    assert gestational_from_dpa(date(2026, 1, 1), ref) is None
    assert gestational_from_dpa(date(2029, 1, 1), ref) is None
    assert gestational_from_dpa(date(2026, 10, 3), ref) == 44   # -28 jours : borne incluse
    assert gestational_from_dpa(date(2026, 10, 2), ref) is None  # -29 jours
    assert gestational_from_dpa(date(2027, 9, 18), ref) == 0     # +322 jours : borne incluse
    assert gestational_from_dpa(date(2027, 9, 19), ref) is None  # +323 jours
