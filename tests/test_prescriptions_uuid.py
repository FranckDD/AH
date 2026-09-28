# tests/test_prescriptions_uuid.py
from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_create_prescription_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 2 : une prescription creee hors ligne
    (PowerSync) fournit son propre uuid - le serveur doit le persister
    tel quel, jamais en generer un nouveau."""
    medecin = create_test_user(db_session, "test_presc_uuid_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="PrescUuid")
    db_session.flush()

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_uuid_medecin", TEST_PASSWORD)

    client_uuid = "66666666-7777-8888-9999-000000000000"
    resp = client.post("/prescriptions/", json={
        "patient_id": patient_id,
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date.today()),
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid


def test_create_prescription_sans_uuid_en_genere_un(db_session, api_client):
    """Non-regression : la creation en ligne continue de fonctionner,
    Postgres genere le uuid comme avant ce chantier."""
    medecin = create_test_user(db_session, "test_presc_uuid_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="PrescSansUuid")
    db_session.flush()

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_uuid_medecin2", TEST_PASSWORD)

    resp = client.post("/prescriptions/", json={
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "1g",
        "frequency": "2x/jour",
        "duration": "7 jours",
        "start_date": str(date.today()),
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] is not None
