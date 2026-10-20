# tests/test_staff_discount_schema.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy.exc import IntegrityError

from models.staff_discount_rule import StaffDiscountRule
from models.patient import Patient
from tests.conftest import create_test_user, create_test_patient

# Les regles reelles de la base de dev ne doivent pas influencer ces tests.
pytestmark = pytest.mark.usefixtures("clean_staff_rules")


def _add_rule(session, **kw):
    data = {"category": "medicament", "rate_percent": 10, "is_active": True}
    data.update(kw)
    rule = StaffDiscountRule(**data)
    session.add(rule)
    return rule


def test_two_active_rules_same_category_rejected(db_session):
    _add_rule(db_session)
    db_session.flush()
    with pytest.raises(IntegrityError):
        _add_rule(db_session, rate_percent=20)
        db_session.flush()


def test_unknown_category_rejected(db_session):
    with pytest.raises(IntegrityError):
        _add_rule(db_session, category="inconnue")
        db_session.flush()


@pytest.mark.parametrize("rate", [0, 101])
def test_rate_out_of_range_rejected(db_session, rate):
    with pytest.raises(IntegrityError):
        _add_rule(db_session, rate_percent=rate)
        db_session.flush()


def test_negative_min_amount_rejected(db_session):
    with pytest.raises(IntegrityError):
        _add_rule(db_session, min_invoice_amount=-1)
        db_session.flush()


def test_patient_is_staff_defaults_false(db_session):
    user = create_test_user(db_session, "sd_schema_secr", "secretaire")
    pid, _ = create_test_patient(db_session, user)
    patient = db_session.get(Patient, pid)
    assert patient.is_staff is False


def test_inactive_and_active_same_category_coexist(db_session):
    _add_rule(db_session, is_active=False)
    _add_rule(db_session, is_active=True)
    db_session.flush()
