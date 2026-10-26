"""Releve B : l'historique des connexions s'etait arrete (log_access ajoute a la session sans jamais etre valide)."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.routes.auth import auth_endpoints
from models.audit import AuditAccess
from tests.conftest import create_test_user, login

PWD = "Correct123!"


def _rows(db_session, **flt):
    db_session.expire_all()
    return db_session.query(AuditAccess).filter_by(**flt).all()


def test_successful_login_is_recorded(db_session, api_client):
    u = create_test_user(db_session, "aud_ok", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    assert login(client, "aud_ok", PWD).status_code == 200
    rows = _rows(db_session, user_id=u.user_id, action_type="LOGIN_SUCCESS")
    assert len(rows) == 1


def test_wrong_password_is_recorded_with_reason(db_session, api_client):
    u = create_test_user(db_session, "aud_bad", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    assert login(client, "aud_bad", "nope").status_code == 401
    rows = _rows(db_session, user_id=u.user_id, action_type="LOGIN_FAILURE")
    assert len(rows) == 1 and "mot de passe" in rows[0].details.lower()


def test_inactive_account_logged_server_side_but_same_user_message(db_session, api_client):
    u = create_test_user(db_session, "aud_off", "secretaire", password=PWD, is_active=False)
    client = api_client(auth_endpoints)
    r = login(client, "aud_off", PWD)
    assert r.status_code == 401 and r.json()["detail"] == "Identifiants invalides"
    rows = _rows(db_session, user_id=u.user_id, action_type="LOGIN_FAILURE")
    assert len(rows) == 1 and "desactive" in rows[0].details.lower()


def test_logout_is_recorded(db_session, api_client):
    u = create_test_user(db_session, "aud_out", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    token = login(client, "aud_out", PWD).json()["access_token"]
    assert client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert len(_rows(db_session, user_id=u.user_id, action_type="LOGOUT")) == 1


def test_login_audit_row_is_committed_not_just_added(db_session, api_client, monkeypatch):
    """Cause racine : sans commit la ligne d'audit etait perdue a la fermeture de la session de la requete."""
    create_test_user(db_session, "aud_commit", "secretaire", password=PWD)
    calls = []
    real_commit = db_session.commit
    monkeypatch.setattr(db_session, "commit", lambda: (calls.append(1), real_commit())[1])
    client = api_client(auth_endpoints)
    assert login(client, "aud_commit", PWD).status_code == 200
    assert calls, "la ligne LOGIN_SUCCESS doit etre validee (commit)"
