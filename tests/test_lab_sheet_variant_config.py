# tests/test_lab_sheet_variant_config.py
"""Variante du titre et du bloc patient des fiches du laboratoire (migration 046) : lecture par tous,
ecriture admin seulement, valeur validee, absence du champ = inchange. Migration et schema CI alignes."""
import os
import re

import pytest

from api_backend.backend_app.routes.admin import config_endpoints
from api_backend.backend_app.routes.auth import auth_endpoints
from repositories.config_repo import ConfigRepository
from tests.conftest import auth_headers, create_test_user

PWD = "TestPass123!"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def env(db_session, api_client):
    for r in ("admin", "Assistant"):
        create_test_user(db_session, f"t_lv_{r.lower()}", r, password=PWD)
    ConfigRepository(db_session).save_config({"name": "Clinique Test"})
    client = api_client(auth_endpoints, config_endpoints)
    return {"client": client, "h": lambda role: auth_headers(client, f"t_lv_{role.lower()}", PWD)}


def test_variant_defaults_to_centered_results(env):
    body = env["client"].get("/config/structure", headers=env["h"]("Assistant")).json()
    assert body["lab_sheet_title_variant"] == "centered_results"


def test_admin_sets_left_variant_other_roles_cannot(env):
    c = env["client"]
    r = c.post("/config/structure", data={"name": "Clinique Test", "lab_sheet_title_variant": "left_laboratory"},
               headers=env["h"]("Assistant"))
    assert r.status_code == 403
    r = c.post("/config/structure", data={"name": "Clinique Test", "lab_sheet_title_variant": "left_laboratory"},
               headers=env["h"]("admin"))
    assert r.status_code == 200 and r.json()["lab_sheet_title_variant"] == "left_laboratory"
    assert c.get("/config/structure", headers=env["h"]("Assistant")).json()["lab_sheet_title_variant"] == "left_laboratory"


def test_save_without_the_field_keeps_it_and_empty_value_resets_to_default(env):
    c = env["client"]
    c.post("/config/structure", data={"name": "Clinique Test", "lab_sheet_title_variant": "left_laboratory"},
           headers=env["h"]("admin"))
    r = c.post("/config/structure", data={"name": "Clinique Renommee"}, headers=env["h"]("admin"))
    assert r.status_code == 200 and r.json()["lab_sheet_title_variant"] == "left_laboratory"
    r = c.post("/config/structure", data={"name": "Clinique Renommee", "lab_sheet_title_variant": ""},
               headers=env["h"]("admin"))
    assert r.status_code == 200 and r.json()["lab_sheet_title_variant"] == "centered_results"


@pytest.mark.parametrize("value", ["centre", "LEFT_LABORATORY", "left_laboratory; drop", "x" * 40])
def test_unknown_variant_is_refused(env, value):
    r = env["client"].post("/config/structure", data={"name": "Clinique Test", "lab_sheet_title_variant": value},
                           headers=env["h"]("admin"))
    assert r.status_code == 422, r.text


def test_database_check_constraint_refuses_unknown_value(db_session):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    ConfigRepository(db_session).save_config({"name": "Clinique Test"})
    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE organization_config SET lab_sheet_title_variant = 'autre'"))
        db_session.flush()
    db_session.rollback()


def test_migration_046_and_schema_ci_are_aligned():
    mig = open(os.path.join(ROOT, "alembic", "versions", "046_lab_sheet_variant.py"), encoding="utf-8").read()
    assert "down_revision = '045_lab_norm_text_groups_notes'" in mig and "revision = '046_lab_sheet_variant'" in mig
    for text_ in ("centered_results", "left_laboratory", "DEFAULT 'centered_results'"):
        assert text_ in mig
    ci = open(os.path.join(ROOT, "ci", "schema_only.sql"), encoding="utf-8").read()
    assert re.search(r"organization_config ADD COLUMN lab_sheet_title_variant varchar\(20\) NOT NULL DEFAULT 'centered_results'", ci)
    assert "ck_organization_config_lab_sheet_variant" in ci and "'left_laboratory'" in ci
