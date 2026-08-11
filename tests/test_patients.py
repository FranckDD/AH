# tests/test_patients.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import create_test_user, create_test_patient, login


def _auth_headers(client, username, password):
    token = login(client, username, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_patient_success(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_create", "admin", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_create", "Correct123!")

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
    pour une secretaire ne se declenche jamais. On force explicitement
    is_spiritual=False dans la requete pour que ce test echoue si le bug
    est corrige sans que ce test soit mis a jour (voir SUIVI-AVANCEMENT.md,
    registre B6).
    """
    create_test_user(db_session, "test_patients_secretaire_create", "secretaire", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_secretaire_create", "Correct123!")

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
    user = create_test_user(db_session, "test_patients_admin_get", "admin", password="Correct123!")
    patient_id, code = create_test_patient(db_session, user, last_name="Lecture")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_get", "Correct123!")

    resp = client.get(f"/patients/{patient_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == patient_id
    assert body["code_patient"] == code
    assert body["last_name"] == "Lecture"


def test_get_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_get404", "admin", password="Correct123!")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = _auth_headers(client, "test_patients_admin_get404", "Correct123!")

    resp = client.get("/patients/999999999", headers=headers)

    assert resp.status_code == 404
