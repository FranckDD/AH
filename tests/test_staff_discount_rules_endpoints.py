# tests/test_staff_discount_rules_endpoints.py
import sys
import os

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.staff_discount import staff_discount_endpoints
from models.staff_discount_rule import StaffDiscountRule
from models.audit import AuditUserAction
from tests.conftest import auth_headers, create_test_user

# Les regles reelles de la base de dev ne doivent pas influencer ces tests.
pytestmark = pytest.mark.usefixtures("clean_staff_rules")

PASSWORD = "TestPass123!"


def _body(min_amount=1000, rate=10, active=True):
    return {"min_invoice_amount": min_amount, "rate_percent": rate, "is_active": active}


def _setup(db_session, api_client, username="sdr_admin", role="admin"):
    create_test_user(db_session, username, role, password=PASSWORD)
    client = api_client(auth_endpoints, staff_discount_endpoints)
    return client, auth_headers(client, username, PASSWORD)


def _rows(db_session, category):
    return db_session.query(StaffDiscountRule).filter_by(category=category).all()


def test_put_creates_then_updates_single_rule(db_session, api_client):
    client, h = _setup(db_session, api_client)
    r1 = client.put("/staff-discount-rules/medicament", json=_body(1000, 10), headers=h)
    assert r1.status_code == 200, r1.text
    r2 = client.put("/staff-discount-rules/medicament", json=_body(2000, 25), headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["rate_percent"] == 25
    assert r2.json()["min_invoice_amount"] == 2000
    assert len(_rows(db_session, "medicament")) == 1


def test_put_forbidden_for_secretaire(db_session, api_client):
    client, h = _setup(db_session, api_client, "sdr_sec", "secretaire")
    r = client.put("/staff-discount-rules/medicament", json=_body(), headers=h)
    assert r.status_code == 403


def test_get_allowed_for_secretaire(db_session, api_client):
    client, h = _setup(db_session, api_client, "sdr_sec2", "secretaire")
    r = client.get("/staff-discount-rules", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_returns_shape(db_session, api_client):
    client, h = _setup(db_session, api_client)
    client.put("/staff-discount-rules/examen", json=_body(500, 15), headers=h)
    rows = client.get("/staff-discount-rules", headers=h).json()
    row = next(x for x in rows if x["category"] == "examen")
    assert row == {"category": "examen", "min_invoice_amount": 500.0,
                   "rate_percent": 15, "is_active": True}


def test_put_rejects_invalid_values(db_session, api_client):
    client, h = _setup(db_session, api_client)
    assert client.put("/staff-discount-rules/medicament", json=_body(rate=0), headers=h).status_code == 422
    assert client.put("/staff-discount-rules/medicament", json=_body(rate=101), headers=h).status_code == 422
    assert client.put("/staff-discount-rules/medicament", json=_body(min_amount=-1), headers=h).status_code == 422
    assert client.put("/staff-discount-rules/xyz", json=_body(), headers=h).status_code == 422
    assert _rows(db_session, "medicament") == []


def test_put_writes_audit_entry(db_session, api_client):
    client, h = _setup(db_session, api_client)
    client.put("/staff-discount-rules/carnet", json=_body(100, 10), headers=h)
    client.put("/staff-discount-rules/carnet", json=_body(300, 40), headers=h)
    logs = (db_session.query(AuditUserAction)
            .filter_by(resource_type="StaffDiscountRule")
            .order_by(AuditUserAction.action_id).all())
    assert len(logs) >= 2
    last = logs[-1]
    assert last.old_values["rate_percent"] == 10
    assert last.new_values["rate_percent"] == 40
    assert last.new_values["category"] == "carnet"


def test_deactivate_then_reactivate_keeps_unique_active_rule(db_session, api_client):
    client, h = _setup(db_session, api_client)
    assert client.put("/staff-discount-rules/consultation", json=_body(0, 20), headers=h).status_code == 200
    r = client.put("/staff-discount-rules/consultation", json=_body(0, 20, False), headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is False
    r = client.put("/staff-discount-rules/consultation", json=_body(0, 30, True), headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is True
    rows = _rows(db_session, "consultation")
    assert len(rows) == 1 and rows[0].is_active and rows[0].rate_percent == 30


def _audit_count(db_session):
    return db_session.query(AuditUserAction).filter_by(resource_type="StaffDiscountRule").count()


def test_put_rejects_nan_infinity_and_oversized_minimum(db_session, api_client):
    client, h = _setup(db_session, api_client)
    hj = {**h, "Content-Type": "application/json"}
    for raw in ('{"min_invoice_amount": NaN, "rate_percent": 10, "is_active": true}',
                '{"min_invoice_amount": Infinity, "rate_percent": 10, "is_active": true}',
                '{"min_invoice_amount": 1e12, "rate_percent": 10, "is_active": true}'):
        r = client.put("/staff-discount-rules/medicament", content=raw, headers=hj)
        assert r.status_code == 422, (raw, r.status_code, r.text)
    assert _rows(db_session, "medicament") == []
    assert _audit_count(db_session) == 0


def test_controller_rejects_non_finite_and_oversized(db_session):
    import pytest
    from controller.staff_discount_controller import StaffDiscountController
    from repositories.staff_discount_repo import StaffDiscountRepository
    from repositories.audit_repo import AuditRepository
    u = create_test_user(db_session, "sdr_ctrl", "admin", password=PASSWORD)
    ctrl = StaffDiscountController(StaffDiscountRepository(db_session), u, AuditRepository(db_session))
    for bad in (float("nan"), float("inf"), 1e12):
        with pytest.raises(ValueError):
            ctrl.update_rule("medicament", bad, 10, True)
    assert _rows(db_session, "medicament") == []


def test_get_forbidden_for_other_role(db_session, api_client):
    client, h = _setup(db_session, api_client, "sdr_med", "medecin")
    assert client.get("/staff-discount-rules", headers=h).status_code == 403


def test_unauthenticated_refused(db_session, api_client):
    client = api_client(auth_endpoints, staff_discount_endpoints)
    assert client.get("/staff-discount-rules").status_code in (401, 403)
    assert client.put("/staff-discount-rules/medicament", json=_body()).status_code in (401, 403)


def test_audit_first_entry_create_with_user_and_no_row_on_failure(db_session, api_client):
    client, h = _setup(db_session, api_client)
    client.put("/staff-discount-rules/medicament", json=_body(rate=0), headers=h)
    assert _audit_count(db_session) == 0
    client.put("/staff-discount-rules/medicament", json=_body(), headers=h)
    logs = db_session.query(AuditUserAction).filter_by(resource_type="StaffDiscountRule").all()
    assert len(logs) == 1 and logs[0].action_performed == "CREATE"
    assert logs[0].user_id is not None
