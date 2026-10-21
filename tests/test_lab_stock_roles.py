# tests/test_lab_stock_roles.py
"""Task 2 (stock labo) : matrice roles x routes de /lab-stock (controle cote serveur).

Pas de connexion par cas (limite 5/min) : get_current_user est surcharge avec un vrai
utilisateur de la base, roles canoniques comme le vrai get_current_user. Un test final
fait de VRAIES connexions (2) pour verifier le cablage jeton -> role_required.
Tasks 3-5 : ajouter leurs routes a ROUTES (receptions : StockController/promoteur/admin,
ToxicoManager -> 403 ; comptage ; depenses ; annulation de reception = admin seul).
"""
from datetime import date, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.lab_stock import lab_stock_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.lab_stock_controller import LabStockController
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("laborantin", "StockController", "promoteur", "ToxicoManager", "admin",
         "medecin", "nurse", "secretaire", "Assistant")
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    """Vitesse (motif de test_stock_endpoints.py) : un seul bcrypt.hash de PWD reutilise."""
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
    db = db_session
    users = {r: create_test_user(db, f"t_lsrole_{r.lower()}", r, password=PWD) for r in ROLES}
    lab = users["laborantin"]
    product = _ctrl(db, lab).create_product({"name": "TEST_LSROLE_P"})
    client = api_client(auth_endpoints, ep)
    return {"db": db, "client": client, "users": users, "product": product, "lab": lab}


def _open_request(e):
    return _ctrl(e["db"], e["lab"]).signal(e["product"]["id"], "fini")


def _ordered_request(e):
    req = _open_request(e)
    return _ctrl(e["db"], e["users"]["admin"]).mark_ordered(req["id"], TOMORROW)


_name_seq = iter(range(10_000))

# route -> (roles autorises, builder(env) -> (method, url, json))
ROUTES = {
    "products_list": (ep.READERS, lambda e: ("get", "/lab-stock/products", None)),
    "products_create": (ep.PRODUCT_WRITERS, lambda e: (
        "post", "/lab-stock/products", {"name": f"TEST_LSROLE_N{next(_name_seq)}"})),
    "products_update": (ep.PRODUCT_WRITERS, lambda e: (
        "put", f"/lab-stock/products/{e['product']['id']}", {"supplier": "S"})),
    "products_signal": (ep.SIGNALERS, lambda e: (
        "post", f"/lab-stock/products/{e['product']['id']}/signal", {"level": "bientot_fini"})),
    "requests_list": (ep.READERS, lambda e: ("get", "/lab-stock/requests", None)),
    "requests_order": (ep.ORDERERS, lambda e: (
        "post", f"/lab-stock/requests/{_open_request(e)['id']}/order", {"expected_date": TOMORROW})),
    "requests_order_date": (ep.ORDERERS, lambda e: (
        "put", f"/lab-stock/requests/{_ordered_request(e)['id']}/order", {"expected_date": TOMORROW})),
    "requests_cancel": (ep.ORDERERS, lambda e: (
        "post", f"/lab-stock/requests/{_open_request(e)['id']}/cancel", {"reason": "test"})),
    "receipts_create": (ep.RECEIVERS, lambda e: ("post", "/lab-stock/receipts", _receipt_body(e))),
    "receipts_list": (ep.READERS, lambda e: ("get", "/lab-stock/receipts", None)),
    "receipts_get": (ep.READERS, lambda e: ("get", f"/lab-stock/receipts/{_receipt(e)['id']}", None)),
    "receipts_cancel": (ep.RECEIPT_CANCELLERS, lambda e: (
        "post", f"/lab-stock/receipts/{_receipt(e)['id']}/cancel", {"reason": "test"})),
    "counts_submit": (ep.COUNTERS, lambda e: ("post", "/lab-stock/counts", {"lines": [
        {"product_id": e["product"]["id"], "previous_qty": 0, "counted_qty": 3}]})),
    "counts_status": (ep.READERS, lambda e: ("get", "/lab-stock/counts/status", None)),
    "alerts": (ep.READERS, lambda e: ("get", "/lab-stock/alerts", None)),
    "expenses": (ep.SPENDERS, lambda e: ("get", "/lab-stock/expenses", None)),
    "price_history": (ep.SPENDERS, lambda e: (
        "get", f"/lab-stock/products/{e['product']['id']}/price-history", None)),
    "movements": (ep.READERS, lambda e: (
        "get", f"/lab-stock/movements?product_id={e['product']['id']}&limit=50", None)),
}


def _receipt_body(e):
    return {"invoice_number": f"TEST_LSROLE_F{next(_name_seq)}", "supplier": "TEST_LSROLE_S",
            "delivery_date": date.today().isoformat(),
            "lines": [{"product_id": e["product"]["id"], "received_qty": 2, "unit_price": "100",
                       "lot_number": "L1", "expiry_date": TOMORROW}]}


def _receipt(e):
    return _ctrl(e["db"], e["users"]["admin"]).create_receipt(_receipt_body(e))

# Matrice du plan figee ici (un changement de constante du routeur doit casser ce test)
EXPECTED = {
    "READERS": {"laborantin", "StockController", "promoteur", "ToxicoManager", "admin"},
    "PRODUCT_WRITERS": {"laborantin", "StockController", "admin"},
    "RECEIVERS": {"StockController", "promoteur", "admin"},
    "COUNTERS": {"laborantin", "admin"},
    "SIGNALERS": {"laborantin", "admin"},
    "ORDERERS": {"promoteur", "ToxicoManager", "admin"},
    "SPENDERS": {"promoteur", "ToxicoManager", "admin"},
    "RECEIPT_CANCELLERS": {"admin"},
}


def test_role_constants_match_plan():
    for name, roles in EXPECTED.items():
        assert set(getattr(ep, name)) == roles, name


def _call(client, method, url, body, headers=None):
    kw = {"headers": headers or {}}
    if body is not None:
        kw["json"] = body
    return getattr(client, method)(url, **kw)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    allowed, build = ROUTES[route]
    method, url, body = build(env)
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r = _call(env["client"], method, url, body)
    if role in allowed:
        assert 200 <= r.status_code < 300, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)


def test_unauthenticated_refused(env):
    for route in sorted(ROUTES):
        method, url, body = ROUTES[route][1](env)
        r = _call(env["client"], method, url, body)
        assert r.status_code in (401, 403), (route, r.status_code)


def test_real_tokens_wiring(env):
    """2 vraies connexions : le jeton du laborantin ouvre la creation, celui du promoteur non."""
    c = env["client"]
    h_lab = auth_headers(c, "t_lsrole_laborantin", PWD)
    h_pro = auth_headers(c, "t_lsrole_promoteur", PWD)
    assert c.post("/lab-stock/products", json={"name": "TEST_LSROLE_Real"}, headers=h_lab).status_code == 201
    assert c.post("/lab-stock/products", json={"name": "TEST_LSROLE_Real2"}, headers=h_pro).status_code == 403
    assert c.get("/lab-stock/requests", headers=h_pro).status_code == 200
