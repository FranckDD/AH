# tests/test_cash_flows.py
"""Cloture de caisse, tache 3 : entrees et sorties d'une periode [t0, t1), par mode normalise.

Toutes les dates sont en 2030 pour ne jamais croiser les donnees reelles de la base de dev.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from repositories.cash_closure_repo import CashClosureRepository
from tests.conftest import create_test_retrait, create_test_transaction, create_test_user
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")


UTC = timezone.utc
D0 = datetime(2030, 3, 10, 0, 0, tzinfo=UTC)          # debut du jour 1
D1 = D0 + timedelta(days=1)                            # debut du jour 2
D2 = D0 + timedelta(days=2)


def _user(db, name="cf_secr"):
    return create_test_user(db, name, "secretaire")


def _sale(db, user, advance=0, mode="Especes", amount=1000, received_at=None, **kw):
    tx = create_test_transaction(
        db, user, amount=amount, advance_amount=advance, payment_method=mode,
        items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": amount,
                "quantity": 1, "line_total": amount}], **kw)
    if received_at is not None:
        db.execute(text("UPDATE paiement_echelonne SET received_at = :r WHERE transaction_id = :t"),
                   {"r": received_at, "t": tx.transaction_id})
    db.flush()
    return tx


def _pay(db, user, tx, amount, mode, received_at):
    db.execute(text(
        "INSERT INTO paiement_echelonne (transaction_id, paid_amount, payment_date, payment_method,"
        " payment_type, handled_by, received_at, uuid)"
        " VALUES (:t, :a, now(), :m, 'VERSEMENT_ECHEANCE', :u, :r, gen_random_uuid())"),
        {"t": tx.transaction_id, "a": amount, "m": mode, "u": user.user_id, "r": received_at})
    db.execute(text("UPDATE caisse SET advance_amount = advance_amount + :a WHERE transaction_id = :t"),
               {"a": amount, "t": tx.transaction_id})


def _cancel_sale(db, user, tx, at_utc_naive, why="erreur de saisie"):
    db.execute(text(
        "UPDATE caisse SET status='cancelled', cancelled_at=:c, cancelled_by=:u, cancel_justification=:j"
        " WHERE transaction_id=:t"),
        {"c": at_utc_naive, "u": user.user_id, "j": why, "t": tx.transaction_id})


def _retrait(db, user, amount, received_at, mode="Especes"):
    r = create_test_retrait(db, user, amount=amount, payment_method=mode)
    db.execute(text("UPDATE caisse_retrait SET received_at=:r WHERE retrait_id=:i"),
               {"r": received_at, "i": r.retrait_id})
    return r


def _cancel_retrait(db, user, r, at_utc_naive):
    db.execute(text(
        "UPDATE caisse_retrait SET status='cancelled', cancelled_at=:c, cancelled_by=:u,"
        " cancel_justification='annule' WHERE retrait_id=:i"),
        {"c": at_utc_naive, "u": user.user_id, "i": r.retrait_id})


def _naive(dt):
    return dt.astimezone(UTC).replace(tzinfo=None)


def _e(flows, mode):
    return flows.get(mode, {}).get("entries", Decimal(0))


def _x(flows, mode):
    return flows.get(mode, {}).get("exits", Decimal(0))


def test_advance_at_creation_counted_once(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u, advance=400, received_at=D0 + timedelta(hours=9))
    assert Decimal(tx.advance_amount) == Decimal(400)   # cache present AND a pe row exists
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "especes") == Decimal(400)
    assert _x(f, "especes") == Decimal(0)


def test_advance_then_instalment_other_day_other_mode(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u, advance=300, received_at=D0 + timedelta(hours=9))
    _pay(db_session, u, tx, 700, "Orange Money", D1 + timedelta(hours=10))
    repo = CashClosureRepository(db_session)
    f1, f2 = repo.flows(D0, D1), repo.flows(D1, D2)
    assert _e(f1, "especes") == Decimal(300) and _e(f1, "orange_money") == Decimal(0)
    assert _e(f2, "orange_money") == Decimal(700) and _e(f2, "especes") == Decimal(0)


def test_pending_approval_sale_excluded(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u, advance=0)
    _pay(db_session, u, tx, 250, "Especes", D0 + timedelta(hours=8))
    db_session.execute(text("UPDATE caisse SET status='pending_approval' WHERE transaction_id=:t"),
                       {"t": tx.transaction_id})
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "especes") == Decimal(0)


def test_active_retrait_is_exit(db_session):
    u = _user(db_session)
    _retrait(db_session, u, 120, D0 + timedelta(hours=11), mode="MTN Money")
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _x(f, "mtn_money") == Decimal(120)


def test_retrait_without_mode_counts_as_cash(db_session):
    u = _user(db_session)
    _retrait(db_session, u, 80, D0 + timedelta(hours=11), mode=None)
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _x(f, "especes") == Decimal(80)


def test_retrait_cancelled_same_period_neither_exit_nor_entry(db_session):
    u = _user(db_session)
    r = _retrait(db_session, u, 120, D0 + timedelta(hours=11))
    _cancel_retrait(db_session, u, r, _naive(D0 + timedelta(hours=15)))
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _x(f, "especes") == Decimal(0) and _e(f, "especes") == Decimal(0)


def test_retrait_cancelled_later_period_is_entry_then(db_session):
    u = _user(db_session)
    r = _retrait(db_session, u, 120, D0 + timedelta(hours=11))
    _cancel_retrait(db_session, u, r, _naive(D1 + timedelta(hours=9)))
    repo = CashClosureRepository(db_session)
    f1, f2 = repo.flows(D0, D1), repo.flows(D1, D2)
    assert _x(f1, "especes") == Decimal(120)              # was active at the first closing
    assert _e(f2, "especes") == Decimal(120) and _x(f2, "especes") == Decimal(0)


def test_cancelled_sale_exit_equals_its_payments_by_mode(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u, advance=300, received_at=D0 + timedelta(hours=9))
    _pay(db_session, u, tx, 200, "Orange Money", D0 + timedelta(hours=10))
    _cancel_sale(db_session, u, tx, _naive(D1 + timedelta(hours=8)), why="doublon")
    repo = CashClosureRepository(db_session)
    f1, f2 = repo.flows(D0, D1), repo.flows(D1, D2)
    assert _e(f1, "especes") == Decimal(300) and _e(f1, "orange_money") == Decimal(200)
    assert _x(f1, "especes") == Decimal(0)
    assert _x(f2, "especes") == Decimal(300) and _x(f2, "orange_money") == Decimal(200)
    c = repo.cancellations(D1, D2)
    assert len(c) == 1
    assert c[0]["transaction_id"] == tx.transaction_id
    assert c[0]["amount"] == Decimal(500)
    assert c[0]["justification"] == "doublon"
    assert c[0]["cancelled_by"] == u.user_id
    assert c[0]["by_mode"] == {"especes": Decimal(300), "orange_money": Decimal(200)}
    assert repo.cancellations(D0, D1) == []


def test_cancelled_sale_same_period_nets_to_zero(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u, advance=300, received_at=D0 + timedelta(hours=9))
    _cancel_sale(db_session, u, tx, _naive(D0 + timedelta(hours=12)))
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "especes") - _x(f, "especes") == Decimal(0)
    assert _x(f, "especes") == Decimal(300)


def test_cancelled_then_reinvoiced_compensate(db_session):
    u = _user(db_session)
    old = _sale(db_session, u, advance=500, received_at=D0 + timedelta(hours=9))
    _cancel_sale(db_session, u, old, _naive(D0 + timedelta(hours=10)))
    _sale(db_session, u, advance=500, received_at=D0 + timedelta(hours=10, minutes=5))
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "especes") == Decimal(1000) and _x(f, "especes") == Decimal(500)
    assert _e(f, "especes") - _x(f, "especes") == Decimal(500)


def test_unknown_mode_goes_to_non_classe(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u)
    _pay(db_session, u, tx, 90, "Virement", D0 + timedelta(hours=9))
    _retrait(db_session, u, 30, D0 + timedelta(hours=9), mode="Chèque")
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "non_classe") == Decimal(90) and _x(f, "non_classe") == Decimal(30)
    assert _e(f, "especes") == Decimal(0)


def test_bounds_left_inclusive_right_exclusive(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u)
    _pay(db_session, u, tx, 10, "Especes", D0)
    _pay(db_session, u, tx, 20, "Especes", D1)
    _retrait(db_session, u, 1, D0)
    _retrait(db_session, u, 2, D1)
    tx2 = _sale(db_session, u, advance=40, received_at=D0 - timedelta(hours=1))
    _cancel_sale(db_session, u, tx2, _naive(D1))         # exactly t1: belongs to next period
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "especes") == Decimal(10)
    assert _x(f, "especes") == Decimal(1)


def test_tz_aware_bounds_other_offset(db_session):
    """Les bornes avec fuseau Douala (+01) et cancelled_at UTC naif se comparent correctement."""
    from utils.cash_rules import TZ
    u = _user(db_session)
    tx = _sale(db_session, u, advance=60, received_at=D0 - timedelta(days=1))
    # 22:30 UTC = 23:30 Douala : apres une borne de 23:00 Douala
    _cancel_sale(db_session, u, tx, datetime(2030, 3, 10, 22, 30))
    t1 = datetime(2030, 3, 10, 23, 0, tzinfo=TZ)
    repo = CashClosureRepository(db_session)
    assert _x(repo.flows(t1 - timedelta(days=1), t1), "especes") == Decimal(0)
    assert _x(repo.flows(t1, t1 + timedelta(days=1)), "especes") == Decimal(60)


def test_legacy_sale_with_advance_and_no_payment_row_never_counted(db_session):
    u = _user(db_session)
    tx = _sale(db_session, u, advance=0)
    db_session.execute(text(
        "UPDATE caisse SET advance_amount=750, paid_at=:p WHERE transaction_id=:t"),
        {"p": _naive(D0 + timedelta(hours=9)), "t": tx.transaction_id})
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _e(f, "especes") == Decimal(0)
    # meme annulee, une vente sans ligne de paiement ne produit pas de sortie
    _cancel_sale(db_session, u, tx, _naive(D0 + timedelta(hours=12)))
    f = CashClosureRepository(db_session).flows(D0, D1)
    assert _x(f, "especes") == Decimal(0)
    assert CashClosureRepository(db_session).cancellations(D0, D1)[0]["amount"] == Decimal(0)


def test_naive_bounds_rejected(db_session):
    import pytest
    with pytest.raises(ValueError):
        CashClosureRepository(db_session).flows(datetime(2030, 1, 1), datetime(2030, 1, 2))


def test_start_row_and_last_closure_none_when_empty(db_session):
    repo = CashClosureRepository(db_session)
    # la base de dev peut ne pas avoir de depart ; on verifie seulement le type de retour
    s = repo.start_row()
    assert s is None or s.id == 1
    lc = repo.last_closure()
    assert lc is None or lc.period_end is not None
