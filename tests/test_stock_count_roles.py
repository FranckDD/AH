# tests/test_stock_count_roles.py
"""Comptage du stock (tache 3) : matrice roles x routes de /stock-counts.

La liste des routes est DERIVEE de l'application reelle (une route oubliee casse
test_routes_table_covers_router). get_current_user est surcharge avec un vrai
utilisateur de la base ; un test final fait 2 VRAIES connexions (limite 5/min).
"""
import re

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.stock_count import stock_count_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("StockController", "admin", "promoteur", "manager", "Assistant", "secretaire", "ProductionManager",
         "medecin", "nurse", "laborantin", "ToxicoManager", "Psychologist", "SpiritualCounsellor")
# manager : role canonique sans ligne application_roles (seme sous Assistant puis user.roles force)
NO_DB_ROW = {"manager": "Assistant"}
READ_OK = {"StockController", "admin", "promoteur"}
WRITE_OK = {"StockController"}  # admin : un comptage d admin serait inapprouvable
ADMIN_OK = {"admin"}
BIG = 987654321
READ, WRITE, ADMIN = "read", "write", "admin"

ROUTES = {
    ("POST", "/stock-counts"): (WRITE, {}),
    ("POST", "/stock-counts/{count_id}/submit"): (WRITE, {"lines": [{"product_id": 1, "counted_qty": 0}]}),
    ("POST", "/stock-counts/{count_id}/abandon"): (WRITE, None),
    ("GET", "/stock-counts/status"): (READ, None),
    ("GET", "/stock-counts/settings"): (READ, None),
    ("PUT", "/stock-counts/settings"): (ADMIN, {}),
    ("GET", "/stock-counts"): (READ, None),
    ("GET", "/stock-counts/{count_id}"): (READ, None),
}


def _router_routes():
    out = set()
    for r in app.routes:
        path = getattr(r, "path", "")
        if path == "/stock-counts" or path.startswith("/stock-counts/"):
            for m in (r.methods or ()):
                if m not in ("HEAD", "OPTIONS"):
                    out.add((m, path))
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
    users = {r: create_test_user(db_session, f"t_scrole_{r.lower()}", NO_DB_ROW.get(r, r), password=PWD)
             for r in ROLES}
    client = api_client(auth_endpoints, ep)
    return {"db": db_session, "client": client, "users": users}


def _call(client, method, path, body, **kw):
    if body is not None:
        kw["json"] = body
    return client.request(method, _url(path), **kw)


def test_routes_table_covers_router():
    assert _router_routes() == set(ROUTES), sorted(_router_routes() ^ set(ROUTES))


def test_role_constants():
    assert set(ep.READERS) == READ_OK
    assert set(ep.COUNTERS) == WRITE_OK
    assert set(ep.SETTINGS_WRITERS) == ADMIN_OK


def test_no_collision_with_stock_router():
    stock = {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "").startswith("/stock/")}
    assert stock and not any(p.startswith("/stock-counts") for p in stock)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    kind, body = ROUTES[route]
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r = _call(env["client"], route[0], route[1], body)
    allowed = {READ: READ_OK, WRITE: WRITE_OK, ADMIN: ADMIN_OK}[kind]
    if role in allowed:
        assert r.status_code not in (401, 403) and r.status_code < 500, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


def test_unauthenticated_refused(env):
    for route in sorted(ROUTES):
        r = _call(env["client"], route[0], route[1], ROUTES[route][1])
        assert r.status_code == 401, (route, r.status_code)


def test_real_login_wiring(env):
    """2 vraies connexions : le jeton StockController ouvre /stock-counts, celui du secretaire non."""
    c = env["client"]
    h_sc = auth_headers(c, "t_scrole_stockcontroller", PWD)
    h_sec = auth_headers(c, "t_scrole_secretaire", PWD)
    assert c.get("/stock-counts/status", headers=h_sc).status_code == 200
    assert c.get("/stock-counts/status", headers=h_sec).status_code == 403
    assert c.post("/stock-counts", json={}, headers=h_sec).status_code == 403
    r = c.post("/stock-counts", json={}, headers=h_sc)
    assert r.status_code == 201, r.text
    # en dernier : le 404 du controleur annule la transaction de test
    assert c.get(f"/stock-counts/{BIG}", headers=h_sc).status_code == 404
