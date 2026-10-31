"""Calcul et formatage de l'age pour le laboratoire (fonctions pures)."""
from __future__ import annotations

import math
from datetime import date
from typing import Optional

MONTH_DAYS = 30.4375
YEAR_DAYS = 365.25
MAX_YEARS = 130
MAX_DAYS = 47500

_UNIT_FACTORS = {
    "jours": 1,
    "semaines": 7,
    "mois": MONTH_DAYS,
    "ans": YEAR_DAYS,
}


def age_in_days(birth: date, ref: date) -> int:
    if birth > ref:
        raise ValueError("birth date is after reference date")
    return (ref - birth).days


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _month_start(k: int) -> int:
    """First day (inclusive) of the k-th month, months being 30.4375 days."""
    return math.floor(k * MONTH_DAYS)


def _full_months(days: int) -> int:
    """Largest k such that the k-th month has started at `days`."""
    k = int(days / MONTH_DAYS)
    while _month_start(k + 1) <= days:
        k += 1
    while k > 0 and _month_start(k) > days:
        k -= 1
    return k


def format_age(days: int) -> str:
    if days < 0:
        raise ValueError("days must be >= 0")
    if days < 7:
        return f"{days} jour" if days <= 1 else f"{days} jours"
    if days < 30:
        weeks, rest = divmod(days, 7)
        out = _plural(weeks, "semaine", "semaines")
        if rest:
            out += " " + _plural(rest, "jour", "jours")
        return out
    if days < 365:
        k = _full_months(days)
        weeks = (days - _month_start(k)) // 7
        out = f"{k} mois"
        if weeks >= 1:
            out += " " + _plural(weeks, "semaine", "semaines")
        return out
    if days < 1826:
        # Mois COMPLETS (plancher, comme sous un an) : un enfant n'est jamais affiche plus age que son age
        # reel, et 1825 j = "4 ans 11 mois" reste coherent avec select_range (moins de 5 ans en jours).
        k = _full_months(days)
        years, months = divmod(k, 12)
        out = _plural(years, "an", "ans")
        if months:
            out += f" {months} mois"
        return out
    return f"{max(5, int(days / YEAR_DAYS))} ans"


def age_from_external(value: int, unit: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer")
    if value < 0:
        raise ValueError("value must be >= 0")
    factor = _UNIT_FACTORS.get(unit)
    if factor is None:
        raise ValueError(f"unknown unit: {unit!r}")
    if unit == "ans" and value > MAX_YEARS:
        raise ValueError("age too large")
    days = value if unit == "jours" else round(factor * value)
    if days > MAX_DAYS:
        raise ValueError("age too large")
    return days


def _to_int(raw):
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        if isinstance(raw, str):
            raw = raw.strip()
            return int(raw) if raw else None
        f = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or f != int(f):
        return None
    return int(f)


def parse_external_age(info: dict) -> int | None:
    if not isinstance(info, dict):
        return None
    d = _to_int(info.get("age_days"))
    if d is not None:
        return d if 0 <= d <= MAX_DAYS else None
    y = _to_int(info.get("age"))
    if y is not None and 0 <= y <= MAX_YEARS:
        return round(YEAR_DAYS * y)
    return None


# Fenetre de coherence d'une DPA par rapport a la date de reference : au plus 4 semaines de depassement
# et 46 semaines a venir. Hors fenetre, on ne propose rien (None) plutot qu'une valeur fausse.
DPA_WINDOW_PAST_DAYS = 4 * 7
DPA_WINDOW_FUTURE_DAYS = 46 * 7


def gestational_from_dpa(dpa: date, ref: date) -> Optional[int]:
    """Semaines d'amenorrhee proposees a partir de la date presumee d'accouchement (DPA) :
    SA = 40 - floor((DPA - date de reference) / 7 jours), bornee a 0..45 (valeur modifiable par l'utilisateur).
    None si la DPA est hors de la fenetre [-4 semaines, +46 semaines] autour de la reference."""
    delta = (dpa - ref).days
    if delta < -DPA_WINDOW_PAST_DAYS or delta > DPA_WINDOW_FUTURE_DAYS:
        return None
    sa = 40 - delta // 7
    return max(0, min(45, sa))
