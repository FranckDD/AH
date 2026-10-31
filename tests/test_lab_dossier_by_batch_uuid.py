# tests/test_lab_dossier_by_batch_uuid.py
"""GET /labo/batch-uuid/{batch_uuid}/dossier : le numero de dossier attribue par le serveur a un passage recu
hors ligne (batch_uuid du client), lu apres la synchronisation pour l'afficher a la reception."""
import uuid

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints
from tests.conftest import auth_headers, create_test_user
from tests.test_lab_pdf_routes import PWD, _exam, _setup, _validated


def _client(api_client, username):
    client = api_client(auth_endpoints, lab_endpoints)
    return client, auth_headers(client, username, PWD)


def test_dossier_du_passage_lu_par_batch_uuid(db_session, api_client):
    lab, pid = _setup(db_session, "bu")
    ex, params = _exam(db_session, "bu", "table", ["Param bu"])
    batch_uuid = str(uuid.uuid4())
    r, _ = _validated(db_session, pid, lab, ex, params, validate=False)
    r.batch_uuid = batch_uuid
    db_session.flush()
    client, headers = _client(api_client, "pr_bu")
    body = client.get(f"/labo/batch-uuid/{batch_uuid}/dossier", headers=headers).json()
    assert body["dossier"] and " du " in body["dossier"] and "/" in body["dossier"]


def test_pas_de_numero_tant_que_le_lot_n_est_pas_synchronise(db_session, api_client):
    _setup(db_session, "bn")
    client, headers = _client(api_client, "pr_bn")
    resp = client.get(f"/labo/batch-uuid/{uuid.uuid4()}/dossier", headers=headers)
    assert resp.status_code == 200 and resp.json() == {"dossier": None}


def test_lot_sans_numero_donne_none_et_roles_refuses(db_session, api_client):
    lab, pid = _setup(db_session, "bs")
    ex, params = _exam(db_session, "bs", "table", ["Param bs"])
    batch_uuid = str(uuid.uuid4())
    r, _ = _validated(db_session, pid, lab, ex, params, dossier=False, validate=False)
    r.batch_uuid = batch_uuid
    db_session.flush()
    client, headers = _client(api_client, "pr_bs")
    assert client.get(f"/labo/batch-uuid/{batch_uuid}/dossier", headers=headers).json() == {"dossier": None}
    create_test_user(db_session, "pr_bs_sec", "secretaire", password=PWD)
    sec = auth_headers(client, "pr_bs_sec", PWD)
    assert client.get(f"/labo/batch-uuid/{batch_uuid}/dossier", headers=sec).status_code == 403
    assert client.get(f"/labo/batch-uuid/{batch_uuid}/dossier").status_code in (401, 403)
