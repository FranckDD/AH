# tests/test_cash_closure_controller.py
"""Cloture de caisse, tache 4 : cloture manuelle et automatique, chainage, verrou, notifications, audit.

Toutes les dates sont en 2030 (horloge injectee) pour ne jamais croiser les donnees reelles.
Africa/Douala = UTC+1 sans heure d'ete : 23:00 local = 22:00 UTC.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from controller.cash_closure_controller import (
    CashClosureConflictError, CashClosureController, CashClosureNotFoundError,
    get_cash_closure_controller,
)
from models.audit import AuditUserAction
from models.cash_closure import CashClosure, CashClosureLine
from models.notification import Notification
from repositories.audit_repo import AuditRepository
from repositories.cash_closure_repo import CashClosureRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_retrait, create_test_transaction, create_test_user
from utils.cash_rules import TZ
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")


UTC = timezone.utc
DAY0 = datetime(2030, 5, 6, 8, 0, tzinfo=TZ)      # 08:00 local, lundi
MODES = ("especes", "orange_money", "mtn_money", "autre_mobile")


class Clock:
    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at


def _ctrl(db, user, clock):
    return CashClosureController(CashClosureRepository(db), AuditRepository(db),
                                 NotificationRepository(db), user, clock=clock)


@pytest.fixture
def env(db_session):
    admin = create_test_user(db_session, "cc_admin", "admin")
    secr = create_test_user(db_session, "cc_secr", "secretaire")
    clock = Clock(DAY0)
    return db_session, admin, secr, clock


def _start(db, admin, clock, opening=0):
    return _ctrl(db, admin, clock).set_start(Decimal(opening))


def _sale(db, user, amount, mode, at):
    tx = create_test_transaction(
        db, user, amount=amount, advance_amount=amount, payment_method=mode,
        items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": amount,
                "quantity": 1, "line_total": amount}])
    db.execute(text("UPDATE paiement_echelonne SET received_at = :r WHERE transaction_id = :t"),
               {"r": at, "t": tx.transaction_id})
    db.commit()  # fige la donnee : un rollback du controleur ne doit pas l'effacer
    return tx


def _retrait(db, user, amount, at, mode="Especes"):
    r = create_test_retrait(db, user, amount=amount, payment_method=mode)
    db.execute(text("UPDATE caisse_retrait SET received_at=:r WHERE retrait_id=:i"),
               {"r": at, "i": r.retrait_id})
    db.commit()
    return r


def _counts(especes=0, comment=None, **others):
    out = [{"mode": "especes", "counted": Decimal(especes), "comment": comment}]
    for m in MODES[1:]:
        out.append({"mode": m, "counted": Decimal(others.get(m, 0)), "comment": None})
    return out


def _line(detail, mode):
    return next(l for l in detail["lines"] if l["mode"] == mode)


def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


# --- etat et depart -------------------------------------------------------------------

def test_not_configured_status_submit_and_auto(env):
    db, admin, secr, clock = env
    c = _ctrl(db, secr, clock)
    assert c.status()["configured"] is False
    with pytest.raises(CashClosureConflictError, match="non initialisee"):
        c.submit(_counts())
    assert c.auto_close_overdue(clock()) == []


def test_set_start_admin_only_once_and_audited(env):
    db, admin, secr, clock = env
    with pytest.raises(PermissionError):
        _ctrl(db, secr, clock).set_start(Decimal(0))
    _start(db, admin, clock, 5000)
    with pytest.raises(CashClosureConflictError):
        _start(db, admin, clock, 10)
    assert db.query(AuditUserAction).filter_by(resource_type="CashClosureStart",
                                               user_id=admin.user_id).count() == 1


def test_status_has_no_totals(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 1000)
    _sale(db, secr, 500, "Especes", DAY0 + timedelta(hours=1))
    clock.at = DAY0 + timedelta(hours=4)
    s = _ctrl(db, secr, clock).status()
    assert s["configured"] is True and s["overdue_days"] == []
    assert [m["code"] for m in s["modes"]] == list(MODES)
    sources = {m["code"]: m["source"] for m in s["modes"]}
    assert sources["especes"] == "physical" and sources["mtn_money"] == "operator_statement"
    for k in _walk_keys(s):
        assert not any(w in k for w in ("expected", "entries", "exits", "opening"))


# --- cloture manuelle -----------------------------------------------------------------

def test_manual_closure_exact(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    _sale(db, secr, 300, "Orange Money", DAY0 + timedelta(hours=3))
    _retrait(db, secr, 200, DAY0 + timedelta(hours=4))
    clock.at = DAY0 + timedelta(hours=10)
    d = _ctrl(db, secr, clock).submit(_counts(800, orange_money=300))
    assert d["kind"] == "manual" and d["closed_by"] == secr.user_id
    assert d["period_start"] == DAY0 and d["period_end"] == clock.at
    assert d["business_date"] == DAY0.date()
    esp = _line(d, "especes")
    assert (esp["opening"], esp["entries"], esp["exits"], esp["expected"], esp["counted"],
            esp["difference"], esp["source"]) == (0, 1000, 200, 800, 800, 0, "physical")
    om = _line(d, "orange_money")
    assert om["expected"] == 300 and om["difference"] == 0 and om["source"] == "operator_statement"
    assert d["expected_cash"] == 800 and d["counted_cash"] == 800 and d["difference"] == 0
    assert d["opening_from_auto"] is False
    assert db.query(CashClosureLine).filter_by(closure_id=d["id"]).count() == 4


def test_gap_requires_comment(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    c = _ctrl(db, secr, clock)
    with pytest.raises(ValueError, match="Commentaire"):
        c.submit(_counts(950))
    assert db.query(CashClosure).count() == 0
    with pytest.raises(ValueError, match="Commentaire"):
        c.submit(_counts(950, comment="   "))
    d = c.submit(_counts(950, comment="billet perdu"))
    assert _line(d, "especes")["difference"] == -50
    assert _line(d, "especes")["comment"] == "billet perdu"


@pytest.mark.parametrize("bad", ["unknown", "inactive", "missing", "duplicate", "negative"])
def test_mode_set_validation(env, bad):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=10)
    counts = _counts()
    if bad == "unknown":
        counts.append({"mode": "virement", "counted": Decimal(0), "comment": None})
    elif bad == "inactive":
        db.execute(text("UPDATE payment_modes SET is_active=false WHERE code='autre_mobile'"))
    elif bad == "missing":
        counts = counts[:-1]
    elif bad == "duplicate":
        counts.append(dict(counts[0]))
    elif bad == "negative":
        counts[0]["counted"] = Decimal(-1)
    with pytest.raises(ValueError):
        _ctrl(db, secr, clock).submit(counts)
    assert db.query(CashClosure).count() == 0


def test_inactive_mode_not_expected(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    db.execute(text("UPDATE payment_modes SET is_active=false WHERE code='autre_mobile'"))
    clock.at = DAY0 + timedelta(hours=10)
    d = _ctrl(db, secr, clock).submit(_counts()[:-1])
    assert {l["mode"] for l in d["lines"]} == set(MODES[:-1])


def test_opening_is_previous_count_and_periods_chain(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 100)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=1))
    clock.at = DAY0 + timedelta(hours=5)
    c = _ctrl(db, secr, clock)
    first = c.submit(_counts(1050, comment="trouve 50"))
    assert _line(first, "especes")["opening"] == 100 and _line(first, "especes")["expected"] == 1100
    _sale(db, secr, 200, "Especes", DAY0 + timedelta(hours=6))
    clock.at = DAY0 + timedelta(hours=9)
    second = c.submit(_counts(1250))
    assert second["period_start"] == first["period_end"]
    assert _line(second, "especes")["opening"] == 1050
    assert second["opening_cash"] == 1050 and second["opening_from_auto"] is False
    assert _line(second, "especes")["difference"] == 0


def test_double_submit_second_is_409(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=10)
    c = _ctrl(db, secr, clock)
    c.submit(_counts())
    with pytest.raises(CashClosureConflictError):
        c.submit(_counts())
    assert db.query(CashClosure).count() == 1


def test_unique_period_end_backstop(env):
    db, admin, secr, clock = env
    end = DAY0 + timedelta(hours=3)
    stmt = text("INSERT INTO cash_closures (period_start, period_end, business_date, kind)"
                " VALUES (:s, :e, :d, 'auto')")
    db.execute(stmt, {"s": DAY0, "e": end, "d": DAY0.date()})
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(stmt, {"s": DAY0 + timedelta(hours=1), "e": end, "d": DAY0.date()})


def test_concurrent_submit_from_other_session_gets_409(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=10)
    _ctrl(db, secr, clock).submit(_counts())   # garde le verrou de transaction (transaction externe du test)
    other = Session(bind=db.get_bind().engine.connect())
    try:
        with pytest.raises(CashClosureConflictError, match="en cours"):
            _ctrl(other, secr, clock).submit(_counts())
    finally:
        other.rollback()
        conn = other.connection()
        other.close()
        conn.close()


# --- cloture automatique --------------------------------------------------------------

def test_submit_refused_while_auto_overdue_then_opening_from_auto(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 700, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(days=1, hours=2)       # lendemain 10:00
    c = _ctrl(db, secr, clock)
    assert c.status()["overdue_days"] == [DAY0.date()]
    with pytest.raises(CashClosureConflictError):
        c.submit(_counts(700))
    autos = c.auto_close_overdue(clock())
    assert len(autos) == 1
    a = autos[0]
    assert a["kind"] == "auto" and a["closed_by"] is None
    assert a["period_end"] == datetime(2030, 5, 6, 22, 0, tzinfo=UTC)
    assert a["counted_cash"] is None and a["difference"] is None and a["expected_cash"] == 700
    assert all(l["counted"] is None and l["difference"] is None for l in a["lines"])
    d = c.submit(_counts(700))
    assert d["period_start"] == a["period_end"]
    assert d["opening_cash"] == 700 and d["opening_from_auto"] is True
    assert _line(d, "especes")["difference"] == 0


def test_three_day_outage(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(days=3, hours=2)
    c = _ctrl(db, secr, clock)
    out = c.auto_close_overdue(clock())
    ends = [x["period_end"] for x in out]
    assert ends == [datetime(2030, 5, 6 + i, 22, 0, tzinfo=UTC) for i in range(3)]
    assert [x["business_date"] for x in out] == [(DAY0 + timedelta(days=i)).date() for i in range(3)]
    assert out[1]["period_start"] == out[0]["period_end"] and out[2]["period_start"] == out[1]["period_end"]
    assert out[1]["opening_from_auto"] is True
    assert c.auto_close_overdue(clock()) == []
    assert db.query(CashClosure).count() == 3


# --- notifications, audit, lecture ----------------------------------------------------

def test_notifications_one_per_recipient(env):
    db, admin, secr, clock = env
    promo = create_test_user(db, "cc_promo", "promoteur")
    gone = create_test_user(db, "cc_admin_off", "admin", is_active=False)
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    d = _ctrl(db, secr, clock).submit(_counts(990, comment="manque"))
    expected_ids = set(CashClosureRepository(db).recipient_user_ids())
    assert {admin.user_id, promo.user_id} <= expected_ids
    notifs = db.query(Notification).filter_by(type="cash_closure").all()
    got = [n.recipient_user_id for n in notifs]
    assert sorted(got) == sorted(expected_ids)
    assert secr.user_id not in got and gone.user_id not in got
    p = notifs[0].payload
    assert set(p) == {"closure_id", "business_date", "expected_cash", "counted_cash",
                      "difference", "auto", "anomaly"}
    assert p["closure_id"] == d["id"] and p["auto"] is False and p["anomaly"] is True
    assert Decimal(p["expected_cash"]) == 1000 and Decimal(p["difference"]) == -10


def test_auto_notification_marked(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(days=1)
    a = _ctrl(db, secr, clock).auto_close_overdue(clock())[0]
    n = db.query(Notification).filter_by(type="cash_closure", recipient_user_id=admin.user_id).one()
    assert n.payload["auto"] is True and n.payload["anomaly"] is True
    assert n.payload["counted_cash"] is None and n.payload["closure_id"] == a["id"]


def test_exact_manual_not_anomaly_and_audit(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=10)
    d = _ctrl(db, secr, clock).submit(_counts())
    n = db.query(Notification).filter_by(type="cash_closure", recipient_user_id=admin.user_id).one()
    assert n.payload["anomaly"] is False
    assert db.query(AuditUserAction).filter_by(resource_type="CashClosure", resource_id=d["id"],
                                               user_id=secr.user_id).count() == 1


def test_get_and_list(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(days=1, hours=1)
    c = _ctrl(db, admin, clock)
    c.auto_close_overdue(clock())
    c.submit(_counts())
    rows = c.list({"date_from": DAY0.date(), "date_to": DAY0.date()})
    assert len(rows) == 1 and rows[0]["kind"] == "auto" and len(rows[0]["lines"]) == 4
    assert c.get(rows[0]["id"])["id"] == rows[0]["id"]
    manual = c.list({"kind": "manual"})
    assert len(manual) == 1 and manual[0]["business_date"] == (DAY0 + timedelta(days=1)).date()
    with pytest.raises(CashClosureNotFoundError):
        c.get(-1)


def test_factory_wires_repos(env):
    db, admin, secr, clock = env
    c = get_cash_closure_controller(db, secr)
    assert isinstance(c.notification_repo, NotificationRepository)
    assert isinstance(c.audit_repo, AuditRepository)


# --- fix round 1 ----------------------------------------------------------------------

def test_manual_day_not_auto_closed_then_next_day_outage(env):
    db, admin, secr, clock = env
    promo = create_test_user(db, "cc_promo2", "promoteur")
    _start(db, admin, clock, 0)
    _sale(db, secr, 400, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)                 # 18:00 local J
    c = _ctrl(db, secr, clock)
    m = c.submit(_counts(400))
    _sale(db, secr, 250, "Especes", DAY0 + timedelta(hours=14, minutes=30))   # 22:30 local J
    clock.at = DAY0 + timedelta(hours=15, minutes=30)     # 23:30 local J
    assert c.status()["overdue_days"] == []
    assert c.auto_close_overdue(clock()) == []
    assert db.query(CashClosure).count() == 1
    assert db.query(Notification).filter_by(type="cash_closure",
                                            recipient_user_id=promo.user_id).count() == 1
    clock.at = DAY0 + timedelta(days=1, hours=2)          # J+1 10:00 : rien en retard
    assert c.status()["overdue_days"] == []
    m2 = c.submit(_counts(650))
    assert m2["period_start"] == m["period_end"]
    esp = _line(m2, "especes")
    assert (esp["opening"], esp["entries"], esp["expected"], esp["difference"]) == (400, 250, 650, 0)
    clock.at = DAY0 + timedelta(days=2, hours=2)          # J+2 10:00 : J+1 a sa cloture manuelle, rien du
    assert c.status()["overdue_days"] == []
    clock.at = DAY0 + timedelta(days=3, hours=2)          # J+2 23:00 manque
    autos = c.auto_close_overdue(clock())
    assert [a["business_date"] for a in autos] == [(DAY0 + timedelta(days=2)).date()]
    assert autos[0]["period_start"] == m2["period_end"]
    n = (db.query(Notification).filter_by(type="cash_closure", recipient_user_id=promo.user_id)
         .order_by(Notification.id).all())
    assert [x.payload["anomaly"] for x in n] == [False, False, True]


def test_unclassified_money_is_anomaly(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 300, "Virement", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    d = _ctrl(db, secr, clock).submit(_counts())
    unc = _line(d, "non_classe")
    assert unc["entries"] == 300 and unc["counted"] is None
    n = db.query(Notification).filter_by(type="cash_closure", recipient_user_id=admin.user_id).one()
    assert n.payload["anomaly"] is True


def test_negative_auto_carry_clamps_column_not_line(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _retrait(db, secr, 500, DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(days=1, hours=2)
    c = _ctrl(db, secr, clock)
    a = c.auto_close_overdue(clock())[0]
    assert a["expected_cash"] == -500
    d = c.submit(_counts(0, comment="retrait sans fonds"))
    assert d["opening_cash"] == 0 and d["opening_from_auto"] is True
    esp = _line(d, "especes")
    assert esp["opening"] == -500 and esp["expected"] == -500 and esp["difference"] == 500


# --- tache 5 : garde double onglet, modes, corrections -----------------------------------

def test_submit_last_closed_at_guard(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=5)
    c = _ctrl(db, secr, clock)
    first = c.submit(_counts(), last_closed_at=None)
    clock.at = DAY0 + timedelta(hours=6)
    with pytest.raises(CashClosureConflictError, match="entre-temps"):
        c.submit(_counts(), last_closed_at=None)
    with pytest.raises(CashClosureConflictError, match="entre-temps"):
        c.submit(_counts(), last_closed_at=(first["period_end"] - timedelta(seconds=1)).isoformat())
    with pytest.raises(ValueError):
        c.submit(_counts(), last_closed_at="2030-05-06T12:00:00")  # sans fuseau
    with pytest.raises(ValueError):
        c.submit(_counts(), last_closed_at="n'importe quoi")
    second = c.submit(_counts(), last_closed_at=first["period_end"].astimezone(UTC).isoformat())
    assert second["period_start"] == first["period_end"]


def test_payment_modes_admin_crud(env):
    db, admin, secr, clock = env
    c = _ctrl(db, admin, clock)
    # Regle 6 : pas de creation de code
    assert not hasattr(c, "create_mode")
    with pytest.raises(PermissionError):
        _ctrl(db, secr, clock).update_mode("mtn_money", {"label": "x"})
    m = c.update_mode("mtn_money", {"label": " MTN ", "sort_order": 9})
    assert m == {"code": "mtn_money", "label": "MTN", "is_active": True, "sort_order": 9}
    assert c.update_mode("mtn_money", {"is_active": False})["is_active"] is False
    with pytest.raises(ValueError):
        c.update_mode("especes", {"is_active": False})
    with pytest.raises(ValueError):
        c.update_mode("mtn_money", {"code": "x"})
    with pytest.raises(CashClosureNotFoundError):
        c.update_mode("nope", {"label": "x"})
    assert "mtn_money" in [x["code"] for x in c.list_modes()]
    assert db.query(AuditUserAction).filter_by(resource_type="PaymentMode",
                                               user_id=admin.user_id).count() == 2


def test_corrections_request_and_decide(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=5)
    d = _ctrl(db, secr, clock).submit(_counts())
    cs = _ctrl(db, secr, clock)
    with pytest.raises(ValueError):
        cs.request_correction(d["id"], {"mode_code": "especes", "amount_delta": "0", "reason": "x"})
    with pytest.raises(CashClosureNotFoundError):
        cs.request_correction(-1, {"mode_code": "especes", "amount_delta": "5", "reason": "x"})
    corr = cs.request_correction(d["id"], {"mode_code": "especes", "amount_delta": "-5.50",
                                           "reason": "erreur de saisie"})
    assert corr["status"] == "pending" and corr["amount_delta"] == Decimal("-5.50")
    ca = _ctrl(db, admin, clock)
    assert [x["id"] for x in ca.list_corrections({"status": "pending"})] == [corr["id"]]
    out = ca.decide_correction(corr["id"], False)
    assert out["status"] == "rejected" and out["decided_by"] == admin.user_id
    with pytest.raises(CashClosureConflictError):
        ca.decide_correction(corr["id"], True)
    assert db.query(AuditUserAction).filter_by(resource_type="CashClosureCorrection").count() == 2


# --- plafond du sondage par refus 'ecart sans commentaire' ------------------------------

def _refusals(db, user):
    return db.query(AuditUserAction).filter_by(user_id=user.user_id,
                                               action_performed="CLOSURE_GAP_REFUSED").count()


def test_three_gap_refusals_then_accepted_with_auto_comment(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    c = _ctrl(db, secr, clock)
    for i in range(3):
        with pytest.raises(ValueError, match="Commentaire") as ei:
            c.submit(_counts(900 + i))
        assert "1000" not in str(ei.value) and "especes" in str(ei.value)
        assert _refusals(db, secr) == i + 1          # l'audit survit au rollback du refus
    assert db.query(CashClosure).count() == 0
    d = c.submit(_counts(990))
    esp = _line(d, "especes")
    assert esp["difference"] == -10 and esp["comment"] == "commentaire non fourni"
    n = db.query(Notification).filter_by(type="cash_closure", recipient_user_id=admin.user_id).one()
    assert n.payload["anomaly"] is True and n.payload["comment_missing"] is True


def test_gap_refusals_cap_is_per_period_all_users(env):
    """Plafond PAR PERIODE : un second compte secretaire n'obtient pas 3 sondages de plus."""
    db, admin, secr, clock = env
    secr2 = create_test_user(db, "cc_secr2b", "secretaire")
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    c, c2 = _ctrl(db, secr, clock), _ctrl(db, secr2, clock)
    for _ in range(2):
        with pytest.raises(ValueError):
            c.submit(_counts(900))
    with pytest.raises(ValueError):                   # 3e refus de la periode, par l'autre compte
        c2.submit(_counts(900))
    d = c2.submit(_counts(900))                       # plafond atteint : accepte, sans commentaire
    assert _line(d, "especes")["comment"] == "commentaire non fourni" and d["comment_missing"] is True


def test_gap_refusals_reset_after_closure(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    c = _ctrl(db, secr, clock)
    for _ in range(3):
        with pytest.raises(ValueError):
            c.submit(_counts(900))
    d = c.submit(_counts(1000))                       # comptage exact : cloture normale
    n = db.query(Notification).filter_by(type="cash_closure", recipient_user_id=admin.user_id).one()
    assert "comment_missing" not in n.payload and n.payload["anomaly"] is False
    _sale(db, secr, 500, "Especes", DAY0 + timedelta(hours=11))
    clock.at = DAY0 + timedelta(hours=12)
    with pytest.raises(ValueError, match="Commentaire"):   # nouvelle periode : compteur remis a 0
        c.submit(_counts(1100))
    ok = c.submit(_counts(1100, comment="erreur de rendu"))
    assert ok["period_start"] == d["period_end"]
    assert _line(ok, "especes")["comment"] == "erreur de rendu"


# --- marqueur comment_missing (revue tache 10) ------------------------------------------

def test_comment_missing_flag_after_three_refusals(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    c = _ctrl(db, secr, clock)
    for i in range(3):
        with pytest.raises(ValueError):
            c.submit(_counts(900))
    d = c.submit(_counts(990))
    assert d["comment_missing"] is True
    assert _line(d, "especes")["comment_missing"] is True
    assert _line(d, "mtn_money")["comment_missing"] is False
    assert c.get(d["id"])["comment_missing"] is True
    assert c.list({})[0]["comment_missing"] is True


def test_comment_missing_false_with_real_comment(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    d = _ctrl(db, secr, clock).submit(_counts(990, comment="piece perdue"))
    assert d["comment_missing"] is False
    assert all(l["comment_missing"] is False for l in d["lines"])


def test_reserved_auto_comment_refused(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=10)
    c = _ctrl(db, secr, clock)
    for txt in ("commentaire non fourni", "  Commentaire NON fourni "):
        with pytest.raises(ValueError, match="reserve"):
            c.submit(_counts(990, comment=txt))
    assert db.query(CashClosure).count() == 0


# --- revue finale : regularisations appliquees, rattrapage public, isolation ----------------

def test_approved_corrections_applied_once_to_next_closure(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    _sale(db, secr, 1000, "Especes", DAY0 + timedelta(hours=2))
    clock.at = DAY0 + timedelta(hours=5)
    cs = _ctrl(db, secr, clock)
    first = cs.submit(_counts(1000))
    req = lambda mode, amt: cs.request_correction(first["id"], {"mode_code": mode, "amount_delta": amt,
                                                                "reason": "regularisation"})
    plus, minus, rej, pend = req("especes", "50.00"), req("orange_money", "-20.00"),         req("especes", "999.00"), req("mtn_money", "7.00")
    clock.at = DAY0 + timedelta(hours=6)
    ca = _ctrl(db, admin, clock)
    ca.decide_correction(plus["id"], True)
    ca.decide_correction(minus["id"], True)
    ca.decide_correction(rej["id"], False)
    # pend reste en attente
    clock.at = DAY0 + timedelta(hours=8)
    second = cs.submit([dict(x, comment="regul orange") if x["mode"] == "orange_money" else x
                        for x in _counts(1050)])
    esp, om, mtn = _line(second, "especes"), _line(second, "orange_money"), _line(second, "mtn_money")
    assert (esp["opening"], esp["entries"], esp["exits"], esp["expected"], esp["difference"]) ==         (1000, 50, 0, 1050, 0)
    assert (om["entries"], om["exits"], om["expected"], om["difference"]) == (0, 20, -20, 20)
    assert (mtn["entries"], mtn["exits"], mtn["expected"]) == (0, 0, 0)
    assert sorted(x["id"] for x in second["corrections_applied"]) == sorted([plus["id"], minus["id"]])
    assert cs.get(second["id"])["corrections_applied"] == second["corrections_applied"]
    # jamais dans la cloture d'origine, jamais deux fois
    assert cs.get(first["id"])["corrections_applied"] == []
    assert _line(cs.get(first["id"]), "especes")["expected"] == 1000
    clock.at = DAY0 + timedelta(hours=9)
    third = cs.submit(_counts(1050))
    assert _line(third, "especes")["entries"] == 0 and third["corrections_applied"] == []
    assert _line(third, "especes")["difference"] == 0


def test_catch_up_public_uses_clock(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(days=2, hours=2)
    c = _ctrl(db, secr, clock)
    assert [x["business_date"] for x in c.catch_up()] == [DAY0.date(), (DAY0 + timedelta(days=1)).date()]
    assert c.catch_up() == []


def test_isolation_survives_preexisting_real_register(db_session):
    """Simule une base de dev ou la vraie caisse est initialisee (depart + cloture + ligne +
    correction), dans la transaction du test, puis prouve que reset_register donne un etat
    vierge sur lequel un scenario complet du controleur tourne."""
    db = db_session
    admin = create_test_user(db, "cc_iso_admin", "admin")
    secr = create_test_user(db, "cc_iso_secr", "secretaire")
    real = datetime(2026, 10, 1, 8, 0, tzinfo=TZ)
    db.execute(text("INSERT INTO cash_closure_start (id, started_at, opening_cash) VALUES (1, :s, 500)"),
               {"s": real})
    cid = db.execute(text("INSERT INTO cash_closures (period_start, period_end, business_date, kind,"
                          " expected_cash) VALUES (:s, :e, :d, 'auto', 500) RETURNING id"),
                     {"s": real, "e": real + timedelta(hours=14), "d": real.date()}).scalar()
    db.execute(text("INSERT INTO cash_closure_lines (closure_id, mode_code, source, expected)"
                    " VALUES (:c, 'especes', 'physical', 500)"), {"c": cid})
    db.execute(text("INSERT INTO cash_closure_corrections (closure_id, mode_code, amount_delta, reason,"
                    " status, requested_by) VALUES (:c, 'especes', 5, 'x', 'pending', :u)"),
               {"c": cid, "u": secr.user_id})
    db.execute(text("UPDATE payment_modes SET is_active=false WHERE code='mtn_money'"))
    db.commit()
    assert CashClosureRepository(db).start_row() is not None
    reset_register(db)
    assert CashClosureRepository(db).start_row() is None
    assert db.query(CashClosure).count() == 0
    clock = Clock(DAY0)
    _ctrl(db, admin, clock).set_start(Decimal(0))
    clock.at = DAY0 + timedelta(hours=4)
    d = _ctrl(db, secr, clock).submit(_counts())
    assert d["period_start"] == DAY0 and len(d["lines"]) == 4
    # les triggers d'immuabilite sont de nouveau actifs apres la remise a zero
    with pytest.raises(Exception):
        with db.begin_nested():
            db.execute(text("UPDATE cash_closures SET comment='x' WHERE id=:i"), {"i": d["id"]})


def test_detail_lists_cancellations_of_its_period(env):
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    tx = _sale(db, secr, 400, "Especes", DAY0 + timedelta(hours=1))
    cancel_at = (DAY0 + timedelta(hours=2)).astimezone(UTC).replace(tzinfo=None)  # UTC naif
    db.execute(text("UPDATE caisse SET status='cancelled', cancelled_at=:c, cancelled_by=:u,"
                    " cancel_justification='doublon' WHERE transaction_id=:t"),
               {"c": cancel_at, "u": secr.user_id, "t": tx.transaction_id})
    db.commit()
    clock.at = DAY0 + timedelta(hours=5)
    c = _ctrl(db, secr, clock)
    d = c.submit(_counts(0))
    assert len(d["cancellations"]) == 1
    x = d["cancellations"][0]
    assert (x["transaction_id"], x["cancelled_by"], x["justification"], x["amount"]) == \
        (tx.transaction_id, secr.user_id, "doublon", Decimal("400"))
    assert x["by_mode"] == {"especes": Decimal("400")}
    assert c.get(d["id"])["cancellations"] == d["cancellations"]
    assert c.list({})[0]["cancellations"] == d["cancellations"]
    clock.at = DAY0 + timedelta(hours=6)
    assert c.submit(_counts(0))["cancellations"] == []


# --- re-revue : horloge de la base, verrou de l'approbation ------------------------------

class _AppClockAhead(datetime):
    """datetime dont now() est en avance d'une heure (hote API desynchronise)."""
    @classmethod
    def now(cls, tz=None):
        return datetime.now(tz) + timedelta(hours=1)


def test_t1_comes_from_db_clock_not_app_clock(db_session, monkeypatch):
    import controller.cash_closure_controller as mod
    db = db_session
    admin = create_test_user(db, "cc_dbclk_admin", "admin")
    secr = create_test_user(db, "cc_dbclk_secr", "secretaire")
    monkeypatch.setattr(mod, "datetime", _AppClockAhead)
    db_now = db.execute(text("SELECT clock_timestamp()")).scalar()
    _ctrl(db, admin, None).set_start(Decimal(0), started_at=db_now - timedelta(minutes=1))
    d = _ctrl(db, secr, None).submit(_counts())
    after = db.execute(text("SELECT clock_timestamp()")).scalar()
    assert db_now <= d["period_end"] <= after          # heure de la base...
    assert d["period_end"] < datetime.now(UTC) + timedelta(minutes=30)   # ...pas l'heure applicative +1h
    assert d["business_date"] == d["period_end"].astimezone(TZ).date()
    assert _ctrl(db, secr, None).status()["overdue_days"] == []


def test_decide_correction_waits_for_closure_lock_and_stamps_db_time(env):
    from api_backend.backend_app.database import SessionLocal
    db, admin, secr, clock = env
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=5)
    d = _ctrl(db, secr, clock).submit(_counts())
    corr = _ctrl(db, secr, clock).request_correction(
        d["id"], {"mode_code": "especes", "amount_delta": "5", "reason": "x"})
    db.commit()
    # une cloture tient le verrou EXCLUSIF (session du test, transaction ouverte)
    assert CashClosureRepository(db).try_lock()
    other = SessionLocal()
    try:
        other.execute(text("SET lock_timeout = '300ms'"))
        with pytest.raises(Exception, match="lock timeout|verrou|timeout"):
            _ctrl(other, admin, None).decide_correction(corr["id"], True)
    finally:
        other.rollback()
        other.close()
    # sans verrou concurrent : decided_at = heure de la base prise sous le verrou partage
    before = db.execute(text("SELECT clock_timestamp()")).scalar()
    out = _ctrl(db, admin, None).decide_correction(corr["id"], True)
    assert out["decided_at"] >= before
