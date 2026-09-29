# tests/test_medical_controller_triage.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from controller.medical_controller import MedicalRecordController
from repositories.medical_repo import MedicalRecordRepository
from repositories.notification_repo import NotificationRepository
from repositories.patient_repo import PatientRepository
from controller.patient_controller import PatientController
from models.notification import Notification
from tests.conftest import create_test_user, create_test_patient


def _make_controller(db_session, current_user, with_notifications=True):
    repo = MedicalRecordRepository(db_session)
    patient_ctrl = PatientController(repo=PatientRepository(db_session), current_user=current_user)
    notification_repo = NotificationRepository(db_session) if with_notifications else None
    return MedicalRecordController(repo=repo, patient_controller=patient_ctrl, current_user=current_user, notification_repo=notification_repo)


def _record_data(**overrides):
    # MedicalRecordRepository.create() appelle CALL public.create_medical_record(...)
    # avec une liste fixe de parametres nommes ; seuls created_by/created_by_name/
    # last_updated_by/last_updated_by_name/appointment_id/uuid ont un setdefault(None)
    # cote repo. Sans ces cles explicitement presentes dans `data`, session.execute()
    # leve InvalidRequestError ("A value is required for bind parameter
    # 'marital_status'") - meme contrainte deja documentee dans
    # tests/conftest.py::create_test_medical_record.
    data = {
        "marital_status": None, "bp": None, "temperature": None, "weight": None,
        "height": None, "medical_history": None, "allergies": None, "symptoms": None,
        "diagnosis": None, "treatment": None, "severity": None, "notes": None,
    }
    data.update(overrides)
    return data


def test_create_record_with_assigned_doctor_sends_notification(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse1", "nurse")
    medecin = create_test_user(db_session, "triage_ctrl_medecin1", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)

    ctrl.create_record(_record_data(
        patient_id=patient_id, motif_code="consultation",
        needs_doctor_review=True, assigned_doctor_id=medecin.user_id,
    ))

    notifs = db_session.query(Notification).filter(Notification.recipient_user_id == medecin.user_id, Notification.type == "patient_pending_review").all()
    assert len(notifs) == 1
    assert notifs[0].payload["patient_id"] == patient_id


def test_create_record_shared_pool_sends_no_notification(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse2", "nurse")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)

    ctrl.create_record(_record_data(
        patient_id=patient_id, motif_code="consultation",
        needs_doctor_review=True, assigned_doctor_id=None,
    ))

    notifs = db_session.query(Notification).filter(Notification.type == "patient_pending_review").all()
    assert notifs == []


def test_create_record_without_flag_sends_no_notification(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse3", "nurse")
    medecin = create_test_user(db_session, "triage_ctrl_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)

    ctrl.create_record(_record_data(patient_id=patient_id, motif_code="consultation"))

    notifs = db_session.query(Notification).filter(Notification.recipient_user_id == medecin.user_id).all()
    assert notifs == []


def test_claim_review_forbidden_for_nurse(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse4", "nurse")
    patient_id, _ = create_test_patient(db_session, nurse)
    ctrl = _make_controller(db_session, nurse)
    ctrl.create_record(_record_data(patient_id=patient_id, motif_code="consultation", needs_doctor_review=True, assigned_doctor_id=None))
    record = ctrl.repo.get_last_for_patient(patient_id)

    with pytest.raises(PermissionError):
        ctrl.claim_review(record.record_id)


def test_claim_review_allowed_for_medecin(db_session):
    nurse = create_test_user(db_session, "triage_ctrl_nurse5", "nurse")
    medecin = create_test_user(db_session, "triage_ctrl_medecin5", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    nurse_ctrl = _make_controller(db_session, nurse)
    nurse_ctrl.create_record(_record_data(patient_id=patient_id, motif_code="consultation", needs_doctor_review=True, assigned_doctor_id=None))
    record = nurse_ctrl.repo.get_last_for_patient(patient_id)

    medecin_ctrl = _make_controller(db_session, medecin)
    claimed = medecin_ctrl.claim_review(record.record_id)

    assert claimed.reviewed_by == medecin.user_id
