# utils/stock_count_rules.py
"""Regles pures du comptage physique du stock (aucun acces base)."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

MAX_COUNTED_QTY = 10_000_000
MAX_OBSERVATION = 1000


def _whole(v: Any, label: str) -> int:
    """Entier strict : bool, chaine, None, flottant non integral refuses ; 2.0 -> 2."""
    if isinstance(v, bool) or v is None:
        raise ValueError(f"{label} invalide.")
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v == v and v not in (float("inf"), float("-inf")) and v.is_integer():
        return int(v)
    raise ValueError(f"{label} doit etre un nombre entier.")


MAX_COUNTED_AT_LEN = 40


def parse_counted_at(v: Any) -> Optional[datetime]:
    """Heure de comptage d'une ligne : None, ou chaine ISO avec decalage (convertie en UTC) ou naive
    (lue comme UTC). Renvoie un datetime UTC naif ; tout le reste -> ValueError."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if not isinstance(v, str) or len(v) > MAX_COUNTED_AT_LEN:
        raise ValueError("Heure de comptage invalide.")
    raw = v.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        raise ValueError("Heure de comptage invalide (format ISO attendu).")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def validate_counts(lines: List[Dict[str, Any]], valid_product_ids: Set[int]) -> List[Dict[str, Any]]:
    """Valide les lignes soumises : [{product_id, counted_qty, observation}] nettoyees.

    Les messages ne citent jamais le stock du systeme (comptage a l'aveugle)."""
    if not isinstance(lines, list) or not lines:
        raise ValueError("Le comptage doit comporter au moins une ligne.")
    seen: Set[int] = set()
    out: List[Dict[str, Any]] = []
    for raw in lines:
        if not isinstance(raw, dict):
            raise ValueError("Ligne de comptage invalide.")
        pid = _whole(raw.get("product_id"), "Le produit")
        if pid not in valid_product_ids:
            raise ValueError(f"Produit introuvable : {pid}.")
        if pid in seen:
            raise ValueError(f"Produit en double dans le comptage : {pid}.")
        seen.add(pid)
        qty = _whole(raw.get("counted_qty"), "La quantite comptee")
        if qty < 0:
            raise ValueError("La quantite comptee ne peut pas etre negative.")
        if qty > MAX_COUNTED_QTY:
            raise ValueError(f"La quantite comptee depasse la limite autorisee ({MAX_COUNTED_QTY}).")
        obs = raw.get("observation")
        if obs is not None:
            if not isinstance(obs, str):
                raise ValueError("Observation invalide.")
            obs = obs.strip() or None
            if obs is not None and len(obs) > MAX_OBSERVATION:
                raise ValueError(f"L'observation depasse {MAX_OBSERVATION} caracteres.")
        out.append({"product_id": pid, "counted_qty": qty, "observation": obs,
                    "counted_at": parse_counted_at(raw.get("counted_at"))})
    return out


def frequency_status(last_counted_at: Optional[datetime], now: datetime,
                     interval_days: int) -> Tuple[str, Optional[int]]:
    """('jamais_compte', None) | ('en_retard', jours) | ('a_jour', jours).

    jours = nombre de jours entiers ecoules (plancher) ; exactement interval_days -> a_jour."""
    if last_counted_at is None:
        return "jamais_compte", None
    days = max(0, int((now - last_counted_at).total_seconds() // 86400))
    return ("en_retard" if days > interval_days else "a_jour"), days


def gap_kind(difference: int) -> str:
    return "plus" if difference > 0 else "moins" if difference < 0 else "aucun"
