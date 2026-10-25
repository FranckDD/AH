# tests/test_reports_roles.py
"""Rapports (tache 6) : matrice roles x routes de /reports.

La liste des routes est DERIVEE de l'application reelle (une route /reports oubliee casse
test_routes_table_covers_router). get_current_user est surcharge avec un vrai utilisateur ;
un test final fait 2 VRAIES connexions (limite 5/min).
"""
import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.reports import reports_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("admin", "promoteur", "manager", "Assistant", "secretaire", "StockController",
         "ProductionManager", "medecin", "nurse", "laborantin", "ToxicoManager", "Psychologist",
         "SpiritualCounsellor")
NO_DB_ROW = {"manager": "Assistant"}
READ_OK = {"promoteur", "admin"}
ADMIN_OK = {"admin"}
READ, ADMIN = "read", "admin"
SETTINGS = {"cancelled_sales_threshold": 3, "adjustment_pending_days": 3}

ROUTES = {
    ("GET", "/reports/overview"): (READ, None),
    ("GET", "/reports/daily-control"): (READ, None),
    ("GET", "/reports/products-sold"): (READ, None),
    ("GET", "/reports/settings"): (READ, None),
    ("GET", "/reports/export.pdf"): (READ, None),
    ("PUT", "/reports/settings"): (ADMIN, SETTINGS),
}


def _router_routes():
    out = set()
    for r in app.routes:
        path = getattr(r, "path", "")
        if path == "/reports" or path.startswith("/reports/"):
            for m in (r.methods or ()):
                if m not in ("HEAD", "OPTIONS"):
                    out.add((m, path))
    return out


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
    users = {r: create_test_user(db_session, f"t_rprole_{r.lower()}", NO_DB_ROW.get(r, r), password=PWD)
             for r in ROLES}
    return {"db": db_session, "client": api_client(auth_endpoints, ep), "users": users}


def _call(client, method, path, body, **kw):
    if body is not None:
        kw["json"] = body
    return client.request(method, path, **kw)


def test_routes_table_covers_router():
    assert _router_routes() == set(ROUTES), sorted(_router_routes() ^ set(ROUTES))


def test_role_constants():
    assert set(ep.READERS) == READ_OK
    assert set(ep.SETTINGS_WRITERS) == ADMIN_OK


def test_no_parametric_route_and_no_prefix_collision():
    paths = {p for _, p in _router_routes()}
    assert not any("{" in p for p in paths)
    others = {getattr(r, "path", "") for r in app.routes} - paths
    assert not any(p.startswith("/reports") for p in others)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    kind, body = ROUTES[route]
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r = _call(env["client"], route[0], route[1], body)
    allowed = {READ: READ_OK, ADMIN: ADMIN_OK}[kind]
    if role in allowed:
        assert r.status_code == 200, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


def test_unauthenticated_refused(env):
    for route in sorted(ROUTES):
        r = _call(env["client"], route[0], route[1], ROUTES[route][1])
        assert r.status_code == 401, (route, r.status_code)


def test_real_login_wiring(env):
    """2 vraies connexions : le jeton promoteur lit /reports, celui du secretaire non."""
    c = env["client"]
    h_p = auth_headers(c, "t_rprole_promoteur", PWD)
    h_s = auth_headers(c, "t_rprole_secretaire", PWD)
    assert c.get("/reports/settings", headers=h_p).status_code == 200
    assert c.get("/reports/settings", headers=h_s).status_code == 403
    assert c.put("/reports/settings", json=SETTINGS, headers=h_p).status_code == 403
