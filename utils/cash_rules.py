# utils/cash_rules.py
"""Regles metier pures de la cloture de caisse (pas de base de donnees, Decimal uniquement)."""
import unicodedata
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Africa/Douala")
CLOSING_HOUR = 23

CASH = "especes"
MOBILE_MODES = {"orange_money", "mtn_money", "autre_mobile"}
OFFICIAL_MODES = {CASH} | MOBILE_MODES
UNCLASSIFIED = "non_classe"


def _fold(raw: str) -> str:
    """Minuscules, sans accents, espaces/underscores/tirets ramenes a un espace."""
    nfkd = unicodedata.normalize("NFKD", raw)
    s = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    return " ".join(s.replace("_", " ").replace("-", " ").split())


def normalize_mode(raw: Optional[str]) -> Optional[str]:
    """Texte libre -> code officiel. None si vide, 'non_classe' si inconnu."""
    if raw is None:
        return None
    s = _fold(raw)
    if not s:
        return None
    if s in ("especes", "espece", "cash"):
        return CASH
    if "orange" in s:
        return "orange_money"
    if "mtn" in s:
        return "mtn_money"
    if "mobile" in s or s == "autre mobile":
        return "autre_mobile"
    return UNCLASSIFIED


def closing_time_for(day: date) -> datetime:
    """23:00 heure Africa/Douala du jour donne (datetime avec fuseau)."""
    return datetime.combine(day, time(CLOSING_HOUR, 0), tzinfo=TZ)


def overdue_days(last_period_end: datetime, now: datetime) -> list[date]:
    """Jours locaux (Douala) dont le 23:00 est passe et non couvert, du plus ancien au plus recent.

    Un jour est du si closing_time_for(jour) <= now (inclusif a 23:00 pile) et
    closing_time_for(jour) > last_period_end (strict). Cas limite : si
    last_period_end est deja a/apres le 23:00 d'un jour, ce jour n'est pas du.
    Les deux arguments sont des datetimes avec fuseau (timestamptz).
    """
    if last_period_end.tzinfo is None or now.tzinfo is None:
        raise ValueError("last_period_end and now must be timezone-aware")
    day = last_period_end.astimezone(TZ).date()
    last_day = now.astimezone(TZ).date()
    out: list[date] = []
    while day <= last_day:
        t = closing_time_for(day)
        if last_period_end < t <= now:
            out.append(day)
        day += timedelta(days=1)
    return out


def compute_line(mode: str, opening: Decimal, entries: Decimal,
                 exits: Decimal, counted: Optional[Decimal]) -> dict:
    """Attendu et ecart d'un mode. Opening ignore pour les modes mobiles."""
    base = Decimal(opening) if mode == CASH else Decimal(0)
    expected = base + Decimal(entries) - Decimal(exits)
    difference = None if counted is None else Decimal(counted) - expected
    return {"mode": mode, "expected": expected, "difference": difference}


def require_comment_if_gap(lines: Iterable[dict]) -> None:
    """ValueError si un ecart non nul n'a pas de commentaire non vide (apres espaces)."""
    for line in lines:
        diff = line.get("difference")
        if diff is not None and Decimal(diff) != 0:
            if not (line.get("comment") or "").strip():
                raise ValueError(
                    f"Commentaire obligatoire pour l'ecart du mode {line.get('mode')}")
