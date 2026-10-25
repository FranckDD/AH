# tests/test_daily_control_cli.py
"""Script du soir du controle quotidien (scripts/daily_control.py).

main() recoit une fabrique de session et une horloge ; la session du test remplace SessionLocal.
compute_anomalies est remplace par une liste fixe (les anomalies d'etat courant de la base de dev
ne doivent pas rendre le test fragile).
"""
import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from controller.reports_controller import ReportsController
from models.notification import Notification
from models.report import DailyControl
from scripts import daily_control as cli
from tests.conftest import create_test_user
from utils.business_time import BUSINESS_TZ as DLA

D1 = date(2033, 6, 6)
NOW = datetime(2033, 6, 9, 23, 45, tzinfo=DLA)  # apres 23:30 : D1..D1+3 si rien avant


@pytest.fixture
def env(db_session, monkeypatch):
    db = db_session
    db.execute(text("DELETE FROM daily_controls"))
    promo = create_test_user(db, f"dcc_{uuid.uuid4().hex[:6]}", "promoteur")
    db.commit()
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(ReportsController, "compute_anomalies", lambda self, day: [
        {"key": "x:1", "kind": "x", "ref": "1", "label": "Point", "detail": {}, "link": "/dashboard/reports"}])
    return db, promo


def test_twice_one_notification_exit_zero(env, caplog):
    db, promo = env
    with caplog.at_level("INFO", logger="daily_control"):
        assert cli.main(session_factory=lambda: db, now=NOW) == 0
    days = [r.business_date for r in db.query(DailyControl).order_by(DailyControl.business_date)]
    assert days == [NOW.date() - timedelta(days=1), NOW.date()]  # sans historique : hier + aujourd'hui (apres 23:30)
    assert any("notified=True" in r.getMessage() for r in caplog.records)
    assert cli.main(session_factory=lambda: db, now=NOW) == 0
    mine = db.query(Notification).filter(Notification.type == "daily_control",
                                         Notification.recipient_user_id == promo.user_id).all()
    assert len(mine) == 1
    assert db.query(DailyControl).count() == 2


def test_database_error_returns_non_zero(env, monkeypatch):
    db, _ = env

    def boom(self, now=None):
        raise OperationalError("SELECT 1", {}, Exception("base indisponible"))
    monkeypatch.setattr(ReportsController, "catch_up", boom)
    assert cli.main(session_factory=lambda: db, now=NOW) != 0


def test_session_factory_error_returns_non_zero():
    def factory():
        raise OperationalError("connect", {}, Exception("connexion refusee"))
    assert cli.main(session_factory=factory, now=NOW) != 0


def test_naive_now_rejected():
    assert cli.main(session_factory=lambda: None, now=datetime(2033, 6, 9)) != 0


def test_lock_busy_logs_warning_exit_zero(env, caplog):
    db, _ = env
    from api_backend.backend_app.database import SessionLocal
    from repositories.report_repo import DAILY_CONTROL_LOCK_KEY
    other = SessionLocal()
    try:
        assert other.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": DAILY_CONTROL_LOCK_KEY}).scalar()
        with caplog.at_level("WARNING", logger="daily_control"):
            assert cli.main(session_factory=lambda: db, now=NOW) == 0
        assert any(r.levelname == "WARNING" for r in caplog.records)
        assert db.query(DailyControl).count() == 0
    finally:
        other.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": DAILY_CONTROL_LOCK_KEY})
        other.close()
