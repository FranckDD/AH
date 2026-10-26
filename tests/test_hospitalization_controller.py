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


class _FakeRedis:
    def __init__(self, keys):
        self.store = {k: "x" for k in keys}

    def scan_iter(self, match=None, count=None):
        import fnmatch
        return [k for k in list(self.store) if match is None or fnmatch.fnmatch(k, match)]

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


def test_admit_and_discharge_invalidate_doctor_dashboard_cache(monkeypatch):
    """Defaut releve par les guides 2026-10-26 : le compteur 'Current stays'
    du tableau de bord medecin restait fige jusqu'a 300 s apres une
    admission ou une sortie. Chaque cle de cache KPI doit etre videe."""
    import controller.doctor_dashboard_controller as dash
    fake = _FakeRedis(["doctor_dashboard:kpi:7:2026-10-01:2026-10-31", "doctor_dashboard:kpi:9:2026-10-01:2026-10-31", "autre:cle"])
    monkeypatch.setattr(dash, "redis_client", fake)

    repo = MagicMock()
    repo.admit.return_value = MagicMock(id=1)
    repo.discharge.return_value = MagicMock(id=1)
    ctrl = HospitalizationController(repo=repo, current_user=MagicMock(user_id=7))

    ctrl.admit(patient_id=1, admission_reason="x")
    assert list(fake.store) == ["autre:cle"]

    fake.store["doctor_dashboard:kpi:7:a:b"] = "x"
    ctrl.discharge(hospitalization_id=1, discharge_disposition="GUERI", discharge_note=None)
    assert list(fake.store) == ["autre:cle"]


def test_cache_invalidation_failure_never_blocks_admission(monkeypatch):
    import controller.doctor_dashboard_controller as dash

    class Boom:
        def scan_iter(self, *a, **k):
            raise RuntimeError("redis down")

    monkeypatch.setattr(dash, "redis_client", Boom())
    repo = MagicMock()
    repo.admit.return_value = MagicMock(id=1)
    ctrl = HospitalizationController(repo=repo, current_user=MagicMock(user_id=7))

    assert ctrl.admit(patient_id=1, admission_reason=None) is repo.admit.return_value
