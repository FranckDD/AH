# tests/test_prescriptions.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.prescription import prescriptions_endpoints
from tests.conftest import create_test_user, create_test_patient, create_test_prescription, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_prescription_success(db_session, api_client):
    """
    Documente un bug reel sur HEAD, plus grave que prevu par la spec
    (SUIVI-AVANCEMENT.md registre E5) : prescriptions_endpoints.py::
    create_prescription() ne renvoie JAMAIS la prescription creee, meme
    en cas de succes complet. repo.create() renvoie le booleen True ;
    en Python, bool est une sous-classe de int, donc
    `isinstance(True, int)` vaut True (ligne 183) - la branche
    `elif created is True or created is None:` (ligne 191), ecrite pour
    gerer exactement ce cas, n'est JAMAIS atteinte : elle est
    court-circuitee par la branche int au-dessus. Le code prend donc le
    chemin `prescription_ctrl.get_prescription(True)` ->
    `repo.get(True)` -> `session.get(Prescription, True)`, qui plante
    contre PostgreSQL (`operator does not exist: integer = boolean` -
    confirme par execution directe pendant le cadrage de ce plan). Cette
    exception est avalee silencieusement (`except Exception: obj = None`),
    et l'endpoint retourne son repli generique : 201 avec
    {"detail": "Prescription creee (lecture non disponible)"} - jamais
    le corps PrescriptionResponse pourtant declare par
    response_model=PrescriptionResponse sur la route (le repli utilise
    JSONResponse directement, qui contourne la validation de response_model).
    Un vrai client (le frontend Vue) ne recoit donc jamais la prescription
    qu'il vient de creer.
    """
    user = create_test_user(db_session, "test_presc_medecin_create", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_create", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "duration": "7 jours",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json() == {"detail": "Prescription créée (lecture non disponible)"}


def test_create_prescription_missing_required_field_returns_422(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_422", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_422", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 422


def test_create_prescription_invalid_dates_crashes_validation_handler(db_session, api_client):
    """
    Documente un bug transversal, pas specifique aux prescriptions (voir
    SUIVI-AVANCEMENT.md registre E1) : main.py::validation_exception_handler
    serialise exc.errors() tel quel en JSON (json.dumps standard, pas
    jsonable_encoder). Quand l'erreur vient d'un model_validator qui leve
    ValueError (PrescriptionBase.check_dates ici), Pydantic inclut
    l'exception ELLE-MEME (pas son texte) dans error['ctx']['error'] - non
    serialisable -> TypeError non intercepte, au lieu d'un 422 propre.
    Constate par execution reelle contre un worktree jetable base sur HEAD
    pendant le cadrage de ce plan (jamais contre le repertoire de travail
    principal, contamine par le travail en cours sur ce module).
    """
    user = create_test_user(db_session, "test_presc_medecin_dates", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_dates", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-20",
        "end_date": "2026-08-10",
    }
    with pytest.raises(TypeError, match="not JSON serializable"):
        client.post("/prescriptions/", json=payload, headers=headers)


def test_create_prescription_forbidden_for_secretaire(db_session, api_client):
    user = create_test_user(db_session, "test_presc_secretaire", "secretaire", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_secretaire", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_create_prescription_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, prescriptions_endpoints)

    payload = {
        "patient_id": 1,
        "medication": "Amoxicilline",
        "dosage": "500mg",
        "frequency": "2x/jour",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload)

    assert resp.status_code == 401


def test_create_prescription_allowed_for_nurse(db_session, api_client):
    """
    Confirme que le role nurse est bien autorise (pas de 403) - le corps
    de reponse n'est pas verifie ici pour le contenu de la prescription,
    voir test_create_prescription_success pour le bug du corps de reponse
    (registre E5, valable pour tout role autorise, pas specifique a
    nurse).

    "duration" est obligatoire dans ce payload malgre son statut Optional
    dans le schema Pydantic PrescriptionCreate : la colonne DB
    prescriptions.duration est NOT NULL, et rien ne comble cet ecart
    cote schema (registre E6 - omettre "duration" fait echouer TOUTE
    creation avec 409, quel que soit le role, decouvert empiriquement
    par l'implementeur de Task 2 puis verifie independamment).
    """
    user = create_test_user(db_session, "test_presc_nurse_create", "nurse", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_nurse_create", TEST_PASSWORD)

    payload = {
        "patient_id": patient_id,
        "medication": "Ibuprofene",
        "dosage": "200mg",
        "frequency": "1x/jour",
        "duration": "3 jours",
        "start_date": "2026-08-11",
    }
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 201


def test_get_prescription_success(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_get", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="Doliprane")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_get", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    resp = client.get(f"/prescriptions/{prescription_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["prescription_id"] == prescription_id
    assert body["medication"] == "Doliprane"


def test_get_prescription_not_found(db_session, api_client):
    create_test_user(db_session, "test_presc_medecin_get404", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_get404", TEST_PASSWORD)

    resp = client.get("/prescriptions/999999999", headers=headers)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Prescription non trouvée"


def test_list_prescriptions_filters_by_patient_id(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_listpid", "medecin", password=TEST_PASSWORD)
    patient_a, _ = create_test_patient(db_session, user, last_name="PatientA2d3")
    patient_b, _ = create_test_patient(db_session, user, last_name="PatientB2d3")
    create_test_prescription(db_session, patient_a, user, medication="MedicamentA2d3")
    create_test_prescription(db_session, patient_b, user, medication="MedicamentB2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_listpid", TEST_PASSWORD)

    resp = client.get(f"/prescriptions/?patient_id={patient_a}", headers=headers)

    assert resp.status_code == 200
    items = resp.json()["data"]
    assert all(p["patient_id"] == patient_a for p in items)
    assert any(p["medication"] == "MedicamentA2d3" for p in items)


def test_list_prescriptions_filters_by_date_range(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_presc_medecin_listdate", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="MedicamentDateRange2d3",
        start_date=date_cls(2030, 1, 15),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_listdate", TEST_PASSWORD)

    resp = client.get("/prescriptions/?date_from=2030-01-01&date_to=2030-01-31", headers=headers)
    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()["data"]]
    assert "MedicamentDateRange2d3" in medications

    resp_excl = client.get("/prescriptions/?date_from=2030-02-01&date_to=2030-02-28", headers=headers)
    assert resp_excl.status_code == 200
    medications_excl = [p["medication"] for p in resp_excl.json()["data"]]
    assert "MedicamentDateRange2d3" not in medications_excl


def test_list_prescriptions_search_finds_by_medication(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_search", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="Zzuniquemedicationsearch2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_search", TEST_PASSWORD)

    resp = client.get("/prescriptions/?search=Zzuniquemedicationsearch2d3", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()["data"]]
    assert "Zzuniquemedicationsearch2d3" in medications
