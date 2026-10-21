# tests/test_stock_extra_fields.py
"""Ledger item 4b : un corps portant un champ reserve au serveur (status, created_by,
controlled_by) est refuse en 422 - jamais pris en compte silencieusement."""
from datetime import date

import pytest

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.stock import stock_endpoints
from models.pharmacy import Pharmacy
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
TODAY = date.today().isoformat()
FORBIDDEN = {"status": "valide", "created_by": 1, "controlled_by": 1}


@pytest.fixture
def env(db_session, api_client):
    p = Pharmacy(drug_name="TEST_XF_PROD", quantity=50, threshold=5, medication_type="pharmaceutique",
                 forme="Autre", price=0, stock_status="normal")
    p.update_stock_status()
    db_session.add(p)
    db_session.flush()
    return {"db": db_session, "client": api_client(auth_endpoints, stock_endpoints), "pid": p.medication_id}


def test_receipt_and_incident_reject_server_fields(env):
    create_test_user(env["db"], "t_xf_assist", "Assistant", password=PWD)
    h = auth_headers(env["client"], "t_xf_assist", PWD)
    bodies = {
        "/stock/receipts": {"origin": "fournisseur", "supplier": "ACME", "received_date": TODAY,
                            "lines": [{"product_id": env["pid"], "qty_good": 1}]},
        "/stock/incidents": {"product_id": env["pid"], "kind": "perdu", "quantity": 1,
                             "reason": "egare", "incident_date": TODAY},
    }
    for url, base in bodies.items():
        assert env["client"].post(url, json=base, headers=h).status_code == 201, url  # temoin
        for k, v in FORBIDDEN.items():
            r = env["client"].post(url, json={**base, k: v}, headers=h)
            assert r.status_code == 422, (url, k, r.status_code, r.text)


def test_adjustment_request_rejects_server_fields(env):
    create_test_user(env["db"], "t_xf_secr", "secretaire", password=PWD)
    h = auth_headers(env["client"], "t_xf_secr", PWD)
    base = {"product_id": env["pid"], "kind": "correction", "quantity": 7, "reason": "inventaire"}
    assert env["client"].post("/stock/adjustment-requests", json=base, headers=h).status_code == 201
    for k, v in FORBIDDEN.items():
        r = env["client"].post("/stock/adjustment-requests", json={**base, k: v}, headers=h)
        assert r.status_code == 422, (k, r.status_code, r.text)
