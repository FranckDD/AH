from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from models.medical_record import MedicalRecord
from models.audit import AuditUserAction
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEST_PASSWORD = "TestPass123!"


def test_dossier_consolide_renvoie_les_domaines_et_journalise(db_session, api_client):
    """Un seul appel doit renvoyer patient + flags + tous les domaines
    cliniques, et journaliser la consultation (politique d'acces
    2026-09-15 : ouverture large, tracabilite forte). Le caller est
    medecin : depuis le 2026-09-22, dossier_toxico/historique_spirituel
    sont absents de la reponse pour ce role (voir test dedie plus bas),
    donc on ne les asserte plus ici comme presents-et-nuls."""
    medecin = create_test_user(db_session, "dossier_medecin", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Dossier")
    db_session.flush()
    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_medecin", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["patient"]["patient_id"] == patient_id
    assert corps["flags"]["is_clinical"] is True
    assert corps["flags"]["is_toxicology"] is False
    assert len(corps["historique_medical"]) == 1
    assert "dossier_toxico" not in corps
    assert "historique_spirituel" not in corps
    assert corps["domaines_indisponibles"] == []
    assert "is_clinical" not in corps["patient"]
    assert "is_toxicology" not in corps["patient"]
    assert "is_spiritual" not in corps["patient"]

    log = (
        db_session.query(AuditUserAction)
        .filter_by(resource_type="Patient", action_performed="VIEW_DOSSIER_COMPLET", resource_id=patient_id)
        .one_or_none()
    )
    assert log is not None, "la consultation du dossier complet doit etre journalisee (tracabilite forte)"


def test_dossier_consolide_tolere_l_echec_d_un_domaine(db_session, api_client, monkeypatch):
    """Un domaine en echec ne doit pas vider les autres - meme principe
    de tolerance aux pannes qu'au chantier 5."""
    medecin = create_test_user(db_session, "dossier_medecin2", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Dossier2")
    # commit (pas juste flush) : avec le rollback() ajoute dans la boucle du
    # controleur (Important #2), un simple flush laisserait medecin/patient
    # dans la meme SAVEPOINT que la requete et le rollback les annulerait
    # aussi (violation FK sur audit_user_actions.user_id). db_session
    # relance la SAVEPOINT automatiquement apres ce commit (voir
    # conftest.create_test_prescription), le rollback fin-de-fixture
    # nettoie toujours tout en fin de test.
    db_session.commit()

    from controller.lab_controller import LabController
    def echoue(self, patient_id):
        raise RuntimeError("panne simulee labo")
    monkeypatch.setattr(LabController, "get_patient_lab_history", echoue)

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_medecin2", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["historique_labo"] is None
    # egalite exacte (pas seulement "in") : prouve qu'aucun AUTRE domaine
    # n'a echoue silencieusement en meme temps
    assert corps["domaines_indisponibles"] == ["historique_labo"]
    # preuve reelle de tolerance aux pannes : "patient" est charge avant la
    # boucle try/except (jamais affecte par un echec de domaine sibling) -
    # ca ne prouve rien. resume_clinique et flags, eux, dependent de code
    # execute apres/independamment du domaine en echec.
    assert corps["resume_clinique"] is not None
    assert corps["flags"] is not None

    log = (
        db_session.query(AuditUserAction)
        .filter_by(resource_type="Patient", action_performed="VIEW_DOSSIER_COMPLET", resource_id=patient_id)
        .one_or_none()
    )
    assert log is not None
    assert log.new_values == {"domaines_en_echec": ["historique_labo"]}


def test_dossier_consolide_refuse_la_secretaire(db_session, api_client):
    """Politique d'acces 2026-09-15 : secretariat exclu du dossier complet."""
    create_test_user(db_session, "dossier_secretaire", "secretaire", password=TEST_PASSWORD)
    medecin_pour_patient = create_test_user(db_session, "dossier_medecin3", "medecin")
    patient_id, _ = create_test_patient(db_session, medecin_pour_patient, first_name="Dossier3")
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_secretaire", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 403


def test_dossier_consolide_medecin_ne_voit_pas_toxico_ni_spirituel(db_session, api_client):
    """Coeur du chantier 2026-09-22 : un patient reellement suivi dans les
    3 domaines a la fois (aucun doublon, chantier 6) ne doit exposer que
    le clinique a un medecin/nurse - jamais toxico/spirituel, mais sans
    jamais bloquer leur EXISTENCE (verifiee via 'flags')."""
    from datetime import date
    from models.toxico import ToxicoDossier
    from models.consultation_spirituelle import ConsultationSpirituel

    medecin = create_test_user(db_session, "dossier_medecin_multi", "medecin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, medecin, first_name="Multi")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(
        patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool",
    ))
    db_session.add(ConsultationSpirituel(
        patient_id=patient_id, created_by=medecin.user_id, created_by_name=medecin.username,
        type_consultation="Spiritual",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_medecin_multi", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    # les 3 domaines existent reellement (verifie via flags, jamais efface)
    assert corps["flags"]["is_clinical"] is True
    assert corps["flags"]["is_toxicology"] is True
    assert corps["flags"]["is_spiritual"] is True
    # mais seul le clinique est expose au medecin
    assert len(corps["historique_medical"]) == 1
    assert "dossier_toxico" not in corps
    assert "historique_spirituel" not in corps


def test_dossier_consolide_admin_voit_toujours_tous_les_domaines(db_session, api_client):
    """Non-regression explicite : le revirement ne concerne QUE
    medecin/nurse. Meme patient multi-domaines que le test precedent,
    vu par un admin - les 5 domaines doivent rester presents (politique
    L5 du chantier 6, inchangee pour ce role)."""
    from datetime import date
    from models.toxico import ToxicoDossier
    from models.consultation_spirituelle import ConsultationSpirituel

    admin = create_test_user(db_session, "dossier_admin_multi", "admin", password=TEST_PASSWORD)
    patient_id, _ = create_test_patient(db_session, admin, first_name="MultiAdmin")
    db_session.flush()

    db_session.add(MedicalRecord(patient_id=patient_id, motif_code="free", diagnosis="RAS"))
    db_session.add(ToxicoDossier(
        patient_id=patient_id, admission_date=date(2026, 1, 10), substance="Alcool",
    ))
    db_session.add(ConsultationSpirituel(
        patient_id=patient_id, created_by=admin.user_id, created_by_name=admin.username,
        type_consultation="Spiritual",
    ))
    db_session.flush()

    client = api_client(auth_endpoints, patient_dossier_endpoint)
    headers = auth_headers(client, "dossier_admin_multi", TEST_PASSWORD)

    reponse = client.get(f"/patients/{patient_id}/dossier", headers=headers)

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert "dossier_toxico" in corps
    assert corps["dossier_toxico"] is not None
    assert "historique_spirituel" in corps
    assert len(corps["historique_spirituel"]) == 1
