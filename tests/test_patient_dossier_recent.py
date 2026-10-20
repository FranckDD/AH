# tests/test_patient_dossier_recent.py
"""GET /patients/{id}/dossier/recent - vue legere (3 derniers dossiers
medicaux + 3 dernieres prescriptions) du modal dossier toxico."""
from datetime import datetime, timedelta

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from models.audit import AuditUserAction
from models.medical_record import MedicalRecord
from tests.conftest import (
    auth_headers, create_test_patient, create_test_prescription, create_test_user,
)

PASSWORD = "TestPass123!"


def _patient_avec_activite(db_session, createur, prefix):
    patient_id, _ = create_test_patient(db_session, createur, first_name=prefix)
    base = datetime(2026, 1, 1)
    for i in range(5):
        db_session.add(MedicalRecord(
            patient_id=patient_id, motif_code="free", diagnosis=f"Diag {i}",
            consultation_date=base + timedelta(days=i),
        ))
    db_session.flush()
    for i in range(5):
        create_test_prescription(db_session, patient_id, createur, medication=f"Med {i}")
    return patient_id


def test_recent_renvoie_les_3_plus_recents_et_journalise(db_session, api_client):
    psy = create_test_user(db_session, "recent_psy", "Psychologist", password=PASSWORD)
    patient_id = _patient_avec_activite(db_session, psy, "RecentA")

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "recent_psy", PASSWORD)
    resp = client.get(f"/patients/{patient_id}/dossier/recent", headers=headers)

    assert resp.status_code == 200, resp.text
    corps = resp.json()
    diagnostics = [r["diagnosis"] for r in corps["historique_medical"]]
    assert diagnostics == ["Diag 4", "Diag 3", "Diag 2"]
    medications = [p["medication"] for p in corps["prescriptions"]]
    assert medications == ["Med 4", "Med 3", "Med 2"]
    assert corps["domaines_indisponibles"] == []

    log = (
        db_session.query(AuditUserAction)
        .filter_by(resource_type="Patient", action_performed="VIEW_DOSSIER_RECENT", resource_id=patient_id)
        .one_or_none()
    )
    assert log is not None


def test_recent_refuse_accompagnateur_spirituel_et_assistant(db_session, api_client):
    createur = create_test_user(db_session, "recent_creator", "admin", password=PASSWORD)
    patient_id = _patient_avec_activite(db_session, createur, "RecentB")
    create_test_user(db_session, "recent_spirit", "SpiritualCounsellor", password=PASSWORD)
    create_test_user(db_session, "recent_assist", "Assistant", password=PASSWORD)

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    for login in ("recent_spirit", "recent_assist"):
        headers = auth_headers(client, login, PASSWORD)
        resp = client.get(f"/patients/{patient_id}/dossier/recent", headers=headers)
        assert resp.status_code == 403, f"{login}: {resp.status_code}"


def test_recent_autorise_manager_toxico_et_admin(db_session, api_client):
    createur = create_test_user(db_session, "recent_creator2", "admin", password=PASSWORD)
    patient_id = _patient_avec_activite(db_session, createur, "RecentC")
    create_test_user(db_session, "recent_tmgr", "ToxicoManager", password=PASSWORD)

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    for login in ("recent_creator2", "recent_tmgr"):
        headers = auth_headers(client, login, PASSWORD)
        resp = client.get(f"/patients/{patient_id}/dossier/recent", headers=headers)
        assert resp.status_code == 200, f"{login}: {resp.text}"


def test_recent_patient_inconnu_renvoie_404(db_session, api_client):
    create_test_user(db_session, "recent_psy2", "Psychologist", password=PASSWORD)
    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "recent_psy2", PASSWORD)
    resp = client.get("/patients/99999999/dossier/recent", headers=headers)
    assert resp.status_code == 404
