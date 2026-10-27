# tests/test_toxico_readmission.py
"""Sortie avec motif, réadmission (séjours), détail et statistiques du module toxico.
Base de dev partagée : chaque test crée ses propres patients/dossiers dans la
transaction de test et n'affirme que sur eux (statistiques : deltas)."""
from datetime import date, datetime, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.toxico_controller import ToxicoController, redis_client
from models.toxico import ToxicoDossier, ToxicoStay, ToxicoPhaseHistory, ToxicoEvaluation, DISCHARGE_REASONS
from repositories.toxico_repo import ToxicoRepository, ToxicoConflictError, ToxicoValidationError
from tests.conftest import auth_headers, create_test_user, create_test_patient

PWD = "TestPass123!"
ROLES = ("Psychologist", "SpiritualCounsellor", "admin", "ToxicoManager", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "promoteur", "StockController")
DISCHARGE_ALLOWED = {"ToxicoManager", "admin", "promoteur"}  # promoteur : 2026-10-22
ADMISSION_ALLOWED = {"ToxicoManager", "admin", "Assistant"}


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
    users = {r: create_test_user(db, f"t_toxre_{r.lower()}", r, password=PWD) for r in ROLES}
    users["psy2"] = create_test_user(db, "t_toxre_psy2", "Psychologist", password=PWD)
    users["psy_off"] = create_test_user(db, "t_toxre_psyoff", "Psychologist", password=PWD, is_active=False)
    return {"db": db, "users": users, "repo": ToxicoRepository(db)}


def _new_dossier(env, first_name="ReadmTest", admission=None):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name=first_name)
    d = env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": admission or date.today() - timedelta(days=30),
        "substance": "Alcool",
        "psychologist_id": env["users"]["Psychologist"].user_id,
        "guardian_name": "Tuteur", "guardian_contact": "000",
    })
    return pid, d


def _readmit_data(env, psy_key="psy2"):
    return {"admission_date": date.today(), "substance": "Cannabis",
            "psychologist_id": env["users"][psy_key].user_id,
            # Auteur obligatoire quand le referent change (transfert automatique trace, Tache 6).
            "decided_by": env["users"]["admin"].user_id}


def _stays(env, dossier_id):
    return env["db"].query(ToxicoStay).filter_by(dossier_id=dossier_id).order_by(ToxicoStay.stay_number).all()


# --------------------------------------------------------------------------- dépôt

def test_premiere_admission_cree_sejour_1_et_phase_liee(env):
    _, d = _new_dossier(env)
    stays = _stays(env, d.id)
    assert [s.stay_number for s in stays] == [1] and stays[0].discharge_date is None
    hist = env["db"].query(ToxicoPhaseHistory).filter_by(dossier_id=d.id).all()
    assert len(hist) == 1 and hist[0].stay_id == stays[0].id


def test_cycle_complet_admission_sortie_readmission(env):
    db, repo, users = env["db"], env["repo"], env["users"]
    pid, d = _new_dossier(env)
    dossier_id = d.id
    # une évaluation (régression simulée: 1 -> 2 -> 1) pendant le séjour 1
    repo.process_evaluation(dossier_id, {"target_phase": 2, "decision": "PROGRESS", "observation": "ok"},
                            users["Psychologist"].user_id)
    repo.process_evaluation(dossier_id, {"target_phase": 1, "decision": "REGRESS", "observation": "rechute"},
                            users["Psychologist"].user_id)
    relapse_before = db.get(ToxicoDossier, dossier_id).relapse_count
    assert relapse_before == 1

    repo.discharge(dossier_id, "autre", "Départ volontaire", users["ToxicoManager"].user_id)
    d = db.get(ToxicoDossier, dossier_id)
    assert d.is_active is False
    assert env["db"].query(ToxicoPhaseHistory).filter_by(dossier_id=dossier_id, end_date=None).count() == 0

    d2 = repo.create_dossier_after_patient_commit(pid, _readmit_data(env))
    assert d2.id == dossier_id
    assert d2.is_active is True and d2.current_phase == 1 and d2.relapse_count == relapse_before
    assert d2.psychologist_id == users["psy2"].user_id and d2.substance == "Cannabis"

    s1, s2 = _stays(env, dossier_id)
    assert (s1.stay_number, s1.discharge_reason, s1.discharge_note) == (1, "autre", "Départ volontaire")
    assert s1.discharged_by == users["ToxicoManager"].user_id and s1.discharge_date is not None
    assert s2.stay_number == 2 and s2.discharge_date is None and s2.psychologist_id == users["psy2"].user_id

    evals = db.query(ToxicoEvaluation).filter_by(dossier_id=dossier_id).all()
    assert len(evals) == 2 and all(e.stay_id == s1.id for e in evals)
    hist = db.query(ToxicoPhaseHistory).filter_by(dossier_id=dossier_id).all()
    assert len(hist) == 4
    new_phase = [h for h in hist if h.stay_id == s2.id]
    assert len(new_phase) == 1 and new_phase[0].phase == 1 and new_phase[0].end_date is None
    assert new_phase[0].comments == "Réadmission, séjour 2"
    assert all(h.stay_id == s1.id for h in hist if h is not new_phase[0])

    # évaluation du séjour 2 rattachée au séjour 2
    repo.process_evaluation(dossier_id, {"target_phase": 2, "decision": "PROGRESS", "observation": "bien"},
                            users["psy2"].user_id)
    e_new = db.query(ToxicoEvaluation).filter_by(dossier_id=dossier_id, stay_id=s2.id).all()
    assert len(e_new) == 1
    assert db.query(ToxicoPhaseHistory).filter_by(dossier_id=dossier_id, phase=2, end_date=None).one().stay_id == s2.id


def test_readmission_dossier_actif_refusee_sans_ecriture(env):
    pid, d = _new_dossier(env)
    with pytest.raises(ToxicoConflictError, match="déjà"):
        env["repo"].create_dossier_after_patient_commit(pid, _readmit_data(env))
    d = env["db"].get(ToxicoDossier, d.id)
    assert len(_stays(env, d.id)) == 1 and d.substance == "Alcool"
    assert env["db"].query(ToxicoPhaseHistory).filter_by(dossier_id=d.id).count() == 1


def test_readmission_en_double_refusee_un_seul_sejour_ouvert(env):
    pid, d = _new_dossier(env)
    env["repo"].discharge(d.id, "abandon", None, env["users"]["admin"].user_id)
    env["repo"].create_dossier_after_patient_commit(pid, _readmit_data(env))
    with pytest.raises(ToxicoConflictError):
        env["repo"].create_dossier_after_patient_commit(pid, _readmit_data(env))
    stays = _stays(env, d.id)
    assert len(stays) == 2 and sum(1 for s in stays if s.discharge_date is None) == 1


def test_readmission_concurrente_index_sejour_ouvert_donne_409(env):
    """Simule l'état où une autre transaction a déjà ouvert un séjour : l'index
    unique partiel refuse le 2e séjour ouvert, converti en conflit propre."""
    db = env["db"]
    pid, d = _new_dossier(env)
    d.is_active = False  # dossier inactif mais séjour encore ouvert
    db.commit()
    with pytest.raises(ToxicoConflictError):
        env["repo"].create_dossier_after_patient_commit(pid, _readmit_data(env))
    assert sum(1 for s in _stays(env, d.id) if s.discharge_date is None) == 1


@pytest.mark.parametrize("reason,note", [(None, None), ("inconnu", None), ("autre", None), ("autre", "   ")])
def test_sortie_invalide_refusee_par_le_depot(env, reason, note):
    _, d = _new_dossier(env)
    with pytest.raises(ToxicoValidationError):
        env["repo"].discharge(d.id, reason, note, env["users"]["admin"].user_id)
    assert env["db"].get(ToxicoDossier, d.id).is_active is True


@pytest.mark.parametrize("reason", DISCHARGE_REASONS)
def test_chaque_motif_accepte_et_double_sortie_409(env, reason):
    _, d = _new_dossier(env)
    note = "précision" if reason == "autre" else None
    env["repo"].discharge(d.id, reason, note, env["users"]["admin"].user_id)
    assert _stays(env, d.id)[0].discharge_reason == reason
    with pytest.raises(ToxicoConflictError):
        env["repo"].discharge(d.id, reason, note, env["users"]["admin"].user_id)


@pytest.mark.parametrize("psy", ["absent", "inactif", "mauvais_role", "inexistant"])
def test_psychologue_invalide_refuse(env, psy):
    pid, d = _new_dossier(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    data = _readmit_data(env)
    data["psychologist_id"] = {"absent": None, "inactif": env["users"]["psy_off"].user_id,
                               "mauvais_role": env["users"]["secretaire"].user_id,
                               "inexistant": 99999999}[psy]
    with pytest.raises(ToxicoValidationError):
        env["repo"].create_dossier_after_patient_commit(pid, data)
    assert len(_stays(env, d.id)) == 1
    assert env["db"].get(ToxicoDossier, d.id).is_active is False


def test_readmission_avant_la_sortie_precedente_422(env):
    pid, d = _new_dossier(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    data = dict(_readmit_data(env), admission_date=date.today() - timedelta(days=1))
    with pytest.raises(ToxicoValidationError, match="antérieure"):
        env["repo"].create_dossier_after_patient_commit(pid, data)
    assert len(_stays(env, d.id)) == 1 and env["db"].get(ToxicoDossier, d.id).is_active is False


def test_readmission_dans_le_futur_422_mais_demain_accepte(env):
    pid, d = _new_dossier(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    with pytest.raises(ToxicoValidationError, match="futur"):
        env["repo"].create_dossier_after_patient_commit(
            pid, dict(_readmit_data(env), admission_date=date.today() + timedelta(days=2)))
    assert len(_stays(env, d.id)) == 1
    env["repo"].create_dossier_after_patient_commit(
        pid, dict(_readmit_data(env), admission_date=date.today() + timedelta(days=1)))
    assert len(_stays(env, d.id)) == 2


def _dossier_sans_sejour(env):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name="NoStay")
    d = ToxicoDossier(patient_id=pid, admission_date=date.today(), substance="Alcool",
                      psychologist_id=env["users"]["Psychologist"].user_id, current_phase=1)
    env["db"].add(d)
    env["db"].commit()  # savepoint de test : survit au rollback interne du dépôt
    return d


def test_sortie_sans_sejour_ouvert_409(env):
    d = _dossier_sans_sejour(env)
    with pytest.raises(ToxicoConflictError, match="séjour ouvert"):
        env["repo"].discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    assert env["db"].get(ToxicoDossier, d.id).is_active is True


def test_evaluation_sur_dossier_sorti_409(env):
    _, d = _new_dossier(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    with pytest.raises(ToxicoConflictError, match="réadmis"):
        env["repo"].process_evaluation(d.id, {"target_phase": 2, "decision": "PROGRESS", "observation": "x"},
                                       env["users"]["Psychologist"].user_id)
    assert env["db"].query(ToxicoEvaluation).filter_by(dossier_id=d.id).count() == 0


def test_statistiques_ignorent_un_sejour_futur(env):
    repo = env["repo"]
    today = date.today()
    start = datetime(today.year, today.month, 1)
    end = datetime(today.year + (today.month == 12), today.month % 12 + 1, 1)
    before_month, before_open = repo.count_dossiers_created_since(start, end), repo.count_dossiers_created_since(start)
    _new_dossier(env, admission=end.date() + timedelta(days=3))  # séjour daté du mois suivant
    assert repo.count_dossiers_created_since(start, end) == before_month
    assert repo.count_dossiers_created_since(start) == before_open
    _new_dossier(env, first_name="ThisMonth", admission=today)
    assert repo.count_dossiers_created_since(start, end) == before_month + 1


def test_toxicomanager_accepte_comme_responsable_admission_et_readmission(env):
    repo, mgr = env["repo"], env["users"]["ToxicoManager"]
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name="MgrResp")
    d = repo.create_dossier_after_patient_commit(pid, {
        "admission_date": date.today(), "substance": "Alcool", "psychologist_id": mgr.user_id})
    assert d.psychologist_id == mgr.user_id
    repo.discharge(d.id, "guerison", None, mgr.user_id)
    d2 = repo.create_dossier_after_patient_commit(pid, dict(_readmit_data(env), psychologist_id=mgr.user_id))
    assert d2.is_active and _stays(env, d.id)[1].psychologist_id == mgr.user_id


def test_liste_et_validation_partagent_les_roles(env):
    from repositories.toxico_repo import RESPONSIBLE_ROLES
    ids = {u.user_id for u in env["repo"].get_psychologists()}
    # la liste deroulante ne propose que les psychologues ; la validation accepte encore les autres roles
    assert env["users"]["Psychologist"].user_id in ids and env["users"]["psy2"].user_id in ids
    assert env["users"]["ToxicoManager"].user_id not in ids and env["users"]["medecin"].user_id not in ids
    assert env["users"]["secretaire"].user_id not in ids and env["users"]["psy_off"].user_id not in ids
    assert set(RESPONSIBLE_ROLES) == {"Psychologist", "ToxicoManager", "medecin"}


def test_detail_du_dossier_expose_les_sejours(env):
    db, repo, users = env["db"], env["repo"], env["users"]
    pid, d = _new_dossier(env)
    repo.process_evaluation(d.id, {"target_phase": 2, "decision": "PROGRESS", "observation": "x"},
                            users["Psychologist"].user_id)
    repo.discharge(d.id, "exclusion", "règlement", users["ToxicoManager"].user_id)
    repo.create_dossier_after_patient_commit(pid, _readmit_data(env))
    db.expire_all()

    ctrl = ToxicoController(repo=repo, patient_controller=None, current_user=users["admin"])
    out = ctrl.serialize_dossier_details(ctrl.get_dossier_details(pid))
    assert [s["stay_number"] for s in out["stays"]] == [1, 2]
    s1, s2 = out["stays"]
    assert s1["discharge_reason"] == "exclusion" and s1["discharge_note"] == "règlement"
    assert s1["discharged_by_name"] == users["ToxicoManager"].full_name and s1["is_open"] is False
    assert s1["psychologist_name"] == users["Psychologist"].full_name and s1["substance"] == "Alcool"
    assert s2["is_open"] is True and s2["psychologist_name"] == users["psy2"].full_name
    assert s2["discharge_reason"] is None
    assert out["current_stay_number"] == 2
    assert [e["stay_number"] for e in out["evaluations"]] == [1]
    assert sorted(h["stay_number"] for h in out["phaseHistory"]) == [1, 1, 2]
    assert out["phaseHistory"][0]["stay_number"] == 2


def test_statistiques_comptent_la_readmission_du_mois(env):
    repo = env["repo"]
    start = datetime(date.today().year, date.today().month, 1)
    pid, d = _new_dossier(env, admission=start.date() - timedelta(days=40))
    repo.discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    before = repo.count_dossiers_created_since(start)
    repo.create_dossier_after_patient_commit(pid, _readmit_data(env))
    assert repo.count_dossiers_created_since(start) == before + 1


# --------------------------------------------------------------------------- HTTP

@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


@pytest.mark.parametrize("role", ROLES)
def test_sortie_matrice_de_roles(env, http, role):
    _, d = _new_dossier(env)
    _as(env["users"][role], role)
    r = http.post(f"/toxico/discharge/{d.id}", json={"reason": "guerison"})
    env["db"].expire_all()
    if role in DISCHARGE_ALLOWED:
        assert r.status_code == 200, (role, r.text)
        assert env["db"].get(ToxicoDossier, d.id).is_active is False
    else:
        assert r.status_code == 403, (role, r.status_code, r.text)
        assert env["db"].get(ToxicoDossier, d.id).is_active is True


@pytest.mark.parametrize("body", [{}, {"reason": "inconnu"}, {"reason": "autre"},
                                  {"reason": "autre", "note": ""},
                                  {"reason": "guerison", "extra": 1}])
def test_sortie_http_corps_invalide_422(env, http, body):
    _, d = _new_dossier(env)
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    r = http.post(f"/toxico/discharge/{d.id}", json=body)
    assert r.status_code == 422, r.text
    env["db"].expire_all()
    assert env["db"].get(ToxicoDossier, d.id).is_active is True


def test_sortie_http_double_409_et_readmission_http(env, http):
    pid, d = _new_dossier(env)
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    assert http.post(f"/toxico/discharge/{d.id}", json={"reason": "autre", "note": "x"}).status_code == 200
    assert http.post(f"/toxico/discharge/{d.id}", json={"reason": "guerison"}).status_code == 409

    month_key = f"toxico:stats:admissions:{datetime.now().strftime('%Y-%m')}"
    redis_client.set(month_key, "999")
    form = {"patientId": str(pid), "admissionDate": date.today().isoformat(), "substance": "Cannabis",
            "psychologist": str(env["users"]["psy2"].user_id), "guardianName": "T", "guardianContact": "1"}

    _as(env["users"]["Psychologist"], "Psychologist")
    assert http.post("/toxico/admission", data=form).status_code == 403

    _as(env["users"]["Assistant"], "Assistant")
    r = http.post("/toxico/admission", data=form)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_readmission"] is True and body["stay_number"] == 2 and body["dossier_id"] == d.id
    assert redis_client.get(month_key) is None, "la réadmission doit invalider le cache du mois"

    r = http.post("/toxico/admission", data=form)
    assert r.status_code == 409, r.text

    bad = dict(form, psychologist=str(env["users"]["secretaire"].user_id))
    http.post(f"/toxico/discharge/{d.id}", json={"reason": "abandon"})  # Assistant -> 403, dossier reste actif
    _as(env["users"]["admin"], "admin")
    assert http.post(f"/toxico/discharge/{d.id}", json={"reason": "abandon"}).status_code == 200
    r = http.post("/toxico/admission", data=bad)
    assert r.status_code == 422, r.text

    detail = http.get(f"/toxico/patients/{pid}").json()
    assert [s["stay_number"] for s in detail["stays"]] == [1, 2] and detail["current_stay_number"] is None


def test_http_evaluation_sur_dossier_sorti_409(env, http):
    _, d = _new_dossier(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["admin"].user_id)
    _as(env["users"]["Psychologist"], "Psychologist")
    r = http.post("/toxico/evaluation", json={"dossier_id": d.id, "decision": "PROGRESS",
                                              "observation": "x", "targetPhase": 2})
    assert r.status_code == 409, r.text


def test_admission_refusee_ne_laisse_pas_de_fichier_orphelin(env, http):
    import os
    from api_backend.backend_app.utils.file_storage import consent_storage_dir
    UPLOAD_DIR = consent_storage_dir()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    pid, d = _new_dossier(env)  # dossier actif -> réadmission refusée (409)
    before = set(os.listdir(UPLOAD_DIR))
    _as(env["users"]["Assistant"], "Assistant")
    r = http.post("/toxico/admission", data={
        "patientId": str(pid), "admissionDate": date.today().isoformat(), "substance": "Alcool",
        "psychologist": str(env["users"]["psy2"].user_id), "guardianName": "T", "guardianContact": "1"},
        files={"consentFile": ("consent.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert r.status_code == 409, r.text
    assert set(os.listdir(UPLOAD_DIR)) == before


def test_premiere_admission_http_indique_sejour_1(env, http):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name="FirstAdm")
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    r = http.post("/toxico/admission", data={
        "patientId": str(pid), "admissionDate": date.today().isoformat(), "substance": "Alcool",
        "psychologist": str(env["users"]["Psychologist"].user_id), "guardianName": "T", "guardianContact": "1"})
    assert r.status_code == 201, r.text
    assert r.json()["is_readmission"] is False and r.json()["stay_number"] == 1


def test_sortie_jetons_reels(env, http):
    """2 vraies connexions : jeton psychologue refusé (403), jeton gestionnaire accepté."""
    _, d = _new_dossier(env)
    h_psy = auth_headers(http, "t_toxre_psychologist", PWD)
    h_mgr = auth_headers(http, "t_toxre_toxicomanager", PWD)
    assert http.post(f"/toxico/discharge/{d.id}", json={"reason": "guerison"}, headers=h_psy).status_code == 403
    assert http.post(f"/toxico/discharge/{d.id}", json={"reason": "guerison"}, headers=h_mgr).status_code == 200
