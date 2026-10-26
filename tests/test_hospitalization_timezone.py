"""Defaut releve par les guides (2026-10-26) : admitted_at local, discharged_at
UTC (sortie avant admission, duree '0 jour(s)'). Convention unique : toutes les
dates d'un sejour sont l'heure locale de Douala (naive), comme Caisse.paid_at."""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime

from repositories import hospitalization_repo
from repositories.hospitalization_repo import HospitalizationRepository, stay_duration_label
from tests.conftest import create_test_user, create_test_patient


def test_admit_status_discharge_use_business_time(db_session, monkeypatch):
    medecin = create_test_user(db_session, "hosp_tz_medecin", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="TzStay", is_clinical=True)
    repo = HospitalizationRepository(db_session)

    clock = {"now": datetime(2026, 10, 26, 6, 38, 0)}
    monkeypatch.setattr(hospitalization_repo, "business_now", lambda: clock["now"])

    hosp = repo.admit(patient_id, medecin.user_id, "Fievre")
    assert hosp.admitted_at == datetime(2026, 10, 26, 6, 38, 0)

    clock["now"] = datetime(2026, 10, 26, 7, 0, 0)
    upd = repo.add_status_update(hosp.id, "STABLE", None, medecin.user_id)
    assert upd.created_at == datetime(2026, 10, 26, 7, 0, 0)

    clock["now"] = datetime(2026, 10, 26, 8, 15, 0)
    hosp = repo.discharge(hosp.id, "GUERI", None, medecin.user_id)
    assert hosp.discharged_at == datetime(2026, 10, 26, 8, 15, 0)
    assert hosp.discharged_at > hosp.admitted_at


def test_real_clock_discharge_never_before_admission(db_session):
    medecin = create_test_user(db_session, "hosp_tz_medecin2", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin, first_name="TzReal", is_clinical=True)
    repo = HospitalizationRepository(db_session)
    hosp = repo.admit(patient_id, medecin.user_id, None)
    hosp = repo.discharge(hosp.id, "GUERI", None, medecin.user_id)
    delta = (hosp.discharged_at - hosp.admitted_at).total_seconds()
    assert 0 <= delta < 60, delta


def test_stay_duration_label():
    a = datetime(2026, 10, 26, 6, 38)
    assert stay_duration_label(a, datetime(2026, 10, 26, 6, 50)) == "12 min"
    assert stay_duration_label(a, datetime(2026, 10, 26, 9, 10)) == "2 h 32 min"
    assert stay_duration_label(a, datetime(2026, 10, 28, 7, 0)) == "2 jour(s) 0 h"
    assert stay_duration_label(a, datetime(2026, 10, 26, 5, 0)) == "0 min"
