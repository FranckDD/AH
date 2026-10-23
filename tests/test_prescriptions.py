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
    POST /prescriptions/ renvoie la prescription creee (corps PrescriptionResponse complet).
    Corrige le defaut E5 du registre (SUIVI-AVANCEMENT.md) : repo.create() renvoie desormais l'objet
    Prescription (plus un booleen), donc l'endpoint relit et renvoie la vraie ligne au lieu du repli
    generique « Prescription creee (lecture non disponible) ».
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
    body = resp.json()
    assert "detail" not in body, "le repli generique ne doit plus etre renvoye"
    assert isinstance(body["prescription_id"], int)
    assert body["patient_id"] == patient_id
    assert body["medication"] == "Amoxicilline"
    assert body["dosage"] == "500mg"
    assert body["frequency"] == "2x/jour"
    assert body["duration"] == "7 jours"
    assert body["start_date"] == "2026-08-11"


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


def test_create_prescription_invalid_dates_returns_422(db_session, api_client):
    """
    Dates incoherentes (fin avant debut) : 422 propre, plus de plantage du gestionnaire de validation global.
    Corrige le defaut E1 du registre : main.py::validation_exception_handler convertit desormais tout le
    contenu de exc.errors() en JSON (dont l'exception brute d'un model_validator) au lieu de lever un TypeError.
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
    resp = client.post("/prescriptions/", json=payload, headers=headers)

    assert resp.status_code == 422
    assert "detail" in resp.json()


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


def test_update_prescription_success(db_session, api_client):
    """
    Le payload doit contenir TOUS les champs de PrescriptionBase : la
    procedure stockee public.update_prescription fait une reecriture
    complete et inconditionnelle de toutes les colonnes (pas de
    COALESCE avec les valeurs existantes) - voir
    test_update_prescription_partial_payload_returns_409 ci-dessous et
    SUIVI-AVANCEMENT.md registre E4.
    """
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_update", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="Doliprane", dosage="500mg",
        start_date=date_cls.today(), end_date=date_cls.today() + timedelta(days=5),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_update", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    full_payload = {
        "patient_id": patient_id,
        "medication": "Doliprane",
        "dosage": "1000mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": str(date_cls.today()),
        "end_date": str(date_cls.today() + timedelta(days=5)),
        "notes": None,
    }
    resp = client.put(f"/prescriptions/{prescription_id}", json=full_payload, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["dosage"] == "1000mg"


def test_update_prescription_partial_payload_keeps_other_fields(db_session, api_client):
    """
    PUT partiel (ici : seulement patient_id + dosage) : 200, le dosage change et les autres champs sont conserves.
    Corrige le defaut E4 du registre : la procedure de mise a jour utilise COALESCE(parametre, valeur_actuelle)
    (migration 003), donc un champ omis n'est plus reecrit a NULL (ce qui violait les NOT NULL -> 409).
    """
    user = create_test_user(db_session, "test_presc_medecin_updatepartial", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_updatepartial", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    before = list_resp.json()["data"][0]
    prescription_id = before["prescription_id"]

    resp = client.put(
        f"/prescriptions/{prescription_id}",
        json={"patient_id": patient_id, "dosage": "750mg"},
        headers=headers,
    )

    assert resp.status_code == 200
    after = resp.json()
    assert after["dosage"] == "750mg"
    for champ in ("medication", "frequency", "duration", "start_date"):
        assert after[champ] == before[champ], f"{champ} ne doit pas etre modifie par un PUT partiel"


def test_update_prescription_not_found_returns_404(db_session, api_client):
    """
    PUT sur un id inexistant : 404 avec le message du depot.
    Corrige le defaut E3 du registre : repo.update() verifie l'existence avant la mise a jour et leve
    ValueError, que l'endpoint traduit en 404 (au lieu d'une erreur SQL generique renvoyee en 500).
    """
    user = create_test_user(db_session, "test_presc_medecin_update404", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_update404", TEST_PASSWORD)

    resp = client.put("/prescriptions/999999999", json={"patient_id": patient_id}, headers=headers)

    assert resp.status_code == 404
    assert resp.json()["detail"]


def test_update_prescription_invalid_dates_returns_422(db_session, api_client):
    """
    Meme regle que a la creation : PrescriptionUpdate partage le model_validator de PrescriptionBase,
    donc des dates incoherentes sur un PUT donnent un 422 propre (defaut E1 du registre, corrige).
    """
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_updatedates", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        start_date=date_cls.today(), end_date=date_cls.today() + timedelta(days=5),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_updatedates", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    full_payload = {
        "patient_id": patient_id,
        "medication": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3x/jour",
        "duration": "5 jours",
        "start_date": "2026-08-20",
        "end_date": "2026-08-10",
        "notes": None,
    }
    resp = client.put(f"/prescriptions/{prescription_id}", json=full_payload, headers=headers)

    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_delete_prescription_success(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_delete", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_delete", TEST_PASSWORD)

    list_resp = client.get(f"/prescriptions/?patient_id={patient_id}", headers=headers)
    prescription_id = list_resp.json()["data"][0]["prescription_id"]

    delete_resp = client.delete(f"/prescriptions/{prescription_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/prescriptions/{prescription_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_prescription_nonexistent_returns_404(db_session, api_client):
    """
    DELETE sur un id inexistant : 404.
    Corrige le defaut E2 du registre : repo.delete() verifie le rowcount au lieu de renvoyer toujours True,
    donc l'endpoint peut distinguer « supprime » (204) de « introuvable » (404).
    """
    create_test_user(db_session, "test_presc_medecin_delete404", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_delete404", TEST_PASSWORD)

    resp = client.delete("/prescriptions/999999999", headers=headers)

    assert resp.status_code == 404


def test_renewals_returns_prescription_within_window(db_session, api_client):
    """
    GET /prescriptions/renewals renvoie une LISTE JSON NUE (pas de cle
    "data") - confirme par execution reelle, different du format de
    GET /prescriptions/ (liste paginee avec data/total/page/per_page).
    """
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_renewals", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="MedicamentRenewal2d3",
        end_date=date_cls.today() + timedelta(days=5),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_renewals", TEST_PASSWORD)

    resp = client.get("/prescriptions/renewals", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()]
    assert "MedicamentRenewal2d3" in medications


def test_renewals_excludes_prescription_outside_window(db_session, api_client):
    from datetime import date as date_cls, timedelta

    user = create_test_user(db_session, "test_presc_medecin_renewalsout", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(
        db_session, patient_id, user,
        medication="MedicamentRenewalOut2d3",
        end_date=date_cls.today() + timedelta(days=30),
    )
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_renewalsout", TEST_PASSWORD)

    resp = client.get("/prescriptions/renewals?within_days=14", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()]
    assert "MedicamentRenewalOut2d3" not in medications


def test_kpi_count_day_includes_todays_prescription(db_session, api_client):
    from datetime import date as date_cls

    user = create_test_user(db_session, "test_presc_medecin_kpiday", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_kpiday", TEST_PASSWORD)

    before = client.get("/prescriptions/kpi/count?period=day", headers=headers).json()["count"]
    create_test_prescription(db_session, patient_id, user, start_date=date_cls.today())
    after = client.get("/prescriptions/kpi/count?period=day", headers=headers).json()["count"]

    assert after == before + 1


def test_kpi_count_week(db_session, api_client):
    create_test_user(db_session, "test_presc_medecin_kpiweek", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_kpiweek", TEST_PASSWORD)

    resp = client.get("/prescriptions/kpi/count?period=week", headers=headers)

    assert resp.status_code == 200
    assert isinstance(resp.json()["count"], int)


def test_kpi_count_day_scoped_to_doctor_id(db_session, api_client):
    """Registre I1 : un doctor_id explicite scope le compte a ce medecin
    uniquement, sans affecter le total etablissement (doctor_id omis)."""
    from datetime import date as date_cls

    medecin_a = create_test_user(db_session, "test_presc_kpi_doctor_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "test_presc_kpi_doctor_b", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin_a)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_kpi_doctor_a", TEST_PASSWORD)

    before_a = client.get(f"/prescriptions/kpi/count?period=day&doctor_id={medecin_a.user_id}", headers=headers).json()["count"]
    before_b = client.get(f"/prescriptions/kpi/count?period=day&doctor_id={medecin_b.user_id}", headers=headers).json()["count"]
    before_total = client.get("/prescriptions/kpi/count?period=day", headers=headers).json()["count"]

    create_test_prescription(db_session, patient_id, medecin_a, start_date=date_cls.today())

    after_a = client.get(f"/prescriptions/kpi/count?period=day&doctor_id={medecin_a.user_id}", headers=headers).json()["count"]
    after_b = client.get(f"/prescriptions/kpi/count?period=day&doctor_id={medecin_b.user_id}", headers=headers).json()["count"]
    after_total = client.get("/prescriptions/kpi/count?period=day", headers=headers).json()["count"]

    assert after_a == before_a + 1
    assert after_b == before_b
    assert after_total == before_total + 1


def test_kpi_count_accepts_arbitrary_date_range(db_session, api_client):
    """Le gap ferme par ce chantier : count_prescriptions n'acceptait
    auparavant que period=day/week, jamais une plage libre - contrairement
    aux 4 autres sources KPI du futur tableau de bord medecin."""
    from datetime import date, timedelta

    medecin = create_test_user(db_session, "tbm_presc_medecin1", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin)
    create_test_prescription(db_session, patient_id, medecin)

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "tbm_presc_medecin1", TEST_PASSWORD)

    today = date.today()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=1)).isoformat()

    resp = client.get(
        f"/prescriptions/kpi/count?start={start}&end={end}&doctor_id={medecin.user_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_kpi_count_date_range_scoped_by_doctor(db_session, api_client):
    from datetime import date, timedelta

    medecin_a = create_test_user(db_session, "tbm_presc_medecin_a", "medecin", password=TEST_PASSWORD)
    medecin_b = create_test_user(db_session, "tbm_presc_medecin_b", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin_a)
    create_test_prescription(db_session, patient_id, medecin_a)

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "tbm_presc_medecin_a", TEST_PASSWORD)

    today = date.today()
    start = (today - timedelta(days=1)).isoformat()
    end = (today + timedelta(days=1)).isoformat()

    resp_a = client.get(f"/prescriptions/kpi/count?start={start}&end={end}&doctor_id={medecin_a.user_id}", headers=headers)
    resp_b = client.get(f"/prescriptions/kpi/count?start={start}&end={end}&doctor_id={medecin_b.user_id}", headers=headers)

    assert resp_a.json()["count"] >= 1
    assert resp_b.json()["count"] == 0


def test_kpi_count_without_dates_still_uses_period(db_session, api_client):
    """Non-regression explicite : l'appel existant (desktop) sans
    start/end/doctor_id doit continuer a fonctionner exactement comme
    avant cette extension."""
    medecin = create_test_user(db_session, "tbm_presc_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin)
    create_test_prescription(db_session, patient_id, medecin)

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "tbm_presc_medecin2", TEST_PASSWORD)

    resp = client.get("/prescriptions/kpi/count?period=day", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_patient_prescription_history_returns_created_prescription(db_session, api_client):
    """
    GET /prescriptions/patient/{id} renvoie aussi une LISTE JSON NUE,
    comme /renewals - confirme par execution reelle.
    """
    user = create_test_user(db_session, "test_presc_medecin_history", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="MedicamentHistory2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_history", TEST_PASSWORD)

    resp = client.get(f"/prescriptions/patient/{patient_id}", headers=headers)

    assert resp.status_code == 200
    medications = [p["medication"] for p in resp.json()]
    assert "MedicamentHistory2d3" in medications


def test_patient_prescription_history_filters_by_status(db_session, api_client):
    user = create_test_user(db_session, "test_presc_medecin_historystatus", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    create_test_prescription(db_session, patient_id, user, medication="MedicamentActive2d3")
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_medecin_historystatus", TEST_PASSWORD)

    resp_active = client.get(f"/prescriptions/patient/{patient_id}?status=active", headers=headers)
    assert resp_active.status_code == 200
    assert any(p["medication"] == "MedicamentActive2d3" for p in resp_active.json())

    resp_completed = client.get(f"/prescriptions/patient/{patient_id}?status=completed", headers=headers)
    assert resp_completed.status_code == 200
    assert not any(p["medication"] == "MedicamentActive2d3" for p in resp_completed.json())


def test_prescriptions_list_forbidden_for_secretaire(db_session, api_client):
    """
    Confirme que role_required s'applique a tout le routeur (declare au
    niveau du router, pas seulement sur POST /) - deja verifie sur
    POST / (Task 2), verifie ici sur GET / pour eliminer tout doute.
    """
    create_test_user(db_session, "test_presc_secretaire_list", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_secretaire_list", TEST_PASSWORD)

    resp = client.get("/prescriptions/", headers=headers)

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Accès refusé : rôle utilisateur insuffisant"


def test_prescriptions_list_unauthenticated_returns_401(db_session, api_client):
    client = api_client(auth_endpoints, prescriptions_endpoints)

    resp = client.get("/prescriptions/")

    assert resp.status_code == 401


def test_list_prescriptions_tolerates_old_lab_order_without_exams_list(db_session, api_client):
    """Bug reel trouve en test navigateur (2026-09-23) : d'anciennes
    prescriptions (is_lab_order=True, lab_exams_list vide/absent,
    anterieures a l'ajout de la regle "liste d'examens requise")
    faisaient planter GET /prescriptions/ - PrescriptionResponse
    reutilisait la regle de coherence metier de PrescriptionCreate
    (check_content), qui n'a de sens qu'a la creation/modification,
    jamais a la lecture de donnees deja persistees. La ligne doit
    apparaitre normalement dans la liste, pas etre exclue/logguee en
    erreur."""
    from datetime import date as date_cls
    from models.prescription import Prescription

    medecin = create_test_user(db_session, "test_presc_old_lab_order", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin)
    # Insertion ORM directe (pas create_test_prescription/le repository,
    # qui appliquent tous deux la meme regle de coherence metier a la
    # creation - refuseraient donc cette ligne) : on simule ici une ligne
    # DEJA en base, incoherente avec les regles actuelles, comme les 3
    # prescriptions reelles trouvees en test navigateur (anterieures a
    # l'ajout de cette regle).
    db_session.add(Prescription(
        patient_id=patient_id, medication="BON D'EXAMEN", dosage="N/A",
        frequency="N/A", duration="N/A", start_date=date_cls.today(),
        is_lab_order=True, lab_exams_list=None,
        prescribed_by=medecin.user_id, prescribed_by_name=medecin.username,
    ))
    db_session.flush()

    client = api_client(auth_endpoints, prescriptions_endpoints)
    headers = auth_headers(client, "test_presc_old_lab_order", TEST_PASSWORD)

    resp = client.get("/prescriptions/", headers=headers)

    assert resp.status_code == 200, resp.text
    medications = [p["medication"] for p in resp.json()["data"]]
    assert "BON D'EXAMEN" in medications
