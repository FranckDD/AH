# printer_bridge/tests/test_server.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

FAKE_CONFIG = {
    "connection_type": "win32raw",
    "printer_name": "POS Printer Emulator",
    "vendor_id": None,
    "product_id": None,
    "token": "test-token-123",
    "port": 9123,
}


@pytest.fixture
def client():
    # Note: le patch doit rester actif pendant tout le corps du test, pas
    # seulement pendant la construction du TestClient - un `return` a
    # l'interieur du `with` fermerait le contexte (et donc de-patcherait
    # server.load_config) avant meme que le test n'emette sa requete HTTP.
    # `yield` garde le contexte ouvert jusqu'a la fin du test.
    with patch("server.load_config", return_value=FAKE_CONFIG):
        import server
        yield TestClient(server.app)


def test_health_endpoint_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_print_endpoint_rejects_missing_token(client):
    r = client.post("/print", json={"transaction_id": 1})
    assert r.status_code == 401


def test_print_endpoint_rejects_wrong_token(client):
    r = client.post("/print", json={"transaction_id": 1}, headers={"X-Print-Token": "wrong"})
    assert r.status_code == 401


def test_print_endpoint_accepts_correct_token_and_calls_render(client):
    with patch("server.get_active_printer") as mock_get_printer, \
         patch("server.render_ticket") as mock_render:
        mock_get_printer.return_value = MagicMock()
        r = client.post(
            "/print",
            json={"transaction_id": 1, "header": {}, "items": []},
            headers={"X-Print-Token": "test-token-123"},
        )
        assert r.status_code == 200
        mock_render.assert_called_once()


def test_print_endpoint_returns_503_when_printer_unreachable(client):
    with patch("server.get_active_printer", side_effect=Exception("printer offline")):
        r = client.post(
            "/print",
            json={"transaction_id": 1, "header": {}, "items": []},
            headers={"X-Print-Token": "test-token-123"},
        )
        assert r.status_code == 503


def test_print_endpoint_returns_500_when_render_fails(client):
    with patch("server.get_active_printer") as mock_get_printer, \
         patch("server.render_ticket", side_effect=Exception("render error")):
        mock_get_printer.return_value = MagicMock()
        r = client.post(
            "/print",
            json={"transaction_id": 1, "header": {}, "items": []},
            headers={"X-Print-Token": "test-token-123"},
        )
        assert r.status_code == 500
