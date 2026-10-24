# tests/test_discount_requests_staff.py
"""Task 6 - interaction reduction manuelle / reduction personnel."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
from unittest.mock import MagicMock

import pytest

from controller.caisse_controller import CaisseController
from controller.discount_request_controller import DiscountRequestController
from repositories.caisse_repo import CaisseRepository
from repositories.discount_request_repo import DiscountRequestRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user
from tests.test_caisse_staff_discount import _only_rule, _patient, _med, _payload, _catalog_exam  # noqa: F401 (fixture autouse)

PWD = "TestPass123!"


def _setup(db, name, staff=True, discount=1500.0):
    sec = create_test_user(db, f"{name}_sec", "secretaire", password=PWD)
    mgr = create_test_user(db, f"{name}_mgr", "admin", password=PWD)
    mgr2 = create_test_user(db, f"{name}_mg2", "promoteur", password=PWD)
    _only_rule(db)
    pid = _patient(db, sec, staff=staff)
    audit = MagicMock()
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db),
        caisse_repo=CaisseRepository(db),
        notification_repo=NotificationRepository(db),
        current_user=sec,
        audit_repo=audit,
    )
    data = _payload(pid, _med(db), discount=discount if staff else None)
    req = ctrl.create_request(data, requested_to=mgr.user_id)
    return sec, mgr, mgr2, ctrl, req, audit


def _decide(ctrl, mgr, req, **kw):
    ctrl.user = mgr
    return ctrl.decide_request(req.id, password=PWD, **kw)


def test_request_original_amount_is_gross_for_staff_invoice(db_session):
    _, _, _, ctrl, req, _ = _setup(db_session, "t6a")
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert float(tx.amount) == 5500.0
    assert float(tx.staff_discount_amount) == 1500.0
    assert float(req.original_amount) == 7000.0


def test_approval_replaces_staff_discount(db_session):
    _, mgr, _, ctrl, req, audit = _setup(db_session, "t6b")
    _decide(ctrl, mgr, req, refuse=False, decision_percent=20)
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert tx.status == "active"
    assert float(tx.amount) == 5600.0  # 7000 * 0.8, pas 5500 * 0.8
    assert float(tx.staff_discount_amount) == 0
    d = tx.staff_discount_details
    assert d["replaced_by_discount_request"] == req.id
    assert d["previous"][0]["category"] == "medicament"
    kwargs = audit.log_user_action.call_args.kwargs
    assert kwargs["new_values"]["replaced_staff_discount_amount"] == 1500.0
    assert kwargs["new_values"]["final_amount"] == 5600.0


def test_ticket_has_no_staff_discount_after_replacement(db_session):
    sec, mgr, _, ctrl, req, _ = _setup(db_session, "t6c")
    _decide(ctrl, mgr, req, refuse=False, decision_percent=10)
    data = CaisseController(repo=CaisseRepository(db_session), current_user=sec).build_ticket_data(req.transaction_id)
    assert data["staff_discount"] is None


def test_refusal_keeps_staff_discount(db_session):
    _, mgr, _, ctrl, req, _ = _setup(db_session, "t6d")
    _decide(ctrl, mgr, req, refuse=True)
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert float(tx.amount) == 5500.0
    assert float(tx.staff_discount_amount) == 1500.0
    assert isinstance(tx.staff_discount_details, list)


def test_approval_echeance_only_keeps_staff_discount(db_session):
    _, mgr, _, ctrl, req, audit = _setup(db_session, "t6e")
    _decide(ctrl, mgr, req, refuse=False, decision_echelonne_deadline=date(2026, 12, 31))
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert float(tx.amount) == 5500.0
    assert float(tx.staff_discount_amount) == 1500.0
    assert isinstance(tx.staff_discount_details, list)
    assert "replaced_staff_discount_amount" not in audit.log_user_action.call_args.kwargs["new_values"]


def test_non_staff_request_unchanged(db_session):
    _, mgr, _, ctrl, req, audit = _setup(db_session, "t6f", staff=False)
    assert float(req.original_amount) == 7000.0
    _decide(ctrl, mgr, req, refuse=False, decision_percent=20)
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    assert float(tx.amount) == 5600.0
    assert float(tx.staff_discount_amount) == 0
    assert tx.staff_discount_details is None
    assert "replaced_staff_discount_amount" not in audit.log_user_action.call_args.kwargs["new_values"]


def test_reassign_keeps_gross_original_amount(db_session):
    _, mgr, mgr2, ctrl, req, _ = _setup(db_session, "t6g")
    new_req = ctrl.cancel_and_reassign(req.id, mgr2.user_id)
    assert float(new_req.original_amount) == 7000.0
    _decide(ctrl, mgr2, new_req, refuse=False, decision_percent=50)
    tx = ctrl.caisse_repo.get_by_id(new_req.transaction_id)
    assert float(tx.amount) == 3500.0
    assert tx.staff_discount_details["replaced_by_discount_request"] == new_req.id


def test_create_request_rejects_wrong_staff_discount(db_session):
    with pytest.raises(ValueError, match="Réduction personnel incohérente"):
        _setup(db_session, "t6h", discount=2000.0)


# ---------------- Fix round 1 ----------------

from decimal import Decimal
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from tests.conftest import auth_headers


def _approved_staff_invoice(db, name, pct=20):
    sec, mgr, _, ctrl, req, _ = _setup(db, name)
    _decide(ctrl, mgr, req, refuse=False, decision_percent=pct)
    return sec, ctrl, req


def _put_ctrl(db, sec):
    return CaisseController(repo=CaisseRepository(db), current_user=sec)


def _assert_locked_unchanged(db, ctrl, req):
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    db.refresh(tx)
    assert float(tx.amount) == 5600.0
    assert float(tx.staff_discount_amount) == 0
    assert tx.staff_discount_details["replaced_by_discount_request"] == req.id
    assert len(tx.staff_discount_details["previous"]) >= 1


@pytest.mark.parametrize("payload_fn", [
    lambda db, tx, sec: {"items": [{"item_type": "Examens", "item_ref_id": 1, "unit_price": 100.0,
                                     "quantity": 1, "line_total": 100.0}]},
    lambda db, tx, sec: {"patient_id": _patient(db, sec, staff=False)},
    lambda db, tx, sec: {"amount": 123.0},
])
def test_put_locked_after_manual_discount(db_session, payload_fn):
    sec, ctrl, req = _approved_staff_invoice(db_session, "t6p")
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    payload = payload_fn(db_session, tx, sec)
    with pytest.raises(ValueError, match="réduction manuelle validée"):
        _put_ctrl(db_session, sec).update_transaction(req.transaction_id, payload)
    _assert_locked_unchanged(db_session, ctrl, req)


def test_put_note_still_works_after_manual_discount(db_session):
    sec, ctrl, req = _approved_staff_invoice(db_session, "t6n")
    _put_ctrl(db_session, sec).update_transaction(req.transaction_id, {"note": "ok"})
    _assert_locked_unchanged(db_session, ctrl, req)


def test_create_request_with_zero_discount_rejected_when_rule_applies(db_session):
    with pytest.raises(ValueError, match="Réduction personnel incohérente"):
        _setup(db_session, "t6z", discount=0.0)


def _rounding_request(db, name, med_total, pct):
    sec = create_test_user(db, f"{name}_sec", "secretaire", password=PWD)
    mgr = create_test_user(db, f"{name}_mgr", "admin", password=PWD)
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db), caisse_repo=CaisseRepository(db),
        notification_repo=NotificationRepository(db), current_user=sec)
    data = {"payment_method": "Espèces", "transaction_type": "Consultation",
            "amount": med_total, "advance_amount": 0,
            "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": med_total,
                       "quantity": 1, "line_total": med_total}]}
    req = ctrl.create_request(data, requested_to=mgr.user_id)
    _decide(ctrl, mgr, req, refuse=False, decision_percent=pct)
    return ctrl.caisse_repo.get_by_id(req.transaction_id)


def test_approval_rounding_half_up(db_session):
    tx = _rounding_request(db_session, "t6r1", 7000.05, 10)
    assert Decimal(str(tx.amount)) == Decimal("6300.05")  # 6300.045 -> half up
    tx2 = _rounding_request(db_session, "t6r2", 7000.05, 100)
    assert Decimal(str(tx2.amount)) == Decimal("0.00")


# ---------------- Final-review fix wave ----------------

def _locked_ctrl(db, sec):
    return CaisseController(repo=CaisseRepository(db), current_user=sec,
                            discount_repo=DiscountRequestRepository(db))


def test_lock_scenario_a_staff_below_threshold_then_threshold_lowered(db_session):
    sec = create_test_user(db_session, "t6la_sec", "secretaire", password=PWD)
    mgr = create_test_user(db_session, "t6la_mgr", "admin", password=PWD)
    _only_rule(db_session, minimum=999999)  # aucune reduction personnel au depart
    pid = _patient(db_session, sec, staff=True)
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session), caisse_repo=CaisseRepository(db_session),
        notification_repo=NotificationRepository(db_session), current_user=sec)
    req = ctrl.create_request(_payload(pid, _med(db_session)), requested_to=mgr.user_id)
    _decide(ctrl, mgr, req, refuse=False, decision_percent=50)
    _only_rule(db_session, minimum=1)  # l'admin abaisse le seuil
    cc = _locked_ctrl(db_session, sec)
    for payload in ({"patient_id": pid}, {"amount": 3500.0}):
        with pytest.raises(ValueError, match="réduction manuelle validée"):
            cc.update_transaction(req.transaction_id, payload)
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    db_session.refresh(tx)
    assert float(tx.amount) == 3500.0 and float(tx.staff_discount_amount) == 0


def test_lock_scenario_b_non_staff_approved_manual_discount(db_session):
    sec, mgr, _, ctrl, req, _ = _setup(db_session, "t6lb", staff=False)
    _decide(ctrl, mgr, req, refuse=False, decision_percent=20)
    items = [{"item_type": "Examens", "item_ref_id": 1, "unit_price": 100.0, "quantity": 1, "line_total": 100.0}]
    with pytest.raises(ValueError, match="réduction manuelle validée"):
        _locked_ctrl(db_session, sec).update_transaction(req.transaction_id, {"items": items})
    tx = ctrl.caisse_repo.get_by_id(req.transaction_id)
    db_session.refresh(tx)
    assert float(tx.amount) == 5600.0 and len(tx.items) == 2


def test_echeance_only_approval_does_not_lock(db_session):
    sec, mgr, _, ctrl, req, _ = _setup(db_session, "t6lc", staff=False)
    _decide(ctrl, mgr, req, refuse=False, decision_echelonne_deadline=date(2026, 12, 31))
    tx = _locked_ctrl(db_session, sec).update_transaction(req.transaction_id, {"amount": 1234.0})
    assert float(tx.amount) == 1234.0


def test_float_sum_invoice_passes_in_both_paths(db_session):
    sec = create_test_user(db_session, "t6fs_sec", "secretaire", password=PWD)
    mgr = create_test_user(db_session, "t6fs_mgr", "admin", password=PWD)
    def data():
        return {"payment_method": "Espèces", "transaction_type": "Consultation",
                "amount": 300.3, "advance_amount": 0,
                "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 100.1, "quantity": 1, "line_total": 100.1},
                          {"item_type": "Service", "item_ref_id": 0, "unit_price": 200.2, "quantity": 1, "line_total": 200.2}]}
    CaisseController(repo=CaisseRepository(db_session), current_user=sec).create_transaction(data())
    ctrl = DiscountRequestController(
        repo=DiscountRequestRepository(db_session), caisse_repo=CaisseRepository(db_session),
        notification_repo=NotificationRepository(db_session), current_user=sec)
    req = ctrl.create_request(data(), requested_to=mgr.user_id)
    assert float(req.original_amount) == 300.3
