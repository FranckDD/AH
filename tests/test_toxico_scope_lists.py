# tests/test_toxico_scope_lists.py
"""Psychologue limite (users.sees_own_toxico_only) : listes actives et sorties,
recherche, export de la liste des sortis, stats du tableau de bord et compteur
mensuel (cache Redis) ne montrent que les dossiers dont il est le referent.
Base de dev partagee : chaque test cree ses donnees avec un marqueur unique."""
import uuid
from datetime import date, datetime, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from controller import toxico_controller
from models.toxico import ToxicoDossier
from repositories.toxico_repo import (
    ToxicoRepository, ToxicoScope, UNRESTRICTED_SCOPE, scope_for_user,
    ToxicoValidationError, ToxicoConflictError, ToxicoForbiddenError, ToxicoNotFoundError,
)
from tests.conftest import create_test_user, create_test_patient

PWD = "TestPass123!"


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


def _user(db, name, role, limited=False):
    u = create_test_user(db, f"t_toxsc_{name}", role, password=PWD)
    u.sees_own_toxico_only = limited
    db.flush()
    return u


def _new(env, suffix, psy, last_name="Scope", admitted=None):
    pid, _ = create_test_patient(env["db"], env["users"]["assistant"],
                                 first_name=f"{env['mark']}{suffix}", last_name=last_name)
    d = env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": admitted or (date.today() - timedelta(days=60)),
        "substance": "Alcool" if psy is env["users"]["psy_a"] else "Cannabis",
        "psychologist_id": psy.user_id})
    return d


@pytest.fixture
def env(db_session):
    db = db_session
    users = {
        "psy_a": _user(db, "psya", "Psychologist", limited=True),
        "psy_b": _user(db, "psyb", "Psychologist"),
        "manager": _user(db, "mgr", "ToxicoManager"),
        "admin": _user(db, "adm", "admin"),
        "assistant": _user(db, "asst", "Assistant", limited=True),
        "spiritual": _user(db, "spi", "SpiritualCounsellor", limited=True),
        "promoteur": _user(db, "promo", "promoteur", limited=True),
    }
    e = {"db": db, "users": users, "repo": ToxicoRepository(db), "mark": "Sc" + uuid.uuid4().hex[:10]}
    e["a_active"] = _new(e, "Aaa", users["psy_a"])
    e["b_active"] = _new(e, "Bee", users["psy_b"])
    pid, _ = create_test_patient(db, users["assistant"], first_name=f"{e['mark']}Nobody", last_name="Scope")
    nobody = ToxicoDossier(patient_id=pid, admission_date=date.today() - timedelta(days=30),
                           substance="Tabac", current_phase=1, is_active=True)
    db.add(nobody)
    db.commit()
    e["unassigned"] = nobody
    mgr_id = users["manager"].user_id
    e["a_out"] = _new(e, "Aout", users["psy_a"])
    e["repo"].discharge(e["a_out"].id, "guerison", None, mgr_id)
    e["b_out"] = _new(e, "Bout", users["psy_b"])
    e["repo"].discharge(e["b_out"].id, "guerison", None, mgr_id)
    # Dernier sejour au nom de A, mais referent desormais B (transfert apres sortie).
    e["moved_out"] = _new(e, "Moved", users["psy_a"])
    e["repo"].discharge(e["moved_out"].id, "abandon", None, mgr_id)
    e["moved_out"].psychologist_id = users["psy_b"].user_id
    db.commit()
    return e


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _active_ids(http, env, **params):
    params.setdefault("search", env["mark"])
    params.setdefault("per_page", 100)
    r = http.get("/toxico/patients", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _discharged_ids(http, env):
    r = http.get("/toxico/dossiers/discharged", params={"search": env["mark"], "per_page": 100})
    assert r.status_code == 200, r.text
    return {x["dossier_id"] for x in r.json()["data"]}


# --- scope_for_user ---------------------------------------------------------

def test_scope_for_user(env):
    u = env["users"]
    u["psy_a"].roles = ["psychologist"]
    assert scope_for_user(u["psy_a"]) == ToxicoScope(u["psy_a"].user_id)
    assert scope_for_user(u["psy_a"]).is_limited is True
    u["psy_b"].roles = ["psychologist"]
    assert scope_for_user(u["psy_b"]) == UNRESTRICTED_SCOPE
    assert UNRESTRICTED_SCOPE.is_limited is False
    for key, role in (("manager", "ToxicoManager"), ("admin", "admin"),
                      ("assistant", "Assistant"), ("spiritual", "SpiritualCounsellor"),
                      ("promoteur", "promoteur")):
        u[key].sees_own_toxico_only = True
        u[key].roles = [normalize_role_name(role)]
        assert scope_for_user(u[key]) == UNRESTRICTED_SCOPE, role
    assert scope_for_user({"user_id": 77, "roles": ["Psychologist"], "sees_own_toxico_only": True}) \
        == ToxicoScope(77)
    assert scope_for_user({"user_id": 77, "roles": ["psychologue"], "sees_own_toxico_only": True}) \
        == ToxicoScope(77)
    assert scope_for_user({"user_id": 77, "roles": ["Psychologist"], "sees_own_toxico_only": False}) \
        == UNRESTRICTED_SCOPE
    assert scope_for_user({"user_id": 77, "roles": ["admin"], "sees_own_toxico_only": True}) \
        == UNRESTRICTED_SCOPE
    assert scope_for_user({"user_id": 77, "roles": ["Psychologist"]}) == UNRESTRICTED_SCOPE


def test_error_classes_carry_optional_code():
    assert ToxicoValidationError("x").code is None
    assert ToxicoConflictError("x", code="same_referent").code == "same_referent"
    assert str(ToxicoConflictError("msg", code="c")) == "msg"
    assert issubclass(ToxicoForbiddenError, ValueError) and issubclass(ToxicoNotFoundError, ValueError)


# --- listes actives --------------------------------------------------------

def test_limited_psychologist_list_shows_only_own_active_patients(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    body = _active_ids(http, env)
    assert body["total"] == 1
    assert [x["dossier_id"] for x in body["data"]] == [env["a_active"].id]
    names = " ".join(x["patientName"] for x in body["data"])
    assert "Bee" not in names and "Nobody" not in names


def test_limited_search_cannot_find_other_patients(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    body = _active_ids(http, env, search=f"{env['mark']}Bee")
    assert body["total"] == 0 and body["data"] == []
    body = _active_ids(http, env, search=f"{env['mark']}Nobody")
    assert body["total"] == 0


def test_unrestricted_psychologist_sees_all(env, http):
    _as(env["users"]["psy_b"], "Psychologist")
    body = _active_ids(http, env)
    assert body["total"] == 3
    assert {x["dossier_id"] for x in body["data"]} == {
        env["a_active"].id, env["b_active"].id, env["unassigned"].id}


def test_toxico_manager_and_admin_see_unassigned_dossier(env, http):
    for key, role in (("manager", "ToxicoManager"), ("admin", "admin")):
        env["users"][key].sees_own_toxico_only = True  # ignore hors psychologue
        _as(env["users"][key], role)
        ids = {x["dossier_id"] for x in _active_ids(http, env)["data"]}
        assert env["unassigned"].id in ids and len(ids) == 3, role


# --- sortis + export -------------------------------------------------------

def test_limited_discharged_list_and_export_only_own(env, http, monkeypatch):
    _as(env["users"]["psy_a"], "Psychologist")
    assert _discharged_ids(http, env) == {env["a_out"].id}

    captured = {}

    def fake_render(template, ctx):
        captured["rows"] = ctx["rows"]
        captured["total"] = ctx["total"]
        return b"%PDF-fake"

    monkeypatch.setattr(toxico_endpoint, "render_pdf_from_template", fake_render)
    r = http.get("/toxico/dossiers/discharged/export", params={"search": env["mark"]})
    assert r.status_code == 200, r.text
    assert captured["total"] == 1
    assert [row["name"] for row in captured["rows"]] == [f"{env['mark']}Aout Scope"]

    _as(env["users"]["psy_b"], "Psychologist")
    assert _discharged_ids(http, env) == {env["a_out"].id, env["b_out"].id, env["moved_out"].id}


# --- stats -----------------------------------------------------------------

def test_limited_stats_are_own_only_and_hide_psychologist_split(env, http):
    env["a_active"].relapse_count = 1
    env["a_active"].current_phase = 2
    env["db"].commit()
    _as(env["users"]["psy_a"], "Psychologist")
    r = http.get("/toxico/stats/dashboard")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["scoped"] is True
    assert s["activeTotal"] == 1
    assert s["byPsychologist"] == []
    assert s["byPhase"] == {"1": 0, "2": 1, "3": 0, "4": 0}
    assert s["bySubstance"] == {"Alcool": 1}
    assert s["relapseRate"] == 100
    assert s["newThisWeek"] == 0


def test_unrestricted_stats_keep_split_and_scoped_false(env, http):
    _as(env["users"]["manager"], "ToxicoManager")
    s = http.get("/toxico/stats/dashboard").json()
    assert s["scoped"] is False
    split = {x["name"]: x["count"] for x in s["byPsychologist"]}
    assert split.get(env["users"]["psy_a"].full_name) == 1
    assert split.get(env["users"]["psy_b"].full_name) == 1
    assert s["activeTotal"] >= 3


def test_limited_month_admissions_ignore_and_do_not_poison_redis_cache(env, http):
    rc = toxico_controller.redis_client
    key = f"toxico:stats:admissions:{datetime.now().strftime('%Y-%m')}"
    previous = rc.get(key)
    ttl = rc.ttl(key)
    try:
        _new(env, "Today", env["users"]["psy_a"], admitted=date.today())
        rc.set(key, 99)
        _as(env["users"]["psy_a"], "Psychologist")
        assert http.get("/toxico/stats/dashboard").json()["currentMonthAdmissions"] == 1
        assert rc.get(key) == "99"
        rc.delete(key)
        assert http.get("/toxico/stats/dashboard").json()["currentMonthAdmissions"] == 1
        assert rc.get(key) is None  # jamais ecrit pour un psychologue limite
        rc.set(key, 99)
        _as(env["users"]["manager"], "ToxicoManager")
        assert http.get("/toxico/stats/dashboard").json()["currentMonthAdmissions"] == 99
    finally:
        if previous is None:
            rc.delete(key)
        else:
            rc.set(key, previous, ex=ttl if ttl and ttl > 0 else None)


# --- autres roles ----------------------------------------------------------

def test_other_roles_unchanged_by_flag(env, http):
    all_active = {env["a_active"].id, env["b_active"].id, env["unassigned"].id}
    all_out = {env["a_out"].id, env["b_out"].id, env["moved_out"].id}
    for key, role in (("promoteur", "promoteur"), ("assistant", "Assistant"),
                      ("spiritual", "SpiritualCounsellor")):
        assert env["users"][key].sees_own_toxico_only is True
        _as(env["users"][key], role)
        assert {x["dossier_id"] for x in _active_ids(http, env)["data"]} == all_active, role
        assert _discharged_ids(http, env) == all_out, role
        assert http.get("/toxico/stats/dashboard").json()["scoped"] is False, role
