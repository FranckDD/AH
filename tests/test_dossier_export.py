# tests/test_dossier_export.py
import io
from datetime import date

from openpyxl import load_workbook
from pypdf import PdfReader

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from models.medical_record import MedicalRecord
from models.toxico import ToxicoDossier
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_export_dossier_pdf_medecin_ne_contient_pas_toxico(db_session, api_client):
    """Chantier exports (2026-09-23) : la garantie de cloisonnement du
    chantier perimetre medical (2026-09-22) doit se propager au fichier
    exporte, pas seulement a l'ecran."""
    medecin = create_test_user(db_session, "export_dossier_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="ExportDossierMulti")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool"))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "export_dossier_medecin", TEST_PASSWORD)

    resp_pdf = client.get(f"/patients/{patient_id}/dossier/export?format=pdf", headers=headers)
    resp_excel = client.get(f"/patients/{patient_id}/dossier/export?format=excel", headers=headers)

    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert "Toxicologie" not in _pdf_text(resp_pdf.content)

    assert resp_excel.status_code == 200
    assert resp_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    wb = load_workbook(io.BytesIO(resp_excel.content))
    assert "Toxicologie" not in wb.sheetnames
    assert "Spirituel" not in wb.sheetnames


def test_export_dossier_admin_contient_toxico(db_session, api_client):
    """Non-regression : seul medecin/nurse est concerne par le
    cloisonnement, admin garde tout."""
    admin = create_test_user(db_session, "export_dossier_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="ExportDossierAdminMulti")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool"))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "export_dossier_admin", TEST_PASSWORD)

    resp_pdf = client.get(f"/patients/{patient_id}/dossier/export?format=pdf", headers=headers)

    assert resp_pdf.status_code == 200
    assert "Toxicologie" in _pdf_text(resp_pdf.content)

    resp_excel = client.get(f"/patients/{patient_id}/dossier/export?format=excel", headers=headers)
    assert resp_excel.status_code == 200
    wb = load_workbook(io.BytesIO(resp_excel.content))
    assert "Toxicologie" in wb.sheetnames
