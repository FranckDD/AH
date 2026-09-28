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


def test_liste_patients_filtre_par_role_secretaire(db_session, api_client):
    """Bug B6 : list_patients() lisait getattr(user, 'role_name', '')
    qui n'existe jamais sur User -> le filtre par role etait mort, une
    secretaire voyait tous les patients. Chantier 6 l'active via
    _get_user_roles_set(), deja utilisee ailleurs dans ce controller."""
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
    assert clinique_id not in codes


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
