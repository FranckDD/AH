# tests/test_toxico_scope_roles.py
"""Psychologues limites et transferts : matrice roles x routes nouvelles.

La table est DERIVEE de l'application reelle (une route nouvelle oubliee casse
test_routes_table_covers_router). La Tache 6 y ajoute POST .../transfer."""
import re

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from datetime import date, timedelta

from models.toxico import ToxicoDossier, ToxicoPsychologistTransfer
from repositories.toxico_repo import ToxicoRepository
from tests.conftest import auth_headers, create_test_user, create_test_patient

PWD = "TestPass123!"
BIG = 987654321
ROLES = ("Psychologist", "ToxicoManager", "admin", "promoteur", "SpiritualCounsellor", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "StockController")

ROUTES = {
    ("GET", "/toxico/dossiers/previous"): {"Psychologist"},
    ("POST", "/toxico/dossiers/{dossier_id}/transfer"): {"ToxicoManager", "admin"},
}
TRANSFER = ("POST", "/toxico/dossiers/{dossier_id}/transfer")


def _feature_routes():
    out = set()
    for r in app.routes:
        path = getattr(r, "path", "")
        if path.startswith("/toxico/dossiers/previous") or re.search(r"/toxico/dossiers/\{[^}]+\}/transfer", path):
            for m in (r.methods or ()):
                if m not in ("HEAD", "OPTIONS"):
                    out.add((m, path))
    return out


def _url(path):
    return re.sub(r"\{[^}]+\}", str(BIG), path)


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
    users = {r: create_test_user(db_session, f"t_toxscr_{r.lower()}", r, password=PWD) for r in ROLES}
    users["psy_b"] = create_test_user(db_session, "t_toxscr_psyb", "Psychologist", password=PWD)
    return {"client": api_client(auth_endpoints, toxico_endpoint), "users": users, "db": db_session}


def _transfer_dossier(env):
    """Dossier dont le Psychologist de la matrice est le referent (meme referent)."""
    pid, _ = create_test_patient(env["db"], env["users"]["admin"], first_name="ScopeTransf", last_name="Rl")
    return ToxicoRepository(env["db"]).create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=10), "substance": "Alcool",
        "psychologist_id": env["users"]["Psychologist"].user_id})


def _call(env, route, headers=None):
    if route == TRANSFER:
        d = _transfer_dossier(env)
        r = env["client"].post(route[1].replace("{dossier_id}", str(d.id)), headers=headers,
                               json={"to_psychologist_id": env["users"]["psy_b"].user_id, "reason": "Matrice"})
        return r, d
    return env["client"].request(route[0], _url(route[1]), headers=headers), None


def test_routes_table_covers_router():
    assert _feature_routes() == set(ROUTES), sorted(_feature_routes() ^ set(ROUTES))


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("route", sorted(ROUTES))
def test_role_matrix(env, route, role):
    user = env["users"][role]
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user
    r, d = _call(env, route)
    if role in ROUTES[route]:
        assert r.status_code == 200, (route, role, r.status_code, r.text)
    else:
        assert r.status_code == 403, (route, role, r.status_code, r.text)
    if d is not None:
        env["db"].expire_all()
        n = env["db"].query(ToxicoPsychologistTransfer).filter_by(dossier_id=d.id).count()
        assert n == (1 if role in ROUTES[route] else 0)


def test_unauthenticated_refused(env):
    for route in sorted(ROUTES):
        r, _ = _call(env, route)
        assert r.status_code == 401, (route, r.status_code)


def test_real_login_wiring(env):
    """2 vraies connexions : jeton responsable accepte, jeton psychologue (referent) refuse."""
    h_psy = auth_headers(env["client"], "t_toxscr_psychologist", PWD)
    h_mgr = auth_headers(env["client"], "t_toxscr_toxicomanager", PWD)
    r, _ = _call(env, TRANSFER, headers=h_psy)
    assert r.status_code == 403, r.text
    r, _ = _call(env, TRANSFER, headers=h_mgr)
    assert r.status_code == 200, r.text
