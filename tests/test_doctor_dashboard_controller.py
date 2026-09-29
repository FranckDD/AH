# tests/test_doctor_dashboard_controller.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
from unittest.mock import MagicMock
import pytest
from controller.doctor_dashboard_controller import DoctorDashboardController


def _make_ctrls():
    appointment_ctrl = MagicMock()
    medical_ctrl = MagicMock()
    prescription_ctrl = MagicMock()
    hospitalization_ctrl = MagicMock()
    return appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl


def _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, user_id=7):
    user = MagicMock(user_id=user_id)
    return DoctorDashboardController(
        appointment_ctrl=appointment_ctrl,
        medical_ctrl=medical_ctrl,
        prescription_ctrl=prescription_ctrl,
        hospitalization_ctrl=hospitalization_ctrl,
        current_user=user,
    )


def test_get_dashboard_composes_all_sources(monkeypatch):
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=None))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock())

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 12
    appointment_ctrl.count_by_status.return_value = {"pending": 5, "completed": 7}
    appointment_ctrl.distinct_patients_count.return_value = 9
    medical_ctrl.count_records_for_doctor.return_value = 20
    medical_ctrl.consultation_type_distribution.return_value = {"suivi": 15, "urgence": 5}
    prescription_ctrl.count_prescriptions.return_value = 3
    hospitalization_ctrl.count_current.return_value = 2

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result == {
        "total_appointments": 12,
        "count_by_status": {"pending": 5, "completed": 7},
        "distinct_patients": 9,
        "medical_records_count": 20,
        "consultation_distribution": {"suivi": 15, "urgence": 5},
        "prescriptions_count": 3,
        "hospitalizations_current_count": 2,
    }
    appointment_ctrl.total_appointments.assert_called_once_with(7, date(2026, 9, 1), date(2026, 9, 30))
    medical_ctrl.count_records_for_doctor.assert_called_once_with(7, date(2026, 9, 1), date(2026, 9, 30))
    prescription_ctrl.count_prescriptions.assert_called_once_with(doctor_id=7, start=date(2026, 9, 1), end=date(2026, 9, 30))
    hospitalization_ctrl.count_current.assert_called_once_with()


def test_get_dashboard_degrades_single_failing_source(monkeypatch):
    """Review Focus : une source qui leve une exception ne doit jamais
    faire echouer les autres - valeur neutre pour cette carte, le reste
    intact."""
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=None))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock())

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 12
    appointment_ctrl.count_by_status.return_value = {"pending": 5}
    appointment_ctrl.distinct_patients_count.return_value = 9
    medical_ctrl.count_records_for_doctor.side_effect = Exception("DB down")
    medical_ctrl.consultation_type_distribution.return_value = {"suivi": 15}
    prescription_ctrl.count_prescriptions.return_value = 3
    hospitalization_ctrl.count_current.return_value = 2

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["total_appointments"] == 12
    assert result["medical_records_count"] == 0
    assert result["consultation_distribution"] == {"suivi": 15}
    assert result["prescriptions_count"] == 3
    assert result["hospitalizations_current_count"] == 2


def test_get_dashboard_degrades_dict_field_to_empty_dict(monkeypatch):
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=None))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock())

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 1
    appointment_ctrl.count_by_status.side_effect = Exception("boom")
    appointment_ctrl.distinct_patients_count.return_value = 1
    medical_ctrl.count_records_for_doctor.return_value = 1
    medical_ctrl.consultation_type_distribution.return_value = {}
    prescription_ctrl.count_prescriptions.return_value = 0
    hospitalization_ctrl.count_current.return_value = 0

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["count_by_status"] == {}


def test_get_dashboard_resolves_doctor_id_from_current_user():
    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl, user_id=42)

    ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    appointment_ctrl.total_appointments.assert_called_once_with(42, date(2026, 9, 1), date(2026, 9, 30))


def test_get_dashboard_uses_cache_on_second_call(monkeypatch):
    """Review Focus : le cache doit etre scope par medecin ET par plage
    de dates - verifie ici que le cache repond bien pour une cle exacte
    (medecin+dates) sans jamais rappeler les sources sous-jacentes."""
    import json
    cached_payload = json.dumps({
        "total_appointments": 99, "count_by_status": {}, "distinct_patients": 0,
        "medical_records_count": 0, "consultation_distribution": {},
        "prescriptions_count": 0, "hospitalizations_current_count": 0,
    })
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(return_value=cached_payload))

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)

    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["total_appointments"] == 99
    appointment_ctrl.total_appointments.assert_not_called()


def test_get_dashboard_survives_redis_being_down(monkeypatch):
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.get", MagicMock(side_effect=Exception("redis down")))
    monkeypatch.setattr("controller.doctor_dashboard_controller.redis_client.setex", MagicMock(side_effect=Exception("redis down")))

    appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl = _make_ctrls()
    appointment_ctrl.total_appointments.return_value = 5
    appointment_ctrl.count_by_status.return_value = {}
    appointment_ctrl.distinct_patients_count.return_value = 0
    medical_ctrl.count_records_for_doctor.return_value = 0
    medical_ctrl.consultation_type_distribution.return_value = {}
    prescription_ctrl.count_prescriptions.return_value = 0
    hospitalization_ctrl.count_current.return_value = 0

    ctrl = _make_controller(appointment_ctrl, medical_ctrl, prescription_ctrl, hospitalization_ctrl)
    result = ctrl.get_dashboard(date(2026, 9, 1), date(2026, 9, 30))

    assert result["total_appointments"] == 5
