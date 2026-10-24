# tests/test_cash_closure_cli.py
"""Script de rattrapage des clotures automatiques (scripts/cash_closure_catchup.py).

main() recoit une fabrique de session et une horloge : la session du test (transaction annulee
en fin de test) remplace SessionLocal ; les dates sont en 2030 comme dans
tests/test_cash_closure_controller.py.
"""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import OperationalError

from controller.cash_closure_controller import CashClosureController
from models.cash_closure import CashClosure
from repositories.audit_repo import AuditRepository
from repositories.cash_closure_repo import CashClosureRepository
from repositories.notification_repo import NotificationRepository
from scripts import cash_closure_catchup as cli
from tests.conftest import create_test_user
from utils.cash_rules import TZ
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")


DAY0 = datetime(2030, 5, 6, 8, 0, tzinfo=TZ)


def _factory(db, monkeypatch):
    monkeypatch.setattr(db, "close", lambda: None)  # la fixture ferme elle-meme sa session
    return lambda: db


def _start(db):
    admin = create_test_user(db, "cli_admin", "admin")
    CashClosureController(CashClosureRepository(db), AuditRepository(db), NotificationRepository(db),
                          admin, clock=lambda: DAY0).set_start(Decimal(0))


def test_twice_one_closure_per_missed_day(db_session, monkeypatch):
    _start(db_session)
    factory = _factory(db_session, monkeypatch)
    now = DAY0 + timedelta(days=3, hours=2)
    assert cli.main(session_factory=factory, now=now) == 0
    assert db_session.query(CashClosure).count() == 3
    assert cli.main(session_factory=factory, now=now) == 0  # idempotent
    rows = db_session.query(CashClosure).all()
    assert len(rows) == 3 and all(r.kind == "auto" for r in rows)
    assert sorted(r.business_date for r in rows) == [(DAY0 + timedelta(days=i)).date() for i in range(3)]


def test_nothing_to_do_returns_zero(db_session, monkeypatch):
    # sans depart (base de dev vierge, comme les tests du controleur) : rien a faire, succes
    assert cli.main(session_factory=_factory(db_session, monkeypatch), now=DAY0) == 0


def test_database_error_returns_non_zero(db_session, monkeypatch):
    def boom(self, now):
        raise OperationalError("SELECT 1", {}, Exception("base indisponible"))
    monkeypatch.setattr(CashClosureController, "auto_close_overdue", boom)
    assert cli.main(session_factory=_factory(db_session, monkeypatch), now=DAY0) != 0


def test_session_factory_error_returns_non_zero():
    def factory():
        raise OperationalError("connect", {}, Exception("connexion refusee"))
    assert cli.main(session_factory=factory, now=DAY0) != 0


def test_naive_now_rejected():
    assert cli.main(session_factory=lambda: None, now=datetime(2030, 5, 6)) != 0


def test_lock_busy_logs_warning_and_creates_nothing(db_session, caplog):
    # la session du test tient le verrou de cloture (transaction ouverte) ; le script, sur sa
    # propre connexion SessionLocal, doit le trouver occupe, avertir et ne rien creer.
    from sqlalchemy import text
    from api_backend.backend_app.database import SessionLocal
    from repositories.cash_closure_repo import LOCK_KEY

    probe = SessionLocal()
    try:  # base reelle vue d'une autre connexion : elle peut contenir de vraies clotures
        before = probe.query(CashClosure).count()
    finally:
        probe.close()
    _start(db_session)
    assert db_session.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": LOCK_KEY}).scalar()
    with caplog.at_level("WARNING", logger="cash_closure_catchup"):
        rc = cli.main(session_factory=SessionLocal, now=DAY0 + timedelta(days=3))
    assert rc == 0
    assert any(r.levelname == "WARNING" and "saute" in r.getMessage() for r in caplog.records)
    assert db_session.query(CashClosure).count() == 0
    probe = SessionLocal()
    try:
        assert probe.query(CashClosure).count() == before
    finally:
        probe.close()
