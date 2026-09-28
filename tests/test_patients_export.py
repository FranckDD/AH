# tests/test_patients_export.py
from datetime import date, timedelta

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def test_export_patients_csv_contient_le_patient_cree(db_session, api_client):
    admin = create_test_user(db_session, "export_patients_csv", "admin", password=TEST_PASSWORD)
    _, data = create_test_patient(db_session, admin, first_name="ExportCsvUnique", last_name="TestExport")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_patients_csv", TEST_PASSWORD)

    resp = client.get("/patients/export?format=csv", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "ExportCsvUnique" in resp.text
    assert "TestExport" in resp.text


def test_export_patients_pdf_genere_un_fichier_valide(db_session, api_client):
    admin = create_test_user(db_session, "export_patients_pdf", "admin", password=TEST_PASSWORD)
    create_test_patient(db_session, admin, first_name="ExportPdfUnique")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_patients_pdf", TEST_PASSWORD)

    resp = client.get("/patients/export?format=pdf", headers=headers)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 500


def test_export_patients_filtre_par_periode_exclut_hors_plage(db_session, api_client):
    admin = create_test_user(db_session, "export_patients_periode", "admin", password=TEST_PASSWORD)
    _, data = create_test_patient(db_session, admin, first_name="ExportPeriodeUnique")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_patients_periode", TEST_PASSWORD)

    hier = date.today() - timedelta(days=1)
    avant_hier = date.today() - timedelta(days=2)

    resp_hors_plage = client.get(
        f"/patients/export?format=csv&date_from={avant_hier}&date_to={hier}", headers=headers
    )
    resp_dans_plage = client.get("/patients/export?format=csv", headers=headers)

    assert "ExportPeriodeUnique" not in resp_hors_plage.text
    assert "ExportPeriodeUnique" in resp_dans_plage.text


def test_export_respecte_le_filtre_onglet_meme_avec_recherche(db_session, api_client):
    """Non-regression du finding Important (revue finale, 2026-09-23) : une
    recherche active sur /patients/export ne doit pas faire disparaitre le
    filtre d'onglet (type=CLINIQUE|TOXICO|SPIRITUEL) - sinon l'export
    renvoie des patients hors du domaine demande."""
    admin = create_test_user(db_session, "export_filtre_admin", "admin", password=TEST_PASSWORD)
    patient_clinique_id, _ = create_test_patient(db_session, admin, first_name="FiltreExportShared")
    patient_toxico_id, _ = create_test_patient(db_session, admin, first_name="FiltreExportShared")
    db_session.flush()

    from models.medical_record import MedicalRecord
    db_session.add(MedicalRecord(patient_id=patient_clinique_id, motif_code="free", diagnosis="RAS"))
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_filtre_admin", TEST_PASSWORD)

    resp = client.get(
        "/patients/export?format=csv&type=CLINIQUE&search=FiltreExportShared",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.text
    assert body.count("FiltreExportShared") == 1  # seul le patient clinique doit apparaitre


def test_export_toxico_refuse_a_medecin(db_session, api_client):
    """Coherence avec /patients/toxicology (garde deja existante,
    chantier perimetre medical 2026-09-22) : un medecin ne doit pas
    pouvoir contourner cette regle via /patients/export?type=TOXICO."""
    medecin = create_test_user(db_session, "export_toxico_medecin", "medecin", password=TEST_PASSWORD)

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "export_toxico_medecin", TEST_PASSWORD)

    resp = client.get("/patients/export?format=csv&type=TOXICO", headers=headers)
    assert resp.status_code == 403

    # Non-regression : l'export CLINIQUE reste autorise pour ce role.
    resp_clinique = client.get("/patients/export?format=csv&type=CLINIQUE", headers=headers)
    assert resp_clinique.status_code == 200
