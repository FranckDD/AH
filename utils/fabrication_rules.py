# utils/fabrication_rules.py
"""Regles metier pures de la Fabrication (pas de base de donnees, Decimal uniquement)."""
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

_CENT = Decimal("0.01")

TRANSITIONS: dict[str, set[str]] = {
    "brouillon": {"en_production", "annule"},
    "en_production": {"termine", "annule"},
    "termine": {"en_production", "expedie", "annule"},
    "expedie": set(),
    "annule": set(),
}

_BATCH_RE = re.compile(r"FAB-(\d{4})-(\d{4,})")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def compute_bilan(expected: int, good: int, damaged: int, rejected: int,
                  tolerance_pct: Decimal) -> dict:
    """Bilan d'un lot : manque non explique et depassement de tolerance."""
    if expected <= 0:
        raise ValueError("expected must be positive")
    found = good + damaged + rejected
    if found > expected:
        raise ValueError("found exceeds expected")
    missing = expected - found
    missing_pct = _q(Decimal(missing) * 100 / Decimal(expected))
    return {
        "expected": expected,
        "found": found,
        "missing": missing,
        "missing_pct": missing_pct,
        # comparaison exacte (non arrondie) : missing/expected > tolerance/100
        "out_of_tolerance": Decimal(missing) * 100 > Decimal(expected) * Decimal(tolerance_pct),
    }


def compute_cost(consumptions: list[tuple[Decimal, Decimal]], good: int
                 ) -> tuple[Decimal, Optional[Decimal]]:
    """Cout du lot (somme quantite x cout unitaire) et cout par bouteille bonne."""
    total = _q(sum((Decimal(q) * Decimal(c) for q, c in consumptions), Decimal("0")))
    if good <= 0:
        return total, None
    return total, _q(total / Decimal(good))


def next_batch_number(last: Optional[str], year: int) -> str:
    """Numero de lot suivant, au format FAB-AAAA-NNNN."""
    if last is None:
        return f"FAB-{year:04d}-0001"
    m = _BATCH_RE.fullmatch(last)
    if not m:
        raise ValueError(f"bad batch number format: {last!r}")
    if int(m.group(1)) != year:
        return f"FAB-{year:04d}-0001"
    return f"FAB-{year:04d}-{int(m.group(2)) + 1:04d}"
