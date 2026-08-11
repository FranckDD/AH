# tests/test_audit_logging.py
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock


def test_auth_controller_logs_when_audit_fails_on_login_error(caplog):
    from controller.auth_controller import AuthController

    ctrl = AuthController.__new__(AuthController)  # bypass __init__ (evite la cascade de sous-repos)
    ctrl.session = MagicMock()
    ctrl.user_repo = MagicMock()
    ctrl.user_repo.get_user_by_username.side_effect = RuntimeError("DB indisponible")
    ctrl.audit_repo = MagicMock()
    ctrl.audit_repo.log_access.side_effect = Exception("audit aussi en echec")

    with caplog.at_level(logging.ERROR):
        result = ctrl.authenticate("admin_test", "peu importe")

    assert result is None  # ne doit jamais lever, comportement inchange
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_caisse_controller_logs_when_audit_fails_on_cancel(caplog):
    from controller.caisse_controller import CaisseController

    repo = MagicMock()
    repo.cancel_transaction.return_value = MagicMock()
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = CaisseController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        tx = ctrl.cancel_transaction(transaction_id=1)

    assert tx is not None  # ne doit jamais lever
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_medical_controller_logs_when_audit_fails_on_delete(caplog):
    from controller.medical_controller import MedicalRecordController

    repo = MagicMock()
    repo.delete.return_value = True
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = MedicalRecordController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.delete_record(record_id=1)

    assert result is True
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_patient_controller_logs_when_audit_fails_on_soft_delete(caplog):
    from controller.patient_controller import PatientController

    repo = MagicMock()
    repo.session = MagicMock()
    repo.delete_patient.return_value = True
    user = MagicMock()
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = PatientController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.delete_patient(patient_id=1)

    assert result is True
    assert any("audit" in r.message.lower() for r in caplog.records)
