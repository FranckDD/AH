# tests/test_toxico_evaluation_roles.py
"""Regle metier : SEUL le psychologue (Psychologist) fait l'evaluation psychologique.
Matrice roles x POST /toxico/evaluation. get_current_user est surcharge (pas de
connexion par cas, limite 5/min) ; un test final fait 2 VRAIES connexions."""
from datetime import date

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.toxico import ToxicoDossier, ToxicoEvaluation
from tests.conftest import auth_headers, create_test_user, create_test_patient

PWD = "TestPass123!"
ROLES = ("Psychologist", "SpiritualCounsellor", "admin", "ToxicoManager", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "promoteur", "StockController")
ALLOWED = {"Psychologist"}


@pytest.fixture(scope="module", autouse=True)
def _memoized_password_hash():
    import tests.conftest as cf
    real = cf.pwd_context
    cache = {}

    class _Ctx:
        def hash(self, pw):
            if pw not in cache:
                cache[pw] = real.hash(pw)
            return cache[pw]

        def __getattr__(self, name):
            return getattr(real, name)

    mp = pytest.MonkeyPatch()
    mp.setattr(cf, "pwd_context", _Ctx())
    yield
    mp.undo()


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    users = {r: create_test_user(db, f"t_toxev_{r.lower()}", r, password=PWD) for r in ROLES}
    patient_id, _ = create_test_patient(db, users["Assistant"], first_name="EvalTest")
    dossier = ToxicoDossier(patient_id=patient_id, admission_date=date.today(), substance="Alcool",
                            psychologist_id=users["Psychologist"].user_id, current_phase=1)
    db.add(dossier)
    db.flush()
    client = api_client(auth_endpoints, toxico_endpoint)
    return {"db": db, "client": client, "users": users, "dossier": dossier}


def _body(e):
    return {"dossier_id": e["dossier"].id, "decision": "PROGRESS",
            "observation": "TEST_TOXEV evolution favorable", "targetPhase": 2}


@pytest.mark.parametrize("role", ROLES)
def test_evaluation_role_matrix(env, role):
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r = env["client"].post("/toxico/evaluation", json=_body(env))
    if role in ALLOWED:
        assert r.status_code == 200, (role, r.status_code, r.text)
        assert env["db"].query(ToxicoEvaluation).filter_by(dossier_id=env["dossier"].id).count() == 1
    else:
        assert r.status_code == 403, (role, r.status_code, r.text)
        assert env["db"].query(ToxicoEvaluation).filter_by(dossier_id=env["dossier"].id).count() == 0


def test_evaluation_real_tokens_wiring(env):
    """2 vraies connexions : jeton psychologue accepte, jeton admin refuse."""
    c = env["client"]
    h_psy = auth_headers(c, "t_toxev_psychologist", PWD)
    h_adm = auth_headers(c, "t_toxev_admin", PWD)
    assert c.post("/toxico/evaluation", json=_body(env), headers=h_adm).status_code == 403
    assert c.post("/toxico/evaluation", json=_body(env), headers=h_psy).status_code == 200
