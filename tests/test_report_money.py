# tests/test_report_money.py
"""Rapports, tache 3 : sources argent (cartes 1 a 5) et croissance (cartes 12 et 13).

Dates en 2030 pour ne jamais croiser les donnees reelles de la base de dev.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from controller.reports_controller import ReportsController
from models.cash_closure import CashClosure, CashClosureLine
from repositories.cash_closure_repo import CashClosureRepository
from tests.conftest import (
    create_test_medical_record, create_test_patient, create_test_retrait,
    create_test_transaction, create_test_user,
)
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")

UTC = timezone.utc
DLA = ZoneInfo("Africa/Douala")
DAY1 = date(2030, 3, 11)   # lundi
DAY2 = date(2030, 3, 12)


def _at(d, h, m=0):
    """Instant aware a l'heure locale de Douala."""
    return datetime(d.year, d.month, d.day, h, m, tzinfo=DLA)


def _promoteur(db, name="rm_promo"):
    return create_test_user(db, name, "promoteur")


def _secr(db, name="rm_secr"):
    return create_test_user(db, name, "secretaire")


def _sale(db, user, amount=1000, advance=0, mode="Especes", received_at=None, paid_at=None,
          status=None, staff_discount=None):
    tx = create_test_transaction(
        db, user, amount=amount, advance_amount=advance, payment_method=mode,
        items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": amount,
                "quantity": 1, "line_total": amount}])
    if received_at is not None:
        db.execute(text("UPDATE paiement_echelonne SET received_at=:r WHERE transaction_id=:t"),
                   {"r": received_at, "t": tx.transaction_id})
    if paid_at is not None:
        db.execute(text("UPDATE caisse SET paid_at=:p WHERE transaction_id=:t"),
                   {"p": paid_at, "t": tx.transaction_id})
    if staff_discount is not None:
        db.execute(text("UPDATE caisse SET staff_discount_amount=:s WHERE transaction_id=:t"),
                   {"s": staff_discount, "t": tx.transaction_id})
    if status is not None:
        db.execute(text("UPDATE caisse SET status=:s WHERE transaction_id=:t"),
                   {"s": status, "t": tx.transaction_id})
    db.flush()
    db.expire_all()
    return tx


def _pay(db, user, tx, amount, mode, received_at):
    db.execute(text(
        "INSERT INTO paiement_echelonne (transaction_id, paid_amount, payment_date, payment_method,"
        " payment_type, handled_by, received_at, uuid)"
        " VALUES (:t, :a, now(), :m, 'VERSEMENT_ECHEANCE', :u, :r, gen_random_uuid())"),
        {"t": tx.transaction_id, "a": amount, "m": mode, "u": user.user_id, "r": received_at})


def _ctrl(db, user=None):
    return ReportsController(db, user or _promoteur(db))


# --- carte 1 : encaisse -------------------------------------------------------------------
def test_collected_equals_cash_closure_flows(db_session):
    u = _secr(db_session)
    _sale(db_session, u, advance=400, received_at=_at(DAY1, 9))
    tx = _sale(db_session, u, advance=0)
    _pay(db_session, u, tx, 700, "Orange Money", _at(DAY2, 10))
    _pay(db_session, u, tx, 50, "MTN Money", _at(DAY2, 11))
    r = create_test_retrait(db_session, u, amount=30, payment_method="Especes")
    db_session.execute(text("UPDATE caisse_retrait SET received_at=:r WHERE retrait_id=:i"),
                       {"r": _at(DAY1, 8), "i": r.retrait_id})

    card = _ctrl(db_session).money(DAY1, DAY2)["collected"]
    flows = CashClosureRepository(db_session).flows(_at(DAY1, 0), _at(DAY2 + timedelta(days=1), 0))
    for mode in ("especes", "orange_money", "mtn_money", "autre_mobile", "non_classe"):
        assert card["by_mode"][mode] == f"{flows[mode]['entries']:.2f}"
    assert card["total"] == f"{sum(f['entries'] for f in flows.values()):.2f}"
    assert card["by_mode"]["especes"] == "400.00"
    assert card["total"] == "1150.00"
    assert card["id"] == "collected" and card["title_key"] == "reports.cards.collected"
    assert card["period"] == {"from": "2030-03-11", "to": "2030-03-12"} and card["source"]


def test_payment_at_2330_utc_counts_on_next_douala_day(db_session):
    u = _secr(db_session)
    # 2030-03-10 23:30 UTC = 2030-03-11 00:30 Douala : dans la periode
    _sale(db_session, u, advance=100, received_at=datetime(2030, 3, 10, 23, 30, tzinfo=UTC))
    # 2030-03-12 23:30 UTC = 2030-03-13 00:30 Douala : hors periode
    _sale(db_session, u, advance=200, received_at=datetime(2030, 3, 12, 23, 30, tzinfo=UTC))
    m = _ctrl(db_session).money(DAY1, DAY2)
    assert m["collected"]["total"] == "100.00"
    rows = m["per_secretary"]["rows"]
    assert len(rows) == 1 and rows[0]["worked_days"] == 1


# --- carte 2 : ecarts lus des clotures ----------------------------------------------------
def test_cash_gaps_read_from_stored_closures(db_session):
    u = _secr(db_session)
    repo = CashClosureRepository(db_session)
    c = CashClosure(period_start=_at(DAY1, 0), period_end=_at(DAY1, 22), business_date=DAY1,
                    kind="manual", closed_by=u.user_id, opening_cash=Decimal(0),
                    expected_cash=Decimal("500"), counted_cash=Decimal("480"),
                    difference=Decimal("-20"))
    lines = [CashClosureLine(mode_code="especes", source="physical", opening=0, entries=500,
                             exits=0, expected=500, counted=480, difference=-20,
                             comment="commentaire non fourni"),
             CashClosureLine(mode_code="orange_money", source="operator_statement", opening=0,
                             entries=100, exits=0, expected=100, counted=110, difference=10,
                             comment="erreur")]
    repo.insert_closure(c, lines)
    c2 = CashClosure(period_start=_at(DAY1, 22), period_end=_at(DAY2, 23), business_date=DAY2,
                     kind="auto", opening_cash=Decimal(480), expected_cash=Decimal(480))
    repo.insert_closure(c2, [CashClosureLine(mode_code="especes", source="physical", opening=480,
                                             entries=0, exits=0, expected=480)])
    card = _ctrl(db_session).money(DAY1, DAY2)["cash_gaps"]
    days = card["days"]
    assert [d["business_date"] for d in days] == ["2030-03-11", "2030-03-12"]
    d1 = days[0]
    assert d1["kind"] == "manual" and d1["comment_missing"] is True
    assert (d1["expected_cash"], d1["counted_cash"], d1["difference"]) == ("500.00", "480.00", "-20.00")
    assert d1["lines"] == [
        {"mode": "especes", "expected": "500.00", "counted": "480.00", "difference": "-20.00"},
        {"mode": "orange_money", "expected": "100.00", "counted": "110.00", "difference": "10.00"},
    ]
    assert days[1]["kind"] == "auto" and days[1]["counted_cash"] is None
    assert card["total_abs_gap"] == "30.00"


# --- carte 3 : retraits et annulations ----------------------------------------------------
def test_withdrawals_and_cancellations(db_session):
    u = _secr(db_session)
    for amount, mode, cat in ((30, "Especes", "transport"), (20, "Orange Money", "transport")):
        r = create_test_retrait(db_session, u, amount=amount, payment_method=mode, category=cat)
        db_session.execute(text("UPDATE caisse_retrait SET received_at=:r WHERE retrait_id=:i"),
                           {"r": _at(DAY1, 9), "i": r.retrait_id})
    gone = create_test_retrait(db_session, u, amount=99)
    db_session.execute(text("UPDATE caisse_retrait SET received_at=:r, status='cancelled',"
                            " cancelled_at=:c WHERE retrait_id=:i"),
                       {"r": _at(DAY1, 9), "c": datetime(2030, 3, 11, 10), "i": gone.retrait_id})
    tx = _sale(db_session, u, advance=300, received_at=_at(DAY1, 9))
    # annulee a 2030-03-12 23:30 UTC naif = 2030-03-13 Douala : hors periode
    late = _sale(db_session, u, advance=0)
    for t, at in ((tx, datetime(2030, 3, 11, 12)), (late, datetime(2030, 3, 12, 23, 30))):
        db_session.execute(text("UPDATE caisse SET status='cancelled', cancelled_at=:c,"
                                " cancelled_by=:u, cancel_justification='doublon'"
                                " WHERE transaction_id=:t"),
                           {"c": at, "u": u.user_id, "t": t.transaction_id})
    card = _ctrl(db_session).money(DAY1, DAY2)["withdrawals_and_cancellations"]
    w = card["withdrawals"]
    assert w["count"] == 2 and w["total"] == "50.00"
    assert w["by_mode"]["especes"] == "30.00" and w["by_mode"]["orange_money"] == "20.00"
    assert w["by_reason"] == {"transport": "50.00"}
    cs = card["cancelled_sales"]
    assert cs["count"] == 1 and cs["amount_returned"] == "300.00"
    assert cs["recent"][0]["transaction_id"] == tx.transaction_id
    assert cs["recent"][0]["justification"] == "doublon"
    assert cs["recent"][0]["cancelled_by_name"] == u.username


# --- carte 4 : reductions -----------------------------------------------------------------
def _discount(db, tx, requester, decider, original, percent, decided_at):
    db.execute(text(
        "INSERT INTO discount_requests (transaction_id, requested_by, requested_to, original_amount,"
        " status, decision_percent, decided_by, decided_at, created_at)"
        " VALUES (:t, :u, :d, :o, 'approved', :p, :d, :at, :at)"),
        {"t": tx.transaction_id, "u": requester.user_id, "d": decider.user_id, "o": original,
         "p": percent, "at": decided_at})


def test_staff_and_manual_discounts_separate_and_cancelled_excluded(db_session):
    u = _secr(db_session)
    boss = _promoteur(db_session, "rm_boss")
    local = datetime(2030, 3, 11, 10)
    _sale(db_session, u, amount=950, paid_at=local, staff_discount=50)
    for st in ("cancelled", "refunded", "pending_approval"):
        _sale(db_session, u, amount=900, paid_at=local, staff_discount=100, status=st)
    ok = _sale(db_session, u, amount=800, paid_at=local)
    _discount(db_session, ok, u, boss, 1000, 20, datetime(2030, 3, 11, 9))
    bad = _sale(db_session, u, amount=500, paid_at=local, status="cancelled")
    _discount(db_session, bad, u, boss, 1000, 50, datetime(2030, 3, 11, 9))
    card = ReportsController(db_session, boss).money(DAY1, DAY2)["discounts"]
    assert card["staff"]["count"] == 1 and card["staff"]["amount"] == "50.00"
    assert card["manual"]["count"] == 1 and card["manual"]["amount"] == "200.00"


# --- carte 5 : par secretaire -------------------------------------------------------------
def test_per_secretary_worked_days(db_session):
    u = _secr(db_session)
    _sale(db_session, u, advance=100, received_at=_at(DAY1, 9))
    _sale(db_session, u, advance=200, received_at=_at(DAY2, 9))
    other = _secr(db_session, "rm_secr2")
    tx = _sale(db_session, other, advance=0)
    _pay(db_session, other, tx, 40, "Especes", _at(DAY1, 9))
    pending = _sale(db_session, other, advance=0, status="pending_approval")
    _pay(db_session, other, pending, 999, "Especes", _at(DAY1, 9))
    rows = {r["user_id"]: r for r in _ctrl(db_session).money(DAY1, DAY2)["per_secretary"]["rows"]}
    assert rows[u.user_id]["collected"] == "300.00"
    assert rows[u.user_id]["worked_days"] == 2
    assert rows[u.user_id]["per_worked_day"] == "150.00"
    assert rows[other.user_id]["collected"] == "40.00"


def test_per_worked_day_none_when_zero_days():
    from utils.report_rules import per_worked_day
    assert per_worked_day(Decimal("0"), 0) is None


# --- periode vide, droits -----------------------------------------------------------------
def test_empty_period_returns_zeros(db_session):
    m = _ctrl(db_session).money(date(2031, 1, 1), date(2031, 1, 1))
    assert m["collected"]["total"] == "0.00"
    assert all(v == "0.00" for v in m["collected"]["by_mode"].values())
    assert m["cash_gaps"]["days"] == [] and m["cash_gaps"]["total_abs_gap"] == "0.00"
    w = m["withdrawals_and_cancellations"]
    assert w["withdrawals"]["count"] == 0 and w["cancelled_sales"]["count"] == 0
    assert m["discounts"]["staff"]["amount"] == "0.00"
    assert m["per_secretary"]["rows"] == []
    g = _ctrl(db_session, _promoteur(db_session, "rm_p2")).growth(date(2031, 1, 1), date(2031, 1, 1))
    assert all(p["value"] == 0 for p in g["new_patients"]["series"])
    assert all(p["value"] == "0.00" for p in g["sales"]["series"])


@pytest.mark.parametrize("role", ["secretaire", "medecin", "StockController"])
def test_non_promoteur_admin_refused(db_session, role):
    try:
        user = create_test_user(db_session, f"rm_{role}", role)
    except Exception:
        pytest.skip(f"role {role} absent")
    c = ReportsController(db_session, user)
    with pytest.raises(PermissionError):
        c.money(DAY1, DAY2)
    with pytest.raises(PermissionError):
        c.growth(DAY1, DAY2)


def test_admin_allowed(db_session):
    admin = create_test_user(db_session, "rm_admin", "admin")
    assert ReportsController(db_session, admin).money(DAY1, DAY1)["collected"]["total"] == "0.00"


# --- croissance ---------------------------------------------------------------------------
def test_growth_weeks_zero_filled_and_previous_period(db_session):
    p = _promoteur(db_session)
    u = _secr(db_session)
    end = date(2030, 3, 13)                      # mercredi ; semaine du lundi 2030-03-11
    last_monday = date(2030, 3, 11)
    first_monday = last_monday - timedelta(weeks=12)
    # ventes actives au paid_at local ; une annulee ignoree
    _sale(db_session, u, amount=1000, paid_at=datetime(2030, 3, 11, 0, 30))
    _sale(db_session, u, amount=500, paid_at=datetime(2030, 3, 10, 23, 30))  # dimanche : semaine precedente
    _sale(db_session, u, amount=777, paid_at=datetime(2030, 3, 11, 9), status="cancelled")
    _sale(db_session, u, amount=250, paid_at=datetime(2029, 12, 3, 9))       # periode precedente
    # patients et consultations
    pid, _ = create_test_patient(db_session, p)
    db_session.execute(text("UPDATE patients SET created_at=:c WHERE patient_id=:i"),
                       {"c": datetime(2030, 3, 12, 8), "i": pid})
    create_test_medical_record(db_session, p, pid)
    db_session.execute(text("UPDATE medical_records SET consultation_date=:c WHERE patient_id=:i"),
                       {"c": datetime(2030, 3, 12, 9), "i": pid})
    # spirituelle : UTC naif ; 2030-03-10 23:30 UTC = 2030-03-11 00:30 Douala
    db_session.execute(text(
        "INSERT INTO consultation_spirituel (patient_id, consultation_date, created_by,"
        " created_by_name, type_consultation) VALUES (:p, :c, :u, 'x', 'Spiritual')"),
        {"p": pid, "c": datetime(2030, 3, 10, 23, 30), "u": p.user_id})
    g = ReportsController(db_session, p).growth(date(2030, 3, 1), end)

    assert len(g["new_patients"]["series"]) == 13
    assert len(g["sales"]["series"]) == 13 and len(g["sales"]["sales_previous"]) == 13
    assert len(g["consultations"]["medical"]) == 13 == len(g["consultations"]["spiritual"])
    weeks = [s["week_start"] for s in g["sales"]["series"]]
    assert weeks[0] == first_monday.isoformat() and weeks[-1] == last_monday.isoformat()
    sales = {s["week_start"]: s["value"] for s in g["sales"]["series"]}
    assert sales["2030-03-11"] == "1000.00" and sales["2030-03-04"] == "500.00"
    assert sum(Decimal(v) for v in sales.values()) == Decimal("1500")
    prev = g["sales"]["sales_previous"]
    assert prev[-1]["week_start"] == (first_monday - timedelta(weeks=1)).isoformat()
    assert {s["week_start"]: s["value"] for s in prev}["2029-12-03"] == "250.00"
    np = {s["week_start"]: s["value"] for s in g["new_patients"]["series"]}
    assert np["2030-03-11"] == 1 and sum(np.values()) == 1
    med = {s["week_start"]: s["value"] for s in g["consultations"]["medical"]}
    spi = {s["week_start"]: s["value"] for s in g["consultations"]["spiritual"]}
    assert med["2030-03-11"] == 1 and spi["2030-03-11"] == 1
    assert g["new_patients"]["id"] == "new_patients" and g["sales"]["source"]


# --- correctifs de revue (ronde 1) --------------------------------------------------------
def test_basis_scope_and_cancelled_later_part(db_session):
    u = _secr(db_session)
    _sale(db_session, u, advance=100, received_at=_at(DAY1, 9))
    gone = _sale(db_session, u, advance=60, received_at=_at(DAY1, 10))
    db_session.execute(text("UPDATE caisse SET status='cancelled', cancelled_at=:c,"
                            " cancelled_by=:u WHERE transaction_id=:t"),
                       {"c": datetime(2030, 3, 20, 9), "u": u.user_id, "t": gone.transaction_id})
    m = _ctrl(db_session).money(DAY1, DAY1)
    row = m["per_secretary"]["rows"][0]
    assert row["collected"] == "160.00" and row["of_which_cancelled_later"] == "60.00"
    assert m["discounts"]["manual"]["basis"] == "reports.basis.decision_date"
    assert m["discounts"]["staff"]["basis"] == "reports.basis.payment_date"
    assert m["cash_gaps"]["scope"] == "all_modes"


def test_received_at_midnight_bounds_one_day(db_session):
    u = _secr(db_session)
    _sale(db_session, u, advance=10, received_at=_at(DAY1, 0))                  # compte
    _sale(db_session, u, advance=20, received_at=_at(DAY1 + timedelta(days=1), 0))  # exclu
    m = _ctrl(db_session).money(DAY1, DAY1)
    assert m["collected"]["total"] == "10.00"
    assert m["per_secretary"]["rows"][0]["collected"] == "10.00"


def test_paid_at_local_midnight_bounds_one_day(db_session):
    u = _secr(db_session)
    _sale(db_session, u, amount=100, paid_at=datetime(2030, 3, 11, 0, 0), staff_discount=5)
    _sale(db_session, u, amount=200, paid_at=datetime(2030, 3, 12, 0, 0), staff_discount=7)
    m = _ctrl(db_session).money(DAY1, DAY1)
    assert m["discounts"]["staff"] == {"count": 1, "amount": "5.00",
                                       "basis": "reports.basis.payment_date"}
    g = _ctrl(db_session, _promoteur(db_session, "rm_p3")).growth(DAY1, DAY1)
    last = g["sales"]["series"][-1]
    assert last == {"week_start": "2030-03-11", "value": "100.00", "partial": True}
    assert all(p["partial"] is False for p in g["sales"]["series"][:-1])
    assert all(p["partial"] is False for p in g["sales"]["sales_previous"])
    assert g["new_patients"]["series"][-1]["partial"] is True
    assert g["consultations"]["medical"][-1]["partial"] is True


def test_growth_full_last_week_on_sunday(db_session):
    g = _ctrl(db_session).growth(date(2030, 3, 17), date(2030, 3, 17))
    assert g["sales"]["series"][-1]["partial"] is False
