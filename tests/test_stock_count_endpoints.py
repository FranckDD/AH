# tests/test_stock_count_endpoints.py
"""Comptage du stock (tache 3) : routes HTTP /stock-counts.

Rappel du harnais : toute erreur du controleur annule la transaction de test (utilisateurs
semes compris) ; un seul scenario d'erreur controleur par test, place en dernier.
Les erreurs de schema (422 pydantic) ne touchent pas le controleur : plusieurs par test.
"""
import uuid

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.notifications import notification_endpoints
from api_backend.backend_app.routes.stock import stock_endpoints
from api_backend.backend_app.routes.stock_count import stock_count_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from models.pharmacy import Pharmacy
from tests.conftest import create_test_user

BIG = 987654321
# Mots interdits dans les cles avant validation (regle d'aveugle). Aucune exception n'est
# necessaire : les cles sanctionnees (interval_days, days_since, last_counted_at, counts, status,
# products, product_id, name, started_at, scope, id) ne contiennent aucun de ces mots.
FORBIDDEN = ("qty", "quantity", "stock", "difference", "gap", "previous", "counted_qty")


def _rand(p):
    return f"{p}_{uuid.uuid4().hex[:8]}"


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield str(k)
            yield from _keys(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _keys(v)


def _blind(obj):
    keys = list(_keys(obj))
    assert keys
    bad = [k for k in keys if any(w in k.lower() for w in FORBIDDEN)]
    assert bad == [], bad


def _product(db, qty):
    p = Pharmacy(drug_name=_rand("TSCE"), quantity=qty, threshold=0, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def env(db_session, api_client):
    users = {k: create_test_user(db_session, _rand(f"t_sce_{k}"), role) for k, role in (
        ("ctrl", "StockController"), ("admin", "admin"), ("promo", "promoteur"))}
    client = api_client(auth_endpoints, ep, stock_endpoints, notification_endpoints)
    return {"db": db_session, "client": client, "users": users}


def _as(env, key):
    u = env["users"][key]
    u.roles = [normalize_role_name(u.application_role.role_name)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: u
    return env["client"]


def test_full_flow_over_http(env):
    p = _product(env["db"], 10)
    c = _as(env, "ctrl")
    r = c.post("/stock-counts", json={})
    assert r.status_code == 201, r.text
    start = r.json()
    _blind(start)
    assert start["scope"] == "tous" and p.medication_id in [x["id"] for x in start["products"]]
    cid = start["id"]

    # avant validation : detail sans lignes, statut sans quantite
    d = c.get(f"/stock-counts/{cid}")
    assert d.status_code == 200 and d.json()["lines"] is None and d.json()["status"] == "en_cours"
    s = c.get("/stock-counts/status")
    assert s.status_code == 200, s.text
    _blind(s.json())

    r = c.post(f"/stock-counts/{cid}/submit",
               json={"lines": [{"product_id": p.medication_id, "counted_qty": 7, "observation": "casse"}]})
    assert r.status_code == 200, r.text
    line = [l for l in r.json()["lines"] if l["product_id"] == p.medication_id][0]
    assert line["counted_qty"] == 7 and line["previous_qty"] == 10 and line["difference"] == -3
    assert line["gap_kind"] and line["adjustment_request_id"]
    req_id = line["adjustment_request_id"]

    d = c.get(f"/stock-counts/{cid}").json()
    assert d["status"] == "valide" and d["lines"][0]["gap_kind"] == line["gap_kind"]
    lst = c.get("/stock-counts").json()
    assert cid in [x["id"] for x in lst["items"]]

    # cablage de la fabrique : demande d'ajustement visible par l'admin + notification admin
    a = _as(env, "admin")
    reqs = a.get("/stock/adjustment-requests").json()
    reqs = reqs["items"] if isinstance(reqs, dict) else reqs
    assert req_id in [x["id"] for x in reqs]
    notifs = a.get("/notifications").json()
    assert any(n["type"] == "stock_adjustment_request" and n["payload"].get("request_id") == req_id
               for n in notifs), notifs

    # promoteur : lecture du detail revele
    assert _as(env, "promo").get(f"/stock-counts/{cid}").status_code == 200


def test_counted_at_list_shape_and_mine_over_http(env):
    p = _product(env["db"], 10)
    c = _as(env, "ctrl")
    cid = c.post("/stock-counts", json={}).json()["id"]
    lst = _as(env, "admin").get("/stock-counts").json()
    assert set(lst) == {"items", "total", "limit", "offset"} and lst["limit"] == 50 and lst["offset"] == 0
    assert _as(env, "admin").get("/stock-counts?mine=true").json()["items"] == []
    mine = _as(env, "ctrl").get("/stock-counts?mine=true").json()
    assert [x["id"] for x in mine["items"]] == [cid] and mine["total"] == 1
    c = _as(env, "ctrl")
    assert c.post(f"/stock-counts/{cid}/submit", json={"lines": [
        {"product_id": p.medication_id, "counted_qty": 1, "counted_at": "x" * 41}]}).status_code == 422
    r = c.post(f"/stock-counts/{cid}/submit", json={"lines": [
        {"product_id": p.medication_id, "counted_qty": 10, "counted_at": "2000-01-01T00:00:00Z"}]})
    assert r.status_code == 200, r.text
    line = r.json()["lines"][0]
    assert {"counted_at", "movements_net", "stock_at_count", "previous_qty", "difference", "gap_kind",
            "movements_during", "recount", "previous_count_id", "superseded_request_ids"} <= set(line)
    assert line["counted_at"].endswith("+00:00") and line["stock_at_count"] == 10


def test_client_now_over_http(env):
    p = _product(env["db"], 10)
    c = _as(env, "ctrl")
    cid = c.post("/stock-counts", json={}).json()["id"]
    for bad in ("x" * 41, "hier", 5):
        r = c.post(f"/stock-counts/{cid}/submit", json={"client_now": bad, "lines": [
            {"product_id": p.medication_id, "counted_qty": 10}]})
        assert r.status_code == 422, (bad, r.text)
    r = c.post(f"/stock-counts/{cid}/submit", json={"client_now": "2000-01-01T00:00:00Z", "lines": [
        {"product_id": p.medication_id, "counted_qty": 10}]})
    assert r.status_code == 200, r.text


def test_invalid_counted_at_string_422(env):
    p = _product(env["db"], 10)
    c = _as(env, "ctrl")
    cid = c.post("/stock-counts", json={}).json()["id"]
    r = c.post(f"/stock-counts/{cid}/submit", json={"lines": [
        {"product_id": p.medication_id, "counted_qty": 1, "counted_at": "hier"}]})
    assert r.status_code == 422, r.text


def test_start_selection_and_abandon(env):
    c = _as(env, "ctrl")
    r = c.post("/stock-counts", json={"scope": "selection"})
    assert r.status_code == 201 and r.json()["scope"] == "selection"
    _blind(r.json())
    r = c.post(f"/stock-counts/{r.json()['id']}/abandon")
    assert r.status_code == 200 and r.json()["status"] == "abandonne"


def test_admin_and_promoteur_cannot_count(env):
    for who in ("admin", "promo"):
        c = _as(env, who)
        assert c.post("/stock-counts", json={}).status_code == 403
        assert c.post(f"/stock-counts/{BIG}/submit",
                      json={"lines": [{"product_id": 1, "counted_qty": 1}]}).status_code == 403
        assert c.post(f"/stock-counts/{BIG}/abandon").status_code == 403
        assert c.get("/stock-counts/status").status_code == 200


def test_settings_get_and_put(env):
    assert _as(env, "promo").get("/stock-counts/settings").status_code == 200
    a = _as(env, "admin")
    r = a.put("/stock-counts/settings", json={"interval_days": 14})
    assert r.status_code == 200 and r.json()["interval_days"] == 14
    assert a.get("/stock-counts/status").json()["interval_days"] == 14


@pytest.mark.parametrize("bad", [True, 2.5, 2.0, "2", -1, 10_000_001, None])
def test_submit_counted_qty_strict(env, bad):
    """StrictInt : bool, float (y compris 2.0 en JSON), chaine refuses avant le controleur."""
    c = _as(env, "ctrl")
    r = c.post(f"/stock-counts/{BIG}/submit", json={"lines": [{"product_id": 1, "counted_qty": bad}]})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("body", [
    {"lines": []},
    {"lines": [{"product_id": 1, "counted_qty": 1, "extra": 1}]},
    {"lines": [{"product_id": True, "counted_qty": 1}]},
    {"lines": [{"product_id": "1", "counted_qty": 1}]},
    {"lines": [{"product_id": 1.5, "counted_qty": 1}]},
    {"lines": [{"product_id": 1.0, "counted_qty": 1}]},
    {"lines": [{"product_id": 1, "counted_qty": 1, "observation": "x" * 1001}]},
    {"lines": [{"product_id": 1, "counted_qty": 1}] * 5001},
    {"lines": [{"product_id": 1, "counted_qty": 1}], "other": 1},
    {},
])
def test_submit_body_strict(env, body):
    r = _as(env, "ctrl").post(f"/stock-counts/{BIG}/submit", json=body)
    assert r.status_code == 422, r.text


def test_other_bodies_and_params_strict(env):
    c = _as(env, "ctrl")
    assert c.post("/stock-counts", json={"scope": "partiel"}).status_code == 422
    assert c.post("/stock-counts", json={"x": 1}).status_code == 422
    for bad in (0, 366, True, 1.5, "7"):
        assert _as(env, "admin").put("/stock-counts/settings", json={"interval_days": bad}).status_code == 422
    c = _as(env, "ctrl")
    for url in ("/stock-counts/0", f"/stock-counts/{2**31}", "/stock-counts/abc", "/stock-counts?limit=201",
                "/stock-counts?limit=0", "/stock-counts?offset=-1", f"/stock-counts/{2**31}/abandon",
                # en dernier : erreur levee par le controleur (annule la transaction de test)
                "/stock-counts?date_from=2026-13-01"):
        method = "POST" if url.endswith("abandon") else "GET"
        assert c.request(method, url).status_code == 422, url


def test_list_bad_status_is_422(env):
    r = _as(env, "ctrl").get("/stock-counts?status=bidon")
    assert r.status_code == 422 and "Statut" in r.json()["detail"]


def test_get_unknown_is_404(env):
    r = _as(env, "ctrl").get(f"/stock-counts/{BIG}")
    assert r.status_code == 404 and r.json()["detail"] == "Comptage introuvable."


def test_submit_unknown_product_is_422(env):
    c = _as(env, "ctrl")
    cid = c.post("/stock-counts", json={}).json()["id"]
    r = c.post(f"/stock-counts/{cid}/submit", json={"lines": [{"product_id": 2**31 - 1, "counted_qty": 1}]})
    assert r.status_code == 422, r.text


def test_second_start_is_409(env):
    c = _as(env, "ctrl")
    assert c.post("/stock-counts", json={}).status_code == 201
    r = c.post("/stock-counts", json={})
    assert r.status_code == 409 and r.json()["detail"] == "Vous avez deja un comptage en cours."


def test_abandon_twice_is_409(env):
    c = _as(env, "ctrl")
    cid = c.post("/stock-counts", json={}).json()["id"]
    assert c.post(f"/stock-counts/{cid}/abandon").status_code == 200
    assert c.post(f"/stock-counts/{cid}/abandon").status_code == 409


def test_other_counter_cannot_read_foreign_count_403(env, db_session):
    c = _as(env, "ctrl")
    cid = c.post("/stock-counts", json={}).json()["id"]
    env["users"]["ctrl2"] = create_test_user(db_session, _rand("t_sce_ctrl2"), "StockController")
    r = _as(env, "ctrl2").get(f"/stock-counts/{cid}")
    assert r.status_code == 403 and "propres" in r.json()["detail"]
