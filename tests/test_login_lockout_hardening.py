# tests/test_login_lockout_hardening.py
"""Chantier 8, correctifs 5b/6 : rafale parallele, atomicite Redis, liste des utilisateurs,
deverrouillage en panne, changement de mot de passe."""
import os
import sys
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.admin import users_endpoint
from api_backend.backend_app.security import login_lockout
from api_backend.backend_app.security.login_lockout import (
    LoginLockout, MemoryBackend, RedisBackend, MAX_FAILURES, WINDOW_SECONDS,
)
from controller.auth_controller import AuthController
from models.audit import AuditUserAction
from tests.conftest import create_test_user, login, auth_headers

PWD = "Correct123!"
BAD = "WrongPass999!"
OLD_TEXT = "L'ancien mot de passe est incorrect"


@pytest.fixture
def store(monkeypatch):
    s = LoginLockout(MemoryBackend())
    monkeypatch.setattr(login_lockout, "_store", s)
    return s


# ---------------------------------------------------------------- I1 : rafale parallele

def test_correct_password_finishing_after_fifth_failure_is_refused(db_session, api_client, store, monkeypatch):
    """Le bon mot de passe dont la verification a commence AVANT le verrou, mais se termine apres, est refuse."""
    create_test_user(db_session, "hd_burst", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    real = AuthController.authenticate

    def slow_authenticate(self, username, password, **kw):
        user = real(self, username, password, **kw)      # "bcrypt" termine...
        if password == PWD:
            for _ in range(MAX_FAILURES):           # ...pendant que 5 echecs s'enregistrent
                store.register_failure(username)
        return user

    monkeypatch.setattr(AuthController, "authenticate", slow_authenticate)
    resp = login(client, "hd_burst", PWD)
    assert resp.status_code == 401 and resp.json() == {"detail": "Identifiants invalides"}
    assert store.is_locked("hd_burst")


def test_success_while_locked_does_not_reset_counter(db_session, api_client, store, monkeypatch):
    create_test_user(db_session, "hd_noreset", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    resets = []
    monkeypatch.setattr(store, "reset", lambda u: resets.append(u))
    real = AuthController.authenticate

    def auth(self, username, password, **kw):
        user = real(self, username, password, **kw)
        for _ in range(MAX_FAILURES):
            store.register_failure(username)
        return user

    monkeypatch.setattr(AuthController, "authenticate", auth)
    assert login(client, "hd_noreset", PWD).status_code == 401
    assert resets == []


def test_threaded_failures_trigger_exactly_one_lock():
    s = LoginLockout(MemoryBackend())
    results = []
    barrier = threading.Barrier(20)

    def worker():
        barrier.wait()
        results.append(s.register_failure("burst_user"))

    threads = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 1
    assert s.is_locked("burst_user")


def test_failures_during_lock_do_not_relock_after_expiry():
    clock = [0.0]
    s = LoginLockout(MemoryBackend(clock=lambda: clock[0]))
    for _ in range(MAX_FAILURES):
        s.register_failure("late")
    for _ in range(30):                              # rafale pendant le verrou
        s.register_failure("late")
    clock[0] += login_lockout.LOCK_SECONDS + 1
    assert not s.is_locked("late")
    assert s.register_failure("late") is False       # repart de zero


# ---------------------------------------------------------------- I2 : atomicite Redis

class FakeRedis:
    """Implemente seulement ce que le backend doit utiliser. incr/expire separes sont INTERDITS."""

    def __init__(self):
        self.data, self.ttl = {}, {}
        self.fail_eval = False
        self.eval_calls = 0

    def eval(self, script, numkeys, key, ttl):
        self.eval_calls += 1
        if self.fail_eval:                           # panne avant execution : script atomique, rien n'est ecrit
            raise ConnectionError("down")
        self.data[key] = self.data.get(key, 0) + 1
        if self.data[key] == 1 or self.ttl.get(key, -1) < 0:
            self.ttl[key] = int(ttl)
        return self.data[key]

    def incr(self, *a):
        raise AssertionError("incr non atomique interdit")

    def expire(self, *a, **k):
        raise AssertionError("expire separe interdit")


def test_redis_incr_is_one_atomic_script_and_counter_always_has_ttl():
    fake = FakeRedis()
    backend = RedisBackend(fake)
    for _ in range(4):
        backend.incr("login:fail:x", WINDOW_SECONDS)
    assert fake.eval_calls == 4
    assert fake.ttl["login:fail:x"] == WINDOW_SECONDS


def test_redis_failure_never_leaves_counter_without_ttl():
    fake = FakeRedis()
    store = LoginLockout(RedisBackend(fake))
    fake.fail_eval = True
    store.register_failure("pannes")                 # tombe en memoire
    assert fake.data == {}
    fake.fail_eval = False
    store.register_failure("pannes")
    assert all(fake.ttl.get(k, -1) > 0 for k in fake.data)


def _real_redis():
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis
        r = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        r.ping()
        return r
    except Exception:
        return None


@pytest.fixture
def real_redis():
    r = _real_redis()
    if r is None:
        pytest.skip("Redis indisponible")
    yield r
    for k in r.scan_iter(match="login:*hd_real_*"):
        r.delete(k)


def test_real_redis_counter_has_ttl_and_selfheals_missing_ttl(real_redis):
    b = RedisBackend(real_redis)
    key = "login:fail:hd_real_a"
    assert b.incr(key, 600) == 1
    assert 0 < real_redis.ttl(key) <= 600
    real_redis.set(key, 3)                           # compteur orphelin sans TTL (ancien defaut)
    assert real_redis.ttl(key) == -1
    assert b.incr(key, 600) == 4
    assert 0 < real_redis.ttl(key) <= 600


def test_real_redis_lock_flow_and_exists_many(real_redis):
    s = LoginLockout(RedisBackend(real_redis, real_redis))
    for _ in range(MAX_FAILURES):
        s.register_failure("hd_real_b")
    assert s.is_locked("HD_REAL_B")
    assert s.locked_usernames(["hd_real_b", "hd_real_c"]) == {"hd_real_b"}
    s.unlock("hd_real_b")
    assert not s.is_locked("hd_real_b")


# ---------------------------------------------------------------- I3 : liste des utilisateurs

def test_non_admin_never_sees_locked_true(db_session, api_client, store):
    create_test_user(db_session, "hd_mgr", "ToxicoManager", password=PWD)
    create_test_user(db_session, "hd_victim", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    for _ in range(MAX_FAILURES):
        store.register_failure("hd_victim")
    headers = auth_headers(client, "hd_mgr", PWD)
    body = client.get("/users/?per_page=500", headers=headers).json()
    assert all(u["locked"] is False for u in body["data"])


def test_admin_sees_locked_true(db_session, api_client, store):
    create_test_user(db_session, "hd_adm", "admin", password=PWD)
    create_test_user(db_session, "hd_victim2", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    for _ in range(MAX_FAILURES):
        store.register_failure("hd_victim2")
    headers = auth_headers(client, "hd_adm", PWD)
    flags = {u["username"]: u["locked"] for u in client.get("/users/?per_page=500", headers=headers).json()["data"]}
    assert flags["hd_victim2"] is True


class CountingDown:
    def __init__(self):
        self.calls = {}

    def __getattr__(self, name):
        def boom(*a, **k):
            self.calls[name] = self.calls.get(name, 0) + 1
            raise ConnectionError("down")
        return boom


def test_redis_down_list_makes_a_single_backend_call(db_session, api_client, monkeypatch):
    backend = CountingDown()
    monkeypatch.setattr(login_lockout, "_store", LoginLockout(backend))
    create_test_user(db_session, "hd_adm2", "admin", password=PWD)
    for i in range(5):
        create_test_user(db_session, f"hd_many_{i}", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "hd_adm2", PWD)
    backend.calls.clear()                            # on ne compte que la liste, pas le login
    resp = client.get("/users/?per_page=500", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 6
    assert backend.calls.get("exists_many") == 1
    assert "exists" not in backend.calls
    assert all(u["locked"] is False for u in resp.json()["data"])


# ---------------------------------------------------------------- unlock en panne

def test_unlock_backend_failure_returns_503_and_no_audit(db_session, api_client, monkeypatch):
    class FailingDelete(MemoryBackend):
        def delete(self, *keys):
            raise ConnectionError("down")

    monkeypatch.setattr(login_lockout, "_store", LoginLockout(FailingDelete()))
    create_test_user(db_session, "hd_adm3", "admin", password=PWD)
    target = create_test_user(db_session, "hd_t3", "secretaire", password=PWD)
    client = api_client(auth_endpoints, users_endpoint)
    headers = auth_headers(client, "hd_adm3", PWD)
    resp = client.post(f"/users/{target.user_id}/unlock", headers=headers)
    assert resp.status_code == 503
    assert "Deverrouillage impossible" in resp.json()["detail"]
    assert db_session.query(AuditUserAction).filter_by(
        action_performed="UNLOCK", resource_id=target.user_id).count() == 0


# ---------------------------------------------------------------- PUT /auth/password

def _change(client, headers, old):
    return client.put("/auth/password", headers=headers, json={
        "old_password": old, "new_password": "NewPass456!x", "confirm_password": "NewPass456!x"})


def test_wrong_old_password_counts_and_locks_then_refuses(db_session, api_client, store):
    create_test_user(db_session, "hd_pw", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    headers = auth_headers(client, "hd_pw", PWD)
    for _ in range(MAX_FAILURES):
        r = _change(client, headers, BAD)
        assert r.status_code == 400 and r.json()["detail"] == OLD_TEXT
    assert store.is_locked("hd_pw")
    r = _change(client, headers, PWD)                # meme le bon ancien mot de passe
    assert r.status_code == 400 and r.json()["detail"] == OLD_TEXT
    assert login(client, "hd_pw", PWD).status_code == 401   # le login est verrouille aussi


def test_other_password_change_errors_do_not_count(db_session, api_client, store):
    create_test_user(db_session, "hd_pw2", "secretaire", password=PWD)
    client = api_client(auth_endpoints)
    headers = auth_headers(client, "hd_pw2", PWD)
    for _ in range(MAX_FAILURES + 2):               # nouveau == ancien : 400 mais autre message
        r = client.put("/auth/password", headers=headers, json={
            "old_password": PWD, "new_password": PWD, "confirm_password": PWD})
        assert r.status_code == 400
    assert not store.is_locked("hd_pw2")
