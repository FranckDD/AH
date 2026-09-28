from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.caisse import caisse_endpoints
from api_backend.backend_app.routes.retrait import retrait_endpoints
from tests.conftest import create_test_user, auth_headers

TEST_PASSWORD = "TestPass123!"


def test_create_transaction_avec_uuid_client_le_persiste(db_session, api_client):
    """Chantier 4 sous-projet 3 : une transaction caisse creee hors ligne
    (PowerSync) fournit son propre uuid - le serveur doit le persister tel
    quel, jamais en generer un nouveau."""
    secretaire = create_test_user(db_session, "test_caisse_uuid_secretaire", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_uuid_secretaire", TEST_PASSWORD)

    client_uuid = "aaaaaaaa-1111-2222-3333-444444444444"
    resp = client.post("/caisse/", json={
        "amount": 50.0,
        "advance_amount": 50.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 50.0, "quantity": 1, "line_total": 50.0}],
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid


def test_create_transaction_sans_uuid_en_genere_un(db_session, api_client):
    """Non-regression : la creation en ligne (aucun uuid fourni) continue
    de fonctionner, Postgres genere le uuid comme avant ce chantier."""
    secretaire = create_test_user(db_session, "test_caisse_uuid_secretaire2", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, caisse_endpoints)
    headers = auth_headers(client, "test_caisse_uuid_secretaire2", TEST_PASSWORD)

    resp = client.post("/caisse/", json={
        "amount": 30.0,
        "advance_amount": 30.0,
        "payment_method": "Especes",
        "transaction_type": "Consultation",
        "items": [{"item_type": "Service", "item_ref_id": 0, "unit_price": 30.0, "quantity": 1, "line_total": 30.0}],
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] is not None


def test_create_retrait_avec_uuid_client_le_persiste(db_session, api_client):
    secretaire = create_test_user(db_session, "test_retrait_uuid_secretaire", "secretaire", password=TEST_PASSWORD)
    client = api_client(auth_endpoints, retrait_endpoints)
    headers = auth_headers(client, "test_retrait_uuid_secretaire", TEST_PASSWORD)

    client_uuid = "bbbbbbbb-1111-2222-3333-444444444444"
    resp = client.post("/retrait/", json={
        "amount": 20.0,
        "justification": "Test retrait uuid",
        "uuid": client_uuid,
    }, headers=headers)

    assert resp.status_code == 201, resp.text
    assert resp.json()["uuid"] == client_uuid
