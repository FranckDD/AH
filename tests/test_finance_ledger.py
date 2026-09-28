from datetime import datetime

from api_backend.backend_app.routes.finance import finance_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from tests.conftest import auth_headers, create_test_user, create_test_transaction, create_test_retrait


def test_journal_melange_recettes_et_depenses_triees(db_session, api_client):
    """Le journal doit renvoyer un flux unique trie par date decroissante,
    tous sens confondus. Avant : le client paginait les deux sources
    separement puis triait la page courante, donc l'ordre etait faux d'une
    page a l'autre et le total valait la somme de deux totaux."""
    admin = create_test_user(db_session, "journal_admin", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=300.0, advance_amount=300.0,
                            paid_at=datetime(2025, 3, 10, 9, 0))
    create_test_retrait(db_session, admin, amount=50.0,
                        retrait_at=datetime(2025, 3, 11, 9, 0))
    create_test_transaction(db_session, admin, amount=200.0, advance_amount=200.0,
                            paid_at=datetime(2025, 3, 12, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin", "TestPass123!")

    reponse = client.get(
        "/finance/mouvements?date_from=2025-03-10&date_to=2025-03-12&page=1&per_page=10",
        headers=headers,
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] == 3
    sens = [m["sens"] for m in corps["data"]]
    assert sens == ["INCOME", "EXPENSE", "INCOME"], "tri par date decroissante, sens melanges"
    assert corps["data"][0]["amount"] == 200.0


def test_journal_pagine_sur_le_flux_fusionne(db_session, api_client):
    """La pagination doit porter sur le flux fusionne, pas sur chaque source
    separement : la page 2 doit contenir le 3e mouvement, pas un doublon."""
    admin = create_test_user(db_session, "journal_admin2", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=300.0, advance_amount=300.0,
                            paid_at=datetime(2025, 4, 10, 9, 0))
    create_test_retrait(db_session, admin, amount=50.0,
                        retrait_at=datetime(2025, 4, 11, 9, 0))
    create_test_transaction(db_session, admin, amount=200.0, advance_amount=200.0,
                            paid_at=datetime(2025, 4, 12, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin2", "TestPass123!")
    base = "/finance/mouvements?date_from=2025-04-10&date_to=2025-04-12&per_page=2"

    page1 = client.get(f"{base}&page=1", headers=headers).json()
    page2 = client.get(f"{base}&page=2", headers=headers).json()

    assert len(page1["data"]) == 2
    assert len(page2["data"]) == 1
    assert page1["total"] == 3 and page2["total"] == 3
    ids_page1 = {(m["sens"], m["id"]) for m in page1["data"]}
    ids_page2 = {(m["sens"], m["id"]) for m in page2["data"]}
    assert ids_page1.isdisjoint(ids_page2), "aucun mouvement ne doit apparaitre deux fois"


def test_journal_filtre_par_categorie_sur_tout_le_flux(db_session, api_client):
    """Le filtre categorie doit s'appliquer en base, pas sur la page deja
    chargee : sinon il ne voit qu'une quarantaine de lignes."""
    admin = create_test_user(db_session, "journal_admin3", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=100.0, advance_amount=100.0,
                            transaction_type="Consultation",
                            paid_at=datetime(2025, 5, 10, 9, 0))
    create_test_transaction(db_session, admin, amount=100.0, advance_amount=100.0,
                            transaction_type="Pharmacie",
                            paid_at=datetime(2025, 5, 11, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin3", "TestPass123!")

    corps = client.get(
        "/finance/mouvements?date_from=2025-05-10&date_to=2025-05-11&category=Consultation",
        headers=headers,
    ).json()

    assert corps["total"] == 1
    assert corps["data"][0]["category"] == "Consultation"


def test_journal_recherche_par_nom_patient(db_session, api_client):
    """Le module Finance recherche desormais sur GET /finance/mouvements
    (journal unifie), pas sur l'ancien endpoint caisse. La recherche par
    nom de patient doit donc fonctionner ici aussi : Task 6 avait etendu
    caisse_repo.search_transactions au patient_label, mais _flux_unifie()
    ne projetait pas du tout cette colonne - une recherche patient
    retournait 0 resultat alors que la transaction existe bel et bien."""
    admin = create_test_user(db_session, "journal_admin4", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=150.0, advance_amount=150.0,
                            patient_label="Nom Unique Test",
                            paid_at=datetime(2025, 6, 10, 9, 0))
    create_test_transaction(db_session, admin, amount=150.0, advance_amount=150.0,
                            patient_label="Autre Personne",
                            paid_at=datetime(2025, 6, 11, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin4", "TestPass123!")

    corps = client.get(
        "/finance/mouvements?date_from=2025-06-10&date_to=2025-06-11&search=Nom+Unique+Test",
        headers=headers,
    ).json()

    assert corps["total"] == 1, "la recherche doit trouver la transaction par nom de patient"
    assert corps["data"][0]["amount"] == 150.0


def test_totaux_kpi_respectent_le_filtre_categorie(db_session, api_client):
    """Les cartes KPI (GET /finance/totaux) doivent refleter exactement le
    meme filtrage que la liste (GET /finance/mouvements) : filtrer par
    categorie sur la liste doit aussi restreindre le total 'income' affiche
    dans les cartes, sinon la carte montre un chiffre pour une periode
    filtree qui ne correspond plus a la liste juste en dessous."""
    admin = create_test_user(db_session, "journal_admin5", "admin")
    db_session.flush()

    create_test_transaction(db_session, admin, amount=100.0, advance_amount=100.0,
                            transaction_type="Consultation",
                            paid_at=datetime(2025, 7, 10, 9, 0))
    create_test_transaction(db_session, admin, amount=250.0, advance_amount=250.0,
                            transaction_type="Pharmacie",
                            paid_at=datetime(2025, 7, 11, 9, 0))
    db_session.flush()

    client = api_client(finance_endpoints, auth_endpoints)
    headers = auth_headers(client, "journal_admin5", "TestPass123!")

    corps = client.get(
        "/finance/totaux?date_from=2025-07-10&date_to=2025-07-11&category=Consultation",
        headers=headers,
    ).json()

    assert corps["income"] == 100.0, "le total ne doit compter que la transaction Consultation"
    assert corps["expense"] == 0.0
