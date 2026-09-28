from api_backend.backend_app.routes.cs import cs_endpoint
from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_patient
from repositories.cs_repo import ConsultationSpirituelRepository


def test_liste_consultations_expose_le_total_reel(db_session, api_client):
    """L'accueil secretariat comptait les consultations en lisant la
    longueur d'une page bornee a 200 : au-dela, le compteur plafonnait en
    silence. Le total doit venir du serveur."""
    create_test_user(db_session, "cs_admin", "admin")
    db_session.flush()

    client = api_client(cs_endpoint, auth_endpoints)
    headers = auth_headers(client, "cs_admin", "TestPass123!")

    reponse = client.get("/cs/?page=1&per_page=5", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, dict), "une liste nue ne porte aucun total"
    assert "total" in corps
    assert len(corps["data"]) <= 5
    assert corps["total"] >= len(corps["data"])


def test_recherche_cs_filtre_reellement_par_patient(db_session, api_client):
    """Registre J1 : le parametre 'search' etait declare mais jamais
    transmis au controller/repo - la recherche ne filtrait jamais rien."""
    admin = create_test_user(db_session, "cs_recherche_admin", "admin")
    patient_id, patient_data = create_test_patient(
        db_session, admin, first_name="Zephyrine", last_name="Uniquetest"
    )
    db_session.flush()

    repo = ConsultationSpirituelRepository(db_session)
    repo.create(
        {"patient_id": patient_id, "type_consultation": "Spiritual"},
        admin,
    )

    client = api_client(cs_endpoint, auth_endpoints)
    headers = auth_headers(client, "cs_recherche_admin", "TestPass123!")

    reponse_trouvee = client.get("/cs/?search=Zephyrine", headers=headers)
    reponse_absente = client.get("/cs/?search=NomQuiNexistePas", headers=headers)

    assert reponse_trouvee.status_code == 200
    corps_trouve = reponse_trouvee.json()
    assert corps_trouve["total"] >= 1
    assert any(c["patient_id"] == patient_id for c in corps_trouve["data"])
    assert any(c.get("patient_name") == "Zephyrine Uniquetest" for c in corps_trouve["data"])

    corps_absent = reponse_absente.json()
    assert corps_absent["total"] == 0
    assert corps_absent["data"] == []
