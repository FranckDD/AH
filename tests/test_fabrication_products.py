# tests/test_fabrication_products.py
"""Fabrication : GET /fabrication/products, liste {id, name} des produits finis pour les READERS."""
import uuid

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.fabrication import fabrication_endpoints as ep
from api_backend.backend_app.security.role_map import normalize_role_name
from models import Pharmacy
from tests.conftest import create_test_user


def _rand(prefix="t"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def env(db_session, api_client):
    client = api_client(auth_endpoints, ep)
    p = Pharmacy(drug_name=_rand("prod"), quantity=10, threshold=0,
                 medication_type="Naturel", forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db_session.add(p)
    ph = Pharmacy(drug_name=_rand("pharma"), quantity=10, threshold=0,
                  medication_type="Pharmaceutique", forme="Autre", price=0, stock_status="normal")
    ph.update_stock_status()
    db_session.add(ph)
    db_session.flush()
    return {"db": db_session, "c": client, "product": p, "pharma": ph}


def _as(env, role):
    u = create_test_user(env["db"], _rand("t_fp"), role)
    u.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: u


@pytest.mark.parametrize("role", ["ProductionManager", "promoteur", "admin"])
def test_readers_list_products(env, role):
    _as(env, role)
    r = env["c"].get("/fabrication/products")
    assert r.status_code == 200, r.text
    rows = r.json()
    p = env["product"]
    assert {"id": p.medication_id, "name": p.drug_name} in rows
    for row in rows:
        assert set(row) == {"id", "name"}  # aucun champ de cout ni de prix


@pytest.mark.parametrize("role", ["secretaire", "Assistant", "StockController", "medecin"])
def test_other_roles_forbidden(env, role):
    _as(env, role)
    assert env["c"].get("/fabrication/products").status_code == 403


def test_list_only_natural_or_traditional(env):
    _as(env, "ProductionManager")
    trad = Pharmacy(drug_name=_rand("trad"), quantity=1, threshold=0, medication_type="Traditionnel",
                    forme="Autre", price=0, stock_status="normal")
    env["db"].add(trad)
    env["db"].flush()
    ids = {row["id"] for row in env["c"].get("/fabrication/products").json()}
    assert env["product"].medication_id in ids
    assert trad.medication_id in ids
    assert env["pharma"].medication_id not in ids
