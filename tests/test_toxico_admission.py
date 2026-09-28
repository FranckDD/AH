from datetime import date

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_admission_toxico_rattache_a_un_patient_existant_sans_le_dupliquer(db_session, api_client):
    """Avant le chantier 6, l'admission toxico creait systematiquement un
    nouveau patient - impossible de rattacher un dossier toxico a un
    patient deja connu du centre (registre L2). Un patient_id fourni doit
    reutiliser ce patient, sans creer de doublon."""
    assistant = create_test_user(db_session, "toxico_assistant", "Assistant", password=TEST_PASSWORD)
    psy = create_test_user(db_session, "toxico_psy", "Psychologist", password=TEST_PASSWORD)
    patient_id, code_patient = create_test_patient(db_session, assistant, first_name="Existant")
    db_session.flush()

    client = api_client(auth_endpoints, toxico_endpoint, patients_endpoints)
    headers = auth_headers(client, "toxico_assistant", TEST_PASSWORD)

    reponse = client.post(
        "/toxico/admission",
        data={
            "patientId": str(patient_id),
            "admissionDate": date.today().isoformat(),
            "substance": "Alcool",
            "psychologist": str(psy.user_id),
            "guardianName": "Tuteur Test",
            "guardianContact": "0000000000",
        },
        headers=headers,
    )

    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["code_patient"] == code_patient

    total_patients = client.get("/patients/?search=Existant", headers=headers).json()["total"]
    assert total_patients == 1, "le rattachement ne doit pas creer un second patient"


def test_admission_toxico_patient_id_introuvable_est_rejetee(db_session, api_client):
    assistant = create_test_user(db_session, "toxico_assistant2", "Assistant", password=TEST_PASSWORD)
    psy = create_test_user(db_session, "toxico_psy2", "Psychologist", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, toxico_endpoint)
    headers = auth_headers(client, "toxico_assistant2", TEST_PASSWORD)

    reponse = client.post(
        "/toxico/admission",
        data={
            "patientId": "999999",
            "admissionDate": date.today().isoformat(),
            "substance": "Alcool",
            "psychologist": str(psy.user_id),
            "guardianName": "Tuteur Test",
            "guardianContact": "0000000000",
        },
        headers=headers,
    )

    assert reponse.status_code == 500
    assert "introuvable" in reponse.json()["detail"]


def test_admission_toxico_creation_sans_patient_id_inchangee(db_session, api_client):
    """Non-regression : le flux de creation existant (sans patient_id)
    continue de fonctionner exactement comme avant."""
    assistant = create_test_user(db_session, "toxico_assistant3", "Assistant", password=TEST_PASSWORD)
    psy = create_test_user(db_session, "toxico_psy3", "Psychologist", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, toxico_endpoint)
    headers = auth_headers(client, "toxico_assistant3", TEST_PASSWORD)

    reponse = client.post(
        "/toxico/admission",
        data={
            "firstName": "Nouveau",
            "lastName": "Patient",
            "dob": "1990-01-01",
            "mothersName": "Mere Test",
            "admissionDate": date.today().isoformat(),
            "substance": "Cannabis",
            "psychologist": str(psy.user_id),
            "guardianName": "Tuteur Test",
            "guardianContact": "0000000000",
        },
        headers=headers,
    )

    assert reponse.status_code == 201, reponse.text
