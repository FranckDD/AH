# printer_bridge/tests/test_private_network.py
# Private Network Access (Chrome/Edge) : une page HTTPS qui appelle le pont
# local en http://127.0.0.1 declenche un preflight portant
# Access-Control-Request-Private-Network: true ; sans reponse
# Access-Control-Allow-Private-Network: true, le navigateur bloque l'appel.
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

PROD = "https://app.ahandtohumanity-ngo.org"

BASE_CONFIG = {
    "connection_type": "win32raw",
    "printer_name": "POS Printer Emulator",
    "token": "test-token-123",
    "port": 9123,
}


def make_client(extra=None):
    cfg = dict(BASE_CONFIG)
    cfg.update(extra or {})
    with patch("server.load_config", return_value=cfg):
        import server
        app = server.create_app()
    return TestClient(app), cfg


def preflight(client, origin, pna=True):
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-print-token",
    }
    if pna:
        headers["Access-Control-Request-Private-Network"] = "true"
    return client.options("/print", headers=headers)


def test_preflight_from_allowed_https_origin_gets_allow_private_network_header():
    client, _ = make_client({"allowed_origins": [PROD, "http://localhost:5173"]})
    r = preflight(client, PROD)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == PROD
    assert r.headers["access-control-allow-private-network"] == "true"


def test_unlisted_origin_refused():
    client, _ = make_client({"allowed_origins": ["http://localhost:5173"]})
    r = preflight(client, "https://evil.example.com")
    assert "access-control-allow-origin" not in r.headers
    assert "access-control-allow-private-network" not in r.headers


def test_wildcard_never_accepted(caplog):
    client, _ = make_client({"allowed_origins": ["*", "http://localhost:5173"]})
    with caplog.at_level(logging.WARNING, logger="printer_bridge"):
        client2, _ = make_client({"allowed_origins": ["*"]})
    assert any("*" in rec.getMessage() for rec in caplog.records)
    for c in (client, client2):
        r = preflight(c, "https://evil.example.com")
        assert r.headers.get("access-control-allow-origin") != "*"
        assert "access-control-allow-origin" not in r.headers
        assert "access-control-allow-private-network" not in r.headers
    # l'origine explicite restante reste servie
    ok = preflight(client, "http://localhost:5173")
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_pna_header_absent_when_not_requested():
    client, _ = make_client({"allowed_origins": [PROD]})
    r = preflight(client, PROD, pna=False)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == PROD
    assert "access-control-allow-private-network" not in r.headers


def test_default_origins_do_not_include_production():
    client, _ = make_client()  # pas de cle allowed_origins
    r = preflight(client, PROD)
    assert "access-control-allow-origin" not in r.headers
    assert "access-control-allow-private-network" not in r.headers
    r2 = preflight(client, "http://localhost:5173")
    assert r2.headers["access-control-allow-private-network"] == "true"


def test_normal_requests_still_need_the_token():
    client, cfg = make_client({"allowed_origins": [PROD]})
    with patch("server.load_config", return_value=cfg):
        r = client.post("/print", json={"transaction_id": 1}, headers={"Origin": PROD})
        assert r.status_code == 401
        r = client.post("/print", json={"transaction_id": 1},
                        headers={"Origin": PROD, "X-Print-Token": "bad"})
        assert r.status_code == 401
