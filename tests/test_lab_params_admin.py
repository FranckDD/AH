"""Catalogue labo : ajouter, modifier, supprimer les parametres d'un examen et leurs plages de reference
(releve B 'aucun ecran pour ajouter ou modifier les parametres d'un examen')."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from tests.conftest import create_test_user, auth_headers

PWD = "Correct123!"


def _setup(db_session, api_client, role="admin"):
    create_test_user(db_session, f"lp_{role}", role, password=PWD)
    client = api_client(auth_endpoints, lab_endpoints)
    headers = auth_headers(client, f"lp_{role}", PWD)
    exam = client.post("/labo/exams", json={"code": "LPX1", "nom": "Test", "categorie": "Hema", "prix": 1000}, headers=headers)
    assert exam.status_code == 201, exam.text
    return client, headers, exam.json()["id"]


def test_add_update_param_and_ranges(db_session, api_client):
    client, headers, exam_id = _setup(db_session, api_client)
    r = client.post(f"/labo/exams/{exam_id}/params", json={"nom_parametre": "Hb", "unite": "g/dl", "type_valeur": "numeric"}, headers=headers)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = client.put(f"/labo/params/{pid}", json={"nom_parametre": "Hemoglobine", "unite": "g/L"}, headers=headers)
    assert r.status_code == 200, r.text

    r = client.post(f"/labo/params/{pid}/ranges", json={"sexe": "F", "age_min": 0, "age_max": 120, "valeur_min": 11.5, "valeur_max": 15.5}, headers=headers)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]

    listed = client.get(f"/labo/exams/{exam_id}/params", headers=headers).json()
    assert listed[0]["nom"] == "Hemoglobine" and listed[0]["unite"] == "g/L"
    assert listed[0]["ranges"][0]["sexe"] == "F"
    assert listed[0]["ranges"][0]["age_min"] == 0 and listed[0]["ranges"][0]["age_max"] == 120

    assert client.delete(f"/labo/ranges/{rid}", headers=headers).status_code == 204
    # un parametre sans resultat se supprime meme avec des plages
    client.post(f"/labo/params/{pid}/ranges", json={"sexe": "M", "age_min": 0, "age_max": 120, "valeur_min": 13, "valeur_max": 17}, headers=headers)
    assert client.delete(f"/labo/params/{pid}", headers=headers).status_code == 204


def test_range_rejects_inverted_bounds(db_session, api_client):
    client, headers, exam_id = _setup(db_session, api_client)
    pid = client.post(f"/labo/exams/{exam_id}/params", json={"nom_parametre": "X", "unite": "u", "type_valeur": "numeric"}, headers=headers).json()["id"]
    r = client.post(f"/labo/params/{pid}/ranges", json={"sexe": "M", "age_min": 0, "age_max": 10, "valeur_min": 9, "valeur_max": 1}, headers=headers)
    assert r.status_code == 422


def test_update_unknown_param_is_404(db_session, api_client):
    client, headers, _ = _setup(db_session, api_client)
    assert client.put("/labo/params/99999999", json={"nom_parametre": "Z"}, headers=headers).status_code == 404


def test_delete_exam_with_params_and_ranges_cascades(db_session, api_client):
    client, headers, exam_id = _setup(db_session, api_client)
    pid = client.post(f"/labo/exams/{exam_id}/params", json={"nom_parametre": "Hb", "unite": "g", "type_valeur": "numeric"}, headers=headers).json()["id"]
    client.post(f"/labo/params/{pid}/ranges", json={"sexe": "M", "age_min": 0, "age_max": 120, "valeur_min": 13, "valeur_max": 17}, headers=headers)
    assert client.delete(f"/labo/exams/{exam_id}", headers=headers).status_code == 204
    from models.lab import Parametre, ReferenceRange
    assert db_session.query(Parametre).filter(Parametre.id == pid).count() == 0
    assert db_session.query(ReferenceRange).filter(ReferenceRange.parametre_id == pid).count() == 0


def test_delete_exam_used_by_results_is_409_with_code(db_session, api_client):
    client, headers, exam_id = _setup(db_session, api_client)
    pid = client.post(f"/labo/exams/{exam_id}/params", json={"nom_parametre": "Hb", "unite": "g", "type_valeur": "numeric"}, headers=headers).json()["id"]
    from models.lab import LabResult, LabResultDetail
    from tests.conftest import create_test_patient
    from models.user import User
    adm = db_session.query(User).filter(User.username == "lp_admin").first()
    patient_id, _ = create_test_patient(db_session, adm, first_name="DelEx", gender="F")
    r = LabResult(patient_id=patient_id, test_type="Test", status="completed", examen_id=exam_id, code_lab_patient="LAB-DELEX-1")
    db_session.add(r)
    db_session.flush()
    db_session.add(LabResultDetail(result_id=r.result_id, parametre_id=pid, valeur_text="1"))
    db_session.flush()
    resp = client.delete(f"/labo/exams/{exam_id}", headers=headers)
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "exam_in_use"
    assert resp.json()["detail"]["message"]
