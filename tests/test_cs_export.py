# tests/test_cs_export.py
from datetime import date, timedelta

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.cs import cs_endpoint
from tests.conftest import create_test_user, create_test_patient, auth_headers
from repositories.cs_repo import ConsultationSpirituelRepository

TEST_PASSWORD = "Correct123!"


def test_export_consultations_csv_contient_le_patient(db_session, api_client):
    admin = create_test_user(db_session, "export_cs_csv", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportCsUnique", last_name="TestCs")
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create({"patient_id": patient_id, "type_consultation": "Spiritual"}, admin)

    client = api_client(auth_endpoints, cs_endpoint)
    headers = auth_headers(client, "export_cs_csv", TEST_PASSWORD)

    resp = client.get("/cs/export?format=csv", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "ExportCsUnique" in resp.text


def test_export_consultations_pdf_genere_un_fichier_valide(db_session, api_client):
    admin = create_test_user(db_session, "export_cs_pdf", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportCsPdfUnique")
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create({"patient_id": patient_id, "type_consultation": "Spiritual"}, admin)

    client = api_client(auth_endpoints, cs_endpoint)
    headers = auth_headers(client, "export_cs_pdf", TEST_PASSWORD)

    resp = client.get("/cs/export?format=pdf", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 500


def test_export_consultations_filtre_par_periode(db_session, api_client):
    admin = create_test_user(db_session, "export_cs_periode", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportCsPeriodeUnique")
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create({"patient_id": patient_id, "type_consultation": "Spiritual"}, admin)

    client = api_client(auth_endpoints, cs_endpoint)
    headers = auth_headers(client, "export_cs_periode", TEST_PASSWORD)

    avant_hier = date.today() - timedelta(days=2)
    hier = date.today() - timedelta(days=1)

    resp_hors_plage = client.get(f"/cs/export?format=csv&date_from={avant_hier}&date_to={hier}", headers=headers)
    resp_dans_plage = client.get("/cs/export?format=csv", headers=headers)

    assert "ExportCsPeriodeUnique" not in resp_hors_plage.text
    assert "ExportCsPeriodeUnique" in resp_dans_plage.text
