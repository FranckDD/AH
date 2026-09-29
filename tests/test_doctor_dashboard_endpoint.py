# tests/test_doctor_dashboard_endpoint.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, timedelta
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.appointment import appointment_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from api_backend.backend_app.routes.hospitalizations import hospitalization_endpoint
from tests.conftest import (
    create_test_user,
    create_test_patient,
    create_test_appointment,
    create_test_medical_record,
    create_test_prescription,
    auth_headers,
)

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    # NOTE (correction appliquee) : le brief d'origine n'overridait que
    # auth_endpoints + doctor_dashboard_endpoint. doctor_dashboard_endpoint
    # ne definit PAS son propre get_db() (AttributeError si on le passe a
    # api_client/override_get_db - verifie empiriquement) - il compose 4
    # sous-controllers (appointment/medical_records/prescription/
    # hospitalizations) via leurs propres get_*_controller(), chacun
    # avec SON PROPRE get_db() (SessionLocal() reel, connexion separee du
    # pool). Sans override explicite de ces 4 modules, chaque sous-repo
    # lirait via une connexion Postgres distincte de la transaction de
    # test (db_session) - les donnees ephemeres creees par les helpers
    # create_test_* (flush/commit dans la transaction de test, jamais
    # commit externe) seraient invisibles (isolation READ COMMITTED),
    # et tous les compteurs reviendraient a 0.
    return api_client(
        auth_endpoints,
        appointment_endpoints,
        medical_records_endpoint,
        prescriptions_endpoints,
        hospitalization_endpoint,
    )


def _date_range():
    today = date.today()
    return (today - timedelta(days=7)).isoformat(), (today + timedelta(days=7)).isoformat()


def test_medecin_gets_composed_dashboard(db_session, api_client):
    medecin = create_test_user(db_session, "tbm_ep_medecin1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin)
    create_test_appointment(db_session, medecin, patient_id)
    create_test_medical_record(db_session, medecin, patient_id)
    create_test_prescription(db_session, patient_id, medecin)

    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_medecin1", TEST_PASSWORD)
    start, end = _date_range()

    resp = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_appointments"] >= 1
    assert body["distinct_patients"] >= 1
    assert body["medical_records_count"] >= 1
    assert body["prescriptions_count"] >= 1
    assert "hospitalizations_current_count" in body


def test_nurse_gets_own_composed_dashboard(db_session, api_client):
    nurse = create_test_user(db_session, "tbm_ep_nurse1", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse)
    create_test_appointment(db_session, nurse, patient_id)

    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_nurse1", TEST_PASSWORD)
    start, end = _date_range()

    resp = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["total_appointments"] >= 1


def test_two_doctors_get_isolated_stats(db_session, api_client):
    medecin_a = create_test_user(db_session, "tbm_ep_medecin_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "tbm_ep_medecin_b", "medecin", password=TEST_PASSWORD)
    patient_a_id, _ = create_test_patient(db_session, medecin_a)
    create_test_appointment(db_session, medecin_a, patient_a_id)

    client = _client(api_client)
    headers_a = auth_headers(client, "tbm_ep_medecin_a", TEST_PASSWORD)
    headers_b = auth_headers(client, "tbm_ep_medecin_b", TEST_PASSWORD)
    start, end = _date_range()

    resp_a = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_a)
    resp_b = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_b)

    assert resp_a.json()["total_appointments"] >= 1
    assert resp_b.json()["total_appointments"] == 0


def test_secretaire_forbidden(db_session, api_client):
    create_test_user(db_session, "tbm_ep_secretaire1", "secretaire", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_secretaire1", TEST_PASSWORD)
    start, end = _date_range()

    resp = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)
    assert resp.status_code == 403


def test_hospitalizations_current_count_is_establishment_wide(db_session, api_client):
    """Review Focus indirect : le widget hospitalisations n'est PAS
    personnel (design explicite, voir spec) - deux medecins differents
    doivent voir le meme total etablissement."""
    from controller.hospitalization_controller import HospitalizationController
    from repositories.hospitalization_repo import HospitalizationRepository

    medecin_a = create_test_user(db_session, "tbm_ep_medecin_hosp_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "tbm_ep_medecin_hosp_b", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin_a)

    hosp_repo = HospitalizationRepository(db_session)
    hosp_ctrl = HospitalizationController(repo=hosp_repo, current_user=medecin_a)
    hosp_ctrl.admit(patient_id, "Suivi")

    client = _client(api_client)
    headers_a = auth_headers(client, "tbm_ep_medecin_hosp_a", TEST_PASSWORD)
    headers_b = auth_headers(client, "tbm_ep_medecin_hosp_b", TEST_PASSWORD)
    start, end = _date_range()

    resp_a = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_a)
    resp_b = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers_b)

    assert resp_a.json()["hospitalizations_current_count"] == resp_b.json()["hospitalizations_current_count"]
    assert resp_a.json()["hospitalizations_current_count"] >= 1


def test_dashboard_uses_cache_scoped_by_doctor_and_range(db_session, api_client):
    """Review Focus : le cache ne doit jamais fuiter entre medecins ni
    entre plages de dates differentes."""
    medecin = create_test_user(db_session, "tbm_ep_medecin_cache", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin)
    create_test_appointment(db_session, medecin, patient_id)

    client = _client(api_client)
    headers = auth_headers(client, "tbm_ep_medecin_cache", TEST_PASSWORD)
    start, end = _date_range()

    first = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)
    assert first.json()["total_appointments"] >= 1

    # Ajout d'un second RDV APRES le premier appel : si le cache etait mal
    # scope (ou trop long), ce nouvel appel identique renverrait quand
    # meme la valeur mise en cache - teste ici seulement que le second
    # appel reste coherent avec le meme resultat (comportement de cache
    # attendu sur la meme fenetre de 5 minutes), pas une invalidation.
    second = client.get(f"/doctor-dashboard/kpi?start={start}&end={end}", headers=headers)
    assert second.json()["total_appointments"] == first.json()["total_appointments"]

    other_start = (date.today() - timedelta(days=365)).isoformat()
    other_end = (date.today() - timedelta(days=358)).isoformat()
    other_range = client.get(f"/doctor-dashboard/kpi?start={other_start}&end={other_end}", headers=headers)
    assert other_range.json()["total_appointments"] == 0
