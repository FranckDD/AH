# tests/test_label_settings.py
"""Taille d'etiquette : lecture par tous (route publique existante), ecriture admin seulement."""
import pytest

from api_backend.backend_app.routes.admin import config_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from repositories.config_repo import ConfigRepository
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"


@pytest.fixture
def env(db_session, api_client):
    for r in ("admin", "Assistant", "ToxicoManager"):
        create_test_user(db_session, f"t_lb_{r.lower()}", r, password=PWD)
    ConfigRepository(db_session).save_config({"name": "Clinique Test", "label_width_mm": 50, "label_height_mm": 30})
    client = api_client(auth_endpoints, config_endpoints)
    cache = {}

    def heads(role):
        if role not in cache:
            cache[role] = auth_headers(client, f"t_lb_{role.lower()}", PWD)
        return cache[role]

    return {"client": client, "h": heads}


def test_label_size_defaults_and_admin_only_write(env):
    c = env["client"]
    for role in ("Assistant", "ToxicoManager", "admin"):
        body = c.get("/config/structure", headers=env["h"](role)).json()
        assert (body["label_width_mm"], body["label_height_mm"]) == (50, 30)
    for role in ("Assistant", "ToxicoManager"):
        r = c.post("/config/structure", data={"name": "X", "label_width_mm": "60"}, headers=env["h"](role))
        assert r.status_code == 403, role
    r = c.post("/config/structure", data={"name": "Clinique Test", "label_width_mm": "60", "label_height_mm": "40"},
               headers=env["h"]("admin"))
    assert r.status_code == 200, r.text
    assert (r.json()["label_width_mm"], r.json()["label_height_mm"]) == (60, 40)
    body = c.get("/config/structure", headers=env["h"]("Assistant")).json()
    assert (body["label_width_mm"], body["label_height_mm"]) == (60, 40)


def test_existing_save_without_label_fields_keeps_them(env):
    c = env["client"]
    c.post("/config/structure", data={"name": "Clinique Test", "label_width_mm": "70"}, headers=env["h"]("admin"))
    r = c.post("/config/structure", data={"name": "Clinique Renommee"}, headers=env["h"]("admin"))
    assert r.status_code == 200
    assert r.json()["name"] == "Clinique Renommee" and r.json()["label_width_mm"] == 70


@pytest.mark.parametrize("field,value", [("label_width_mm", "19"), ("label_width_mm", "121"),
                                          ("label_height_mm", "0"), ("label_height_mm", "500"),
                                          ("label_width_mm", "abc")])
def test_label_size_rejects_out_of_range(env, field, value):
    r = env["client"].post("/config/structure", data={"name": "Clinique Test", field: value},
                           headers=env["h"]("admin"))
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("value", ["20", "120"])
def test_label_size_bounds_accepted(env, value):
    r = env["client"].post("/config/structure", data={"name": "Clinique Test", "label_width_mm": value},
                           headers=env["h"]("admin"))
    assert r.status_code == 200 and r.json()["label_width_mm"] == int(value)
