# tests/test_daily_control.py
"""Rapports, tache 5 : controle quotidien (anomalies, instantane, notification, reglages).

Dates en 2033 pour ne jamais croiser les donnees reelles. La table daily_controls est videe DANS
la transaction du test (annulee en fin de test). Les tests de la logique de notification
remplacent compute_anomalies par une liste fixe : les anomalies d'etat courant de la base de dev
(produits jamais comptes, lots...) ne doivent pas les rendre fragiles. Les tests de sources
cherchent leurs propres references dans le resultat.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from controller.cash_closure_controller import CashClosureController
from controller.reports_controller import ReportsController, get_reports_controller
from models.audit import AuditUserAction
from models.fabrication import FabBatch, FabBatchOutput
from models.notification import Notification
from models.pharmacy import Pharmacy
from models.report import DailyControl, ReportSettings
from models.stock_reception import StockAdjustmentRequest
from repositories.audit_repo import AuditRepository
from repositories.cash_closure_repo import CashClosureRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_transaction, create_test_user
from utils.business_time import BUSINESS_TZ as DLA

D1 = date(2033, 4, 4)   # lundi
UTC = timezone.utc


def _r(p="t"):
    return f"{p}_{uuid.uuid4().hex[:8]}"


def _at(d, h=23, m=40):
    return datetime(d.year, d.month, d.day, h, m, tzinfo=DLA)


class Clock:
    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at


def _a(kind, ref, label="Point"):
    return {"key": f"{kind}:{ref}", "kind": kind, "ref": str(ref), "label": label,
            "detail": {}, "link": "/dashboard/reports"}


@pytest.fixture
def env(db_session):
    db = db_session
    db.execute(text("DELETE FROM daily_controls"))
    users = {
        "promo": create_test_user(db, _r("dc_promo"), "promoteur"),
        "admin": create_test_user(db, _r("dc_admin"), "admin"),
        "admin_off": create_test_user(db, _r("dc_admoff"), "admin", is_active=False),
        "secr": create_test_user(db, _r("dc_secr"), "secretaire"),
        "stock": create_test_user(db, _r("dc_stock"), "StockController"),
    }
    db.commit()  # fige la mise en place : un rollback du controleur ne doit pas l'effacer
    clock = Clock(_at(D1))
    return db, users, clock


def _ctrl(db, user, clock, anomalies=None):
    c = ReportsController(db, user, clock=clock)
    if anomalies is not None:
        c.compute_anomalies = lambda day: anomalies(day) if callable(anomalies) else list(anomalies)
    return c


def _notifs(db, users=None):
    q = db.query(Notification).filter(Notification.type == "daily_control")
    if users is not None:
        q = q.filter(Notification.recipient_user_id.in_([u.user_id for u in users]))
    return q.order_by(Notification.id).all()


def _snaps(db):
    return db.query(DailyControl).order_by(DailyControl.business_date).all()


def _recipients(db):
    return len(CashClosureRepository(db).recipient_user_ids())


# --- notification : nouveau, idempotence, roles -----------------------------------------------
def test_new_anomaly_notifies_promoteur_and_active_admins_once(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [_a("sortie_autre", 1)])
    out = c.run_daily_control(D1, now=clock())
    assert out["notified"] is True and out["reason"] == "nouveau"
    assert out["new"] == 1 and out["still_open"] == 0
    mine = _notifs(db, u.values())
    assert sorted(n.recipient_user_id for n in mine) == sorted([u["promo"].user_id, u["admin"].user_id])
    assert len(_notifs(db)) == _recipients(db)
    p = mine[0].payload
    assert p == {"business_date": D1.isoformat(), "new_count": 1, "open_count": 1, "reason": "nouveau"}
    snap = _snaps(db)
    assert len(snap) == 1 and snap[0].notified_at is not None and snap[0].reminder_sent_at is None
    assert snap[0].anomalies[0]["first_seen"] == D1.isoformat()
    # second passage du meme jour : ni instantane ni notification de plus
    again = c.run_daily_control(D1, now=clock() + timedelta(minutes=5))
    assert again["notified"] is False and again["created"] is False
    assert len(_snaps(db)) == 1 and len(_notifs(db)) == _recipients(db)


def test_next_day_still_open_silent_then_reminder_after_7_days(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [_a("comptage_jamais", 5)])
    assert c.run_daily_control(D1, now=_at(D1))["notified"] is True
    n0 = len(_notifs(db))
    for i in range(1, 7):
        d = D1 + timedelta(days=i)
        out = c.run_daily_control(d, now=_at(d))
        assert out["notified"] is False and out["new"] == 0 and out["still_open"] == 1
    assert len(_notifs(db)) == n0
    d7 = D1 + timedelta(days=7)
    out = c.run_daily_control(d7, now=_at(d7))
    assert out["notified"] is True and out["reason"] == "rappel"
    mine = _notifs(db, [u["promo"]])
    assert len(mine) == 2 and mine[-1].payload["reason"] == "rappel"
    assert mine[-1].payload["new_count"] == 0 and mine[-1].payload["open_count"] == 1
    assert _snaps(db)[-1].reminder_sent_at is not None
    d8 = D1 + timedelta(days=8)
    assert c.run_daily_control(d8, now=_at(d8))["notified"] is False  # un rappel par 7 jours


def test_no_anomaly_no_notification_but_snapshot(env):
    db, u, clock = env
    out = _ctrl(db, None, clock, []).run_daily_control(D1, now=clock())
    assert out["notified"] is False and out["created"] is True
    snap = _snaps(db)
    assert len(snap) == 1 and snap[0].anomalies == [] and snap[0].new_count == 0
    assert snap[0].notified_at is None
    assert _notifs(db, u.values()) == []


def test_new_key_next_day_notifies_with_counts(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, lambda d: [_a("x", 1)] + ([_a("x", 2)] if d > D1 else []))
    c.run_daily_control(D1, now=_at(D1))
    d2 = D1 + timedelta(days=1)
    out = c.run_daily_control(d2, now=_at(d2))
    assert out["notified"] is True and out["reason"] == "nouveau"
    p = _notifs(db, [u["admin"]])[-1].payload
    assert p["new_count"] == 1 and p["open_count"] == 2


def test_notification_failure_keeps_snapshot_and_retry_sends_once(env, monkeypatch):
    db, u, clock = env
    c = _ctrl(db, None, clock, [_a("x", 1)])

    def boom(self, *a, **k):
        raise RuntimeError("notification indisponible")
    with monkeypatch.context() as m:
        m.setattr(NotificationRepository, "create", boom)
        out = c.run_daily_control(D1, now=clock())
    assert out["notified"] is False and out["created"] is True
    snap = _snaps(db)
    assert len(snap) == 1 and snap[0].notified_at is None
    assert _notifs(db, u.values()) == []
    assert c.retry_notification(D1) is True
    assert len(_notifs(db, u.values())) == 2
    assert c.retry_notification(D1) is False  # deja envoyee
    assert len(_notifs(db, u.values())) == 2
    db.expire_all()
    assert _snaps(db)[0].notified_at is not None


def test_audit_run_only_with_user(env):
    db, u, clock = env
    _ctrl(db, None, clock, []).run_daily_control(D1, now=clock())
    _ctrl(db, u["admin"], clock, []).run_daily_control(D1 + timedelta(days=1), now=clock())
    rows = db.query(AuditUserAction).filter(AuditUserAction.resource_type == "DailyControl",
                                           AuditUserAction.action_performed == "RUN").all()
    assert [r.user_id for r in rows] == [u["admin"].user_id]


def test_run_refused_for_other_roles(env):
    db, u, clock = env
    with pytest.raises(PermissionError):
        _ctrl(db, u["secr"], clock, []).run_daily_control(D1, now=clock())


# --- rattrapage ------------------------------------------------------------------------------
def test_catch_up_three_missed_days_in_order(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [_a("x", 1)])
    c.run_daily_control(D1, now=_at(D1))
    now = _at(D1 + timedelta(days=4), 10, 0)   # avant 23:30 : aujourd'hui exclu
    out = c.catch_up(now)
    assert [o["day"] for o in out] == [(D1 + timedelta(days=i)).isoformat() for i in (1, 2, 3)]
    assert [s.business_date for s in _snaps(db)] == [D1 + timedelta(days=i) for i in range(4)]
    assert all(o["notified"] is False for o in out)  # meme point, deja signale
    assert c.catch_up(now) == []                     # deux fois : rien de plus


def test_catch_up_today_only_after_2330_douala(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [])
    c.run_daily_control(D1, now=_at(D1))
    d2 = D1 + timedelta(days=1)
    assert c.catch_up(_at(d2, 23, 29)) == []
    out = c.catch_up(_at(d2, 23, 30))
    assert [o["day"] for o in out] == [d2.isoformat()]


def test_catch_up_first_run_only_yesterday_and_today_after_2330(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [])
    out = c.catch_up(_at(D1, 10, 0))
    assert [o["day"] for o in out] == [(D1 - timedelta(days=1)).isoformat()]
    assert out[0]["recomputed"] is True
    db.execute(text("DELETE FROM daily_controls"))
    db.commit()
    out = c.catch_up(_at(D1, 23, 45))
    assert [o["day"] for o in out] == [(D1 - timedelta(days=1)).isoformat(), D1.isoformat()]
    assert [o["recomputed"] for o in out] == [True, False]


def test_catch_up_gap_with_history_capped_to_30_days_and_recomputed(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [])
    c.run_daily_control(D1 - timedelta(days=60), now=_at(D1 - timedelta(days=60)))
    out = c.catch_up(_at(D1, 10, 0))
    assert len(out) == 30 and out[0]["day"] == (D1 - timedelta(days=30)).isoformat()
    assert all(o["recomputed"] for o in out)
    rows = _snaps(db)
    assert rows[0].recomputed is False and all(r.recomputed for r in rows[1:])
    view = _ctrl(db, u["promo"], Clock(_at(D1, 11)), []).get_control(D1 - timedelta(days=2), D1 - timedelta(days=1))
    assert view["recomputed"] == [(D1 - timedelta(days=2)).isoformat(), (D1 - timedelta(days=1)).isoformat()]


def test_snapshot_before_2330_on_its_day_is_recomputed(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [])
    assert c.run_daily_control(D1, now=_at(D1, 23, 29))["recomputed"] is True
    d2 = D1 + timedelta(days=1)
    assert c.run_daily_control(d2, now=_at(d2, 23, 30))["recomputed"] is False


def test_retry_after_quiet_day_sends_stored_decision_once(env, monkeypatch):
    db, u, clock = env
    plan = {D1: ["A"], D1 + timedelta(days=1): [], D1 + timedelta(days=2): ["A"]}
    c = _ctrl(db, None, clock, lambda d: [_a("k", r) for r in plan[d]])
    c.run_daily_control(D1, now=_at(D1))
    d2, d3 = D1 + timedelta(days=1), D1 + timedelta(days=2)
    c.run_daily_control(d2, now=_at(d2))
    with monkeypatch.context() as m:
        m.setattr(NotificationRepository, "create",
                  lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
        assert c.run_daily_control(d3, now=_at(d3))["notified"] is False
    row = _snaps(db)[-1]
    assert row.notify_reason == "nouveau" and row.notify_new_count == 1 and row.notified_at is None
    c.catch_up(_at(d3 + timedelta(days=1), 9, 0))
    mine = _notifs(db, [u["promo"]])
    assert len(mine) == 2 and mine[-1].payload["new_count"] == 1
    assert mine[-1].payload["business_date"] == d3.isoformat()
    assert c.retry_notification(d3) is False
    c.catch_up(_at(d3 + timedelta(days=1), 10, 0))
    assert len(_notifs(db, [u["promo"]])) == 2


def test_quiet_snapshot_never_retried(env):
    db, u, clock = env
    c = _ctrl(db, None, clock, [])
    c.run_daily_control(D1, now=_at(D1))
    assert _snaps(db)[0].notify_reason is None
    assert c.retry_notification(D1) is False
    c.catch_up(_at(D1 + timedelta(days=1), 9, 0))
    assert _notifs(db, u.values()) == []


def test_catch_up_retries_pending_notification_of_latest(env, monkeypatch):
    db, u, clock = env
    c = _ctrl(db, None, clock, [_a("x", 1)])
    with monkeypatch.context() as m:
        m.setattr(NotificationRepository, "create",
                  lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
        c.run_daily_control(D1, now=_at(D1))
    assert _notifs(db, u.values()) == []
    c.catch_up(_at(D1 + timedelta(days=1), 10, 0))
    assert len(_notifs(db, u.values())) == 2
    c.catch_up(_at(D1 + timedelta(days=1), 11, 0))
    assert len(_notifs(db, u.values())) == 2


def test_catch_up_lock_busy_returns_empty(env):
    db, u, clock = env
    from api_backend.backend_app.database import SessionLocal
    from repositories.report_repo import DAILY_CONTROL_LOCK_KEY
    other = SessionLocal()
    try:
        assert other.execute(text("SELECT pg_try_advisory_lock(:k)"),
                             {"k": DAILY_CONTROL_LOCK_KEY}).scalar()
        assert _ctrl(db, None, clock, []).catch_up(_at(D1, 10)) == []
        assert _snaps(db) == []
    finally:
        other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": DAILY_CONTROL_LOCK_KEY})
        other.close()


# --- lecture ---------------------------------------------------------------------------------
def test_get_control_live_writes_nothing_and_flags_recomputed(env):
    db, u, clock = env
    c = _ctrl(db, u["promo"], Clock(_at(D1 + timedelta(days=2), 9, 0)),
              lambda d: [_a("x", 1)] + ([_a("y", d.isoformat())] if d == D1 else []))
    _ctrl(db, None, clock, [_a("x", 1)]).run_daily_control(D1, now=_at(D1))
    n_before = len(_notifs(db))
    out = c.get_control(D1, D1 + timedelta(days=2))
    assert out["recomputed"] == [(D1 + timedelta(days=1)).isoformat()]
    keys = {i["key"]: i for i in out["items"]}
    assert set(keys) == {"x:1"}  # D1 lu de l'instantane (y n'y est pas)
    assert keys["x:1"]["first_seen"] == D1.isoformat()
    assert keys["x:1"]["already_notified_on"] == D1.isoformat()
    assert len(_snaps(db)) == 1 and len(_notifs(db)) == n_before


def test_get_control_today_live_not_recomputed(env):
    db, u, clock = env
    c = _ctrl(db, u["admin"], Clock(_at(D1, 9, 0)), [_a("z", 9)])
    out = c.get_control(D1, D1)
    assert out["recomputed"] == [] and [i["key"] for i in out["items"]] == ["z:9"]
    assert out["items"][0]["already_notified_on"] is None
    assert _snaps(db) == []


def test_get_control_refused_for_other_roles(env):
    db, u, clock = env
    with pytest.raises(PermissionError):
        _ctrl(db, u["secr"], clock, []).get_control(D1, D1)


def test_first_seen_across_three_snapshots(env):
    db, u, clock = env
    plan = {D1: ["a"], D1 + timedelta(days=1): ["a", "b"], D1 + timedelta(days=2): ["a", "b", "c"]}
    c = _ctrl(db, None, clock, lambda d: [_a("k", r) for r in plan[d]])
    for d in plan:
        c.run_daily_control(d, now=_at(d))
    last = _snaps(db)[-1].anomalies
    fs = {a["key"]: a["first_seen"] for a in last}
    assert fs == {"k:a": D1.isoformat(), "k:b": (D1 + timedelta(days=1)).isoformat(),
                  "k:c": (D1 + timedelta(days=2)).isoformat()}
    reader = _ctrl(db, u["promo"], Clock(_at(D1 + timedelta(days=3), 8)), [])
    items = {i["key"]: i for i in reader.get_control(D1 + timedelta(days=2), D1 + timedelta(days=2))["items"]}
    assert items["k:a"]["first_seen"] == D1.isoformat()


# --- reglages --------------------------------------------------------------------------------
def test_settings_admin_only_bounds_audit_and_upsert(env):
    db, u, clock = env
    db.execute(text("DELETE FROM report_settings"))
    db.commit()
    assert _ctrl(db, u["promo"], clock).get_settings()["cancelled_sales_threshold"] == 3
    for who in ("promo", "secr"):
        with pytest.raises(PermissionError):
            _ctrl(db, u[who], clock).set_settings(5, 5)
    c = _ctrl(db, u["admin"], clock)
    for bad in ((0, 3), (1001, 3), (3, 0), (3, 366), ("4", 3), (True, 3), (3.5, 3)):
        with pytest.raises(ValueError):
            c.set_settings(*bad)
    out = c.set_settings(5, 7)
    assert out["cancelled_sales_threshold"] == 5 and out["adjustment_pending_days"] == 7
    row = db.query(ReportSettings).one()
    assert row.updated_by == u["admin"].user_id
    assert c.set_settings(1000, 365)["adjustment_pending_days"] == 365
    audits = db.query(AuditUserAction).filter(AuditUserAction.resource_type == "ReportSettings",
                                             AuditUserAction.action_performed == "UPDATE").all()
    assert len(audits) == 2


# --- sources ---------------------------------------------------------------------------------
def _keys(c, day):
    return {a["key"]: a for a in c.compute_anomalies(day)}


def _cancelled_sales(db, user, n, day):
    for i in range(n):
        tx = create_test_transaction(
            db, user, amount=100, advance_amount=100,
            items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": 100, "quantity": 1,
                    "line_total": 100}])
        db.execute(text("UPDATE caisse SET status='cancelled', cancelled_at=:c, cancelled_by=:u,"
                        " cancel_justification='test' WHERE transaction_id=:t"),
                   {"c": _at(day, 10, i), "u": user.user_id, "t": tx.transaction_id})
    db.flush()


@pytest.mark.parametrize("n,expected", [(3, False), (4, True)])
def test_cancelled_sales_strictly_above_threshold(env, n, expected):
    db, u, clock = env
    _ctrl(db, u["admin"], clock).set_settings(3, 3)
    _cancelled_sales(db, u["secr"], n, D1)
    k = _keys(_ctrl(db, u["promo"], clock), D1)
    assert (f"ventes_annulees:{D1.isoformat()}" in k) is expected
    if expected:
        a = k[f"ventes_annulees:{D1.isoformat()}"]
        assert a["detail"]["count"] == 4 and a["link"].startswith("/dashboard/")


def _product(db):
    p = Pharmacy(drug_name=_r("DCP"), quantity=10, threshold=0, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    db.add(p)
    db.flush()
    return p


@pytest.mark.parametrize("age_h,expected", [(72, False), (96, True)])
def test_pending_adjustment_strictly_older_than_setting(env, age_h, expected):
    db, u, clock = env
    _ctrl(db, u["admin"], clock).set_settings(3, 3)
    p = _product(db)
    now_naive = clock().astimezone(UTC).replace(tzinfo=None)
    a = StockAdjustmentRequest(product_id=p.medication_id, kind="correction", quantity=1, reason="t",
                               status="en_attente", requested_by=u["stock"].user_id,
                               requested_at=now_naive - timedelta(hours=age_h))
    db.add(a)
    db.flush()
    k = _keys(_ctrl(db, u["promo"], clock), D1)
    assert (f"ajustement_en_attente:{a.id}" in k) is expected


def test_closures_auto_and_gap(env):
    from tests.cash_closure_isolation import reset_register
    db, u, clock = env
    reset_register(db)
    start = datetime(2033, 4, 4, 8, 0, tzinfo=DLA)
    cc = lambda at: CashClosureController(CashClosureRepository(db), AuditRepository(db),  # noqa: E731
                                          NotificationRepository(db), u["admin"], clock=lambda: at)
    cc(start).set_start(Decimal(0))
    # D1 : fermee seulement par l'automatique
    cc(start).auto_close_overdue(_at(D1 + timedelta(days=1), 9, 0))
    # D1+1 : cloture manuelle avec un ecart especes
    d2 = D1 + timedelta(days=1)
    counts = [{"mode": "especes", "counted": Decimal(50), "comment": "manque"}] + [
        {"mode": m, "counted": Decimal(0), "comment": None}
        for m in ("orange_money", "mtn_money", "autre_mobile")]
    cc(_at(d2, 18, 0)).submit(counts)
    c = _ctrl(db, u["promo"], clock)
    k1 = _keys(c, D1)
    assert f"cloture_auto:{D1.isoformat()}" in k1
    k2 = _keys(c, d2)
    assert f"cloture_auto:{d2.isoformat()}" not in k2
    assert f"ecart_caisse:{d2.isoformat()}:especes" in k2
    assert k2[f"ecart_caisse:{d2.isoformat()}:especes"]["link"] == "/dashboard/cash-closures"


def _batch(db, user, **kw):
    p = _product(db)
    b = FabBatch(batch_number=_r("DCB")[:30], product_id=p.medication_id, production_date=D1,
                 created_by=user.user_id, **kw)
    db.add(b)
    db.flush()
    return b


def test_outputs_autre_active_only(env):
    db, u, clock = env
    b = _batch(db, u["admin"], status="termine", qty_good=100)
    decl = _at(D1, 10).astimezone(UTC).replace(tzinfo=None)
    ok = FabBatchOutput(batch_id=b.id, reason="autre", quantity=2, note="casse",
                        declared_by=u["admin"].user_id, declared_at=decl)
    gone = FabBatchOutput(batch_id=b.id, reason="autre", quantity=1, note="x", status="annulee",
                          declared_by=u["admin"].user_id, declared_at=decl,
                          cancelled_by=u["admin"].user_id, cancelled_at=decl, cancel_reason="erreur")
    sample = FabBatchOutput(batch_id=b.id, reason="echantillon", quantity=1,
                            declared_by=u["admin"].user_id, declared_at=decl)
    db.add_all([ok, gone, sample])
    db.flush()
    k = _keys(_ctrl(db, u["promo"], clock), D1)
    assert f"sortie_autre:{ok.id}" in k
    assert f"sortie_autre:{gone.id}" not in k and f"sortie_autre:{sample.id}" not in k


def test_fabrication_out_of_tolerance(env):
    db, u, clock = env
    b = _batch(db, u["admin"], status="termine", qty_good=90, expected_qty=100, found_qty=90,
               missing_qty=10, missing_pct=Decimal("10.00"), tolerance_applied=Decimal("2.00"),
               out_of_tolerance=True, justification="fuite")
    k = _keys(_ctrl(db, u["promo"], clock), D1)
    a = k[f"lot_hors_tolerance:{b.batch_number}"]
    assert a["link"].startswith("/dashboard/fabrication")


def test_price_mismatch_of_the_day(env):
    db, u, clock = env
    tx = create_test_transaction(db, u["secr"], amount=100, advance_amount=100,
                                 items=[{"item_type": "Service", "item_ref_id": 1, "unit_price": 100,
                                         "quantity": 1, "line_total": 100}])
    for ts in (_at(D1, 10), _at(D1 + timedelta(days=1), 10)):
        db.add(AuditUserAction(user_id=u["secr"].user_id, resource_type="Transaction",
                               resource_id=tx.transaction_id, action_performed="PRICE_MISMATCH",
                               new_values={"lines": []}, timestamp=ts))
    db.flush()
    c = _ctrl(db, u["promo"], clock)
    assert f"prix_different:{tx.transaction_id}" in _keys(c, D1)
    assert f"prix_different:{tx.transaction_id}" not in _keys(c, D1 - timedelta(days=1))


def test_stock_count_never_counted_is_one_point(env):
    db, u, clock = env
    c = _ctrl(db, u["promo"], clock)
    before = _keys(c, D1).get("comptage_jamais:tous", {"detail": {"total": 0}})["detail"]["total"]
    for _ in range(200):
        _product(db)
    k = _keys(c, D1)
    assert not any(x.startswith("comptage_jamais:") and x != "comptage_jamais:tous" for x in k)
    a = k["comptage_jamais:tous"]
    assert a["detail"]["total"] == before + 200 and len(a["detail"]["products"]) == 20
    assert a["detail"]["current_state"] is True
    assert str(before + 200) in a["label"]


def test_first_run_empty_history_one_small_notification(env):
    db, u, clock = env
    for _ in range(50):
        _product(db)
    db.commit()
    out = _ctrl(db, None, clock).catch_up(_at(D1, 10, 0))
    mine = _notifs(db, [u["promo"]])
    assert len(mine) == 1 and len(out) == 1
    assert mine[0].payload["new_count"] < 50


def test_catch_up_missed_days_one_notification_with_union(env):
    db, u, clock = env
    plan = {D1: ["a"], D1 + timedelta(days=1): ["a", "b"], D1 + timedelta(days=2): ["a", "c"],
            D1 + timedelta(days=3): ["a", "d"]}
    c = _ctrl(db, None, clock, lambda d: [_a("k", r) for r in plan[d]])
    c.run_daily_control(D1, now=_at(D1))
    n0 = len(_notifs(db, [u["promo"]]))
    out = c.catch_up(_at(D1 + timedelta(days=4), 9, 0))
    assert [o["day"] for o in out] == [(D1 + timedelta(days=i)).isoformat() for i in (1, 2, 3)]
    mine = _notifs(db, [u["promo"]])
    assert len(mine) == n0 + 1
    assert mine[-1].payload["business_date"] == (D1 + timedelta(days=3)).isoformat()
    assert mine[-1].payload["new_count"] == 1 and mine[-1].payload["open_count"] == 2
    assert len(_notifs(db, [u["admin"]])) == n0 + 1
    snaps = _snaps(db)
    assert [s.notified_at is not None for s in snaps] == [True, False, False, True]
    assert c.catch_up(_at(D1 + timedelta(days=4), 10, 0)) == []
    assert len(_notifs(db, [u["promo"]])) == n0 + 1


def test_catch_up_gap_key_still_open_at_end_is_new(env):
    db, u, clock = env
    plan = {D1: [], D1 + timedelta(days=1): ["b"], D1 + timedelta(days=2): ["b"]}
    c = _ctrl(db, None, clock, lambda d: [_a("k", r) for r in plan[d]])
    c.run_daily_control(D1, now=_at(D1))
    c.catch_up(_at(D1 + timedelta(days=3), 9, 0))
    mine = _notifs(db, [u["promo"]])
    assert len(mine) == 1 and mine[0].payload["new_count"] == 1


def test_all_labels_ascii_punctuation(env):
    db, u, clock = env
    _product(db)
    for a in _ctrl(db, u["promo"], clock).compute_anomalies(D1):
        assert not any(ch in a["label"] for ch in "–—…·"), a["label"]
        assert a["link"].startswith("/dashboard/")


def test_factory_wired_creates_notifications(env):
    db, u, clock = env
    c = get_reports_controller(db, None, clock=clock)
    c.compute_anomalies = lambda day: [_a("x", 1)]
    assert c.run_daily_control(D1, now=clock())["notified"] is True
    assert len(_notifs(db, u.values())) == 2


def test_get_control_live_recompute_capped_at_31_days(env):
    db, u, clock = env
    calls = []

    def fake(day):
        calls.append(day)
        return [_a("k", day.isoformat())]
    end = D1 + timedelta(days=99)
    c = _ctrl(db, u["promo"], Clock(_at(end, 9)), fake)
    out = c.get_control(D1, end)
    assert len(calls) == 31 and min(calls) == end - timedelta(days=30)
    assert out["uncontrolled_days"] == 69
    assert out["uncontrolled_range"] == {"from": D1.isoformat(),
                                         "to": (end - timedelta(days=31)).isoformat()}
    assert len(out["items"]) == 31 and len(out["recomputed"]) == 30


def test_get_control_no_cap_fields_when_covered(env):
    db, u, clock = env
    out = _ctrl(db, u["promo"], Clock(_at(D1, 9)), []).get_control(D1, D1)
    assert out["uncontrolled_days"] == 0 and out["uncontrolled_range"] is None
