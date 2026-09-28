from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.medical_records import medical_records_endpoint
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_create_medical_record_with_appointment_id(db_session, api_client):
    """Chantier 7c : un dossier medical peut etre cree avec un
    appointment_id, persiste et renvoye par l'API."""
    medecin = create_test_user(db_session, "test_7c_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Consultation")
    db_session.flush()

    from models.appointment import Appointment
    from datetime import date, time
    appt = Appointment(
        patient_id=patient_id, doctor_id=medecin.user_id,
        appointment_date=date.today(), appointment_time=time(9, 0), status="pending",
    )
    db_session.add(appt)
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_7c_medecin", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
        "appointment_id": appt.id,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["appointment_id"] == appt.id


def test_create_medical_record_without_appointment_id_stays_null(db_session, api_client):
    """Non-regression : une consultation spontanee (bouton "Nouvelle
    consultation" du dossier patient, sans RDV d'origine) continue de
    fonctionner, appointment_id reste NULL."""
    medecin = create_test_user(db_session, "test_7c_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Spontanee")
    db_session.flush()

    client = api_client(auth_endpoints, medical_records_endpoint)
    headers = auth_headers(client, "test_7c_medecin2", TEST_PASSWORD)

    resp = client.post("/medical_records/", json={
        "patient_id": patient_id,
        "motif_code": "consultation",
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["appointment_id"] is None
