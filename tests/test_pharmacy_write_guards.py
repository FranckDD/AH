# tests/test_pharmacy_write_guards.py
"""Task 6 : gardes d'ecriture du routeur /pharmacy (vrais appels HTTP)."""
from unittest.mock import MagicMock

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.pharmacy import pharmacy_endpoints
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROLES = ("admin", "Assistant", "ToxicoManager", "secretaire", "StockController")


@pytest.fixture(scope="module", autouse=True)
def _no_redis_no_celery():
    """Neutralise Redis/Celery pour ce module (portee module => actif avant les
    fixtures autouse du conftest).

    - PharmacyController._trigger_stock_alert appelle task.delay() : sans Redis,
      le backend resultat Celery reessaie de se reconnecter INDEFINIMENT et la
      requete HTTP ne revient jamais (cause du blocage de 9 h sur test_renew_admin_ok).
    - Chaque acces redis_client vers un Redis arrete coute ~2 s (refus de connexion
      sous Windows) : sans ce patch le fichier depasse plusieurs minutes.
    """
    mp = pytest.MonkeyPatch()
    mp.setattr("controller.pharmacy_controller.task_check_low_stock_alert", MagicMock())
    mp.setattr("controller.pharmacy_controller.redis_client", MagicMock(get=MagicMock(return_value=None)))
    mp.setattr("controller.patient_controller.redis_client", MagicMock())
    yield
    mp.undo()


@pytest.fixture
def env(db_session, api_client):
    for r in ROLES:
        create_test_user(db_session, f"t_pwg_{r.lower()}", r, password=PWD)
    client = api_client(auth_endpoints, pharmacy_endpoints)

    class _Heads(dict):
        """Connexion paresseuse, une seule fois par role (bcrypt est lent)."""
        def __missing__(self, role):
            self[role] = auth_headers(client, f"t_pwg_{role.lower()}", PWD)
            return self[role]

    heads = _Heads()
    p = Pharmacy(drug_name="TEST_PWG_PROD", quantity=30, threshold=5, medication_type="pharmaceutique",
                 forme="Autre", price=10, stock_status="normal")
    p.update_stock_status()
    db_session.add(p)
    db_session.flush()
    return {"db": db_session, "client": client, "h": heads, "pid": p.medication_id}


def _qty(env, pid=None):
    env["db"].expire_all()
    return env["db"].get(Pharmacy, pid or env["pid"]).quantity


def _movements(env, kind):
    env["db"].expire_all()
    return env["db"].query(StockMovement).filter_by(medication_id=env["pid"], movement_type=kind).count()


# ---------- renew / delete : admin seul ----------
@pytest.mark.parametrize("role", ["Assistant", "ToxicoManager", "secretaire", "StockController"])
def test_renew_forbidden(env, role):
    r = env["client"].post(f"/pharmacy/{env['pid']}/renew?added_quantity=5", headers=env["h"][role])
    assert r.status_code == 403
    assert _qty(env) == 30


def test_renew_admin_ok(env):
    r = env["client"].post(f"/pharmacy/{env['pid']}/renew?added_quantity=5", headers=env["h"]["admin"])
    assert r.status_code == 200
    assert _qty(env) == 35


@pytest.mark.parametrize("role", ["Assistant", "ToxicoManager", "secretaire", "StockController"])
def test_delete_forbidden(env, role):
    r = env["client"].delete(f"/pharmacy/{env['pid']}", headers=env["h"][role])
    assert r.status_code == 403
    env["db"].expire_all()
    assert env["db"].get(Pharmacy, env["pid"]) is not None


def test_delete_admin_ok(env):
    r = env["client"].delete(f"/pharmacy/{env['pid']}", headers=env["h"]["admin"])
    assert r.status_code == 204


# ---------- PUT ----------
@pytest.mark.parametrize("role", ["Assistant", "ToxicoManager", "admin"])
def test_put_without_quantity_ok(env, role):
    r = env["client"].put(f"/pharmacy/{env['pid']}", json={"price": 99}, headers=env["h"][role])
    assert r.status_code == 200, r.text
    env["db"].expire_all()
    assert float(env["db"].get(Pharmacy, env["pid"]).price) == 99
    assert _qty(env) == 30


@pytest.mark.parametrize("role", ["secretaire", "StockController"])
def test_put_forbidden_roles(env, role):
    r = env["client"].put(f"/pharmacy/{env['pid']}", json={"price": 99}, headers=env["h"][role])
    assert r.status_code == 403


@pytest.mark.parametrize("role", ["Assistant", "ToxicoManager"])
@pytest.mark.parametrize("qty", [77, 30])
def test_put_quantity_forbidden_for_non_admin(env, role, qty):
    r = env["client"].put(f"/pharmacy/{env['pid']}", json={"quantity": qty, "price": 5}, headers=env["h"][role])
    assert r.status_code == 403
    assert "Seul l'admin" in r.json()["detail"]
    assert _qty(env) == 30
    env["db"].expire_all()
    assert float(env["db"].get(Pharmacy, env["pid"]).price) == 10


def test_put_quantity_admin_ok(env):
    before = _movements(env, "update")
    r = env["client"].put(f"/pharmacy/{env['pid']}", json={"quantity": 77}, headers=env["h"]["admin"])
    assert r.status_code == 200, r.text
    assert _qty(env) == 77
    assert _movements(env, "update") == before + 1


# ---------- POST create ----------
def _body(qty=50):
    return {"drug_name": "TEST_PWG_NEW", "quantity": qty, "threshold": 5,
            "medication_type": "pharmaceutique", "forme": "Autre", "price": 3}


@pytest.mark.parametrize("role,expected", [("Assistant", 0), ("ToxicoManager", 0), ("admin", 50)])
def test_create_quantity_forced(env, role, expected):
    r = env["client"].post("/pharmacy/", json=_body(), headers=env["h"][role])
    assert r.status_code == 201, r.text
    assert r.json()["quantity"] == expected
    assert _qty(env, r.json()["medication_id"]) == expected


@pytest.mark.parametrize("role", ["secretaire", "StockController"])
def test_create_forbidden(env, role):
    r = env["client"].post("/pharmacy/", json=_body(), headers=env["h"][role])
    assert r.status_code == 403


# ---------- GET ----------
def test_get_secretaire_ok_stockcontroller_403(env):
    c = env["client"]
    for url in ("/pharmacy/", "/pharmacy/?term=TEST_PWG", f"/pharmacy/{env['pid']}"):
        assert c.get(url, headers=env["h"]["secretaire"]).status_code == 200
        assert c.get(url, headers=env["h"]["StockController"]).status_code == 403
