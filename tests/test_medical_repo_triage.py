import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from repositories.medical_repo import MedicalRecordRepository
from tests.conftest import create_test_user, create_test_patient


def _create_pending_record(session, repo, patient_id, creator, assigned_doctor_id=None):
    data = {
        "patient_id": patient_id,
        "motif_code": "consultation",
        "diagnosis": None, "treatment": None, "notes": None,
        "marital_status": None, "bp": None, "temperature": None,
        "weight": None, "height": None, "medical_history": None,
        "allergies": None, "symptoms": None, "severity": None,
        "created_by": creator.user_id, "created_by_name": creator.username,
    }
    repo.create(data)
    session.flush()
    record = repo.get_last_for_patient(patient_id)
    record.needs_doctor_review = True
    record.assigned_doctor_id = assigned_doctor_id
    session.commit()
    return record


def test_list_pending_for_doctor_returns_own_assignment(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse1", "nurse")
    medecin_a = create_test_user(db_session, "triage_repo_medecin_a", "medecin")
    medecin_b = create_test_user(db_session, "triage_repo_medecin_b", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=medecin_a.user_id)

    pending_a = repo.list_pending_for_doctor(medecin_a.user_id)
    pending_b = repo.list_pending_for_doctor(medecin_b.user_id)

    assert record.record_id in [r.record_id for r in pending_a]
    assert record.record_id not in [r.record_id for r in pending_b]


def test_list_pending_for_doctor_includes_shared_pool(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse2", "nurse")
    medecin_a = create_test_user(db_session, "triage_repo_medecin_a2", "medecin")
    medecin_b = create_test_user(db_session, "triage_repo_medecin_b2", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=None)

    pending_a = repo.list_pending_for_doctor(medecin_a.user_id)
    pending_b = repo.list_pending_for_doctor(medecin_b.user_id)

    assert record.record_id in [r.record_id for r in pending_a]
    assert record.record_id in [r.record_id for r in pending_b]


def test_list_pending_excludes_records_not_flagged(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse3", "nurse")
    medecin = create_test_user(db_session, "triage_repo_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    repo.create({
        "patient_id": patient_id, "motif_code": "consultation",
        "diagnosis": None, "treatment": None, "notes": None,
        "marital_status": None, "bp": None, "temperature": None,
        "weight": None, "height": None, "medical_history": None,
        "allergies": None, "symptoms": None, "severity": None,
        "created_by": nurse.user_id, "created_by_name": nurse.username,
    })
    db_session.flush()

    pending = repo.list_pending_for_doctor(medecin.user_id)
    assert pending == []


def test_claim_marks_reviewed_and_assigns_if_pool(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse4", "nurse")
    medecin = create_test_user(db_session, "triage_repo_medecin4", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=None)

    claimed = repo.claim(record.record_id, medecin.user_id)

    assert claimed.reviewed_by == medecin.user_id
    assert claimed.reviewed_at is not None
    assert claimed.assigned_doctor_id == medecin.user_id
    assert repo.list_pending_for_doctor(medecin.user_id) == []


def test_claim_already_reviewed_raises(db_session):
    nurse = create_test_user(db_session, "triage_repo_nurse5", "nurse")
    medecin_a = create_test_user(db_session, "triage_repo_medecin_a5", "medecin")
    medecin_b = create_test_user(db_session, "triage_repo_medecin_b5", "medecin")
    patient_id, _ = create_test_patient(db_session, nurse)
    repo = MedicalRecordRepository(db_session)
    record = _create_pending_record(db_session, repo, patient_id, nurse, assigned_doctor_id=None)
    repo.claim(record.record_id, medecin_a.user_id)

    with pytest.raises(ValueError, match="déjà"):
        repo.claim(record.record_id, medecin_b.user_id)


def test_claim_unknown_record_raises(db_session):
    medecin = create_test_user(db_session, "triage_repo_medecin6", "medecin")
    repo = MedicalRecordRepository(db_session)
    with pytest.raises(ValueError, match="introuvable"):
        repo.claim(999999999, medecin.user_id)
