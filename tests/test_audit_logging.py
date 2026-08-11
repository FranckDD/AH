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
