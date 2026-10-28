"""Heure metier (Africa/Douala).

Convention : les colonnes naives qui portent une heure "metier" (ex.
Caisse.paid_at) contiennent l'heure locale de Douala, quel que soit le
fuseau du processus (un hote UTC donne le meme resultat).

L'horloge est injectable (parametre `clock`) pour les tests.
"""
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Africa/Douala")


def _utc_clock() -> datetime:
    return datetime.now(timezone.utc)


def business_now(clock: Optional[Callable[[], datetime]] = None) -> datetime:
    """Heure locale de Douala, naive. `clock` doit renvoyer un datetime aware."""
    now = (clock or _utc_clock)()
    return now.astimezone(BUSINESS_TZ).replace(tzinfo=None)


def business_today(clock: Optional[Callable[[], datetime]] = None) -> date:
    """Jour metier courant (Douala)."""
    return business_now(clock).date()


class ClientTimeError(ValueError):
    """Horodatage envoye par le client illisible : les endpoints repondent 422."""


FUTURE_TOLERANCE = timedelta(minutes=5)
MAX_AGE = timedelta(days=7)


def resolve_client_time(raw, clock: Optional[Callable[[], datetime]] = None, ref: str = "") -> datetime:
    """Heure metier (Douala, naive) d'une operation faite hors ligne.

    `raw` : chaine ISO. Avec fuseau (Z, +00:00) elle est convertie en heure de Douala ; sans fuseau
    elle est prise pour de l'heure de Douala. Absente => heure serveur. Invalide => ClientTimeError.
    Hors bornes (futur de plus de 5 min, ou plus de 7 jours) => heure serveur et avertissement
    (la vente a reellement eu lieu : on ne la refuse jamais)."""
    now = business_now(clock)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return now
    if isinstance(raw, datetime):
        dt = raw
    else:
        text = str(raw).strip()
        if text[-1:] in ("Z", "z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            raise ClientTimeError("Date de l'operation invalide : format ISO 8601 attendu.")
    if dt.tzinfo is not None:
        dt = dt.astimezone(BUSINESS_TZ).replace(tzinfo=None)
    if dt > now + FUTURE_TOLERANCE or dt < now - MAX_AGE:
        logging.getLogger(__name__).warning(
            "Heure client hors bornes ignoree (operation %s) : heure serveur utilisee.", ref or "?")
        return now
    return dt
