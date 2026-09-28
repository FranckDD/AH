# tests/test_lab_medical_scope.py
import sys
import os
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from models.lab import Examen, LabResult
from tests.conftest import create_test_user, create_test_patient, auth_headers

TEST_PASSWORD = "Correct123!"


def _creer_examen(db_session, code_suffix):
    examen = Examen(code=f"EX-{code_suffix}", nom="Glycémie", categorie="Biochimie", prix=1500)
    db_session.add(examen)
    db_session.flush()
    return examen


def _creer_resultat(db_session, patient_id, examen_id, status, code_suffix):
    r = LabResult(
        patient_id=patient_id,
        test_type="Glycémie",
        status=status,
        examen_id=examen_id,
        code_lab_patient=f"LAB-{code_suffix}-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(r)
    db_session.flush()
    return r


def test_medecin_ne_voit_que_les_resultats_completed_dans_historique(db_session, api_client):
    medecin = create_test_user(db_session, "lab_medecin_hist", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="LaboHist")
    examen = _creer_examen(db_session, "HIST1")
    _creer_resultat(db_session, patient_id, examen.id, "pending", "P")
    _creer_resultat(db_session, patient_id, examen.id, "completed", "C")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_medecin_hist", TEST_PASSWORD)

    # Tentative explicite de contourner le filtre par le parametre - doit
    # etre ignoree, jamais respectee, pour ce role.
    resp = client.get("/labo/history/paginated?status=pending", headers=headers)

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    statuses = {item["status"] for item in items}
    assert statuses == {"completed"}


def test_laborantin_voit_toujours_tous_les_statuts_dans_historique(db_session, api_client):
    """Non-regression : seul medecin/nurse est filtre. Recherche scopee sur
    le code unique du resultat cree (evite toute collision avec des
    donnees pending preexistantes dans la vraie base partagee - meme motif
    que le reste du projet, ex. chantier 2d-3)."""
    laborantin = create_test_user(db_session, "lab_laborantin_hist", "laborantin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, laborantin, first_name="LaboHist2")
    examen = _creer_examen(db_session, "HIST2")
    resultat_pending = _creer_resultat(db_session, patient_id, examen.id, "pending", "P2")
    _creer_resultat(db_session, patient_id, examen.id, "completed", "C2")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_laborantin_hist", TEST_PASSWORD)

    resp = client.get(
        "/labo/history/paginated",
        params={"status": "pending", "search": resultat_pending.code_lab_patient},
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "pending"
    assert items[0]["code"] == resultat_pending.code_lab_patient


def test_nurse_ne_voit_que_completed_dans_historique_patient(db_session, api_client):
    nurse = create_test_user(db_session, "lab_nurse_patient_hist", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, nurse, first_name="LaboPatientHist")
    examen = _creer_examen(db_session, "PATHIST")
    _creer_resultat(db_session, patient_id, examen.id, "partial", "PA")
    _creer_resultat(db_session, patient_id, examen.id, "completed", "CO")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_nurse_patient_hist", TEST_PASSWORD)

    resp = client.get(f"/labo/patient/{patient_id}/history", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "completed"


def test_medecin_refuse_sur_detail_resultat_non_complet(db_session, api_client):
    medecin = create_test_user(db_session, "lab_medecin_detail", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="LaboDetail")
    examen = _creer_examen(db_session, "DET1")
    resultat = _creer_resultat(db_session, patient_id, examen.id, "pending", "D")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_medecin_detail", TEST_PASSWORD)

    resp = client.get(f"/labo/results/{resultat.result_id}", headers=headers)

    assert resp.status_code == 403


def test_medecin_autorise_sur_detail_resultat_complet(db_session, api_client):
    medecin = create_test_user(db_session, "lab_medecin_detail_ok", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="LaboDetailOk")
    examen = _creer_examen(db_session, "DET2")
    resultat = _creer_resultat(db_session, patient_id, examen.id, "completed", "DOK")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_medecin_detail_ok", TEST_PASSWORD)

    resp = client.get(f"/labo/results/{resultat.result_id}", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_laborantin_toujours_autorise_sur_detail_non_complet(db_session, api_client):
    """Non-regression explicite."""
    laborantin = create_test_user(db_session, "lab_laborantin_detail", "laborantin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, laborantin, first_name="LaboDetail3")
    examen = _creer_examen(db_session, "DET3")
    resultat = _creer_resultat(db_session, patient_id, examen.id, "pending", "D3")
    db_session.flush()

    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, "lab_laborantin_detail", TEST_PASSWORD)

    resp = client.get(f"/labo/results/{resultat.result_id}", headers=headers)

    assert resp.status_code == 200
