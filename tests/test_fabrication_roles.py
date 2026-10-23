# tests/test_fabrication_roles.py
"""Task 7 (Fabrication) : matrice roles x routes de /fabrication + absence de fuite de couts.

La liste des routes est DERIVEE du routeur reel (une future route oubliee casse
test_routes_table_covers_router). get_current_user est surcharge avec un vrai
utilisateur de la base ; un test final fait 2 VRAIES connexions (limite 5/min).
"""
import re
import uuid

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.routes.pharmacy import pharmacy_endpoints
from api_backend.backend_app.routes.stock import stock_endpoints
from models.pharmacy import Pharmacy
from api_backend.backend_app.security.role_map import normalize_role_name
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("ProductionManager", "promoteur", "admin", "Assistant", "StockController", "secretaire",
         "medecin", "nurse", "laborantin", "ToxicoManager", "Psychologist")
READ_OK = {"ProductionManager", "promoteur", "admin"}
WRITE_OK = {"ProductionManager"}
ADMIN_OK = {"admin"}
BIG = 987654321  # identifiant inexistant : une route acceptee repond 404/422, jamais 403

READ, WRITE, ADMIN = "read", "write", "admin"

# (methode, chemin du routeur) -> (famille, corps)
ROUTES = {
    ("GET", "/fabrication/intrants"): (READ, None),
    ("POST", "/fabrication/intrants"): (WRITE, {}),
    ("PUT", "/fabrication/intrants/{intrant_id}"): (WRITE, {}),
    ("PUT", "/fabrication/intrants/{intrant_id}/threshold"): (ADMIN, {"value": "1"}),
    ("GET", "/fabrication/purchases"): (READ, None),
    ("POST", "/fabrication/purchases"): (WRITE, {}),
    ("PUT", "/fabrication/purchases/{purchase_id}"): (WRITE, {}),
    ("POST", "/fabrication/purchases/{purchase_id}/cancel"): (WRITE, {"reason": "x"}),
    ("GET", "/fabrication/batches"): (READ, None),
    ("POST", "/fabrication/batches"): (WRITE, {}),
    ("GET", "/fabrication/batches/{batch_id}"): (READ, None),
    ("PUT", "/fabrication/batches/{batch_id}"): (WRITE, {}),
    ("POST", "/fabrication/batches/{batch_id}/start"): (WRITE, None),
    ("POST", "/fabrication/batches/{batch_id}/finish"): (WRITE, {}),
    ("POST", "/fabrication/batches/{batch_id}/reopen"): (WRITE, None),
    ("POST", "/fabrication/batches/{batch_id}/cancel"): (WRITE, {"reason": "x"}),
    ("POST", "/fabrication/batches/{batch_id}/ship"): (WRITE, {}),
    ("GET", "/fabrication/settings"): (READ, None),
    ("PUT", "/fabrication/settings"): (ADMIN, {}),
    ("GET", "/fabrication/anomalies"): (READ, None),
    ("GET", "/fabrication/summary"): (READ, None),
    ("GET", "/fabrication/products"): (READ, None),
    ("GET", "/fabrication/products/{product_id}/cost"): (READ, None),
    ("GET", "/fabrication/trace/production-lot/{production_lot_id}"): (READ, None),
}


def _router_routes():
    out = set()
    for r in app.routes:
        path = getattr(r, "path", "")
        if path == "/fabrication" or path.startswith("/fabrication/"):
            for m in (r.methods or ()):
                if m not in ("HEAD", "OPTIONS"):
                    out.add((m, path))
    return out


def _url(path):
    return re.sub(r"\{[^}]+\}", str(BIG), path)


def _allowed(kind):
    return {READ: READ_OK, WRITE: WRITE_OK, ADMIN: ADMIN_OK}[kind]


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    """Vitesse : un seul bcrypt.hash de PWD reutilise."""
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
    users = {r: create_test_user(db_session, f"t_fabrole_{r.lower()}", r, password=PWD) for r in ROLES}
    client = api_client(auth_endpoints, ep, stock_endpoints, pharmacy_endpoints)
    return {"db": db_session, "client": client, "users": users}


def _call(client, method, path, body):
    kw = {}
    if body is not None:
        kw["json"] = body
    return client.request(method, _url(path), **kw)


def test_routes_table_covers_router():
    assert _router_routes() == set(ROUTES), (
        "routes /fabrication non couvertes ou obsoletes : "
        f"{sorted(_router_routes() ^ set(ROUTES))}")


def test_role_constants():
    assert set(ep.READERS) == READ_OK
    assert set(ep.WRITERS) == WRITE_OK
    assert set(ep.SETTINGS_WRITERS) == ADMIN_OK


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    kind, body = ROUTES[route]
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r = _call(env["client"], route[0], route[1], body)
    if role in _allowed(kind):
        # garde franchie : 2xx, 404 (id inexistant) ou 422 (corps vide) mais jamais 401/403/5xx
        assert r.status_code not in (401, 403) and r.status_code < 500, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


def test_unauthenticated_refused(env):
    for route in sorted(ROUTES):
        r = _call(env["client"], route[0], route[1], ROUTES[route][1])
        assert r.status_code in (401, 403), (route, r.status_code)


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from _keys(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _keys(v)


def test_no_cost_field_in_existing_routes(env):
    """Aucune route existante de produits (stock, pharmacie) ne renvoie un champ de cout.

    Un produit aleatoire est seme (annule en fin de test) pour que le balayage porte sur de
    vraies cles ; chaque reponse doit contenir ce produit avant le balayage.
    """
    name = "T_" + uuid.uuid4().hex[:12]
    prod = Pharmacy(drug_name=name, quantity=5, threshold=1, medication_type="comprime", price=10)
    env["db"].add(prod)
    env["db"].flush()
    pid = prod.medication_id
    checks = (("admin", "/stock/products"), ("StockController", "/stock/products"),
              ("admin", f"/pharmacy/?per_page=200&term={name}"))
    for role, url in checks:
        user = env["users"][role]
        user.roles = [normalize_role_name(role)]
        app.dependency_overrides[auth_endpoints.get_current_user] = lambda u=user: u
        r = env["client"].get(url)
        assert r.status_code == 200, (url, r.status_code, r.text)
        data = r.json()
        assert name in str(data) or pid in [x.get("id") for x in data if isinstance(x, dict)], (
            url, "produit seme absent de la reponse")
        keys = list(_keys(data))
        assert keys, url
        bad = [k for k in keys if "cost" in k.lower()]
        assert not bad, (url, bad)


def test_real_login_wiring(env):
    """2 vraies connexions : le jeton ProductionManager ouvre /fabrication, celui du secretaire non."""
    c = env["client"]
    h_pm = auth_headers(c, "t_fabrole_productionmanager", PWD)
    h_sec = auth_headers(c, "t_fabrole_secretaire", PWD)
    assert c.get("/fabrication/intrants", headers=h_pm).status_code == 200
    assert c.get("/fabrication/intrants", headers=h_sec).status_code == 403
