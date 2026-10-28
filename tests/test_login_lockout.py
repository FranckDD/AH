# tests/test_login_lockout.py
"""Chantier 8, tache 5b : verrouillage de compte, limite par IP a 60/minute, deverrouillage admin."""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.security import login_lockout
from api_backend.backend_app.security.login_lockout import (
    LoginLockout, MemoryBackend, MAX_FAILURES, WINDOW_SECONDS, LOCK_SECONDS, LOGIN_IP_LIMIT,
)
from models.audit import AuditAccess, AuditUserAction
from tests.conftest import create_test_user, login, auth_headers

PWD = "Correct123!"
BAD = "WrongPass999!"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    """Remplace le stockage global par un stockage memoire a horloge controlee."""
    c = FakeClock()
    monkeypatch.setattr(login_lockout, "_store", LoginLockout(MemoryBackend(clock=c)))
    return c


def _fail(client, username, n=1):
    last = None
    for _ in range(n):
        last = login(client, username, BAD)
    return last


def _lock_audits(db_session, user_id):
    return db_session.query(AuditAccess).filter_by(user_id=user_id, action_type="ACCOUNT_LOCKED").all()


def test_constants_documented_values():
    assert (MAX_FAILURES, WINDOW_SECONDS, LOCK_SECONDS, LOGIN_IP_LIMIT) == (5, 600, 600, "60/minute")


def test_five_failures_lock_and_correct_password_is_refused_identically(db_session, api_client, clock):
    create_test_user(db_session, "lk_basic", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    wrong = _fail(client, "lk_basic", MAX_FAILURES)
    assert wrong.status_code == 401
    right_but_locked = login(client, "lk_basic", PWD)
    assert right_but_locked.status_code == wrong.status_code == 401
    assert right_but_locked.json() == wrong.json() == {"detail": "Identifiants invalides"}
    assert dict(right_but_locked.headers).get("www-authenticate") == dict(wrong.headers).get("www-authenticate")


def test_fourth_failure_does_not_lock(db_session, api_client, clock):
    create_test_user(db_session, "lk_four", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    _fail(client, "lk_four", MAX_FAILURES - 1)
    assert login(client, "lk_four", PWD).status_code == 200


def test_success_resets_counter(db_session, api_client, clock):
    create_test_user(db_session, "lk_reset", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    _fail(client, "lk_reset", MAX_FAILURES - 1)
    assert login(client, "lk_reset", PWD).status_code == 200
    _fail(client, "lk_reset", MAX_FAILURES - 1)  # 4 de nouveau : pas de verrou
    assert login(client, "lk_reset", PWD).status_code == 200


def test_failures_spread_over_more_than_window_do_not_lock(db_session, api_client, clock):
    create_test_user(db_session, "lk_spread", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    _fail(client, "lk_spread", 3)
    clock.advance(WINDOW_SECONDS + 1)
    _fail(client, "lk_spread", 3)  # 3 + 3 mais fenetre expiree : jamais 5 dans la fenetre
    assert login(client, "lk_spread", PWD).status_code == 200


def test_lock_expires_after_lock_duration(db_session, api_client, clock):
    create_test_user(db_session, "lk_expire", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    _fail(client, "lk_expire", MAX_FAILURES)
    assert login(client, "lk_expire", PWD).status_code == 401
    clock.advance(LOCK_SECONDS - 1)
    assert login(client, "lk_expire", PWD).status_code == 401
    clock.advance(2)
    assert login(client, "lk_expire", PWD).status_code == 200


def test_username_is_normalised_case_insensitively(db_session, api_client, clock):
    create_test_user(db_session, "lk_case", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    for name in ["LK_CASE", "lk_case", "Lk_Case ", "lk_CASE", "LK_case"]:
        login(client, name, BAD)
    assert login(client, "lk_case", PWD).status_code == 401


def test_unknown_usernames_are_counted_with_same_generic_response_and_no_audit(db_session, api_client, clock):
    client = api_client(auth_endpoints)
    before = db_session.query(AuditAccess).filter_by(action_type="ACCOUNT_LOCKED").count()
    responses = [login(client, "lk_ghost_user", BAD) for _ in range(MAX_FAILURES + 1)]
    assert all(r.status_code == 401 and r.json() == {"detail": "Identifiants invalides"} for r in responses)
    assert login_lockout.get_store().is_locked("lk_ghost_user") is True
    assert db_session.query(AuditAccess).filter_by(action_type="ACCOUNT_LOCKED").count() == before


def test_one_audit_entry_per_lock_event_and_no_password(db_session, api_client, clock):
    user = create_test_user(db_session, "lk_audit", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    _fail(client, "lk_audit", MAX_FAILURES)
    login(client, "lk_audit", PWD)
    _fail(client, "lk_audit", 3)  # tentatives sur compte deja verrouille : pas d'audit
    rows = _lock_audits(db_session, user.user_id)
    assert len(rows) == 1
    assert BAD not in (rows[0].details or "") and PWD not in (rows[0].details or "")
    # tentatives bloquees : aucune ligne LOGIN_FAILURE supplementaire apres le verrouillage
    failures = db_session.query(AuditAccess).filter_by(user_id=user.user_id, action_type="LOGIN_FAILURE").count()
    assert failures == MAX_FAILURES
    # nouveau verrouillage apres expiration : une deuxieme ligne
    clock.advance(LOCK_SECONDS + 1)
    _fail(client, "lk_audit", MAX_FAILURES)
    assert len(_lock_audits(db_session, user.user_id)) == 2


def test_admin_unlock_allowed_unlocks_immediately_and_audits(db_session, api_client, clock):
    admin = create_test_user(db_session, "lk_admin", "admin", password=PWD)
    target = create_test_user(db_session, "lk_target", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "lk_admin", PWD)
    _fail(client, "lk_target", MAX_FAILURES)
    assert login(client, "lk_target", PWD).status_code == 401

    resp = client.post(f"/users/{target.user_id}/unlock", headers=headers)
    assert resp.status_code == 204
    assert login(client, "lk_target", PWD).status_code == 200
    audit = db_session.query(AuditUserAction).filter_by(
        resource_type="User", action_performed="UNLOCK", resource_id=target.user_id).all()
    assert len(audit) == 1 and audit[0].user_id == admin.user_id
    assert PWD not in str(audit[0].new_values)


def test_unlock_counter_is_cleared_too(db_session, api_client, clock):
    create_test_user(db_session, "lk_admin2", "admin", password=PWD)
    target = create_test_user(db_session, "lk_target2", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "lk_admin2", PWD)
    _fail(client, "lk_target2", MAX_FAILURES)
    client.post(f"/users/{target.user_id}/unlock", headers=headers)
    _fail(client, "lk_target2", MAX_FAILURES - 1)  # repart de zero
    assert login(client, "lk_target2", PWD).status_code == 200


def test_unlock_forbidden_for_other_roles(db_session, api_client, clock):
    create_test_user(db_session, "lk_sec", "secretaire", password=PWD)
    target = create_test_user(db_session, "lk_target3", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "lk_sec", PWD)
    assert client.post(f"/users/{target.user_id}/unlock", headers=headers).status_code == 403


def test_unlock_unknown_user_is_404(db_session, api_client, clock):
    create_test_user(db_session, "lk_admin3", "admin", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "lk_admin3", PWD)
    assert client.post("/users/999999999/unlock", headers=headers).status_code == 404


def test_user_list_flags_locked_accounts(db_session, api_client, clock):
    create_test_user(db_session, "lk_admin4", "admin", password=PWD)
    create_test_user(db_session, "lk_locked4", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "lk_admin4", PWD)
    _fail(client, "lk_locked4", MAX_FAILURES)
    body = client.get("/users/?per_page=500", headers=headers).json()
    flags = {u["username"]: u["locked"] for u in body["data"]}
    assert flags["lk_locked4"] is True
    assert flags["lk_admin4"] is False


def test_ip_limit_is_60_per_minute_and_lockout_does_not_interfere(db_session, api_client, clock):
    client = api_client(auth_endpoints)
    statuses = [login(client, f"lk_nobody_{i}", BAD).status_code for i in range(60)]
    assert set(statuses) == {401}
    assert login(client, "lk_nobody_61", BAD).status_code == 429


def test_memory_fallback_when_redis_url_unset():
    store = login_lockout.build_store(None)
    assert isinstance(store._backend, MemoryBackend)
    for _ in range(MAX_FAILURES - 1):
        assert store.register_failure("Fallback_User") is False
    assert store.register_failure("fallback_user") is True
    assert store.is_locked("FALLBACK_USER")
    store.unlock("fallback_user")
    assert not store.is_locked("fallback_user")


def test_unreachable_redis_fails_open_and_falls_back():
    class Broken:
        def __getattr__(self, name):
            def boom(*a, **k):
                raise ConnectionError("down")
            return boom

    store = LoginLockout(Broken())
    assert store.is_locked("anyone") is False
    for _ in range(MAX_FAILURES - 1):
        assert store.register_failure("anyone") is False
    assert store.register_failure("anyone") is True
    assert store.is_locked("anyone") is True
    assert store.locked_usernames(["anyone", "other"]) == {"anyone"}


def test_audit_rows_carry_client_ip_and_never_a_password(db_session, api_client, clock):
    """Chantier 8, correctif tache 7 : succes, echecs (compte connu et inconnu) et verrouillage
    enregistrent l'IP du client (TestClient : 'testclient'), sans mot de passe ni revelation."""
    user = create_test_user(db_session, "lk_ip", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    assert login(client, "lk_ip", PWD).status_code == 200
    login(client, "inconnu_ip_xyz", BAD)
    _fail(client, "lk_ip", MAX_FAILURES)
    rows = db_session.query(AuditAccess).filter(
        (AuditAccess.user_id == user.user_id) | (AuditAccess.details.like("%inconnu_ip_xyz%"))).all()
    kinds = {r.action_type for r in rows}
    assert {"LOGIN_SUCCESS", "LOGIN_FAILURE", "ACCOUNT_LOCKED"} <= kinds
    assert rows and all(r.ip_address == "testclient" for r in rows)
    assert all(PWD not in (r.details or "") and BAD not in (r.details or "") for r in rows)
    unknown = [r for r in rows if "inconnu_ip_xyz" in (r.details or "")]
    assert unknown and unknown[0].user_id is None
