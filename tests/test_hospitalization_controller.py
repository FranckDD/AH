import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
from controller.hospitalization_controller import HospitalizationController


def test_admit_logs_audit_entry():
    repo = MagicMock()
    hosp = MagicMock(id=42)
    repo.admit.return_value = hosp
    user = MagicMock(user_id=7)
    audit_repo = MagicMock()

    ctrl = HospitalizationController(repo=repo, current_user=user, audit_repo=audit_repo)
    result = ctrl.admit(patient_id=1, admission_reason="Fièvre")

    assert result is hosp
    repo.admit.assert_called_once_with(1, 7, "Fièvre")
    audit_repo.log_user_action.assert_called_once()
    call_kwargs = audit_repo.log_user_action.call_args.kwargs
    assert call_kwargs["resource_type"] == "Hospitalization"
    assert call_kwargs["action_performed"] == "ADMIT"
    assert call_kwargs["resource_id"] == 42


def test_discharge_logs_audit_entry():
    repo = MagicMock()
    hosp = MagicMock(id=42)
    repo.discharge.return_value = hosp
    user = MagicMock(user_id=7)
    audit_repo = MagicMock()

    ctrl = HospitalizationController(repo=repo, current_user=user, audit_repo=audit_repo)
    ctrl.discharge(hospitalization_id=42, discharge_disposition="GUERI", discharge_note=None)

    repo.discharge.assert_called_once_with(42, "GUERI", None, 7)
    audit_repo.log_user_action.assert_called_once()
    assert audit_repo.log_user_action.call_args.kwargs["action_performed"] == "DISCHARGE"


def test_controller_logs_when_audit_fails(caplog):
    """Meme motif que le reste du projet (test_audit_logging.py) : un
    echec d'ecriture d'audit ne doit jamais faire echouer l'action
    metier elle-meme."""
    repo = MagicMock()
    repo.admit.return_value = MagicMock(id=1)
    user = MagicMock(user_id=7)
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = HospitalizationController(repo=repo, current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.admit(patient_id=1, admission_reason=None)

    assert result is not None
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_add_status_update_delegates_to_repo():
    repo = MagicMock()
    update = MagicMock()
    repo.add_status_update.return_value = update
    user = MagicMock(user_id=9)

    ctrl = HospitalizationController(repo=repo, current_user=user)
    result = ctrl.add_status_update(hospitalization_id=42, status="AMELIORATION", note="ok")

    assert result is update
    repo.add_status_update.assert_called_once_with(42, "AMELIORATION", "ok", 9)


def test_list_current_delegates_to_repo():
    repo = MagicMock()
    repo.list_current.return_value = ["a", "b"]
    ctrl = HospitalizationController(repo=repo, current_user=MagicMock())

    assert ctrl.list_current() == ["a", "b"]


def test_count_current_delegates_to_repo():
    repo = MagicMock()
    repo.count_current.return_value = 3
    ctrl = HospitalizationController(repo=repo, current_user=MagicMock())

    assert ctrl.count_current() == 3
