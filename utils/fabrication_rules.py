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


# ---------------- sorties declarees (echantillons, autres) ----------------
OUTPUT_REASONS = ("echantillon", "autre")
OUTPUT_NOTE_MAX = 2000


class OutputExceedsAvailable(ValueError):
    """Quantite declaree superieure au disponible (le controleur la traduit en conflit 409)."""


def validate_output(reason, quantity, note, available: int) -> tuple[str, int, Optional[str]]:
    """Valide une sortie declaree ; retourne (motif, quantite entiere, note nettoyee ou None)."""
    if reason not in OUTPUT_REASONS:
        raise ValueError("Motif de sortie invalide : echantillon ou autre.")
    if isinstance(quantity, bool):
        raise ValueError("La quantite doit etre un nombre entier.")
    if isinstance(quantity, float):
        if quantity != quantity or quantity in (float("inf"), float("-inf")) or not quantity.is_integer():
            raise ValueError("La quantite doit etre un nombre entier.")
        quantity = int(quantity)
    elif not isinstance(quantity, int):
        raise ValueError("La quantite doit etre un nombre entier.")
    if quantity <= 0:
        raise ValueError("La quantite doit etre superieure a zero.")
    if note is not None and not isinstance(note, str):
        raise ValueError("Note invalide.")
    note = (note or "").strip() or None
    if note is not None and len(note) > OUTPUT_NOTE_MAX:
        raise ValueError(f"La note depasse {OUTPUT_NOTE_MAX} caracteres.")
    if reason == "autre" and note is None:
        raise ValueError("Une note est obligatoire pour le motif autre.")
    if quantity > available:
        raise OutputExceedsAvailable(
            f"Quantite superieure au disponible du lot ({available} bouteilles).")
    return reason, quantity, note
