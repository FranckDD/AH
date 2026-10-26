"""Defaut releve par les guides (2026-10-26) : sortie de toxicologie d'un patient
hospitalise sans aucun avertissement. Le ToxicoManager ne peut pas lire
/hospitalizations/patient/{id} (403) : un indicateur minimal passe par /toxico."""
from datetime import date, datetime

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.routes.hospitalizations import hospitalization_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.hospitalization import Hospitalization
from models.toxico import ToxicoDossier, ToxicoStay
from tests.conftest import create_test_user, create_test_patient

PWD = "TestPass123!"


@pytest.fixture
def env(db_session, api_client):
    mgr = create_test_user(db_session, "t_toxdh_mgr", "ToxicoManager", password=PWD)
    doc = create_test_user(db_session, "t_toxdh_doc", "medecin", password=PWD)
    patient_id, _ = create_test_patient(db_session, mgr, first_name="ToxHosp")
    d = ToxicoDossier(patient_id=patient_id, admission_date=date.today(), substance="Alcool", current_phase=1)
    db_session.add(d)
    db_session.flush()
    db_session.add(ToxicoStay(dossier_id=d.id, stay_number=1, admission_date=date.today(), substance="Alcool"))
    db_session.flush()
    mgr.roles = [normalize_role_name("ToxicoManager")]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: mgr
    client = api_client(auth_endpoints, toxico_endpoint, hospitalization_endpoint)
    return {"db": db_session, "client": client, "dossier": d, "patient_id": patient_id, "doc": doc}


def _admit(env):
    h = Hospitalization(patient_id=env["patient_id"], admitted_by=env["doc"].user_id,
                        admitted_at=datetime(2026, 10, 26, 6, 38))
    env["db"].add(h)
    env["db"].flush()
    return h


def test_manager_cannot_read_hospitalization_history_hence_the_flag(env):
    assert env["client"].get(f"/hospitalizations/patient/{env['patient_id']}").status_code == 403


def test_open_hospitalization_flag_when_stay_open(env):
    h = _admit(env)
    r = env["client"].get(f"/toxico/dossiers/{env['dossier'].id}/open-hospitalization")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["open"] is True
    assert body["hospitalization_id"] == h.id
    assert body["admitted_at"].startswith("2026-10-26T06:38")


def test_open_hospitalization_flag_false_when_none_or_closed(env):
    url = f"/toxico/dossiers/{env['dossier'].id}/open-hospitalization"
    assert env["client"].get(url).json() == {"open": False, "hospitalization_id": None, "admitted_at": None}
    h = _admit(env)
    h.discharged_at = datetime(2026, 10, 26, 9, 0)
    env["db"].flush()
    assert env["client"].get(url).json()["open"] is False


def test_open_hospitalization_flag_unknown_dossier_404(env):
    assert env["client"].get("/toxico/dossiers/999999999/open-hospitalization").status_code == 404


def test_discharge_reports_open_stay_and_leaves_it_open(env):
    h = _admit(env)
    r = env["client"].post(f"/toxico/discharge/{env['dossier'].id}", json={"reason": "guerison"})
    assert r.status_code == 200, r.text
    assert r.json()["open_hospitalization"]["hospitalization_id"] == h.id
    env["db"].refresh(h)
    assert h.discharged_at is None  # laisse ouvert en connaissance de cause, jamais clos en silence


def test_discharge_without_open_stay_has_no_warning_payload(env):
    r = env["client"].post(f"/toxico/discharge/{env['dossier'].id}", json={"reason": "guerison"})
    assert r.status_code == 200, r.text
    assert r.json()["open_hospitalization"] is None
