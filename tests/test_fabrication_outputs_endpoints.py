# tests/test_fabrication_outputs_endpoints.py
"""Sorties declarees, couche HTTP : routes, schemas stricts, codes d'erreur.

Tout tourne dans la transaction de test (db_session). La matrice des roles et la
vraie connexion sont dans tests/test_fabrication_roles.py.
"""
import uuid
from datetime import date, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from models import FabBatch, Pharmacy
from tests.conftest import create_test_user


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def env(db_session, api_client):
    user = create_test_user(db_session, _rand("t_foe"), "ProductionManager")
    user.roles = [normalize_role_name("ProductionManager")]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    return {"db": db_session, "c": api_client(auth_endpoints, ep), "user": user}


def _batch(env, status="termine", qty_good=100):
    db = env["db"]
    p = Pharmacy(drug_name=_rand("prod"), quantity=0, threshold=0, medication_type="Naturel", forme="Autre")
    db.add(p)
    db.flush()
    b = FabBatch(batch_number=_rand("FE")[:30], product_id=p.medication_id, status=status,
                 production_date=date.today(), qty_good=qty_good, created_by=env["user"].user_id,
                 cancel_reason="test" if status == "annule" else None)
    db.add(b)
    db.flush()
    return b


def _declare(env, bid, body):
    return env["c"].post(f"/fabrication/batches/{bid}/outputs", json=body)


def test_declare_then_batch_detail_carries_derived_fields(env):
    b = _batch(env)
    r = _declare(env, b.id, {"reason": "echantillon", "quantity": 12, "note": "salon"})
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["reason"] == "echantillon" and o["quantity"] == 12 and o["status"] == "active"
    d = env["c"].get(f"/fabrication/batches/{b.id}")
    assert d.status_code == 200, d.text
    d = d.json()
    assert d["qty_outputs"] == 12 and d["qty_shipped"] == 88
    assert [x["id"] for x in d["outputs"]] == [o["id"]]


def test_cancel_output(env):
    b = _batch(env)
    oid = _declare(env, b.id, {"reason": "autre", "quantity": 5, "note": "n"}).json()["id"]
    r = env["c"].post(f"/fabrication/batches/{b.id}/outputs/{oid}/cancel", json={"reason": "erreur"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "annulee"
    again = env["c"].post(f"/fabrication/batches/{b.id}/outputs/{oid}/cancel", json={"reason": "erreur"})
    assert again.status_code == 409
    assert env["c"].get(f"/fabrication/batches/{b.id}").json()["qty_outputs"] == 0


def test_cancel_unknown_or_wrong_batch_is_404(env):
    b, other = _batch(env), _batch(env)
    oid = _declare(env, b.id, {"reason": "autre", "quantity": 1, "note": "n"}).json()["id"]
    assert env["c"].post(f"/fabrication/batches/{other.id}/outputs/{oid}/cancel",
                         json={"reason": "x"}).status_code == 404
    assert env["c"].post(f"/fabrication/batches/{b.id}/outputs/987654321/cancel",
                         json={"reason": "x"}).status_code == 404
    assert _declare(env, 987654321, {"reason": "autre", "quantity": 1, "note": "n"}).status_code == 404


def test_conflicts_are_409(env):
    # une erreur du controleur annule toute la transaction de test : un seul 409 par test
    b = _batch(env, qty_good=10)
    assert _declare(env, b.id, {"reason": "autre", "quantity": 11, "note": "n"}).status_code == 409


def test_declare_outside_termine_is_409(env):
    enc = _batch(env, status="en_production", qty_good=0)
    assert _declare(env, enc.id, {"reason": "autre", "quantity": 1, "note": "n"}).status_code == 409


def test_list_outputs_filtered_by_dates_and_reason(env):
    b = _batch(env)
    e = _declare(env, b.id, {"reason": "echantillon", "quantity": 2}).json()["id"]
    a = _declare(env, b.id, {"reason": "autre", "quantity": 3, "note": "n"}).json()["id"]
    today = date.today()
    r = env["c"].get("/fabrication/outputs", params={"date_from": today.isoformat(),
                                                    "date_to": today.isoformat()})
    assert r.status_code == 200, r.text
    ids = [x["id"] for x in r.json()]
    assert e in ids and a in ids
    row = next(x for x in r.json() if x["id"] == e)
    assert row["batch_number"] == b.batch_number and row["product_id"] == b.product_id
    r = env["c"].get("/fabrication/outputs", params={"reason": "autre"})
    ids = [x["id"] for x in r.json()]
    assert a in ids and e not in ids
    tomorrow = (today + timedelta(days=1)).isoformat()
    r = env["c"].get("/fabrication/outputs", params={"date_from": tomorrow})
    assert r.status_code == 200 and e not in [x["id"] for x in r.json()]


@pytest.mark.parametrize("params", [
    {"date_from": "2026-13-01"},
    {"date_to": "pas-une-date"},
    {"date_from": "2026-10-10", "date_to": "2026-10-01"},
    {"reason": "Echantillon"},
    {"reason": "vol"},
])
def test_list_outputs_bad_filters_422(env, params):
    assert env["c"].get("/fabrication/outputs", params=params).status_code == 422


@pytest.mark.parametrize("body", [
    {"reason": "echantillon", "quantity": 2.5},
    {"reason": "echantillon", "quantity": 2.0},     # StrictInt : un flottant JSON integral est refuse aussi
    {"reason": "echantillon", "quantity": "2"},
    {"reason": "echantillon", "quantity": True},
    {"reason": "echantillon", "quantity": 0},
    {"reason": "echantillon", "quantity": -1},
    {"reason": "echantillon", "quantity": 1000001},
    {"reason": "echantillon", "quantity": 10 ** 30},
    {"reason": "echantillon"},
    {"quantity": 1},
    {"reason": "Echantillon", "quantity": 1},
    {"reason": " autre ", "quantity": 1},         # pas de rognage du motif : refuse
    {"reason": "vol", "quantity": 1},
    {"reason": None, "quantity": 1},
    {"reason": "autre", "quantity": 1, "note": "x" * 2001},
    {"reason": "autre", "quantity": 1},                # note obligatoire pour autre (controleur)
    {"reason": "autre", "quantity": 1, "note": "   "},
    {"reason": "autre", "quantity": 1, "extra": 1},
    [],
])
def test_declare_invalid_inputs_422(env, body):
    b = _batch(env)
    r = _declare(env, b.id, body)
    assert r.status_code == 422, (body, r.status_code, r.text)


@pytest.mark.parametrize("body", [{}, {"reason": ""}, {"reason": "x" * 501}, {"reason": 3},
                                  {"reason": "x", "extra": 1}])
def test_cancel_invalid_inputs_422(env, body):
    b = _batch(env)
    oid = _declare(env, b.id, {"reason": "autre", "quantity": 1, "note": "n"}).json()["id"]
    r = env["c"].post(f"/fabrication/batches/{b.id}/outputs/{oid}/cancel", json=body)
    assert r.status_code == 422, (body, r.status_code, r.text)


@pytest.mark.parametrize("url", [
    "/fabrication/batches/0/outputs",
    "/fabrication/batches/2147483648/outputs",
    "/fabrication/batches/99999999999999999999/outputs",
    "/fabrication/batches/1/outputs/0/cancel",
    "/fabrication/batches/1/outputs/2147483648/cancel",
    "/fabrication/batches/-1/outputs/1/cancel",
])
def test_path_ids_out_of_range_422(env, url):
    body = {"reason": "x"} if url.endswith("cancel") else {"reason": "autre", "quantity": 1, "note": "n"}
    assert env["c"].post(url, json=body).status_code == 422


def test_cancel_reason_500_chars_accepted(env):
    b = _batch(env)
    oid = _declare(env, b.id, {"reason": "autre", "quantity": 1, "note": "n"}).json()["id"]
    r = env["c"].post(f"/fabrication/batches/{b.id}/outputs/{oid}/cancel", json={"reason": "x" * 500})
    assert r.status_code == 200, r.text


def test_output_times_carry_explicit_utc_offset(env):
    """declared_at / cancelled_at sont UTC naifs en base : serialises avec +00:00 (detail, liste, reponses)."""
    b = _batch(env)
    r = _declare(env, b.id, {"reason": "autre", "quantity": 2, "note": "n"})
    oid = r.json()["id"]
    assert r.json()["declared_at"].endswith("+00:00") and r.json()["cancelled_at"] is None
    c = env["c"].post(f"/fabrication/batches/{b.id}/outputs/{oid}/cancel", json={"reason": "erreur"}).json()
    assert c["declared_at"].endswith("+00:00") and c["cancelled_at"].endswith("+00:00")
    o = next(x for x in env["c"].get(f"/fabrication/batches/{b.id}").json()["outputs"] if x["id"] == oid)
    assert o["declared_at"].endswith("+00:00") and o["cancelled_at"].endswith("+00:00")
    row = next(x for x in env["c"].get("/fabrication/outputs").json() if x["id"] == oid)
    assert row["declared_at"].endswith("+00:00") and row["cancelled_at"].endswith("+00:00")


def test_cancel_batch_with_active_output_is_409(env):
    b = _batch(env)
    assert _declare(env, b.id, {"reason": "echantillon", "quantity": 2}).status_code == 201
    r = env["c"].post(f"/fabrication/batches/{b.id}/cancel", json={"reason": "erreur"})
    assert r.status_code == 409
    assert "Annulez d'abord les sorties declarees" in r.text
