# tests/test_hospitalization_repo.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from repositories.hospitalization_repo import HospitalizationRepository
from tests.conftest import create_test_user, create_test_patient


def test_admit_creates_open_hospitalization(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin1", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoAdmit", is_clinical=True)

    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, "Fièvre persistante")

    assert hosp.id is not None
    assert hosp.patient_id == patient_id
    assert hosp.admitted_by == medecin.user_id
    assert hosp.discharged_at is None


def test_admit_refuses_unknown_patient(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin_unknown", "medecin")
    repo = HospitalizationRepository(db_session)

    with pytest.raises(ValueError, match="introuvable"):
        repo.admit(999999999, medecin.user_id, None)


def test_admit_accepts_toxico_only_patient(db_session):
    """Soins holistiques : un patient suivi uniquement en toxico peut etre
    hospitalise (decision utilisateur 2026-09-28)."""
    medecin = create_test_user(db_session, "hosp_repo_medecin_nonclin", "medecin")
    patient_id, _ = create_test_patient(
        db_session, medecin, first_name="RepoNonClinical", is_clinical=False, is_toxicology=True
    )
    # Vrai dossier toxico (la colonne is_toxicology n'est plus la source de
    # verite - compute_domain_flags lit l'existence reelle des dossiers).
    from datetime import date
    from models.toxico import ToxicoDossier
    db_session.add(ToxicoDossier(patient_id=patient_id, admission_date=date.today(), substance="Test"))
    db_session.flush()
    repo = HospitalizationRepository(db_session)

    hosp = repo.admit(patient_id, medecin.user_id, None)
    assert hosp.discharged_at is None


def test_admit_refuses_second_open_stay_for_same_patient(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin2", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoDoubleAdmit", is_clinical=True)

    repo = HospitalizationRepository(db_session)
    repo.admit(patient_id, medecin.user_id, None)

    with pytest.raises(ValueError, match="déjà"):
        repo.admit(patient_id, medecin.user_id, None)


def test_add_status_update_on_open_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoStatus", is_clinical=True)
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)

    update = repo.add_status_update(hosp.id, "AMELIORATION", "Fièvre en baisse", medecin.user_id)

    assert update.hospitalization_id == hosp.id
    assert update.status == "AMELIORATION"


def test_add_status_update_refuses_on_discharged_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin4", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoStatusClosed", is_clinical=True)
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)
    repo.discharge(hosp.id, "GUERI", None, medecin.user_id)

    with pytest.raises(ValueError, match="clos"):
        repo.add_status_update(hosp.id, "STABLE", None, medecin.user_id)


def test_discharge_closes_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin5", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoDischarge", is_clinical=True)
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)

    discharged = repo.discharge(hosp.id, "TRANSFERE", "Vers hôpital régional", medecin.user_id)

    assert discharged.discharged_at is not None
    assert discharged.discharge_disposition == "TRANSFERE"
    assert discharged.discharged_by == medecin.user_id


def test_discharge_refuses_already_discharged_stay(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin6", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoDoubleDischarge", is_clinical=True)
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)
    repo.discharge(hosp.id, "GUERI", None, medecin.user_id)

    with pytest.raises(ValueError, match="clos"):
        repo.discharge(hosp.id, "GUERI", None, medecin.user_id)


def test_get_open_for_patient(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin7", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoGetOpen", is_clinical=True)
    repo = HospitalizationRepository(db_session)

    assert repo.get_open_for_patient(patient_id) is None

    hosp = repo.admit(patient_id, medecin.user_id, None)
    assert repo.get_open_for_patient(patient_id).id == hosp.id

    repo.discharge(hosp.id, "GUERI", None, medecin.user_id)
    assert repo.get_open_for_patient(patient_id) is None


def test_list_current_only_returns_open_stays(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin8", "medecin")
    p1, _ = create_test_patient(db_session, medecin, first_name="RepoCurrent1", is_clinical=True)
    p2, _ = create_test_patient(db_session, medecin, first_name="RepoCurrent2", is_clinical=True)
    repo = HospitalizationRepository(db_session)

    open_hosp = repo.admit(p1, medecin.user_id, None)
    closed_hosp = repo.admit(p2, medecin.user_id, None)
    repo.discharge(closed_hosp.id, "GUERI", None, medecin.user_id)

    current_ids = [h.id for h in repo.list_current()]
    assert open_hosp.id in current_ids
    assert closed_hosp.id not in current_ids


def test_get_history_for_patient_includes_open_and_closed_stays(db_session):
    medecin = create_test_user(db_session, "hosp_repo_medecin9", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="RepoHistory", is_clinical=True)
    repo = HospitalizationRepository(db_session)

    first_stay = repo.admit(patient_id, medecin.user_id, None)
    repo.discharge(first_stay.id, "GUERI", None, medecin.user_id)
    second_stay = repo.admit(patient_id, medecin.user_id, None)

    history_ids = [h.id for h in repo.get_history_for_patient(patient_id)]
    assert first_stay.id in history_ids
    assert second_stay.id in history_ids
