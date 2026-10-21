# tests/test_toxico_discharged_list.py
"""GET /toxico/dossiers/discharged : liste paginée des patients sortis.
Base de dev partagée : chaque test crée ses patients avec un marqueur unique
et ne filtre/affirme que sur eux (search=<marqueur>)."""
import uuid
from datetime import date, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.toxico import ToxicoDossier, ToxicoStay
from repositories.toxico_repo import ToxicoRepository
from tests.conftest import auth_headers, create_test_user, create_test_patient

PWD = "TestPass123!"
ROLES = ("Psychologist", "SpiritualCounsellor", "admin", "ToxicoManager", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "promoteur", "StockController")
READ_ALLOWED = {"ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin",
                "promoteur"}  # 2026-10-22 : lecture ouverte au promoteur (validation de sortie)
URL = "/toxico/dossiers/discharged"


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
def env(db_session):
    db = db_session
    users = {r: create_test_user(db, f"t_toxdl_{r.lower()}", r, password=PWD) for r in ROLES}
    users["psy2"] = create_test_user(db, "t_toxdl_psy2", "Psychologist", password=PWD)
    return {"db": db, "users": users, "repo": ToxicoRepository(db),
            "mark": "Dl" + uuid.uuid4().hex[:10]}


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _new(env, suffix="A", last_name="Sortie"):
    pid, code = create_test_patient(env["db"], env["users"]["Assistant"],
                                    first_name=f"{env['mark']}{suffix}", last_name=last_name)
    d = env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=60), "substance": "Alcool",
        "psychologist_id": env["users"]["Psychologist"].user_id})
    return pid, code, d.id


def _discharge(env, dossier_id, reason="guerison", note=None, on=None):
    env["repo"].discharge(dossier_id, reason, note, env["users"]["ToxicoManager"].user_id)
    if on is not None:
        s = env["db"].query(ToxicoStay).filter_by(dossier_id=dossier_id) \
            .order_by(ToxicoStay.stay_number.desc()).first()
        s.discharge_date = on
        env["db"].commit()


def _get(http, env, **params):
    params.setdefault("search", env["mark"])
    return http.get(URL, params=params)


def test_seuls_les_dossiers_inactifs_sont_listes(env, http):
    _, _, active = _new(env, "Act")
    _, _, out = _new(env, "Out")
    _discharge(env, out)
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    r = _get(http, env)
    assert r.status_code == 200, r.text
    ids = [x["dossier_id"] for x in r.json()["data"]]
    assert ids == [out] and active not in ids


def test_dernier_sejour_apres_readmission_et_nouvelle_sortie(env, http):
    db, repo, users = env["db"], env["repo"], env["users"]
    pid, code, did = _new(env, "Two")
    _discharge(env, did, "abandon", on=date.today() - timedelta(days=20))
    repo.create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=10), "substance": "Cannabis",
        "psychologist_id": users["psy2"].user_id})
    _discharge(env, did, "exclusion", "règlement")
    _as(users["Psychologist"], "Psychologist")
    item = _get(http, env).json()["data"][0]
    assert item["dossier_id"] == did and item["patient_id"] == pid and item["code"] == code
    assert item["patientName"] == f"{env['mark']}Two Sortie"
    assert item["stays_count"] == 2
    ls = item["last_stay"]
    assert ls["stay_number"] == 2 and ls["discharge_reason"] == "exclusion"
    assert "discharge_note" not in ls and ls["substance"] == "Cannabis"
    assert ls["admission_date"] == (date.today() - timedelta(days=10)).isoformat()
    assert ls["discharge_date"] == date.today().isoformat()
    assert ls["psychologist_name"] == users["psy2"].full_name
    assert ls["discharged_by_name"] == users["ToxicoManager"].full_name


def test_recherche_nom_et_code_insensible_a_la_casse(env, http):
    _, code, did = _new(env, "Srch", last_name="Zebulon")
    _discharge(env, did)
    _as(env["users"]["admin"], "admin")
    assert [x["dossier_id"] for x in _get(http, env, search=env["mark"].upper()).json()["data"]] == [did]
    assert did in [x["dossier_id"] for x in _get(http, env, search=f"{env['mark']}srch zebulon").json()["data"]]
    assert [x["dossier_id"] for x in _get(http, env, search=code.lower()).json()["data"]] == [did]


def test_filtres_motif_et_dates_et_tri(env, http):
    today = date.today()
    _, _, a = _new(env, "R1")
    _, _, b = _new(env, "R2")
    _, _, c = _new(env, "R3")
    _discharge(env, a, "guerison", on=today - timedelta(days=10))
    _discharge(env, b, "abandon", on=today - timedelta(days=5))
    _discharge(env, c, "guerison", on=today - timedelta(days=5))
    _as(env["users"]["Assistant"], "Assistant")
    ids = lambda **p: [x["dossier_id"] for x in _get(http, env, **p).json()["data"]]
    assert ids() == [max(b, c), min(b, c), a]  # date desc puis id desc (stable)
    assert ids(reason="guerison") == [c, a]
    assert ids(reason="abandon") == [b]
    d5 = (today - timedelta(days=5)).isoformat()
    d10 = (today - timedelta(days=10)).isoformat()
    assert sorted(ids(discharged_from=d5)) == sorted([b, c])
    assert ids(discharged_to=d10) == [a]
    assert ids(discharged_from=d10, discharged_to=d10) == [a]
    assert sorted(ids(discharged_from=d10, discharged_to=d5, reason="guerison")) == sorted([a, c])


@pytest.mark.parametrize("wild", ["_", "%", "\\", "%_%"])
def test_jokers_sql_echappes(env, http, wild):
    _, _, did = _new(env, "Wild")
    _discharge(env, did)
    _as(env["users"]["admin"], "admin")
    r = http.get(URL, params={"search": wild, "per_page": 100})
    assert r.status_code == 200, r.text
    assert did not in [x["dossier_id"] for x in r.json()["data"]]
    # le marqueur suivi d'un joker ne correspond pas non plus
    assert _get(http, env, search=env["mark"] + "_").json()["data"] == []
    assert _get(http, env, search=env["mark"] + "%").json()["data"] == []


@pytest.mark.parametrize("params", [{"reason": "inconnu"}, {"discharged_from": "pas-une-date"},
                                    {"discharged_from": "2026-05-02", "discharged_to": "2026-05-01"},
                                    {"per_page": 0}, {"per_page": 101}, {"page": 0}])
def test_parametres_invalides_422(env, http, params):
    _as(env["users"]["admin"], "admin")
    assert _get(http, env, **params).status_code == 422


def test_pagination(env, http):
    for i in range(3):
        _, _, d = _new(env, f"P{i}")
        _discharge(env, d)
    _as(env["users"]["admin"], "admin")
    body = _get(http, env, per_page=2, page=1).json()
    assert (body["total"], body["total_pages"], body["page"], body["per_page"]) == (3, 2, 1, 2)
    assert len(body["data"]) == 2
    body2 = _get(http, env, per_page=2, page=2).json()
    assert len(body2["data"]) == 1
    assert not {x["dossier_id"] for x in body["data"]} & {x["dossier_id"] for x in body2["data"]}
    empty = _get(http, env, search=env["mark"] + "none").json()
    assert (empty["total"], empty["total_pages"], empty["data"]) == (0, 0, [])


def test_patient_readmis_disparait_de_la_liste(env, http):
    pid, _, did = _new(env, "Back")
    _discharge(env, did)
    _as(env["users"]["admin"], "admin")
    assert [x["dossier_id"] for x in _get(http, env).json()["data"]] == [did]
    env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": date.today(), "substance": "Alcool",
        "psychologist_id": env["users"]["psy2"].user_id})
    assert _get(http, env).json()["data"] == []


def test_dossier_sans_sejour_ne_plante_pas(env, http):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name=f"{env['mark']}NoStay")
    d = ToxicoDossier(patient_id=pid, admission_date=date.today(), substance="Alcool",
                      current_phase=1, is_active=False)
    env["db"].add(d)
    env["db"].commit()
    _as(env["users"]["admin"], "admin")
    r = _get(http, env)
    assert r.status_code == 200, r.text
    item = r.json()["data"][0]
    assert item["dossier_id"] == d.id and item["stays_count"] == 0 and item["last_stay"] is None


@pytest.mark.parametrize("role", ROLES)
def test_matrice_de_roles(env, http, role):
    _as(env["users"][role], role)
    r = _get(http, env)
    assert r.status_code == (200 if role in READ_ALLOWED else 403), (role, r.text)


def test_sans_authentification_refuse(env, http):
    app.dependency_overrides.pop(auth_endpoints.get_current_user, None)
    assert http.get(URL).status_code == 401


def test_jetons_reels(env, http):
    """2 vraies connexions : psychologue accepté, secrétaire refusée."""
    h_psy = auth_headers(http, "t_toxdl_psychologist", PWD)
    h_sec = auth_headers(http, "t_toxdl_secretaire", PWD)
    assert http.get(URL, params={"search": env["mark"]}, headers=h_psy).status_code == 200
    assert http.get(URL, params={"search": env["mark"]}, headers=h_sec).status_code == 403
