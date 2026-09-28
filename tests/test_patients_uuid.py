# tests/test_patients_uuid.py
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def _uuid_of(db_session, patient_id):
    return db_session.execute(
        text("SELECT uuid::text FROM patients WHERE patient_id = :pid"), {"pid": patient_id}
    ).scalar()


def test_create_patient_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 4 : un patient cree hors ligne fournit son
    uuid - le serveur doit le persister tel quel (sinon la ligne locale
    PowerSync ne correspond jamais a la ligne confirmee)."""
    create_test_user(db_session, "test_pat_uuid_nurse", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_nurse", TEST_PASSWORD)

    client_uuid = "aaaaaaaa-1111-2222-3333-444444444444"
    resp = client.post("/patients/", json={
        "first_name": "Hors", "last_name": "Ligne", "birth_date": "1990-01-01",
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert _uuid_of(db_session, resp.json()["patient_id"]) == client_uuid


def test_create_patient_rejoue_meme_uuid_est_idempotent(db_session, api_client):
    """Rejeu d'un envoi dont la reponse a ete perdue (coupure) : 200 avec le
    patient deja cree, jamais un doublon ni un 500 (un 500 bloquerait la
    file d'envoi PowerSync indefiniment)."""
    create_test_user(db_session, "test_pat_uuid_sec", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_sec", TEST_PASSWORD)

    client_uuid = "bbbbbbbb-1111-2222-3333-444444444444"
    payload = {"first_name": "Rejeu", "last_name": "Test", "birth_date": "1991-02-02", "uuid": client_uuid}
    first = client.post("/patients/", json=payload, headers=headers)
    second = client.post("/patients/", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["patient_id"] == first.json()["patient_id"]
    count = db_session.execute(
        text("SELECT count(*) FROM patients WHERE uuid = CAST(:u AS uuid)"), {"u": client_uuid}
    ).scalar()
    assert count == 1


def test_create_patient_national_id_deja_pris_renvoie_409(db_session, api_client):
    """Vrai doublon (autre patient, autre uuid) : 409, c'est ce code qui
    declenche la quarantaine cote client - jamais 500."""
    create_test_user(db_session, "test_pat_uuid_nurse2", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_nurse2", TEST_PASSWORD)

    base = {"first_name": "Doublon", "last_name": "Nid", "birth_date": "1992-03-03", "national_id": "NID-TEST-DOUBLON-010"}
    first = client.post("/patients/", json={**base, "uuid": "cccccccc-1111-2222-3333-444444444444"}, headers=headers)
    second = client.post("/patients/", json={**base, "uuid": "dddddddd-1111-2222-3333-444444444444"}, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text


def test_create_patient_uuid_invalide_renvoie_422(db_session, api_client):
    create_test_user(db_session, "test_pat_uuid_nurse3", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_nurse3", TEST_PASSWORD)

    resp = client.post("/patients/", json={
        "first_name": "Mauvais", "last_name": "Uuid", "birth_date": "1993-04-04", "uuid": "pas-un-uuid",
    }, headers=headers)
    assert resp.status_code == 422, resp.text


def test_create_patient_rejoue_meme_uuid_apres_suppression_est_idempotent(db_session, api_client):
    """Fix round 1 (revue independante) : si le patient cree avec cet uuid a
    ete supprime entre-temps, le rejeu du meme POST ne doit jamais tomber
    sur l'INSERT (patients_uuid_key est un index unique SANS clause WHERE,
    l'uuid reste "pris" apres suppression) -> ce serait un faux 409,
    indiscernable d'un vrai doublon national_id, qui mettrait a tort le
    patient en quarantaine cote client alors qu'il a bien ete cree."""
    create_test_user(db_session, "test_pat_uuid_admin_del", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_pat_uuid_admin_del", TEST_PASSWORD)

    client_uuid = "eeeeeeee-1111-2222-3333-444444444444"
    payload = {"first_name": "Supprime", "last_name": "Rejeu", "birth_date": "1994-05-05", "uuid": client_uuid}
    first = client.post("/patients/", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    patient_id = first.json()["patient_id"]

    delete_resp = client.delete(f"/patients/{patient_id}", headers=headers)
    assert delete_resp.status_code == 204, delete_resp.text

    second = client.post("/patients/", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    assert second.json()["patient_id"] == patient_id


def test_index_unique_patients_uuid_present(db_session):
    """Migration 010 : deux patients ne peuvent pas partager un uuid."""
    user = create_test_user(db_session, "test_pat_uuid_idx", "admin", password=TEST_PASSWORD)
    pid_a, _ = create_test_patient(db_session, user, first_name="IdxA")
    pid_b, _ = create_test_patient(db_session, user, first_name="IdxB")
    uuid_a = _uuid_of(db_session, pid_a)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text("UPDATE patients SET uuid = CAST(:u AS uuid) WHERE patient_id = :pid"),
                {"u": uuid_a, "pid": pid_b},
            )
