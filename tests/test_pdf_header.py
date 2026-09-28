# tests/test_pdf_header.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
from api_backend.backend_app.utils.pdf_header import resolve_local_asset_path, get_ticket_header_context


def test_resolve_local_asset_path_returns_none_for_empty_url():
    assert resolve_local_asset_path(None) is None
    assert resolve_local_asset_path("") is None


def test_resolve_local_asset_path_returns_none_for_missing_file():
    assert resolve_local_asset_path("/static/uploads/logos/does-not-exist.png") is None


def test_resolve_local_asset_path_resolves_existing_relative_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("static/uploads/logos", exist_ok=True)
    with open("static/uploads/logos/real.png", "wb") as f:
        f.write(b"fake-png-bytes")
    result = resolve_local_asset_path("/static/uploads/logos/real.png")
    assert result is not None
    assert result.name == "real.png"


def test_get_ticket_header_context_no_logo_when_field_empty():
    structure = MagicMock(ticket_logo_url=None)
    config_ctrl = MagicMock()
    config_ctrl.get_structure_info.return_value = structure
    ctx = get_ticket_header_context(config_ctrl)
    assert ctx["structure"] is structure
    assert ctx["ticket_logo_path"] is None
