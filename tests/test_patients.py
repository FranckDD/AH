# tests/test_patients.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import create_test_user, create_test_patient, login, auth_headers

TEST_PASSWORD = "Correct123!"


def test_create_patient_success(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_create", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_create", TEST_PASSWORD)

    payload = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "birth_date": "1985-03-12",
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "Jean"
    assert body["last_name"] == "Dupont"
    assert body["birth_date"] == "1985-03-12"
    assert body["code_patient"]


def test_create_patient_success_all_business_fields(db_session, api_client):
    """Le formulaire de creation (chantier 7a) envoie desormais 10 champs
    (pas seulement first_name/last_name/birth_date comme avant) - ce test
    verifie que chacun d'eux atteint bien la base et revient inchange dans
    la reponse."""
    create_test_user(db_session, "test_patients_admin_create_all", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_create_all", TEST_PASSWORD)

    payload = {
        "first_name": "Alphonse",
        "last_name": "Nkomo",
        "birth_date": "1978-11-05",
        "gender": "M",
        "national_id": "CNI-ALL-FIELDS-0001",
        "contact_phone": "+237611223344",
        "assurance": "CNPS",
        "residence": "Yaounde, Cameroun",
        "father_name": "Paul Nkomo",
        "mother_name": "Sylvie Nkomo",
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["first_name"] == "Alphonse"
    assert body["last_name"] == "Nkomo"
    assert body["birth_date"] == "1978-11-05"
    assert body["gender"] == "M"
    assert body["national_id"] == "CNI-ALL-FIELDS-0001"
    assert body["contact_phone"] == "+237611223344"
    assert body["assurance"] == "CNPS"
    assert body["residence"] == "Yaounde, Cameroun"
    assert body["father_name"] == "Paul Nkomo"
    assert body["mother_name"] == "Sylvie Nkomo"


def test_create_patient_role_flag_injection_does_not_trigger(db_session, api_client):
    """
    Documente un bug present sur HEAD (controller/patient_controller.py) :
    getattr(self.user, 'role_name', '') est toujours vide (cet attribut
    n'existe pas sur User), donc l'injection automatique de is_spiritual=True
    pour une secretaire ne se declenche jamais. is_spiritual=False est
    explicite ici par clarte (identique au defaut du schema) - si le bug
    etait corrige, une secretaire creant un patient devrait voir ce champ
    force a True independamment de la valeur demandee, ce que ce test
    detecterait (voir SUIVI-AVANCEMENT.md, registre B6).
    """
    create_test_user(db_session, "test_patients_secretaire_create", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_secretaire_create", TEST_PASSWORD)

    payload = {
        "first_name": "Marie",
        "last_name": "Curie",
        "birth_date": "1990-06-01",
        "is_spiritual": False,
    }
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["is_spiritual"] is False


def test_create_patient_by_secretaire_does_not_force_is_spiritual(db_session, api_client):
    """Chantier L4b-e : le bloc mort dans PatientController.create_patient
    forcait is_spiritual=True pour un createur 'app_secretaire'/'secretaire'
    quand le champ n'etait pas fourni. PatientCreate.is_spiritual defaut a
    False (jamais None, voir patients_schemas.py) : la condition
    'data.get('is_spiritual') is None' n'a jamais ete vraie, ce bloc etait
    deja inerte avant sa suppression. Ce test prouve juste qu'une secretaire
    peut creer un patient et que is_spiritual reste False par defaut,
    inchange par sa suppression."""
    create_test_user(db_session, "l4_secretaire_create_patient", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_secretaire_create_patient", TEST_PASSWORD)

    payload = {"first_name": "Test", "last_name": "Inerte", "birth_date": "1990-01-01"}
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 201
    assert resp.json()["is_spiritual"] is False


def test_get_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_get", "admin", password=TEST_PASSWORD)
    patient_id, code = create_test_patient(db_session, user, last_name="Lecture")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_get", TEST_PASSWORD)

    resp = client.get(f"/patients/{patient_id}", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_id"] == patient_id
    assert body["code_patient"] == code
    assert body["last_name"] == "Lecture"


def test_get_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_get404", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_get404", TEST_PASSWORD)

    resp = client.get("/patients/999999999", headers=headers)

    assert resp.status_code == 404


def test_update_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_update", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, first_name="Avant")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_update", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"first_name": "Apres"}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Apres"


def test_update_patient_toxicology_flag_reflects_the_stored_procedure(db_session, api_client):
    """La procedure stockee public.update_patient (ci/schema_only.sql)
    fait COALESCE(p_is_toxicology, is_toxicology) - un appelant autorise
    qui envoie explicitement une nouvelle valeur la voit appliquee. Le
    bloc Python qui pretendait proteger ce champ (retire par ce chantier,
    voir la spec chantier 7a) etait redondant avec cette protection deja
    assuree par la base, et cachait ce comportement reel derriere une
    logique de roles confuse et partiellement obsolete (roles 'app_*' qui
    ne correspondent a aucun role reel du systeme depuis le chantier 6)."""
    user = create_test_user(db_session, "test_patients_admin_flag2", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, is_toxicology=False)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_flag2", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"is_toxicology": True}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["is_toxicology"] is True


def test_update_patient_sans_drapeaux_les_laisse_inchanges(db_session, api_client):
    """Le formulaire patient (chantier 7a) n'envoie jamais les 3 drapeaux
    de domaine - une mise a jour classique (juste le telephone, par
    exemple) ne doit avoir aucun effet sur eux, exactement comme avant la
    simplification (COALESCE(None, is_X) preserve la valeur existante)."""
    user = create_test_user(db_session, "test_patients_admin_flag3", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, is_toxicology=True, is_clinical=False, is_spiritual=False)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_flag3", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"contact_phone": "+237600000000"}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_toxicology"] is True
    assert body["is_clinical"] is False
    assert body["is_spiritual"] is False
    assert body["contact_phone"] == "+237600000000"


def test_update_patient_empty_string_clears_contact_phone(db_session, api_client):
    """Contrat backend dont depend le correctif frontend du chantier 7a
    (patientStore.js addPatient/updatePatient) : la procedure stockee
    public.update_patient fait COALESCE(p_contact_phone, contact_phone),
    donc seul NULL signifie "ne pas modifier" - une chaine vide "" est une
    vraie valeur et doit bien effacer le champ. Ce test cible le backend
    (deja correct avant ce chantier) pour verrouiller ce comportement,
    puisque le bug etait uniquement cote frontend (null envoye au lieu de
    "" quand l'utilisateur vidait le champ)."""
    user = create_test_user(db_session, "test_patients_admin_clearphone", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, contact_phone="+237699999999")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_clearphone", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"contact_phone": ""}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["contact_phone"] != "+237699999999"
    assert body["contact_phone"] in ("", None)


def test_update_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_update404", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_update404", TEST_PASSWORD)

    resp = client.put("/patients/999999999", json={"first_name": "X"}, headers=headers)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Patient introuvable"


def test_delete_patient_success(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_delete", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_delete", TEST_PASSWORD)

    delete_resp = client.delete(f"/patients/{patient_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/patients/{patient_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_patient_not_found(db_session, api_client):
    create_test_user(db_session, "test_patients_admin_delete404", "admin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_delete404", TEST_PASSWORD)

    resp = client.delete("/patients/999999999", headers=headers)

    assert resp.status_code == 404


def test_list_patients_search_finds_created_patient(db_session, api_client):
    user = create_test_user(db_session, "test_patients_admin_list", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, user, last_name="Zzuniquesearchname")
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "test_patients_admin_list", TEST_PASSWORD)

    resp = client.get("/patients/?search=Zzuniquesearchname", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)
    assert "data" in body
    ids = [p["patient_id"] for p in body["data"]]
    assert patient_id in ids


def test_toxicomanager_can_search_patients(db_session, api_client):
    """Registre L4a : /patients autorisait deja assistant/secretaire/medecin/
    nurse/admin/manager mais pas ToxicoManager, alors que MainLayout.vue lui
    donne deja une entree de menu vers /dashboard/patients."""
    create_test_user(db_session, "l4a_toxicomanager_patients", "ToxicoManager", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4a_toxicomanager_patients", TEST_PASSWORD)

    resp = client.get("/patients/", headers=headers)

    assert resp.status_code == 200


def test_assistant_forbidden_from_update_patient(db_session, api_client):
    """Dette parquee au chantier 6 : le role 'assistant', elargi sur le
    routeur /patients entier pour permettre la recherche (necessaire a
    l'admission toxico), avait de facto acces a PUT/DELETE sur n'importe
    quel patient. La composition des dependances FastAPI est un ET logique :
    une dependance de route plus stricte, ajoutee en plus de la dependance
    de routeur, retire assistant de l'ecriture sans toucher a son acces en
    lecture (GET), toujours necessaire au flux d'admission toxico."""
    admin = create_test_user(db_session, "l4_assistant_denied_update_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="Avant")
    create_test_user(db_session, "l4_assistant_denied_update", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_denied_update", TEST_PASSWORD)

    resp = client.put(f"/patients/{patient_id}", json={"first_name": "Apres"}, headers=headers)

    assert resp.status_code == 403


def test_assistant_forbidden_from_delete_patient(db_session, api_client):
    admin = create_test_user(db_session, "l4_assistant_denied_delete_admin", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin)
    create_test_user(db_session, "l4_assistant_denied_delete", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_denied_delete", TEST_PASSWORD)

    resp = client.delete(f"/patients/{patient_id}", headers=headers)

    assert resp.status_code == 403


def test_assistant_still_allowed_to_search_patients(db_session, api_client):
    """Garde-fou : la restriction PUT/DELETE ne doit pas toucher a GET,
    necessaire au flux d'admission toxico de l'assistant."""
    create_test_user(db_session, "l4_assistant_still_search", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_still_search", TEST_PASSWORD)

    resp = client.get("/patients/", headers=headers)

    assert resp.status_code == 200


def test_assistant_forbidden_from_create_patient(db_session, api_client):
    """Complete la restriction d'ecriture de la Task 2 (registre L4, dette
    parquee au chantier 6) : PUT et DELETE etaient deja refuses a
    assistant, POST ne l'etait pas encore - trouve par la revue finale du
    chantier L4b-e."""
    create_test_user(db_session, "l4_assistant_denied_create", "Assistant", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "l4_assistant_denied_create", TEST_PASSWORD)

    payload = {"first_name": "Test", "last_name": "Refuse", "birth_date": "1990-01-01"}
    resp = client.post("/patients/", json=payload, headers=headers)

    assert resp.status_code == 403


def test_medecin_refuse_sur_onglet_toxicologie(db_session, api_client):
    """Meme si medecin/nurse est deja restreint par defaut sur /patients/
    (registre B6, chantier 6), rien n'empechait aujourd'hui d'appeler
    directement /patients/toxicology - route sans garde de role propre."""
    create_test_user(db_session, "medecin_onglet_toxico", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "medecin_onglet_toxico", TEST_PASSWORD)

    resp = client.get("/patients/toxicology", headers=headers)

    assert resp.status_code == 403


def test_nurse_refuse_sur_onglet_spirituel(db_session, api_client):
    create_test_user(db_session, "nurse_onglet_spirituel", "nurse", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "nurse_onglet_spirituel", TEST_PASSWORD)

    resp = client.get("/patients/spiritual/list", headers=headers)

    assert resp.status_code == 403


def test_secretaire_toujours_autorisee_sur_onglet_spirituel(db_session, api_client):
    """Non-regression : seuls medecin/nurse sont exclus, secretaire garde
    l'acces existant (deja utilise par la fiche patient secretariat)."""
    create_test_user(db_session, "secretaire_onglet_spirituel", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "secretaire_onglet_spirituel", TEST_PASSWORD)

    resp = client.get("/patients/spiritual/list", headers=headers)

    assert resp.status_code == 200


def test_medecin_toujours_autorise_sur_onglet_clinique(db_session, api_client):
    """Non-regression : /patients/clinical reste ouvert a medecin - c'est
    son propre perimetre, jamais touche par ce chantier."""
    create_test_user(db_session, "medecin_onglet_clinique", "medecin", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "medecin_onglet_clinique", TEST_PASSWORD)

    resp = client.get("/patients/clinical", headers=headers)

    assert resp.status_code == 200
