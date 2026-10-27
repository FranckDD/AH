# tests/test_toxico_referent_evaluation.py
"""Seul le psychologue referent du dossier peut ajouter une evaluation
(limite ou non). Base de dev partagee : donnees creees avec un marqueur unique."""
import uuid
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import text

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.toxico import ToxicoDossier, ToxicoEvaluation
from repositories.toxico_repo import ToxicoRepository
from tests.conftest import create_test_user, create_test_patient

PWD = "TestPass123!"
BIG = 987654321
BODY = {"decision": "MAINTAIN", "observation": "x", "targetPhase": 1}


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
    u = create_test_user(db, f"t_toxref_{name}", role, password=PWD)
    u.sees_own_toxico_only = limited
    db.flush()
    return u


def _new(env, suffix, referent):
    pid, _ = create_test_patient(env["db"], env["users"]["admin"],
                                 first_name=f"{env['mark']}{suffix}", last_name="Ref")
    return env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=60),
        "substance": "Alcool", "psychologist_id": referent.user_id})


@pytest.fixture
def env(db_session):
    db = db_session
    users = {
        "psy_a": _user(db, "psya", "Psychologist"),
        "psy_b": _user(db, "psyb", "Psychologist"),
        "psy_lim": _user(db, "psylim", "Psychologist", limited=True),
        "manager": _user(db, "mgr", "ToxicoManager"),
        "admin": _user(db, "adm", "admin"),
    }
    return {"db": db, "users": users, "repo": ToxicoRepository(db),
            "mark": "Rf" + uuid.uuid4().hex[:10]}


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _post(http, dossier):
    return http.post("/toxico/evaluation", json={**BODY, "dossier_id": dossier.id})


def _count(env, dossier):
    env["db"].expire_all()
    return env["db"].query(ToxicoEvaluation).filter_by(dossier_id=dossier.id).count()


def test_non_referent_psychologist_gets_403_not_referent_and_nothing_written(env, http):
    d = _new(env, "NonRef", env["users"]["psy_b"])
    _as(env["users"]["psy_a"], "Psychologist")
    r = _post(http, d)
    assert r.status_code == 403, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "not_referent" and detail["message"]
    assert set(detail) == {"code", "message"}
    assert _count(env, d) == 0


def test_referent_psychologist_can_evaluate(env, http):
    d = _new(env, "Ok", env["users"]["psy_a"])
    _as(env["users"]["psy_a"], "Psychologist")
    r = _post(http, d)
    assert r.status_code == 200, r.text
    assert _count(env, d) == 1


def test_referent_is_required_even_when_flag_is_off(env, http):
    assert env["users"]["psy_a"].sees_own_toxico_only is False
    d = _new(env, "FlagOff", env["users"]["psy_b"])
    _as(env["users"]["psy_a"], "Psychologist")
    r = _post(http, d)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "not_referent"
    assert _count(env, d) == 0


def test_dossier_without_referent_cannot_be_evaluated_by_any_psychologist(env, http):
    d = _new(env, "NoRef", env["users"]["psy_b"])
    env["db"].execute(text("UPDATE toxico_dossiers SET psychologist_id = NULL WHERE id = :i"), {"i": d.id})
    env["db"].commit()
    for key in ("psy_a", "psy_b"):
        _as(env["users"][key], "Psychologist")
        r = _post(http, d)
        assert r.status_code == 403 and r.json()["detail"]["code"] == "not_referent", key
    assert _count(env, d) == 0


def test_dossier_whose_referent_is_not_a_psychologist_cannot_be_evaluated(env, http):
    d = _new(env, "MgrRef", env["users"]["manager"])
    _as(env["users"]["psy_a"], "Psychologist")
    r = _post(http, d)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "not_referent"
    assert _count(env, d) == 0


def test_old_referent_is_refused_after_referent_changed(env, http):
    A, B = env["users"]["psy_a"], env["users"]["psy_b"]
    d = _new(env, "Changed", A)
    env["db"].execute(text("UPDATE toxico_dossiers SET psychologist_id = :b WHERE id = :i"),
                      {"b": B.user_id, "i": d.id})
    env["db"].commit()
    _as(A, "Psychologist")
    r = _post(http, d)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "not_referent"
    assert _count(env, d) == 0
    _as(B, "Psychologist")
    assert _post(http, d).status_code == 200
    assert _count(env, d) == 1


def test_readonly_psychologist_cannot_evaluate(env, http):
    """Limite + ancien referent : read_only_access prime (Tache 4), rien d'ecrit."""
    lim, B = env["users"]["psy_lim"], env["users"]["psy_b"]
    d = _new(env, "Ro", lim)
    env["db"].execute(text("UPDATE toxico_dossiers SET psychologist_id = :b WHERE id = :i"),
                      {"b": B.user_id, "i": d.id})
    env["db"].commit()
    _as(lim, "Psychologist")
    r = _post(http, d)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "read_only_access"
    assert _count(env, d) == 0


def test_limited_foreign_dossier_still_looks_like_unknown_id(env, http):
    d = _new(env, "Hidden", env["users"]["psy_b"])
    _as(env["users"]["psy_lim"], "Psychologist")
    foreign = _post(http, d)
    unknown = http.post("/toxico/evaluation", json={**BODY, "dossier_id": BIG})
    assert foreign.status_code == unknown.status_code and foreign.json() == unknown.json()
    assert _count(env, d) == 0


def test_admin_and_toxico_manager_still_403_by_role(env, http):
    d = _new(env, "Roles", env["users"]["psy_a"])
    for key, role in (("admin", "admin"), ("manager", "ToxicoManager")):
        _as(env["users"][key], role)
        r = _post(http, d)
        assert r.status_code == 403, (role, r.text)
        assert not isinstance(r.json().get("detail"), dict) or r.json()["detail"].get("code") != "not_referent"
    assert _count(env, d) == 0


def test_list_item_can_evaluate_only_for_referent(env, http):
    A, B = env["users"]["psy_a"], env["users"]["psy_b"]
    mine = _new(env, "Mine", A)
    theirs = _new(env, "Theirs", B)

    def items(user, role):
        _as(user, role)
        r = http.get("/toxico/patients", params={"search": env["mark"], "per_page": 100})
        assert r.status_code == 200, r.text
        return {x["dossier_id"]: x for x in r.json()["data"]}

    got = items(A, "Psychologist")
    assert got[mine.id]["canEvaluate"] is True and got[mine.id]["psychologistId"] == A.user_id
    assert got[theirs.id]["canEvaluate"] is False and got[theirs.id]["psychologistId"] == B.user_id
    for key, role in (("admin", "admin"), ("manager", "ToxicoManager")):
        got = items(env["users"][key], role)
        assert got[mine.id]["canEvaluate"] is False and got[theirs.id]["canEvaluate"] is False, role


def test_repo_process_evaluation_rechecks_referent_under_lock(env):
    """Course controleur/transfert : le controleur a laisse passer l'ancien referent,
    le referent change avant l'ecriture -> le depot refuse et n'ecrit rien."""
    from repositories.toxico_repo import ToxicoForbiddenError
    A, B = env["users"]["psy_a"], env["users"]["psy_b"]
    d = _new(env, "Race", A)
    env["db"].execute(text("UPDATE toxico_dossiers SET psychologist_id = :b WHERE id = :i"),
                      {"b": B.user_id, "i": d.id})
    env["db"].commit()
    data = {"target_phase": 1, "decision": "MAINTAIN", "observation": "x"}
    with pytest.raises(ToxicoForbiddenError) as ei:
        env["repo"].process_evaluation(d.id, data, A.user_id)
    assert ei.value.code == "not_referent"
    assert _count(env, d) == 0
    env["repo"].process_evaluation(d.id, data, B.user_id)
    assert _count(env, d) == 1
