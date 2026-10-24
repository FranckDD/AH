# tests/test_cash_closure_roles.py
"""Cloture de caisse, tache 5 : matrice roles x routes de /cash-closure et /payment-modes.

La table des routes est comparee aux routes reelles de l'application (une route oubliee casse
test_routes_table_covers_router). Un test final fait 2 VRAIES connexions (limite 5/min).
"""
import re

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.cash_closure import cash_closure_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from tests.conftest import auth_headers, create_test_user
from tests.cash_closure_isolation import clean_register, reset_register  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_register")


PWD = "TestPass123!"
ROLES = ("secretaire", "promoteur", "admin", "Assistant", "StockController", "ProductionManager",
         "medecin", "nurse", "laborantin", "ToxicoManager", "Psychologist", "SpiritualCounsellor")
BIG = 987654321

READ, CLOSE, START, MODES_W, CORR_REQ, CORR_ADM = (
    "read", "close", "start", "modes_w", "corr_req", "corr_adm")
ALLOWED = {
    READ: {"secretaire", "promoteur", "admin"},
    CLOSE: {"secretaire"},
    START: {"admin"},
    MODES_W: {"admin"},
    CORR_REQ: {"secretaire"},
    CORR_ADM: {"promoteur", "admin"},
}

# (methode, chemin) -> (famille, corps). Corps vides : une route permise repond 422/404,
# jamais 403, et n'ecrit rien.
ROUTES = {
    ("GET", "/cash-closure/status"): (READ, None),
    ("GET", "/cash-closure"): (READ, None),
    ("GET", "/cash-closure/{closure_id}"): (READ, None),
    ("POST", "/cash-closure"): (CLOSE, {}),
    ("POST", "/cash-closure/start"): (START, {}),
    ("POST", "/cash-closure/catchup"): (READ, None),
    ("POST", "/cash-closure/{closure_id}/corrections"): (CORR_REQ, {}),
    ("GET", "/cash-closure/corrections"): (CORR_ADM, None),
    ("POST", "/cash-closure/corrections/{correction_id}/decide"): (CORR_ADM, {}),
    ("GET", "/payment-modes"): (READ, None),
    ("PUT", "/payment-modes/{code}"): (MODES_W, {}),
}


def _app_routes():
    out = set()
    for r in app.routes:
        p = getattr(r, "path", "")
        if p in ("/cash-closure", "/payment-modes") or p.startswith(("/cash-closure/", "/payment-modes/")):
            for m in (r.methods or ()):
                if m not in ("HEAD", "OPTIONS"):
                    out.add((m, p))
    return out


def _url(path):
    return re.sub(r"\{[^}]+\}", str(BIG), path)


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    import tests.conftest as cf
    real = cf.pwd_context
    cache = {}

    class _Ctx:
        def hash(self, pw):
            if pw not in cache:
                cache[pw] = real.hash(pw)
            return cache[pw]

        def __getattr__(self, name):
            return getattr(real, name)

    mp = pytest.MonkeyPatch()
    mp.setattr(cf, "pwd_context", _Ctx())
    yield
    mp.undo()


@pytest.fixture
def env(db_session, api_client):
    users = {r: create_test_user(db_session, f"t_ccrole_{r.lower()}", r, password=PWD) for r in ROLES}
    client = api_client(auth_endpoints, ep)
    return {"db": db_session, "client": client, "users": users}


def _call(client, method, path, body):
    kw = {"json": body} if body is not None else {}
    return client.request(method, _url(path), **kw)


def test_routes_table_covers_router():
    assert _app_routes() == set(ROUTES), sorted(_app_routes() ^ set(ROUTES))


def test_role_constants():
    assert set(ep.READERS) == ALLOWED[READ]
    assert set(ep.CLOSERS) == ALLOWED[CLOSE]
    assert set(ep.ADMINS) == ALLOWED[START] == ALLOWED[MODES_W]
    assert set(ep.CORRECTION_REQUESTERS) == ALLOWED[CORR_REQ]
    assert set(ep.CORRECTION_DECIDERS) == ALLOWED[CORR_ADM]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    kind, body = ROUTES[route]
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r = _call(env["client"], route[0], route[1], body)
    if role in ALLOWED[kind]:
        assert r.status_code not in (401, 403) and r.status_code < 500, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


def test_unauthenticated_refused(env):
    for route in sorted(ROUTES):
        r = _call(env["client"], route[0], route[1], ROUTES[route][1])
        assert r.status_code == 401, (route, r.status_code)


def test_real_login_wiring(env):
    """2 vraies connexions : le jeton secretaire ouvre le statut, celui du medecin non."""
    c = env["client"]
    h_sec = auth_headers(c, "t_ccrole_secretaire", PWD)
    h_med = auth_headers(c, "t_ccrole_medecin", PWD)
    assert c.get("/cash-closure/status", headers=h_sec).status_code == 200
    assert c.get("/cash-closure/status", headers=h_med).status_code == 403
