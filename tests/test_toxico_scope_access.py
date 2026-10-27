# tests/test_toxico_scope_access.py
"""Psychologue limite (users.sees_own_toxico_only) : acces direct plein /
lecture seule / refuse, liste "suivis auparavant", portes laterales (export,
consentement, dossier consolide + export, activite recente).
Hors perimetre = 404 identique a un id inconnu (jamais d'indice d'existence).
Base de dev partagee : chaque test cree ses donnees avec un marqueur unique."""
import uuid
from datetime import date, datetime, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.toxico import ToxicoDossier, ToxicoEvaluation, ToxicoPsychologistTransfer
from repositories.toxico_repo import ToxicoRepository, ToxicoScope, UNRESTRICTED_SCOPE
from tests.conftest import create_test_user, create_test_patient

PWD = "TestPass123!"
BIG = 987654321


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
    u = create_test_user(db, f"t_toxacc_{name}", role, password=PWD)
    u.sees_own_toxico_only = limited
    db.flush()
    return u


def _new(env, suffix, psy):
    pid, _ = create_test_patient(env["db"], env["users"]["admin"],
                                 first_name=f"{env['mark']}{suffix}", last_name="Acces")
    return env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=60),
        "substance": "Alcool", "psychologist_id": psy.user_id})


def _transfer(env, dossier, frm, to):
    env["db"].add(ToxicoPsychologistTransfer(
        dossier_id=dossier.id, from_psychologist_id=frm.user_id if frm else None,
        to_psychologist_id=to.user_id, decided_by=env["users"]["manager"].user_id,
        decided_at=datetime.now(), reason="Test transfert"))
    dossier.psychologist_id = to.user_id
    env["db"].commit()


@pytest.fixture
def env(db_session):
    db = db_session
    users = {
        "psy_a": _user(db, "psya", "Psychologist", limited=True),
        "psy_b": _user(db, "psyb", "Psychologist"),
        "manager": _user(db, "mgr", "ToxicoManager", limited=True),
        "admin": _user(db, "adm", "admin", limited=True),
        "medecin": _user(db, "med", "medecin", limited=True),
    }
    e = {"db": db, "users": users, "repo": ToxicoRepository(db), "mark": "Ac" + uuid.uuid4().hex[:10]}
    A, B = users["psy_a"], users["psy_b"]
    e["own"] = _new(e, "Own", A)
    e["foreign"] = _new(e, "Foreign", B)
    # Cause 1 : transfert depuis A (A n'a jamais eu de sejour ni d'evaluation).
    e["by_transfer"] = _new(e, "Transfer", B)
    _transfer(e, e["by_transfer"], A, B)
    # Cause 2 : sejour au nom de A, referent desormais B (sans ligne de transfert).
    e["by_stay"] = _new(e, "Stay", A)
    e["by_stay"].psychologist_id = B.user_id
    db.commit()
    # Cause 3 : evaluation ecrite par A, dossier de B.
    e["by_eval"] = _new(e, "Eval", B)
    db.add(ToxicoEvaluation(dossier_id=e["by_eval"].id, created_by=A.user_id, decision="MAINTAIN",
                            observation=f"{e['mark']} observation", phase_before=1, phase_after=1))
    e["by_eval"].consent_file = "https://example.invalid/consent.pdf"
    e["own"].consent_file = "https://example.invalid/own.pdf"
    e["foreign"].consent_file = "https://example.invalid/foreign.pdf"
    db.commit()
    return e


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint, patient_dossier_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _pid(env, key):
    return env[key].patient_id


# --- acces direct au detail --------------------------------------------------

def test_direct_detail_of_other_patient_is_404_for_limited_psychologist(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    foreign = http.get(f"/toxico/patients/{_pid(env, 'foreign')}")
    unknown = http.get(f"/toxico/patients/{BIG}")
    assert foreign.status_code == 404 and unknown.status_code == 404
    assert foreign.json() == unknown.json()
    assert env["repo"].get_dossier_access(env["foreign"].id, ToxicoScope(env["users"]["psy_a"].user_id)) == "none"
    assert env["repo"].get_dossier_access(BIG, UNRESTRICTED_SCOPE) == "none"


def test_detail_of_own_patient_is_full(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    r = http.get(f"/toxico/patients/{_pid(env, 'own')}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accessMode"] == "full"
    assert body["psychologistId"] == env["users"]["psy_a"].user_id


# --- suivis auparavant -------------------------------------------------------

def _previous(http, env):
    r = http.get("/toxico/dossiers/previous", params={"search": env["mark"], "per_page": 100})
    assert r.status_code == 200, r.text
    return r.json()


def test_previously_followed_list_has_patients_with_transfer_stay_or_evaluation_by_me(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    body = _previous(http, env)
    ids = {x["dossier_id"] for x in body["data"]}
    assert ids == {env["by_transfer"].id, env["by_stay"].id, env["by_eval"].id}
    assert body["total"] == 3 and body["page"] == 1 and body["per_page"] == 100
    item = next(x for x in body["data"] if x["dossier_id"] == env["by_eval"].id)
    assert item["patient_id"] == env["by_eval"].patient_id
    assert item["patientName"] == f"{env['mark']}Eval Acces"
    assert item["psychologist"] == env["users"]["psy_b"].full_name
    assert item["isActive"] is True and item["substance"] == "Alcool" and item["code"]
    items, total = env["repo"].list_previously_followed(env["users"]["psy_a"].user_id, search=env["mark"])
    assert total == 3 and {d.id for d in items} == ids


def test_current_referent_is_not_in_previously_followed(env, http):
    A, B = env["users"]["psy_a"], env["users"]["psy_b"]
    d = _new(env, "Back", A)
    _transfer(env, d, A, B)
    _as(A, "Psychologist")
    assert d.id in {x["dossier_id"] for x in _previous(http, env)["data"]}
    _transfer(env, d, B, A)  # A redevient referent
    assert d.id not in {x["dossier_id"] for x in _previous(http, env)["data"]}
    assert env["repo"].get_dossier_access(d.id, ToxicoScope(A.user_id)) == "full"


def test_readonly_detail_shows_full_history_but_marks_readonly(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    r = http.get(f"/toxico/patients/{_pid(env, 'by_eval')}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accessMode"] == "readonly"
    assert body["psychologistId"] == env["users"]["psy_b"].user_id
    assert len(body["evaluations"]) == 1 and body["evaluations"][0]["observation"]
    assert len(body["stays"]) == 1 and len(body["phaseHistory"]) >= 1


def test_readonly_export_and_consent_are_403_and_foreign_are_404(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    for path in (f"/toxico/patients/{_pid(env, 'by_eval')}/export",
                 f"/toxico/dossiers/{env['by_eval'].id}/consent"):
        r = http.get(path, follow_redirects=False)
        assert r.status_code == 403, (path, r.text)
        assert r.json()["detail"]["code"] == "read_only_access"
        assert r.json()["detail"]["message"]
    exp_f = http.get(f"/toxico/patients/{_pid(env, 'foreign')}/export")
    exp_u = http.get(f"/toxico/patients/{BIG}/export")
    assert exp_f.status_code == exp_u.status_code == 404 and exp_f.json() == exp_u.json()
    con_f = http.get(f"/toxico/dossiers/{env['foreign'].id}/consent", follow_redirects=False)
    con_u = http.get(f"/toxico/dossiers/{BIG}/consent", follow_redirects=False)
    assert con_f.status_code == con_u.status_code == 404 and con_f.json() == con_u.json()
    own = http.get(f"/toxico/dossiers/{env['own'].id}/consent", follow_redirects=False)
    assert own.status_code in (302, 307), own.text


def test_limited_evaluation_on_foreign_dossier_looks_like_unknown_id(env, http):
    """Porte laterale POST /toxico/evaluation : hors perimetre = meme reponse qu'un id inconnu, rien d'ecrit."""
    _as(env["users"]["psy_a"], "Psychologist")
    body = {"decision": "MAINTAIN", "observation": "x", "targetPhase": 1}
    foreign = http.post("/toxico/evaluation", json={**body, "dossier_id": env["foreign"].id})
    unknown = http.post("/toxico/evaluation", json={**body, "dossier_id": BIG})
    assert foreign.status_code == unknown.status_code and foreign.json() == unknown.json(), foreign.text
    assert env["db"].query(ToxicoEvaluation).filter_by(dossier_id=env["foreign"].id).count() == 0


def test_readonly_evaluation_is_403_and_writes_nothing(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    before = env["db"].query(ToxicoEvaluation).filter_by(dossier_id=env["by_stay"].id).count()
    r = http.post("/toxico/evaluation", json={"decision": "MAINTAIN", "observation": "x",
                                              "targetPhase": 1, "dossier_id": env["by_stay"].id})
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "read_only_access" and r.json()["detail"]["message"]
    assert env["db"].query(ToxicoEvaluation).filter_by(dossier_id=env["by_stay"].id).count() == before


# --- dossier consolide -------------------------------------------------------

def test_consolidated_dossier_drops_toxico_block_outside_scope_but_keeps_flags(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    r = http.get(f"/patients/{_pid(env, 'foreign')}/dossier")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "dossier_toxico" not in body
    assert body["flags"]["is_toxicology"] is True
    ro = http.get(f"/patients/{_pid(env, 'by_eval')}/dossier").json()
    assert ro["dossier_toxico"]["accessMode"] == "readonly"
    own = http.get(f"/patients/{_pid(env, 'own')}/dossier").json()
    assert own["dossier_toxico"]["accessMode"] == "full"


def test_consolidated_dossier_other_domains_still_served(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    body = http.get(f"/patients/{_pid(env, 'foreign')}/dossier").json()
    for key in ("patient", "historique_medical", "prescriptions", "historique_labo", "historique_spirituel"):
        assert key in body, key
    assert body["domaines_indisponibles"] == []
    assert body["patient"]["patient_id"] == _pid(env, "foreign")


def test_dossier_export_pdf_and_excel_omit_toxico_block_for_limited_psychologist(env, http, monkeypatch):
    captured = {}

    def fake_pdf(template, ctx):
        captured["pdf"] = ctx
        return b"%PDF-fake"

    def fake_excel(dossier):
        captured["excel"] = dossier
        return b"xlsx"

    monkeypatch.setattr(patient_dossier_endpoint, "render_pdf_from_template", fake_pdf)
    monkeypatch.setattr(patient_dossier_endpoint, "build_dossier_excel", fake_excel)
    _as(env["users"]["psy_a"], "Psychologist")
    for key in ("foreign", "by_eval"):
        r = http.get(f"/patients/{_pid(env, key)}/dossier/export", params={"format": "pdf"})
        assert r.status_code == 200, r.text
        assert captured["pdf"]["dossier_toxico"] is None, key
        r = http.get(f"/patients/{_pid(env, key)}/dossier/export", params={"format": "excel"})
        assert r.status_code == 200, r.text
        assert "dossier_toxico" not in captured["excel"], key
    http.get(f"/patients/{_pid(env, 'own')}/dossier/export", params={"format": "pdf"})
    assert captured["pdf"]["dossier_toxico"]["dossier_id"] == env["own"].id
    http.get(f"/patients/{_pid(env, 'own')}/dossier/export", params={"format": "excel"})
    assert captured["excel"]["dossier_toxico"]["dossier_id"] == env["own"].id


def test_dossier_recent_404_for_limited_psychologist_outside_scope_200_inside(env, http):
    _as(env["users"]["psy_a"], "Psychologist")
    unknown = http.get(f"/patients/{BIG}/dossier/recent")
    assert unknown.status_code == 404
    for key in ("foreign", "by_eval"):
        pid = _pid(env, key)
        r = http.get(f"/patients/{pid}/dossier/recent")
        assert r.status_code == 404, (key, r.text)
        assert r.json()["detail"] == unknown.json()["detail"].replace(str(BIG), str(pid)), key
    r = http.get(f"/patients/{_pid(env, 'own')}/dossier/recent")
    assert r.status_code == 200, r.text


# --- autres roles ------------------------------------------------------------

def test_unrestricted_psychologist_and_other_roles_keep_full_access(env, http, monkeypatch):
    monkeypatch.setattr(toxico_endpoint, "render_pdf_from_template", lambda t, c: b"%PDF-fake")
    for key, role in (("psy_b", "Psychologist"), ("manager", "ToxicoManager"), ("admin", "admin")):
        _as(env["users"][key], role)
        for d in ("own", "foreign", "by_eval"):
            r = http.get(f"/toxico/patients/{_pid(env, d)}")
            assert r.status_code == 200 and r.json()["accessMode"] == "full", (role, d)
            assert http.get(f"/toxico/patients/{_pid(env, d)}/export").status_code == 200, (role, d)
            con = http.get(f"/toxico/dossiers/{env[d].id}/consent", follow_redirects=False)
            assert con.status_code in (302, 307), (role, d, con.text)
            body = http.get(f"/patients/{_pid(env, d)}/dossier").json()
            assert body["dossier_toxico"]["accessMode"] == "full", (role, d)
            assert http.get(f"/patients/{_pid(env, d)}/dossier/recent").status_code == 200, (role, d)
    _as(env["users"]["medecin"], "medecin")
    body = http.get(f"/patients/{_pid(env, 'own')}/dossier").json()
    assert "dossier_toxico" not in body  # regle medecin/nurse inchangee
