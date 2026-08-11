# tests/test_patients.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import create_test_user, create_test_patient, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_patient_success(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_create", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_create", TEST_PASSWORD)

    payload = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "birth_date": "1985-03-12",
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "Jean"
    assert body["last_name"] == "Dupont"
    assert body["birth_date"] == "1985-03-12"
    assert body["code_patient"]


def test_create_patient_role_flag_injection_does_not_trigger(db_session, api_client):
    """
    Documente un bug present sur HEAD (controller/patient_controller.py) :
    getattr(self.user, 'role_name', '') est toujours vide (cet attribut
    n'existe pas sur User), donc l'injection automatique de is_spiritual=True
    pour une secretaire ne se declenche jamais. is_spiritual=False est
    explicite ici par clarte (identique au defaut du schema) - si le bug
    etait corrige, une secretaire creant un patient devrait voir ce champ
    force a True independamment de la valeur demandee, ce que ce test
    detecterait (voir SUIVI-AVANCEMENT.md, registre B6).
    """
    create_test_user(db_session, "test_patients_secretaire_create", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_secretaire_create", TEST_PASSWORD)

    payload = {
        "first_name": "Marie",
        "last_name": "Curie",
        "birth_date": "1990-06-01",
        "is_spiritual": False,
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["is_spiritual"] is False


def test_get_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_get", "admin", password=TEST_PASSWORD)
    patient_id, code = create_test_patient(db_session, user, last_name="Lecture")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_get", TEST_PASSWORD)

    resp = client.get(f"/patients/{patient_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == patient_id
    assert body["code_patient"] == code
    assert body["last_name"] == "Lecture"


def test_get_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_get404", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_get404", TEST_PASSWORD)

    resp = client.get("/patients/999999999", headers=headers)

    assert resp.status_code == 404


def test_update_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_update", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, first_name="Avant")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_update", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"first_name": "Apres"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Apres"


def test_update_patient_flag_protection_prevents_any_change(db_session, api_client):
    """
    Documente un bug present sur HEAD : la condition
    "if 'admin' not in user_app_role" est toujours vraie (user_app_role
    vaut toujours '', voir Task 2), donc is_toxicology est systematiquement
    reecrit avec son ancienne valeur pour TOUT appelant, y compris un
    admin. Personne ne peut changer ce drapeau via PUT aujourd'hui (voir
    SUIVI-AVANCEMENT.md registre B6).
    """
    user = create_test_user(db_session, "test_patients_admin_flagprotect", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, is_toxicology=False)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_flagprotect", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"is_toxicology": True}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["is_toxicology"] is False


def test_update_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_update404", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_update404", TEST_PASSWORD)

    resp = client.put("/patients/999999999", json={"first_name": "X"}, headers=headers)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Patient introuvable"


def test_delete_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_delete", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_delete", TEST_PASSWORD)

    delete_resp = client.delete(f"/patients/{patient_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/patients/{patient_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_delete404", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_delete404", TEST_PASSWORD)

    resp = client.delete("/patients/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_patients_search_finds_created_patient(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_list", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, last_name="Zzuniquesearchname")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_list", TEST_PASSWORD)

    resp = client.get("/patients/?search=Zzuniquesearchname", headers=headers)

    assert resp.status_code == 200
    ids = [p["patient_id"] for p in resp.json()]
    assert patient_id in ids
