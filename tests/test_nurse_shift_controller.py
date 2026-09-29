# tests/test_nurse_shift_controller.py
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock
from controller.nurse_shift_controller import NurseShiftController


def _make_user(roles, is_head_nurse=False, user_id=7):
    user = MagicMock(user_id=user_id, is_head_nurse=is_head_nurse)
    user.roles = roles
    return user


def test_medecin_can_assign_shift():
    repo = MagicMock()
    shift = MagicMock(id=1)
    repo.assign.return_value = shift
    user = _make_user(["medecin"])

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user, audit_repo=MagicMock())
    result = ctrl.assign_shift("2026-10-03", "MATIN", 5)

    assert result is shift
    repo.assign.assert_called_once_with("2026-10-03", "MATIN", 5, 7)


def test_head_nurse_can_assign_shift():
    repo = MagicMock()
    repo.assign.return_value = MagicMock(id=1)
    user = _make_user(["nurse"], is_head_nurse=True)

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user)
    ctrl.assign_shift("2026-10-03", "MATIN", 5)

    repo.assign.assert_called_once()


def test_plain_nurse_cannot_assign_shift():
    repo = MagicMock()
    user = _make_user(["nurse"], is_head_nurse=False)

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user)

    with pytest.raises(PermissionError):
        ctrl.assign_shift("2026-10-03", "MATIN", 5)
    repo.assign.assert_not_called()


def test_plain_nurse_cannot_remove_shift():
    repo = MagicMock()
    user = _make_user(["nurse"], is_head_nurse=False)

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user)

    with pytest.raises(PermissionError):
        ctrl.remove_shift(42)
    repo.remove.assert_not_called()


def test_assign_shift_logs_audit_entry():
    repo = MagicMock()
    repo.assign.return_value = MagicMock(id=42)
    user = _make_user(["medecin"])
    audit_repo = MagicMock()

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user, audit_repo=audit_repo)
    ctrl.assign_shift("2026-10-03", "MATIN", 5)

    audit_repo.log_user_action.assert_called_once()
    kwargs = audit_repo.log_user_action.call_args.kwargs
    assert kwargs["resource_type"] == "NurseShift"
    assert kwargs["action_performed"] == "ASSIGN"


def test_controller_logs_when_audit_fails(caplog):
    repo = MagicMock()
    repo.assign.return_value = MagicMock(id=1)
    user = _make_user(["medecin"])
    audit_repo = MagicMock()
    audit_repo.log_user_action.side_effect = Exception("boom")

    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=user, audit_repo=audit_repo)

    with caplog.at_level(logging.ERROR):
        result = ctrl.assign_shift("2026-10-03", "MATIN", 5)

    assert result is not None
    assert any("audit" in r.message.lower() for r in caplog.records)


def test_list_shifts_delegates_to_repo():
    repo = MagicMock()
    repo.list_for_range.return_value = ["a", "b"]
    ctrl = NurseShiftController(repo=repo, user_repo=MagicMock(), current_user=_make_user(["nurse"]))

    assert ctrl.list_shifts("2026-10-01", "2026-10-31") == ["a", "b"]
    repo.list_for_range.assert_called_once_with("2026-10-01", "2026-10-31")


def test_list_active_nurses_delegates_to_user_repo():
    user_repo = MagicMock()
    user_repo.get_users_by_role_names.return_value = ["nurse1", "nurse2"]
    ctrl = NurseShiftController(repo=MagicMock(), user_repo=user_repo, current_user=_make_user(["medecin"]))

    assert ctrl.list_active_nurses() == ["nurse1", "nurse2"]
    user_repo.get_users_by_role_names.assert_called_once_with(["nurse"])
