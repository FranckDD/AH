# tests/test_auth_manager.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
from managers.auth_manager import AuthManager


def make_manager_with_gateway_response(login_response):
    gateway = MagicMock()
    gateway.login.return_value = login_response
    manager = AuthManager(gateway)
    manager.settings = MagicMock()  # evite d'ecrire dans le registre Windows reel
    return manager


def test_login_surfaces_fastapi_detail_message():
    manager = make_manager_with_gateway_response(
        {"detail": "Identifiants invalides", "_status_code": 401}
    )
    success, payload = manager.login("admin_test", "mauvais_mdp")
    assert success is False
    assert payload["details"] == "Identifiants invalides"


def test_login_surfaces_rate_limit_error_message():
    manager = make_manager_with_gateway_response(
        {"error": "Rate limit exceeded: 5 per 1 minute", "_status_code": 429}
    )
    success, payload = manager.login("admin_test", "x")
    assert success is False
    assert "Rate limit exceeded" in payload["details"]


def test_login_surfaces_gateway_network_error():
    manager = make_manager_with_gateway_response(
        {"error": "Network error", "details": "Connection refused", "_status_code": None}
    )
    success, payload = manager.login("admin_test", "x")
    assert success is False
    assert payload["details"] == "Connection refused"


def test_login_falls_back_when_no_recognizable_error_shape():
    manager = make_manager_with_gateway_response({"_status_code": 500})
    success, payload = manager.login("admin_test", "x")
    assert success is False
    assert payload["details"] == "Erreur inconnue du serveur"


def test_login_success_path_unaffected():
    gateway = MagicMock()
    gateway.login.return_value = {"access_token": "abc123", "_status_code": 200}
    gateway.request.return_value = {"id": 1, "username": "admin_test"}
    manager = AuthManager(gateway)
    manager.settings = MagicMock()

    success, payload = manager.login("admin_test", "wSaBGTy6fD2QUHub")
    assert success is True
    assert payload["token"] == "abc123"
