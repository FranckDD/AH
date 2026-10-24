# utils/cash_lock.py
"""Horodatage des mouvements d'argent sous le verrou de la cloture de caisse.

La cloture prend le verrou consultatif EXCLUSIF (pg_try_advisory_xact_lock) le temps de lire
ses flux. Chaque ecriture d'argent (paiement, retrait, annulation) prend d'abord le verrou
PARTAGE de la meme cle, puis s'horodate avec clock_timestamp() (heure reelle, pas le debut de
la transaction) :
- une cloture qui demarre pendant une ecriture en cours echoue (409) au lieu de la manquer ;
- une ecriture qui attend la fin d'une cloture s'horodate APRES son t1 et tombe dans la
  periode suivante. Aucun mouvement ne peut donc tomber entre deux periodes.
Pas de dependance vers les repositories (pas d'import circulaire).
"""
from datetime import datetime, timezone

from sqlalchemy import text

CASH_CLOSURE_LOCK_KEY = 2026102324  # meme cle que repositories.cash_closure_repo.LOCK_KEY


def lock_cash_write(session) -> datetime:
    """Prend le verrou partage (relache au commit/rollback) puis renvoie clock_timestamp()
    (datetime avec fuseau), a utiliser comme received_at."""
    session.execute(text("SELECT pg_advisory_xact_lock_shared(:k)"), {"k": CASH_CLOSURE_LOCK_KEY})
    return session.execute(text("SELECT clock_timestamp()")).scalar()


def utc_naive(ts: datetime) -> datetime:
    """Pour les colonnes cancelled_at (UTC naif)."""
    return ts.astimezone(timezone.utc).replace(tzinfo=None)
