# tests/test_lab_pdf_export.py
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from api_backend.backend_app.routes.admin import config_endpoints
from models.lab import Examen, LabResult
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def test_lab_pdf_reflete_le_nom_etablissement_configure(db_session, api_client):
    """Chantier exports (2026-09-23) : le PDF labo doit refleter le nom
    d'etablissement reellement configure, pas une valeur figee - preuve
    que get_pdf_header_context() lit bien OrganizationConfig en direct."""
    admin = create_test_user(db_session, "pdf_labo_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="PdfLabo")
    examen = Examen(code="PDFTEST1", nom="Glycemie", categorie="Biochimie", prix=1000)
    db_session.add(examen)
    db_session.flush()
    resultat = LabResult(
        patient_id=patient_id, test_type="Glycemie", status="completed",
        examen_id=examen.id, code_lab_patient="LABPDF-001",
    )
    db_session.add(resultat)
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints, config_endpoints)
    headers = auth_headers(client, "pdf_labo_admin", TEST_PASSWORD)

    nom_unique = "Clinique Test Chantier Exports 2026"
    # /config/structure est POST + multipart/form-data (Form(...) cote
    # endpoint, pas de JSON) - "name" est le seul champ requis.
    resp_config = client.post("/config/structure", data={"name": nom_unique}, headers=headers)
    assert resp_config.status_code == 200, resp_config.text

    resp_pdf = client.get(f"/labo/results/{resultat.result_id}/pdf", headers=headers)

    assert resp_pdf.status_code == 200, resp_pdf.text
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert len(resp_pdf.content) > 1000
