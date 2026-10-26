# tests/test_lab_stock_requests.py
"""Task 2 (stock labo) : signalement (une seule demande ouverte, notifications dedupliquees)
et suivi de commande (transitions, dates, annulation)."""
from datetime import date, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.lab_stock import lab_stock_endpoints
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.lab_stock_controller import LabStockController
from models.lab_stock import LabStockRequest
from models.notification import Notification
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import LabStockRepository
from repositories.notification_repo import NotificationRepository
from tests.conftest import create_test_user

TODAY = date.today()


def _ctrl(db, user):
    return LabStockController(LabStockRepository(db), NotificationRepository(db), AuditRepository(db), user)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    u = {
        "lab": create_test_user(db, "t_lsr_lab", "laborantin"),
        "promo": create_test_user(db, "t_lsr_promo", "promoteur"),
        "mgr": create_test_user(db, "t_lsr_mgr", "ToxicoManager"),
        "promo_off": create_test_user(db, "t_lsr_promo_off", "promoteur", is_active=False),
        "admin": create_test_user(db, "t_lsr_admin", "admin"),
    }
    product = _ctrl(db, u["lab"]).create_product({"name": "TEST_LSR_Reactif", "alert_threshold": 4})
    # la creation sous le seuil ouvre sa demande « seuil » ; ces tests partent d'un produit sans demande
    db.query(Notification).filter_by(type="lab_stock_low").delete()
    db.query(LabStockRequest).filter_by(product_id=product["id"]).delete()
    db.flush()
    client = api_client(lab_stock_endpoints)
    return {"db": db, "client": client, "u": u, "product": product}


def _notifs(db, user):
    return db.query(Notification).filter_by(recipient_user_id=user.user_id, type="lab_stock_signal").all()


def _signal(env, level="bientot_fini"):
    _as(env["u"]["lab"], "laborantin")
    return env["client"].post(f"/lab-stock/products/{env['product']['id']}/signal", json={"level": level})


def test_signal_creates_then_updates_single_open_request(env):
    db, u = env["db"], env["u"]
    r = _signal(env)
    assert r.status_code == 200, r.text
    first = r.json()
    assert first["origin"] == "signalement" and first["status"] == "a_commander"
    assert first["level"] == "bientot_fini" and first["requested_by_name"] == u["lab"].full_name
    assert first["product_name"] == "TEST_LSR_Reactif" and first["quantity"] == 0
    assert first["alert_threshold"] == 4
    r = _signal(env, "fini")
    assert r.status_code == 200 and r.json()["id"] == first["id"] and r.json()["level"] == "fini"
    rows = db.query(LabStockRequest).filter_by(product_id=env["product"]["id"]).all()
    assert len(rows) == 1
    # exactement une notification non lue par destinataire actif ; aucune pour l'inactif
    for k in ("promo", "mgr"):
        n = _notifs(db, u[k])
        assert len(n) == 1 and n[0].payload["request_id"] == first["id"] and n[0].payload["level"] == "fini"
    assert _notifs(db, u["promo_off"]) == []
    assert _notifs(db, u["lab"]) == [] and _notifs(db, u["admin"]) == []


def test_signal_invalid_level_and_unknown_product(env):
    _as(env["u"]["lab"], "laborantin")
    c = env["client"]
    assert c.post(f"/lab-stock/products/{env['product']['id']}/signal", json={"level": "vide"}).status_code == 422
    assert c.post("/lab-stock/products/99999999/signal", json={"level": "fini"}).status_code == 404


def test_order_transitions(env):
    c, u = env["client"], env["u"]
    rid = _signal(env).json()["id"]
    _as(u["promo"], "promoteur")
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    # modifier la date avant commande -> 409
    assert c.put(f"/lab-stock/requests/{rid}/order", json={"expected_date": tomorrow}).status_code == 409
    # date passee -> 422
    past = (TODAY - timedelta(days=1)).isoformat()
    assert c.post(f"/lab-stock/requests/{rid}/order", json={"expected_date": past}).status_code == 422
    r = c.post(f"/lab-stock/requests/{rid}/order", json={"expected_date": TODAY.isoformat()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "commande" and body["ordered_by_name"] == u["promo"].full_name
    assert body["ordered_at"] is not None
    # deja commandee -> 409
    assert c.post(f"/lab-stock/requests/{rid}/order", json={"expected_date": tomorrow}).status_code == 409
    r = c.put(f"/lab-stock/requests/{rid}/order", json={"expected_date": tomorrow})
    assert r.status_code == 200 and r.json()["expected_date"] == tomorrow
    assert c.put(f"/lab-stock/requests/{rid}/order", json={"expected_date": past}).status_code == 422
    assert c.post("/lab-stock/requests/99999999/order", json={"expected_date": tomorrow}).status_code == 404
    lst = c.get("/lab-stock/requests?status=commande").json()
    assert rid in [x["id"] for x in lst]
    assert c.get("/lab-stock/requests?status=bidon").status_code == 422


def test_signal_on_ordered_request_updates_level_only(env):
    db, u, c = env["db"], env["u"], env["client"]
    rid = _signal(env).json()["id"]
    _as(u["promo"], "promoteur")
    assert c.post(f"/lab-stock/requests/{rid}/order",
                  json={"expected_date": TODAY.isoformat()}).status_code == 200
    r = _signal(env, "fini")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == rid and body["status"] == "commande" and body["level"] == "fini"
    assert db.query(LabStockRequest).filter_by(product_id=env["product"]["id"]).count() == 1
    # notification non lue existante rafraichie, pas de doublon
    for k in ("promo", "mgr"):
        n = _notifs(db, u[k])
        assert len(n) == 1 and n[0].payload["level"] == "fini"


def test_signal_race_on_open_request_index_is_not_500(env, monkeypatch):
    """Simule le perdant d'une course : open_request_for ne voit pas (une fois) la demande
    ouverte deja inseree -> INSERT viole l'index unique -> relance -> mise a jour."""
    db = env["db"]
    rid = _signal(env).json()["id"]
    real = LabStockRepository.open_request_for
    calls = {"n": 0}

    def flaky(self, product_id, lock=True):
        calls["n"] += 1
        return None if calls["n"] == 1 else real(self, product_id, lock)

    monkeypatch.setattr(LabStockRepository, "open_request_for", flaky)
    r = _signal(env, "fini")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == rid and r.json()["level"] == "fini" and calls["n"] == 2
    assert db.query(LabStockRequest).filter_by(product_id=env["product"]["id"]).count() == 1
    # toujours la course (jamais visible) -> 409, pas 500
    monkeypatch.setattr(LabStockRepository, "open_request_for", lambda self, pid, lock=True: None)
    assert _signal(env).status_code == 409


def test_cancel_request(env):
    c, u = env["client"], env["u"]
    rid = _signal(env).json()["id"]
    _as(u["mgr"], "ToxicoManager")
    assert c.post(f"/lab-stock/requests/{rid}/cancel", json={"reason": "  "}).status_code == 422
    assert c.post(f"/lab-stock/requests/{rid}/cancel", json={}).status_code == 422
    r = c.post(f"/lab-stock/requests/{rid}/cancel", json={"reason": "doublon"})
    assert r.status_code == 200 and r.json()["status"] == "annule" and r.json()["cancel_reason"] == "doublon"
    assert c.post(f"/lab-stock/requests/{rid}/cancel", json={"reason": "encore"}).status_code == 409
    # apres annulation, un nouveau signalement ouvre une nouvelle demande
    r2 = _signal(env)
    assert r2.status_code == 200 and r2.json()["id"] != rid


# ---- desactivation d'un produit : sa demande ouverte est annulee ----
@pytest.mark.parametrize("ordered", [False, True])
def test_deactivation_cancels_open_request(env, ordered):
    db, u, pid = env["db"], env["u"], env["product"]["id"]
    req = _ctrl(db, u["lab"]).signal(pid, "fini")
    if ordered:
        _ctrl(db, u["promo"]).mark_ordered(req["id"], (TODAY + timedelta(days=3)).isoformat())
    _ctrl(db, u["admin"]).update_product(pid, {"is_active": False})
    db.expire_all()
    r = db.get(LabStockRequest, req["id"])
    assert r.status == "annule" and r.cancel_reason == "produit désactivé" and r.closed_at is not None
    listed = [x for x in _ctrl(db, u["lab"]).list_requests("annule") if x["id"] == req["id"]]
    assert len(listed) == 1
    assert not [x for x in _ctrl(db, u["lab"]).list_requests() if x["product_id"] == pid
                and x["status"] in ("a_commander", "commande")]
    from models.audit import AuditUserAction
    assert db.query(AuditUserAction).filter_by(resource_type="LabStockRequest", resource_id=req["id"],
                                               action_performed="CANCEL").count() == 1
    # produit inactif : ignore des alertes
    alerts = _ctrl(db, u["lab"]).get_alerts()
    assert pid not in [x["product_id"] for x in alerts["low"]]
    assert pid not in [x["product_id"] for x in alerts["expiring"]]


def test_deactivation_without_open_request_is_noop(env):
    db, u, pid = env["db"], env["u"], env["product"]["id"]
    before = db.query(LabStockRequest).filter_by(product_id=pid).count()
    out = _ctrl(db, u["admin"]).update_product(pid, {"is_active": False})
    assert out["is_active"] is False
    assert db.query(LabStockRequest).filter_by(product_id=pid).count() == before


def test_reactivation_allows_new_request(env):
    db, u, pid = env["db"], env["u"], env["product"]["id"]
    first = _ctrl(db, u["lab"]).signal(pid, "fini")
    _ctrl(db, u["admin"]).update_product(pid, {"is_active": False})
    _ctrl(db, u["admin"]).update_product(pid, {"is_active": True})
    second = _ctrl(db, u["lab"]).signal(pid, "bientot_fini")
    assert second["id"] != first["id"] and second["status"] == "a_commander"
    # comptage sous le seuil apres reactivation : la demande ouverte reste unique
    _ctrl(db, u["lab"]).submit_count([{"product_id": pid, "previous_qty": 0, "counted_qty": 1}])
    open_ = [x for x in _ctrl(db, u["lab"]).list_requests("a_commander") if x["product_id"] == pid]
    assert len(open_) == 1
