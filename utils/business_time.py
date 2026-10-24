"""Heure metier (Africa/Douala).

Convention : les colonnes naives qui portent une heure "metier" (ex.
Caisse.paid_at) contiennent l'heure locale de Douala, quel que soit le
fuseau du processus (un hote UTC donne le meme resultat).

L'horloge est injectable (parametre `clock`) pour les tests.
"""
from datetime import datetime, date, timezone
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
