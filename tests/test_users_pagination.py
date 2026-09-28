from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import auth_headers, create_test_user


def test_liste_utilisateurs_renvoie_le_total(db_session, api_client):
    """GET /users/ doit exposer le nombre total de comptes : le tableau de
    bord admin lit ce champ. Avant correction, la reponse est une liste nue,
    donc 'Utilisateurs inscrits' affiche toujours 0."""
    create_test_user(db_session, "pagin_users_admin", "admin")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "pagin_users_admin", "TestPass123!")

    reponse = client.get("/users/?page=1&per_page=1", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, dict), "une liste nue ne porte aucun total"
    assert corps["total"] >= 1
    assert len(corps["data"]) == 1


def test_recherche_utilisateurs_respecte_la_pagination(db_session, api_client):
    """Avec un terme de recherche, page et per_page etaient ignores cote
    serveur : la recherche renvoyait tous les resultats d'un coup."""
    create_test_user(db_session, "chercheadmin", "admin")
    for i in range(3):
        create_test_user(db_session, f"cherchecible{i}", "secretaire")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "chercheadmin", "TestPass123!")

    reponse = client.get("/users/?search=cherchecible&page=1&per_page=2", headers=headers)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps["data"]) == 2, "la recherche doit honorer per_page"
    assert corps["total"] >= 3, "le total doit compter tous les resultats, pas la page"


def test_endpoint_recherche_dediee_honore_per_page(db_session, api_client):
    """GET /users/search (l'endpoint de recherche dedie, distinct de /users/)
    plafonnait silencieusement a 50 resultats une fois search_users() devenu
    paginable, sans aucun moyen pour l'appelant d'en demander plus. Il doit
    desormais accepter page/per_page comme /users/."""
    create_test_user(db_session, "chercheadmin_dedie", "admin")
    for i in range(3):
        create_test_user(db_session, f"recherchededie{i}", "secretaire")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "chercheadmin_dedie", "TestPass123!")

    reponse = client.get(
        "/users/search?q=recherchededie&page=1&per_page=2", headers=headers
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert isinstance(corps, list), "cet endpoint garde une liste nue (pas d'enveloppe)"
    assert len(corps) == 2, "per_page doit etre honore, pas seulement le defaut a 50"

    reponse_page2 = client.get(
        "/users/search?q=recherchededie&page=2&per_page=2", headers=headers
    )
    assert reponse_page2.status_code == 200
    assert len(reponse_page2.json()) == 1, "la 2e page doit renvoyer le reste des resultats"


def test_toxicomanager_can_list_users(db_session, api_client):
    """Registre L4a : ToxicoManager est deja normalise par role_required()
    (voir api_backend/backend_app/security/role_map.py) mais le routeur
    /users ne le listait pas encore parmi les roles autorises."""
    create_test_user(db_session, "l4a_toxicomanager_users", "ToxicoManager")
    db_session.flush()

    client = api_client(users_endpoint, auth_endpoints)
    headers = auth_headers(client, "l4a_toxicomanager_users", "TestPass123!")

    reponse = client.get("/users/?page=1&per_page=1", headers=headers)

    assert reponse.status_code == 200
