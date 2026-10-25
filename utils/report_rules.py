# utils/report_rules.py
"""Regles pures des Rapports / controle quotidien (aucun acces base)."""
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

MAX_PERIOD_DAYS = 366
REMINDER_INTERVAL = timedelta(days=7)
_KIND_RE = re.compile(r"^[a-z0-9_]+$")


def anomaly_key(kind: Any, ref: Any) -> str:
    """Cle stable d'une anomalie : '{kind}:{ref}'. Valeurs vides refusees."""
    if not isinstance(kind, str) or kind is None:
        raise ValueError("Type d'anomalie invalide.")
    k = kind.strip()
    if not k or not _KIND_RE.match(k):
        raise ValueError("Type d'anomalie invalide.")
    if ref is None or isinstance(ref, bool):
        raise ValueError("Reference d'anomalie invalide.")
    r = str(ref).strip()
    if not r:
        raise ValueError("Reference d'anomalie invalide.")
    return f"{k}:{r}"


def normalize_anomaly(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Anomalie invalide.")
    key = anomaly_key(raw.get("kind"), raw.get("ref"))
    label = raw.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("Libelle d'anomalie requis.")
    kind, _, ref = key.partition(":")
    return {"key": key, "kind": kind, "ref": ref, "label": label.strip(), "detail": raw.get("detail")}


def diff_anomalies(previous_keys: Set[str], today: List[Dict[str, Any]]) -> Dict[str, Any]:
    prev = set(previous_keys or ())
    seen: Set[str] = set()
    new: List[Dict[str, Any]] = []
    still_open: List[Dict[str, Any]] = []
    for a in today:
        k = a["key"]
        if k in seen:
            continue
        seen.add(k)
        (still_open if k in prev else new).append(a)
    return {"new": new, "still_open": still_open, "resolved_keys": sorted(prev - seen)}


def should_notify(new: List[Any], still_open: List[Any], last_reminder_at: Optional[datetime],
                  now: datetime) -> Tuple[bool, Optional[str]]:
    if new:
        return True, "nouveau"
    if still_open and (last_reminder_at is None or now - last_reminder_at >= REMINDER_INTERVAL):
        return True, "rappel"
    return False, None


def first_seen_map(snapshots: List[Dict[str, Any]]) -> Dict[str, date]:
    out: Dict[str, date] = {}
    for snap in sorted(snapshots, key=lambda s: s["business_date"]):
        d = snap["business_date"]
        for k in snap["keys"]:
            out.setdefault(k, d)
    return out


def worked_days(payment_dates: Iterable[Any]) -> int:
    days = set()
    for d in payment_dates:
        days.add(d.date() if isinstance(d, datetime) else d)
    return len(days)


def per_worked_day(total: Decimal, days: int) -> Optional[Decimal]:
    if days == 0:
        return None
    return (Decimal(total) / days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _as_date(v: Any, label: str) -> date:
    if isinstance(v, datetime) or not isinstance(v, date):
        raise ValueError(f"{label} invalide.")
    return v


def parse_period(date_from: Any, date_to: Any, today: date) -> Tuple[date, date]:
    d_to = None if date_to is None else _as_date(date_to, "Date de fin")
    d_from = None if date_from is None else _as_date(date_from, "Date de debut")
    if d_from is None:
        d_from = d_to if d_to is not None else today
    if d_to is None:
        d_to = today
    if d_to < d_from:
        raise ValueError("La date de fin precede la date de debut.")
    if (d_to - d_from).days + 1 > MAX_PERIOD_DAYS:
        raise ValueError(f"Periode limitee a {MAX_PERIOD_DAYS} jours.")
    return d_from, d_to
