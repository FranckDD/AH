# tests/test_lab_stock_products.py
"""Task 2 (stock labo) : produits - creation, validation, doublon, quantite initiale 0."""
import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.lab_stock import lab_stock_endpoints
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.lab_stock_controller import LabStockController
from models.audit import AuditUserAction  # noqa: F401  (verifie que le modele existe)
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockConflictError, LabStockNotFoundError, LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _as(user, role):
    """Surcharge get_current_user (aucune connexion) ; roles canoniques comme le vrai get_current_user."""
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


@pytest.fixture
def env(db_session, api_client):
    u = create_test_user(db_session, "t_lsp_lab", "laborantin")
    db_session.commit()  # un rollback du controleur ne doit pas emporter l'utilisateur de fixture
    client = api_client(lab_stock_endpoints)
    _as(u, "laborantin")
    return {"db": db_session, "client": client, "user": u}


def test_controller_requires_three_repos(db_session):
    with pytest.raises(TypeError):
        LabStockController(LabStockRepository(db_session), None, AuditRepository(db_session), None)


def test_create_product_quantity_always_zero_and_names(env):
    c = _ctrl(env["db"], env["user"])
    out = c.create_product({"name": "  TEST_LSP_Reactif A ", "packaging": "Boite de 100",
                            "alert_threshold": 5, "supplier": "LabCo", "quantity": 50})
    assert out["quantity"] == 0 and out["name"] == "TEST_LSP_Reactif A"
    assert out["created_by_name"] == env["user"].full_name and out["is_active"] is True
    r = env["client"].post("/lab-stock/products", json={"name": "TEST_LSP_B", "alert_threshold": 2})
    assert r.status_code == 201, r.text
    assert r.json()["quantity"] == 0
    # quantite envoyee par HTTP : corps strict -> 422, jamais de stock initial
    r = env["client"].post("/lab-stock/products", json={"name": "TEST_LSP_C", "quantity": 9})
    assert r.status_code == 422


@pytest.mark.parametrize("body", [
    {"name": ""}, {"name": "   "}, {"name": "TEST_LSP_X", "alert_threshold": -1},
    {"name": "TEST_LSP_X", "alert_threshold": "3"}, {"name": "x" * 151}, {"name": "TEST_LSP_X", "foo": 1},
])
def test_invalid_product_422(env, body):
    r = env["client"].post("/lab-stock/products", json=body)
    assert r.status_code == 422, r.text


def test_duplicate_active_name_409_case_insensitive(env):
    c = env["client"]
    assert c.post("/lab-stock/products", json={"name": "TEST_LSP_Dup"}).status_code == 201
    r = c.post("/lab-stock/products", json={"name": "test_lsp_dup"})
    assert r.status_code == 409, r.text


def test_update_product_and_inactive_rules(env):
    c = env["client"]
    a = c.post("/lab-stock/products", json={"name": "TEST_LSP_U1"}).json()
    b = c.post("/lab-stock/products", json={"name": "TEST_LSP_U2"}).json()
    r = c.put(f"/lab-stock/products/{a['id']}", json={"packaging": "Flacon", "alert_threshold": 3,
                                                       "supplier": "S1"})
    assert r.status_code == 200 and r.json()["alert_threshold"] == 3 and r.json()["packaging"] == "Flacon"
    assert c.put(f"/lab-stock/products/{b['id']}", json={"name": "TEST_LSP_U1"}).status_code == 409
    assert c.put(f"/lab-stock/products/{a['id']}", json={"is_active": False}).status_code == 200
    # nom libere par la desactivation
    assert c.put(f"/lab-stock/products/{b['id']}", json={"name": "TEST_LSP_U1"}).status_code == 200
    # reactiver a -> doublon actif
    assert c.put(f"/lab-stock/products/{a['id']}", json={"is_active": True}).status_code == 409
    assert c.put(f"/lab-stock/products/{a['id']}", json={"alert_threshold": -2}).status_code == 422
    assert c.put(f"/lab-stock/products/{a['id']}", json={"quantity": 5}).status_code == 422
    assert c.put("/lab-stock/products/99999999", json={"supplier": "x"}).status_code == 404
    ids = [p["id"] for p in c.get("/lab-stock/products").json()]
    assert b["id"] in ids and a["id"] not in ids
    ids = [p["id"] for p in c.get("/lab-stock/products?include_inactive=true").json()]
    assert a["id"] in ids


def test_explicit_null_on_required_fields_422(env):
    c = env["client"]
    a = c.post("/lab-stock/products", json={"name": "TEST_LSP_Null", "alert_threshold": 7}).json()
    for body in ({"alert_threshold": None}, {"name": None}, {"is_active": None}):
        r = c.put(f"/lab-stock/products/{a['id']}", json=body)
        assert r.status_code == 422, (body, r.text)
    assert c.post("/lab-stock/products", json={"name": "TEST_LSP_Null2", "alert_threshold": None}).status_code == 422
    p = [x for x in c.get("/lab-stock/products").json() if x["id"] == a["id"]][0]
    assert p["alert_threshold"] == 7


def test_writes_are_audited(env):
    from models.audit import AuditUserAction as A
    out = _ctrl(env["db"], env["user"]).create_product({"name": "TEST_LSP_Audit"})
    rows = env["db"].query(A).filter_by(resource_type="LabStockProduct", resource_id=out["id"]).all()
    assert [r.action_performed for r in rows] == ["CREATE"]


def test_errors_types(env):
    c = _ctrl(env["db"], env["user"])
    with pytest.raises(LabStockNotFoundError):
        c.update_product(99999999, {"name": "x"})
    c.create_product({"name": "TEST_LSP_E"})
    with pytest.raises(LabStockConflictError):
        c.create_product({"name": "TEST_LSP_E"})


def test_apply_delta_never_negative_and_writes_movement(env):
    from models.lab_stock import LabStockMovement
    db = env["db"]
    p = _ctrl(db, env["user"]).create_product({"name": "TEST_LSP_Delta"})
    repo = LabStockRepository(db)
    assert repo.apply_delta(p["id"], 5, "reception", "receipt", None, env["user"]) == 5
    with pytest.raises(LabStockConflictError):
        repo.apply_delta(p["id"], -6, "comptage", "count", None, env["user"])
    mv = db.query(LabStockMovement).filter_by(product_id=p["id"]).all()
    assert len(mv) == 1 and mv[0].quantity_after == 5 and mv[0].change_qty == 5
