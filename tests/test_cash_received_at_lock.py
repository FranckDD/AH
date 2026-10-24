# tests/test_cash_received_at_lock.py
"""Regle 13 : les ecritures d'argent prennent le verrou PARTAGE de la cloture et s'horodatent
avec clock_timestamp() une fois le verrou tenu (jamais l'heure de debut de transaction)."""
import os
import sys
import threading
import time
from datetime import timedelta

from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.database import SessionLocal
from repositories.caisse_retrait_repo import CaisseRetraitRepository
from repositories.cash_closure_repo import LOCK_KEY, CashClosureRepository
from tests.conftest import create_test_retrait, create_test_transaction, create_test_user
from utils.cash_lock import CASH_CLOSURE_LOCK_KEY, lock_cash_write


def test_cle_unique():
    assert LOCK_KEY == CASH_CLOSURE_LOCK_KEY


def test_ecriture_attend_la_fin_de_la_cloture_et_s_horodate_apres():
    """(a) Une cloture tient le verrou exclusif : le retrait attend, puis s'horodate apres la liberation."""
    closer = SessionLocal()
    writer = SessionLocal()
    created = {}
    try:
        user_id = writer.execute(text("SELECT user_id FROM users ORDER BY user_id LIMIT 1")).scalar()
        assert user_id is not None
        assert closer.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": LOCK_KEY}).scalar()

        def run():
            r = CaisseRetraitRepository(writer).create(
                amount=1, justification="test verrou cloture", handled_by=user_id,
                payment_method="especes")
            created["id"] = r.retrait_id
            created["received_at"] = r.received_at
            created["done"] = time.monotonic()

        t = threading.Thread(target=run)
        t.start()
        time.sleep(1.0)
        assert t.is_alive(), "l'ecriture n'a pas attendu le verrou exclusif de la cloture"
        released_db = closer.execute(text("SELECT clock_timestamp()")).scalar()
        closer.rollback()  # libere le verrou (fin de la transaction de cloture)
        t.join(timeout=10)
        assert not t.is_alive()
        received = writer.execute(text("SELECT received_at FROM caisse_retrait WHERE retrait_id=:i"),
                                  {"i": created["id"]}).scalar()
        assert received >= released_db
    finally:
        closer.rollback()
        closer.close()
        if "id" in created:
            writer.rollback()
            writer.execute(text("DELETE FROM caisse_retrait WHERE retrait_id=:i"), {"i": created["id"]})
            writer.commit()
        writer.close()


def test_cloture_refusee_pendant_une_ecriture():
    """(a bis) Ecriture en cours (verrou partage tenu) : le try-lock exclusif de la cloture echoue."""
    writer = SessionLocal()
    closer = SessionLocal()
    try:
        lock_cash_write(writer)
        assert closer.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": LOCK_KEY}).scalar() is False
        # (pas d'assertion "True apres rollback" : une autre session de test concurrente
        # peut tenir le verrou partage a ce moment-la)
    finally:
        writer.rollback()
        closer.rollback()
        writer.close()
        closer.close()


def test_received_at_est_l_heure_reelle_pas_le_debut_de_transaction(db_session):
    """(b) Transaction ouverte, 1 s d'attente, puis ecriture : received_at ~1 s apres now()."""
    user = create_test_user(db_session, "rcv_lock_user", "secretaire")
    tx_start = db_session.execute(text("SELECT now()")).scalar()
    time.sleep(1.1)
    r = create_test_retrait(db_session, user, amount=7)
    tx = create_test_transaction(db_session, user, amount=100.0, advance_amount=40.0)
    pay_at = db_session.execute(text(
        "SELECT received_at FROM paiement_echelonne WHERE transaction_id=:t"), {"t": tx.transaction_id}).scalar()
    rt_at = db_session.execute(text(
        "SELECT received_at FROM caisse_retrait WHERE retrait_id=:i"), {"i": r.retrait_id}).scalar()
    assert rt_at - tx_start >= timedelta(seconds=1)
    assert pay_at - tx_start >= timedelta(seconds=1)

    # (c) les flux comptent toujours ces lignes
    flows = CashClosureRepository(db_session).flows(tx_start, pay_at + timedelta(seconds=1))
    assert flows["especes"]["exits"] >= 7
    assert flows["especes"]["entries"] >= 40


def test_annulations_horodatees_sous_verrou(db_session):
    user = create_test_user(db_session, "rcv_lock_cancel", "secretaire")
    tx_start = db_session.execute(text("SELECT now()")).scalar()
    time.sleep(1.1)
    r = create_test_retrait(db_session, user, amount=3)
    CaisseRetraitRepository(db_session).cancel_with_justification(r.retrait_id, user.user_id, "erreur")
    cancelled = db_session.execute(text(
        "SELECT cancelled_at AT TIME ZONE 'UTC' FROM caisse_retrait WHERE retrait_id=:i"),
        {"i": r.retrait_id}).scalar()
    assert cancelled - tx_start >= timedelta(seconds=1)
