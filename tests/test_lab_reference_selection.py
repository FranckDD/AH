"""Selection deterministe des plages de reference (jours, SA, sexe) et age du patient (tache B3)."""
import random
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from repositories.lab_repo import LabRepository, reference_date_for
from utils.business_time import business_today
from utils.lab_reference import select_range

Y = 365


def R(id, sexe="X", amin=None, amax=None, gmin=None, gmax=None, ymin=None, ymax=None):
    return SimpleNamespace(id=id, sexe=sexe, age_min_days=amin, age_max_days=amax,
                           ga_min_weeks=gmin, ga_max_weeks=gmax, age_min=ymin, age_max=ymax)


def legacy(id, ymin, ymax, sexe="X"):
    return R(id, sexe, ymin=ymin, ymax=ymax)


def pick(ranges, sex="X", age=None, ga=None):
    r = select_range(ranges, sex, age, ga)
    return None if r is None else r.id


# ------------------------------------------------------------ anciennes plages (annees)
def test_legacy_years_converted_to_days_inclusive():
    r = legacy(1, 0, 1)                      # 0..1 an => 0..729 jours
    assert pick([r], age=400) == 1
    assert pick([r], age=729) == 1           # (1+1)*365-1 inclus
    assert pick([r], age=730) is None        # le jour suivant exclu
    assert pick([r], age=0) == 1


def test_legacy_lower_bound():
    r = legacy(1, 5, 10)
    assert pick([r], age=5 * Y - 1) is None
    assert pick([r], age=5 * Y) == 1
    assert pick([r], age=11 * Y - 1) == 1
    assert pick([r], age=11 * Y) is None


def test_legacy_0_120_means_no_bound_even_for_unknown_age():
    r = legacy(1, 0, 120)
    assert pick([r], age=None) == 1
    assert pick([r], age=50 * Y) == 1


def test_day_columns_win_over_legacy_when_set():
    r = R(1, amin=0, amax=28, ymin=0, ymax=120)
    assert pick([r], age=29) is None
    assert pick([r], age=28) == 1


# ------------------------------------------------------------ plages en jours
def test_day_bounds_inclusive():
    r = R(1, amin=29, amax=1825)
    assert pick([r], age=28) is None
    assert pick([r], age=29) == 1
    assert pick([r], age=1825) == 1
    assert pick([r], age=1826) is None


def test_only_min_and_open_ended():
    r = R(1, amin=100)
    assert pick([r], age=99) is None
    assert pick([r], age=100) == 1
    assert pick([r], age=40000) == 1
    only_max = R(2, amax=28)
    assert pick([only_max], age=0) == 2
    assert pick([only_max], age=29) is None


def test_unknown_age_only_ranges_without_age_bounds():
    bounded = R(1, amin=0, amax=28)
    free = R(2)
    assert pick([bounded], age=None) is None
    assert pick([bounded, free], age=None) == 2


def test_newborn_prefers_narrow_days_over_legacy_years():
    legacy_r = legacy(1, 0, 1)               # 0..729 jours
    newborn = R(2, amin=0, amax=28)
    assert pick([legacy_r, newborn], age=10) == 2
    assert pick([newborn, legacy_r], age=10) == 2
    assert pick([legacy_r, newborn], age=29) == 1


def test_child_one_year_six_months():
    ranges = [R(1, amin=0, amax=28), R(2, amin=29, amax=5 * Y - 1), legacy(3, 0, 120)]
    assert pick(ranges, age=540) == 2


def test_overlap_narrowest_wins_then_smaller_id():
    a = R(5, amin=0, amax=1000)
    b = R(6, amin=100, amax=200)
    assert pick([a, b], age=150) == 6
    c = R(3, amin=100, amax=200)
    assert pick([b, c, a], age=150) == 3     # meme largeur : plus petit id


def test_open_bound_is_infinite_width():
    closed = R(9, amin=10, amax=40000)
    open_ = R(1, amin=10)
    assert pick([open_, closed], age=20) == 9
    narrow = R(3, amin=10, amax=500)
    assert pick([open_, narrow], age=20) == 3


# ------------------------------------------------------------ sexe
def test_sex_specific_beats_generic_and_other_sex_excluded():
    m, f, x = R(1, "M"), R(2, "F"), R(3, "X")
    assert pick([m, f, x], "F") == 2
    assert pick([m, x], "F") == 3
    assert pick([m], "F") is None
    assert pick([m, f], "X") is None         # sexe inconnu : seulement X / vide
    assert pick([m, f, x], "X") == 3
    assert pick([R(4, None)], "X") == 4
    assert pick([R(4, None)], "M") == 4


def test_more_criteria_first():
    sexed = R(7, "F")
    sexed_aged = R(8, "F", amin=0, amax=39999)   # plus large mais plus de criteres
    generic_aged = R(1, "X", amin=0, amax=28)
    assert pick([sexed, sexed_aged], "F", 100) == 8
    assert pick([sexed, generic_aged], "F", 10) == 1   # un critere chacun : age le plus etroit


# ------------------------------------------------------------ SA
def test_ga_range_requires_ga():
    ga = R(1, "F", gmin=0, gmax=13)
    assert pick([ga], "F", 30 * Y, None) is None
    assert pick([ga], "F", 30 * Y, 10) == 1
    assert pick([ga], "F", 30 * Y, 14) is None
    assert pick([ga], "F", 30 * Y, 13) == 1
    assert pick([ga], "F", 30 * Y, 0) == 1


def test_ga_wins_by_criteria_and_plain_applies_to_everyone():
    plain = R(1, "F")
    ga = R(2, "F", gmin=14, gmax=27)
    assert pick([plain, ga], "F", 30 * Y, 20) == 2
    assert pick([plain, ga], "F", 30 * Y, None) == 1
    assert pick([plain, ga], "F", 30 * Y, 30) == 1


def test_ga_only_vs_age_only():
    ga_only = R(1, gmin=14, gmax=27)
    age_only = R(2, amin=0, amax=39999)
    # un critere chacun : l'intervalle d'age le plus etroit (la plage SA seule est infinie)
    assert pick([ga_only, age_only], "X", 30 * Y, 20) == 2
    assert pick([age_only, ga_only], "X", 30 * Y, 20) == 2
    assert pick([ga_only, age_only], "X", 30 * Y, None) == 2


def test_ga_single_bound():
    r = R(1, gmin=37)
    assert pick([r], "X", None, 36) is None
    assert pick([r], "X", None, 45) == 1


# ------------------------------------------------------------ determinisme
@pytest.mark.parametrize("seed", range(8))
def test_shuffled_input_same_result(seed):
    ranges = [
        R(1, "X"), R(2, "F"), R(3, "F", amin=0, amax=28), R(4, "F", amin=0, amax=729),
        R(5, "F", amin=0, amax=28), R(6, "F", gmin=0, gmax=45), R(7, "M", amin=0, amax=28),
        legacy(8, 0, 120), legacy(9, 0, 1, "F"), R(10, "X", amin=29),
        R(11, "F", amin=0, amax=28, gmin=10, gmax=20),
    ]
    rng = random.Random(seed)
    for sex in ("M", "F", "X"):
        for age in (None, 0, 10, 28, 29, 400, 730, 20 * Y):
            for ga in (None, 5, 15, 40):
                expected = pick(ranges, sex, age, ga)
                for _ in range(5):
                    shuffled = ranges[:]
                    rng.shuffle(shuffled)
                    assert pick(shuffled, sex, age, ga) == expected
                assert pick(ranges, sex, age, ga) == expected


def test_no_candidates_none():
    assert select_range([], "F", 10, None) is None


# ------------------------------------------------------------ _patient_bio (sans base)
def bio_for(result):
    return LabRepository(None)._patient_bio(result)


def _res(patient=None, ext=None, test_date=None, ga=None):
    return SimpleNamespace(patient=patient, external_patient_info=ext, test_date=test_date,
                           gestational_age_weeks=ga)


def test_patient_bio_internal_born_12_days_ago():
    ref = reference_date_for(_res())
    assert ref == business_today()
    p = SimpleNamespace(birth_date=ref - timedelta(days=12), gender="F")
    b = bio_for(_res(patient=p))
    assert b.age_days == 12 and b.sex == "F" and b.ga_weeks is None
    assert b.age_label == "1 semaine 5 jours"


def test_patient_bio_uses_reception_date_and_ga():
    p = SimpleNamespace(birth_date=date(2026, 1, 1), gender="Masculin")
    assert bio_for(_res(patient=p, test_date=datetime(2026, 1, 11, 10, 0))).age_days == 10
    p2 = SimpleNamespace(birth_date=date(1990, 1, 1), gender="F")
    b2 = bio_for(_res(patient=p2, test_date=datetime(2026, 1, 11, 10, 0), ga=22))
    assert b2.ga_weeks == 22 and b2.age_label == "36 ans"


def test_patient_bio_future_or_missing_birth_is_unknown():
    for dob in (None, date(2999, 1, 1)):
        b = bio_for(_res(patient=SimpleNamespace(birth_date=dob, gender="F")))
        assert b.age_days is None and b.age_label is None


def test_patient_bio_external_days_and_legacy_years():
    b = bio_for(_res(ext={"nom": "A", "age_days": 17, "sexe": "M"}))
    assert (b.age_days, b.sex, b.age_label) == (17, "M", "2 semaines 3 jours")
    b = bio_for(_res(ext={"age": 30, "gender": "F"}))
    assert b.age_days == round(365.25 * 30) and b.sex == "F" and b.age_label == "30 ans"
    assert bio_for(_res(ext={"age": "abc"})).age_days is None
    assert tuple(bio_for(_res())) == (None, "X", None, None)


def test_reference_date_converts_to_douala():
    d = reference_date_for(SimpleNamespace(test_date=datetime(2026, 3, 1, 23, 30, tzinfo=timezone.utc)))
    assert d == date(2026, 3, 2)             # 00:30 a Douala (UTC+1)


def test_reference_date_naive_is_douala_whatever_the_process_timezone(monkeypatch):
    """Un test_date naif est deja une heure de Douala : 23:30 reste le meme jour, meme sur un hote UTC."""
    class Boom(datetime):
        def astimezone(self, tz=None):
            if tz is None:
                raise AssertionError("fuseau du processus utilise")
            return super().astimezone(tz)
    naive = Boom(2026, 3, 1, 23, 30)
    assert reference_date_for(SimpleNamespace(test_date=naive)) == date(2026, 3, 1)
    import repositories.lab_repo as lr
    monkeypatch.setattr(lr, "datetime", Boom)
    assert reference_date_for(SimpleNamespace(test_date=Boom(2026, 12, 31, 23, 59))) == date(2026, 12, 31)


# ------------------------------------------------------------ base : colonnes, nullabilite, lecture heritee
def test_db_new_rows_can_omit_legacy_years_and_old_rows_still_select(db_session):
    import uuid
    from models.lab import Examen, Parametre, ReferenceRange
    from sqlalchemy.exc import IntegrityError
    ex = Examen(code=f"RS-{uuid.uuid4().hex[:8]}", nom="RS", categorie="Bio", prix=0)
    db_session.add(ex)
    db_session.flush()
    p = Parametre(examen_id=ex.id, nom_parametre="Hb", unite="g/dL", type_valeur="numeric", input_type="numeric")
    db_session.add(p)
    db_session.flush()
    old = ReferenceRange(parametre_id=p.id, sexe="X", age_min=0, age_max=1, valeur_min=1, valeur_max=2)
    new = ReferenceRange(parametre_id=p.id, sexe="X", age_min_days=0, age_max_days=28, valeur_min=3, valeur_max=4)
    ga = ReferenceRange(parametre_id=p.id, sexe="F", ga_min_weeks=14, ga_max_weeks=27, valeur_min=5, valeur_max=6)
    db_session.add_all([old, new, ga])
    db_session.flush()
    db_session.refresh(p)
    assert new.age_min is None and new.age_max is None
    rs = p.reference_ranges
    assert select_range(rs, "M", 400, None) is old          # ancienne ligne : annees converties
    assert select_range(rs, "M", 10, None) is new
    assert select_range(rs, "F", 30 * Y, 20) is ga
    assert select_range(rs, "F", 30 * Y, None) is None
    db_session.add(ReferenceRange(parametre_id=p.id, sexe="F", ga_min_weeks=46, valeur_min=1, valeur_max=2))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ------------------------------------------------------------ cas partages avec le banc (JS)
import json
from pathlib import Path

_CASES = json.loads((Path(__file__).parent / "fixtures" / "lab_range_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_shared_cases_with_js_selector(case):
    ranges = [SimpleNamespace(**r) for r in case["ranges"]]
    got = select_range(ranges, case["sex"], case["age_days"], case["ga_weeks"])
    assert (None if got is None else got.id) == case["expected_id"]


def test_tie_on_open_bounds_prefers_higher_lower_bound():
    one_year, adult = R(1, amin=365), R(2, amin=18 * Y)
    assert pick([one_year, adult], age=20 * Y) == 2
    assert pick([adult, one_year], age=20 * Y) == 2
    assert pick([one_year, adult], age=2 * Y) == 1
