from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_create_medical_record_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 2 : un dossier medical cree hors ligne
    (PowerSync) fournit son propre uuid - le serveur doit le persister
    tel quel, jamais en generer un nouveau, sinon la ligne locale ne
    matche jamais la ligne confirmee par le serveur."""
    medecin = create_test_user(db_session, "test_dossier_uuid_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="DossierUuid")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_dossier_uuid_medecin", TEST_PASSWORD)

    client_uuid = "11111111-2222-3333-4444-555555555555"
    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid


def test_create_medical_record_sans_uuid_en_genere_un(db_session, api_client):
    """Non-regression : la creation en ligne (aucun uuid fourni par le
    client) continue de fonctionner, Postgres genere le uuid comme
    avant ce chantier."""
    medecin = create_test_user(db_session, "test_dossier_uuid_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="DossierSansUuid")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_dossier_uuid_medecin2", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] is not None


def test_create_medical_record_persists_authenticated_author(db_session, api_client):
    """Bug reel trouve le 2026-09-28 en construisant le KPI "consultations
    realisees" : created_by/created_by_name n'etaient jamais renseignes a
    la creation (MedicalRecordController.create_record() ne les mettait
    jamais dans `data`), donc count_records_for_doctor() (filtre WHERE
    created_by = doctor_id) renvoyait toujours 0 pour tout le monde - en
    base reelle, les 41 dossiers medicaux existants avaient tous
    created_by=NULL au moment de la decouverte."""
    medecin = create_test_user(db_session, "test_dossier_auteur_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="DossierAuteur")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_dossier_auteur_medecin", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created_by"] == medecin.user_id
    assert body["created_by_name"] == medecin.full_name
