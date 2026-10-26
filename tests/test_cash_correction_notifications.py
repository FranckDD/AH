"""Releve B : les ajustements de caisse (corrections) n'envoyaient aucune notification."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import timedelta

import pytest

from models.notification import Notification
from tests.cash_closure_isolation import clean_register  # noqa: F401
from tests.conftest import create_test_user
from tests.test_cash_closure_controller import env, _ctrl, _start, _counts, DAY0  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")


def _closed(env_):
    db, admin, secr, clock = env_
    _start(db, admin, clock, 0)
    clock.at = DAY0 + timedelta(hours=5)
    return _ctrl(db, secr, clock).submit(_counts())


def _notifs(db, user, type_):
    db.expire_all()
    return db.query(Notification).filter_by(recipient_user_id=user.user_id, type=type_).all()


def test_request_notifies_promoteur_and_admin(env):
    db, admin, secr, clock = env
    promo = create_test_user(db, "cc_promo_n", "promoteur")
    d = _closed(env)
    corr = _ctrl(db, secr, clock).request_correction(d["id"], {"mode_code": "especes", "amount_delta": "-5.50", "reason": "erreur de rendu"})
    for who in (admin, promo):
        rows = _notifs(db, who, "cash_correction_requested")
        assert len(rows) == 1
        assert rows[0].payload["correction_id"] == corr["id"] and rows[0].payload["amount_delta"] == "-5.50"
    assert _notifs(db, secr, "cash_correction_requested") == []


def test_decision_notifies_the_requesting_secretary(env):
    db, admin, secr, clock = env
    promo = create_test_user(db, "cc_promo_d", "promoteur")
    d = _closed(env)
    corr = _ctrl(db, secr, clock).request_correction(d["id"], {"mode_code": "especes", "amount_delta": "5", "reason": "x"})
    _ctrl(db, promo, clock).decide_correction(corr["id"], True)
    rows = _notifs(db, secr, "cash_correction_decided")
    assert len(rows) == 1 and rows[0].payload["status"] == "approved" and rows[0].payload["correction_id"] == corr["id"]
