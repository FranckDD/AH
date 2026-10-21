# tests/test_pharmacy_qty_guard.py
"""Ledger item 4a : garde 'quantity' de PharmacyController (fail-closed) et
traduction PermissionError -> 403 sur PUT /pharmacy/{id}. Aucun login."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.pharmacy import pharmacy_endpoints
from api_backend.backend_app.routes.auth.auth_endpoints import get_current_user
from controller.pharmacy_controller import PharmacyController


def test_controller_quantity_guard_fails_closed_without_user():
    repo = MagicMock()
    ctrl = PharmacyController(repo, None)
    with pytest.raises(PermissionError):
        ctrl.update_product(1, {"quantity": 5})
    repo.update.assert_not_called()


def test_update_endpoint_maps_permission_error_to_403():
    fake = SimpleNamespace(user=SimpleNamespace(roles=["admin"]),
                           update_product=MagicMock(side_effect=PermissionError("interdit")))
    app.dependency_overrides[pharmacy_endpoints.get_pharmacy_controller] = lambda: fake
    app.dependency_overrides[get_current_user] = lambda: fake.user  # role_required -> admin
    try:
        r = TestClient(app).put("/pharmacy/1", json={"quantity": 5})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 403, r.text
