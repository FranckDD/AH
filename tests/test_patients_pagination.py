from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_liste_patients_renvoie_enveloppe_paginee(db_session, api_client):
    """GET /patients/ doit renvoyer {data,total,page,per_page,total_pages},
    comme le font deja /patients/clinical, /toxicology et /spiritual/list.
    Avant correction : renvoie une liste nue, donc le client ne connait
    jamais le nombre total et bloque la pagination sur une seule page."""
    admin = create_test_user(db_session, "pagin_admin", "admin", password=TEST_PASSWORD)
    for i in range(3):
        create_test_patient(db_session, admin, first_name=f"Pagin{i}")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "pagin_admin", TEST_PASSWORD)

    reponse = client.get("/patients/?page=1&per_page=2", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, dict), "une liste nue ne permet pas de paginer"
    assert set(corps) >= {"data", "total", "page", "per_page", "total_pages"}
    assert len(corps["data"]) == 2
    assert corps["total"] >= 3
    assert corps["total_pages"] >= 2
    assert corps["page"] == 1
    assert corps["per_page"] == 2


def test_liste_patients_secretaire_voit_tous_les_patients(db_session, api_client):
    """Defaut 1 (2026-10-26, decision utilisateur) : la secretaire (accueil
    et caisse) enregistre tous les patients, elle doit donc les voir tous,
    comme l'admin. Le filtre par defaut is_spiritual de B6 la limitait aux
    patients ayant un dossier spirituel (10 lignes, "Page 1 sur 1") alors
    que l'en-tete affichait le total global. Le total de la liste doit
    egaler celui de l'admin et le compteur /patients/counts/global."""
    from repositories.patient_repo import PatientRepository
    from models.medical_record import MedicalRecord
    from models.consultation_spirituelle import ConsultationSpirituel

    secretaire = create_test_user(db_session, "b6_secretaire", "secretaire", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "b6_admin", "admin", password=TEST_PASSWORD)
    clinique_id, _ = create_test_patient(db_session, admin, first_name="Clinique")
    spirituel_id, _ = create_test_patient(db_session, admin, first_name="Spirituel")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=clinique_id, motif_code="consultation"))
    db_session.add(ConsultationSpirituel(
        patient_id=spirituel_id, created_by=admin.user_id, created_by_name=admin.username,
        type_consultation="Spiritual",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_secretaire", TEST_PASSWORD)

    reponse = client.get("/patients/?per_page=50", headers=headers)

    assert reponse.status_code == 200
    codes = [p["patient_id"] for p in reponse.json()["data"]]
    assert spirituel_id in codes
    assert clinique_id in codes

    total_secretaire = reponse.json()["total"]
    headers_admin = auth_headers(client, "b6_admin", TEST_PASSWORD)
    total_admin = client.get("/patients/?per_page=1", headers=headers_admin).json()["total"]
    assert total_secretaire == total_admin


def test_liste_patients_filtre_par_role_medecin(db_session, api_client):
    from models.medical_record import MedicalRecord
    from models.consultation_spirituelle import ConsultationSpirituel

    medecin = create_test_user(db_session, "b6_medecin", "medecin", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "b6_admin2", "admin", password=TEST_PASSWORD)
    clinique_id, _ = create_test_patient(db_session, admin, first_name="Clinique2")
    spirituel_id, _ = create_test_patient(db_session, admin, first_name="Spirituel2")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=clinique_id, motif_code="consultation"))
    db_session.add(ConsultationSpirituel(
        patient_id=spirituel_id, created_by=admin.user_id, created_by_name=admin.username,
        type_consultation="Spiritual",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_medecin", TEST_PASSWORD)

    reponse = client.get("/patients/?per_page=50", headers=headers)

    assert reponse.status_code == 200
    codes = [p["patient_id"] for p in reponse.json()["data"]]
    assert clinique_id in codes
    assert spirituel_id not in codes


def test_assistant_peut_chercher_un_patient(db_session, api_client):
    """Chantier 6 : la personne qui admet en toxicologie (role Assistant,
    voir POST /toxico/admission) doit pouvoir chercher un patient existant
    avant l'admission. Avant cet ajout, le routeur /patients/ n'autorisait
    pas Assistant (403)."""
    create_test_user(db_session, "b6_assistant", "Assistant", password=TEST_PASSWORD)
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_assistant", TEST_PASSWORD)

    reponse = client.get("/patients/?search=test", headers=headers)

    assert reponse.status_code == 200


def test_assistant_recherche_trouve_patient_sans_dossier_toxico(db_session, api_client):
    """Finding 1 (revue finale chantier 6) : list_patients() appliquait le
    filtre par domaine (B6) meme quand un terme `search` etait fourni, donc
    un Assistant (role d'admission toxico) ne pouvait retrouver, via
    /patients/?search=..., que des patients ayant DEJA un dossier toxico -
    exactement ceux qui n'ont pas besoin d'etre rattaches. Un patient tout
    neuf, sans aucun dossier dans aucun domaine, doit rester trouvable par
    recherche explicite pour permettre le rattachement inter-domaines."""
    assistant = create_test_user(db_session, "b6_assistant_search", "Assistant", password=TEST_PASSWORD)
    admin = create_test_user(db_session, "b6_admin3", "admin", password=TEST_PASSWORD)
    sans_dossier_id, _ = create_test_patient(db_session, admin, first_name="SansDossierXYZ")
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "b6_assistant_search", TEST_PASSWORD)

    reponse = client.get("/patients/?search=SansDossierXYZ", headers=headers)

    assert reponse.status_code == 200
    codes = [p["patient_id"] for p in reponse.json()["data"]]
    assert sans_dossier_id in codes



def test_secretaire_et_medecin_garde_le_silo_clinique():
    """Revue defaut 1 : un utilisateur portant secretaire + medecin reste
    cantonne au clinique (le silo medical passe avant la regle sans filtre).
    Un compte en base n'a qu'un role_id : plusieurs roles arrivent par le
    jeton (_roles), d'ou un test direct du controleur."""
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    from controller.patient_controller import PatientController

    for roles, attendu in ((["secretaire", "medecin"], {"is_clinical": True}),
                           (["nurse", "secretaire"], {"is_clinical": True}),
                           (["secretaire"], {})):
        repo = MagicMock()
        ctrl = PatientController.__new__(PatientController)
        ctrl.repo = repo
        ctrl.user = SimpleNamespace(roles=roles, postgres_role=None)
        ctrl.list_patients(page=1, per_page=10)
        assert repo.list_patients.call_args.kwargs["filters"] == attendu, roles


def test_liste_patients_calcule_le_type_depuis_les_dossiers(db_session, api_client):
    """Defaut releve par les guides 2026-10-26 : la colonne Type affichait
    NOUVEAU pour un patient ayant des consultations alors que sa fiche disait
    CLINIQUE. Les drapeaux de la liste doivent etre calcules a la lecture
    (existence de dossiers), jamais lus depuis les colonnes stockees."""
    from models.medical_record import MedicalRecord

    admin = create_test_user(db_session, "flags_admin", "admin", password=TEST_PASSWORD)
    avec_id, _ = create_test_patient(db_session, admin, first_name="AvecDossier")
    sans_id, _ = create_test_patient(db_session, admin, first_name="SansDossier")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=avec_id, motif_code="consultation"))
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "flags_admin", TEST_PASSWORD)
    data = client.get("/patients/?per_page=100", headers=headers).json()["data"]
    par_id = {p["patient_id"]: p for p in data}

    assert par_id[avec_id]["is_clinical"] is True
    assert par_id[sans_id]["is_clinical"] is False

    clinique = client.get("/patients/clinical?per_page=100", headers=headers).json()["data"]
    assert {p["patient_id"]: p for p in clinique}[avec_id]["is_clinical"] is True


def test_liste_patients_plus_recent_en_premier(db_session, api_client):
    """Defaut releve par les guides 2026-10-26 : un nouveau patient doit
    apparaitre en tete de liste (tri par creation decroissante, pas par
    derniere modification)."""
    from datetime import datetime, timedelta
    from models.patient import Patient

    admin = create_test_user(db_session, "order_admin", "admin", password=TEST_PASSWORD)
    ancien_id, _ = create_test_patient(db_session, admin, first_name="Ancien")
    recent_id, _ = create_test_patient(db_session, admin, first_name="Recent")
    db_session.flush()
    maintenant = datetime.now()
    db_session.query(Patient).filter_by(patient_id=ancien_id).update(
        {"created_at": maintenant - timedelta(days=30), "last_updated_at": maintenant + timedelta(days=1)})
    db_session.query(Patient).filter_by(patient_id=recent_id).update(
        {"created_at": maintenant, "last_updated_at": maintenant - timedelta(days=30)})
    db_session.flush()

    client = api_client(auth_endpoints, patients_endpoints)
    headers = auth_headers(client, "order_admin", TEST_PASSWORD)
    ids = [p["patient_id"] for p in client.get("/patients/?per_page=100", headers=headers).json()["data"]]

    assert ids.index(recent_id) < ids.index(ancien_id)
