# tests/test_hospitalizations_endpoints.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.hospitalizations import hospitalization_endpoint
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "TestPass123!"


def _client(api_client):
    return api_client(auth_endpoints, hospitalization_endpoint)


def test_admit_success(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpAdmit", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin1", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={
        "patient_id": patient_id,
        "admission_reason": "Fièvre persistante",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["patient_id"] == patient_id
    assert body["discharged_at"] is None


def test_admit_refuses_double_open_stay(db_session, api_client):
    """Review Focus : admettre un patient deja hospitalise doit etre
    refuse avec un message clair, jamais une erreur SQL brute."""
    medecin = create_test_user(db_session, "hosp_ep_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpDoubleAdmit", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin2", TEST_PASSWORD)

    client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)
    resp = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)

    assert resp.status_code == 409
    assert "déjà" in resp.json()["detail"]


def test_admit_unknown_patient_returns_404(db_session, api_client):
    create_test_user(db_session, "hosp_ep_medecin_unknown", "medecin", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin_unknown", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={"patient_id": 999999999}, headers=headers)

    assert resp.status_code == 404
    assert "introuvable" in resp.json()["detail"]


def test_admit_toxico_only_patient_returns_201(db_session, api_client):
    """Soins holistiques : aucun refus par parcours (decision utilisateur 2026-09-28)."""
    medecin = create_test_user(db_session, "hosp_ep_medecin_nonclin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(
        db_session, medecin, first_name="EpNonClinical", is_clinical=False, is_toxicology=True
    )
    # Vrai dossier toxico (la colonne is_toxicology n'est plus la source de
    # verite - compute_domain_flags lit l'existence reelle des dossiers).
    from datetime import date
    from models.toxico import ToxicoDossier
    db_session.add(ToxicoDossier(patient_id=patient_id, admission_date=date.today(), substance="Test"))
    db_session.flush()
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin_nonclin", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)

    assert resp.status_code == 201, resp.text


def test_status_and_discharge_on_unknown_hospitalization_return_404(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin_unknownhosp", "medecin", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin_unknownhosp", TEST_PASSWORD)

    resp_status = client.post(
        "/hospitalizations/999999999/status", json={"status": "STABLE"}, headers=headers
    )
    assert resp_status.status_code == 404

    resp_discharge = client.post(
        "/hospitalizations/999999999/discharge", json={"discharge_disposition": "GUERI"}, headers=headers
    )
    assert resp_discharge.status_code == 404


def test_status_update_refused_on_discharged_stay(db_session, api_client):
    """Review Focus : ajouter une evolution clinique sur un sejour
    deja clos doit etre refuse (400)."""
    medecin = create_test_user(db_session, "hosp_ep_medecin3", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpStatusClosed", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin3", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    resp = client.post(f"/hospitalizations/{hosp_id}/status", json={"status": "STABLE"}, headers=headers)
    assert resp.status_code == 400


def test_discharge_requires_valid_disposition(db_session, api_client):
    """Review Focus : sortir sans discharge_disposition valide doit
    etre refuse (422), jamais persiste avec une valeur libre."""
    medecin = create_test_user(db_session, "hosp_ep_medecin4", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpBadDisposition", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin4", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]

    resp = client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "PAS_UNE_VRAIE_VALEUR"}, headers=headers)
    assert resp.status_code == 422

    resp_missing = client.post(f"/hospitalizations/{hosp_id}/discharge", json={}, headers=headers)
    assert resp_missing.status_code == 422


def test_discharge_refused_on_already_discharged_stay(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin5", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpDoubleDischarge", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin5", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    resp = client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)
    assert resp.status_code == 400


def test_list_current_only_shows_open_stays(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin6", "medecin", password=TEST_PASSWORD)
    p_open, _ = create_test_patient(db_session, medecin, first_name="EpCurrentOpen", is_clinical=True)
    p_closed, _ = create_test_patient(db_session, medecin, first_name="EpCurrentClosed", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin6", TEST_PASSWORD)

    open_id = client.post("/hospitalizations/", json={"patient_id": p_open}, headers=headers).json()["id"]
    closed_id = client.post("/hospitalizations/", json={"patient_id": p_closed}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{closed_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    resp = client.get("/hospitalizations/current", headers=headers)
    assert resp.status_code == 200
    ids = [h["id"] for h in resp.json()]
    assert open_id in ids
    assert closed_id not in ids


def test_patient_history_includes_all_stays(db_session, api_client):
    medecin = create_test_user(db_session, "hosp_ep_medecin7", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpHistory", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin7", TEST_PASSWORD)

    first_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{first_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)
    second_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]

    resp = client.get(f"/hospitalizations/patient/{patient_id}", headers=headers)
    assert resp.status_code == 200
    ids = [h["id"] for h in resp.json()]
    assert first_id in ids
    assert second_id in ids


def test_nurse_has_same_rights_as_medecin(db_session, api_client):
    nurse = create_test_user(db_session, "hosp_ep_nurse1", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse, first_name="EpNurse", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_nurse1", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)
    assert resp.status_code == 201


def test_secretaire_forbidden_on_write_and_read(db_session, api_client):
    """Review Focus : un role non clinique doit etre refuse aussi bien
    en ecriture qu'en lecture (/current, /patient/{id}) - le perimetre
    clinique est etanche."""
    create_test_user(db_session, "hosp_ep_secretaire1", "secretaire", password=TEST_PASSWORD)
    medecin = create_test_user(db_session, "hosp_ep_medecin8", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpSecretaire", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_secretaire1", TEST_PASSWORD)

    assert client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).status_code == 403
    assert client.get("/hospitalizations/current", headers=headers).status_code == 403
    assert client.get(f"/hospitalizations/patient/{patient_id}", headers=headers).status_code == 403


def test_admin_forbidden_except_kpi_endpoint(db_session, api_client):
    """Review Focus : le reste du routeur reste medecin/nurse seul pour
    admin - la seule exception est l'endpoint KPI."""
    create_test_user(db_session, "hosp_ep_admin1", "admin", password=TEST_PASSWORD)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_admin1", TEST_PASSWORD)

    assert client.get("/hospitalizations/current", headers=headers).status_code == 403


def test_kpi_endpoint_accessible_to_admin_and_medecin(db_session, api_client):
    """Review Focus : l'endpoint KPI doit rester accessible a
    admin/promoteur EN PLUS de medecin/nurse."""
    medecin = create_test_user(db_session, "hosp_ep_medecin9", "medecin", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "hosp_ep_admin2", "admin", password=TEST_PASSWORD)
    client = _client(api_client)

    medecin_headers = auth_headers(client, "hosp_ep_medecin9", TEST_PASSWORD)
    admin_headers = auth_headers(client, "hosp_ep_admin2", TEST_PASSWORD)

    resp_medecin = client.get("/hospitalizations/kpi/count_current", headers=medecin_headers)
    resp_admin = client.get("/hospitalizations/kpi/count_current", headers=admin_headers)

    assert resp_medecin.status_code == 200
    assert resp_admin.status_code == 200
    assert "count" in resp_admin.json()


def test_admit_and_discharge_write_audit_entries(db_session, api_client):
    from models.audit import AuditUserAction

    medecin = create_test_user(db_session, "hosp_ep_medecin10", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpAudit", is_clinical=True)
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin10", TEST_PASSWORD)

    hosp_id = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers).json()["id"]
    client.post(f"/hospitalizations/{hosp_id}/discharge", json={"discharge_disposition": "GUERI"}, headers=headers)

    entries = (
        db_session.query(AuditUserAction)
        .filter(AuditUserAction.resource_type == "Hospitalization", AuditUserAction.resource_id == hosp_id)
        .all()
    )
    actions = {e.action_performed for e in entries}
    assert "ADMIT" in actions
    assert "DISCHARGE" in actions


def test_admit_patient_with_stale_is_clinical_column_but_real_medical_record(db_session, api_client):
    """Retour terrain 2026-09-28 : admission refusee (400) pour un patient
    clinique reel dont la colonne patients.is_clinical (depreciee, chantier 6)
    valait False. Le perimetre doit se lire sur l'existence reelle des
    dossiers (compute_domain_flags), pas sur la colonne stockee."""
    medecin = create_test_user(db_session, "hosp_ep_medecin_stale", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="EpStale", is_clinical=False)
    from models.medical_record import MedicalRecord
    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="consultation"))
    db_session.flush()
    client = _client(api_client)
    headers = auth_headers(client, "hosp_ep_medecin_stale", TEST_PASSWORD)

    resp = client.post("/hospitalizations/", json={"patient_id": patient_id}, headers=headers)

    assert resp.status_code == 201, resp.text
