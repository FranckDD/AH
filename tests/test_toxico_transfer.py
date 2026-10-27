# tests/test_toxico_transfer.py
"""Transfert d'un patient de toxicologie d'un psychologue a un autre (Tache 6)
et transfert automatique a la readmission. Base de dev partagee : donnees
creees avec un marqueur unique, annulees en fin de test."""
import uuid
from datetime import date, timedelta
from unittest import mock

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.routes.toxico.toxico_endpoint import _build_dossier_pdf_context
from api_backend.backend_app.security.role_map import normalize_role_name
from controller.toxico_controller import ToxicoController
from models.notification import Notification
from models.toxico import ToxicoDossier, ToxicoStay, ToxicoEvaluation, ToxicoPsychologistTransfer
from repositories.toxico_repo import (ToxicoRepository, ToxicoValidationError, ToxicoConflictError,
                                      ToxicoNotFoundError)
from tests.conftest import create_test_user, create_test_patient
from utils.business_time import business_now

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


@pytest.fixture
def env(db_session):
    db = db_session
    mk = lambda n, r, **kw: create_test_user(db, f"t_toxtr_{n}", r, password=PWD, **kw)
    users = {
        "psy_a": mk("psya", "Psychologist"),
        "psy_b": mk("psyb", "Psychologist"),
        "psy_off": mk("psyoff", "Psychologist", is_active=False),
        "manager": mk("mgr", "ToxicoManager"),
        "medecin": mk("med", "medecin"),
        "admin": mk("adm", "admin"),
    }
    return {"db": db, "users": users, "repo": ToxicoRepository(db), "mark": "Tr" + uuid.uuid4().hex[:10]}


def _new(env, suffix="", referent_key="psy_a"):
    pid, _ = create_test_patient(env["db"], env["users"]["admin"],
                                 first_name=f"{env['mark']}{suffix}", last_name="Transf")
    return env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=60),
        "substance": "Alcool", "psychologist_id": env["users"][referent_key].user_id})


def _transfer(env, d, to_key="psy_b", reason="Charge de travail"):
    return env["repo"].transfer_dossier(d.id, env["users"][to_key].user_id, reason,
                                        env["users"]["manager"].user_id)


def _stays(env, dossier_id):
    return env["db"].query(ToxicoStay).filter_by(dossier_id=dossier_id).order_by(ToxicoStay.stay_number).all()


def _transfers(env, dossier_id):
    return (env["db"].query(ToxicoPsychologistTransfer).filter_by(dossier_id=dossier_id)
            .order_by(ToxicoPsychologistTransfer.id).all())


def _ctrl(env, key="manager", role="ToxicoManager"):
    u = env["users"][key]
    u.roles = [normalize_role_name(role)]
    return ToxicoController(repo=env["repo"], patient_controller=None, current_user=u)


def _readmit(env, d, psy_key, by_key="manager"):
    data = {"admission_date": date.today(), "substance": "Cannabis",
            "psychologist_id": env["users"][psy_key].user_id if psy_key else None}
    if by_key:
        data["decided_by"] = env["users"][by_key].user_id
    return env["repo"].create_dossier_after_patient_commit(d.patient_id, data)


# --------------------------------------------------------------------------- effets

def test_transfer_changes_dossier_and_open_stay_only(env):
    users, repo = env["users"], env["repo"]
    d = _new(env)
    repo.discharge(d.id, "guerison", None, users["manager"].user_id,
                   discharge_date=date.today() - timedelta(days=1))
    _readmit(env, d, "psy_a")
    s1, s2 = _stays(env, d.id)
    t = _transfer(env, d)
    env["db"].expire_all()
    s1, s2 = _stays(env, d.id)
    assert env["db"].get(ToxicoDossier, d.id).psychologist_id == users["psy_b"].user_id
    assert s1.psychologist_id == users["psy_a"].user_id  # sejour clos inchange
    assert s2.psychologist_id == users["psy_b"].user_id
    assert t.stay_id == s2.id and t.from_psychologist_id == users["psy_a"].user_id
    assert t.to_psychologist_id == users["psy_b"].user_id and t.decided_by == users["manager"].user_id


def test_transfer_of_discharged_patient_changes_dossier_only(env):
    users = env["users"]
    d = _new(env)
    env["repo"].discharge(d.id, "abandon", None, users["manager"].user_id)
    t = _transfer(env, d)
    env["db"].expire_all()
    assert t.stay_id is None
    assert env["db"].get(ToxicoDossier, d.id).psychologist_id == users["psy_b"].user_id
    assert [s.psychologist_id for s in _stays(env, d.id)] == [users["psy_a"].user_id]


def test_transfer_gives_first_referent_when_none(env):
    d = _new(env)
    d.psychologist_id = None
    env["db"].commit()
    t = _transfer(env, d)
    assert t.from_psychologist_id is None
    assert env["db"].get(ToxicoDossier, d.id).psychologist_id == env["users"]["psy_b"].user_id


def test_transfer_from_non_psychologist_referent_allowed(env):
    d = _new(env, referent_key="manager")
    t = _transfer(env, d)
    assert t.from_psychologist_id == env["users"]["manager"].user_id


def test_transfer_records_douala_time(env):
    t = _transfer(env, _new(env))
    assert abs((t.decided_at - business_now()).total_seconds()) < 60


def test_transfer_notifies_new_psychologist_only(env):
    users, db = env["users"], env["db"]
    d = _new(env)
    _transfer(env, d)
    notifs = db.query(Notification).filter(Notification.type == "toxico_transfer",
                                           Notification.payload["dossier_id"].as_integer() == d.id).all()
    assert len(notifs) == 1
    n = notifs[0]
    assert n.recipient_user_id == users["psy_b"].user_id
    assert set(n.payload) == {"dossier_id", "patient_id", "patient_name", "from_name", "decided_by_name"}
    assert n.payload["patient_id"] == d.patient_id and env["mark"] in n.payload["patient_name"]
    assert n.payload["from_name"] == users["psy_a"].full_name
    assert n.payload["decided_by_name"] == users["manager"].full_name


def test_transfer_commits_once(env):
    db = env["db"]
    d = _new(env)
    real = db.commit
    with mock.patch.object(db, "commit", side_effect=real) as spy:
        _transfer(env, d)
    assert spy.call_count == 1
    assert db.query(Notification).filter(Notification.type == "toxico_transfer",
                                         Notification.recipient_user_id == env["users"]["psy_b"].user_id).count() >= 1


def test_transfer_is_atomic_when_notification_fails(env):
    db, users = env["db"], env["users"]
    d = _new(env)
    with mock.patch("repositories.notification_repo.NotificationRepository.create",
                    side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            _transfer(env, d)
    db.expire_all()
    assert db.get(ToxicoDossier, d.id).psychologist_id == users["psy_a"].user_id
    assert [s.psychologist_id for s in _stays(env, d.id)] == [users["psy_a"].user_id]
    assert _transfers(env, d.id) == []


# --------------------------------------------------------------------------- validations (HTTP)

@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _post(env, http, dossier_id, to_id, reason="Charge de travail"):
    _as(env["users"]["manager"], "ToxicoManager")
    return http.post(f"/toxico/dossiers/{dossier_id}/transfer",
                     json={"to_psychologist_id": to_id, "reason": reason})


def test_blank_reason_is_422_transfer_reason_required(env, http):
    d = _new(env)
    r = _post(env, http, d.id, env["users"]["psy_b"].user_id, "   ")
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "transfer_reason_required"
    assert _transfers(env, d.id) == []
    with pytest.raises(ToxicoValidationError):
        _transfer(env, d, reason="   ")


def test_reason_over_1000_chars_rejected(env, http):
    d = _new(env)
    r = _post(env, http, d.id, env["users"]["psy_b"].user_id, "x" * 1001)
    assert r.status_code == 422, r.text
    with pytest.raises(ToxicoValidationError) as ei:
        _transfer(env, d, reason="x" * 1001)
    assert ei.value.code == "transfer_reason_required"
    assert _transfers(env, d.id) == []


@pytest.mark.parametrize("target", ["psy_off", "manager", "medecin", "unknown"])
def test_target_must_be_active_psychologist(env, http, target):
    d = _new(env)
    to_id = BIG if target == "unknown" else env["users"][target].user_id
    r = _post(env, http, d.id, to_id)
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "transfer_target_invalid"
    env["db"].expire_all()
    assert env["db"].get(ToxicoDossier, d.id).psychologist_id == env["users"]["psy_a"].user_id
    assert _transfers(env, d.id) == []


def test_transfer_to_current_referent_is_409(env, http):
    d = _new(env)
    r = _post(env, http, d.id, env["users"]["psy_a"].user_id)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "transfer_same_referent"
    assert _transfers(env, d.id) == []


def test_unknown_dossier_is_404(env, http):
    _new(env)
    r = _post(env, http, BIG, env["users"]["psy_b"].user_id)
    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "Dossier introuvable"
    with pytest.raises(ToxicoNotFoundError):
        env["repo"].transfer_dossier(BIG, env["users"]["psy_b"].user_id, "x", env["users"]["manager"].user_id)


def test_http_transfer_returns_row(env, http):
    d = _new(env)
    r = _post(env, http, d.id, env["users"]["psy_b"].user_id, "  Conge  ")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "Patient transféré."
    t = body["transfer"]
    assert t["to_name"] == env["users"]["psy_b"].full_name and t["from_name"] == env["users"]["psy_a"].full_name
    assert t["decided_by_name"] == env["users"]["manager"].full_name and t["reason"] == "Conge"
    assert t["stay_number"] == 1


# --------------------------------------------------------------------------- historique

def test_evaluations_keep_their_author_after_transfer(env):
    users, repo = env["users"], env["repo"]
    d = _new(env)
    repo.process_evaluation(d.id, {"target_phase": 1, "decision": "MAINTAIN", "observation": "x"},
                            users["psy_a"].user_id)
    _transfer(env, d)
    env["db"].expire_all()
    ev = env["db"].query(ToxicoEvaluation).filter_by(dossier_id=d.id).one()
    assert ev.created_by == users["psy_a"].user_id
    ctrl = _ctrl(env)
    out = ctrl.serialize_dossier_details(ctrl.get_dossier_details(d.patient_id))
    assert out["evaluations"][0]["evaluator_name"] == users["psy_a"].full_name


def test_detail_lists_transfers_newest_first_with_names_and_reason(env):
    users = env["users"]
    d = _new(env)
    _transfer(env, d, "psy_b", "Premier")
    _transfer(env, d, "psy_a", "Second")
    env["db"].expire_all()
    ctrl = _ctrl(env)
    out = ctrl.serialize_dossier_details(ctrl.get_dossier_details(d.patient_id))
    tr = out["transfers"]
    assert [t["reason"] for t in tr] == ["Second", "Premier"]
    assert set(tr[0]) == {"id", "decided_at", "from_name", "to_name", "decided_by_name", "reason", "stay_number"}
    assert tr[0]["from_name"] == users["psy_b"].full_name and tr[0]["to_name"] == users["psy_a"].full_name
    assert tr[1]["from_name"] == users["psy_a"].full_name and tr[1]["to_name"] == users["psy_b"].full_name
    assert tr[0]["decided_by_name"] == users["manager"].full_name and tr[0]["stay_number"] == 1


def test_readonly_psychologist_sees_transfers(env):
    """Ancien referent limite : lecture seule, l'historique des transferts est visible."""
    d = _new(env)
    _transfer(env, d)
    env["db"].expire_all()
    u = env["users"]["psy_a"]
    u.sees_own_toxico_only = True
    u.roles = [normalize_role_name("Psychologist")]
    ctrl = ToxicoController(repo=env["repo"], patient_controller=None, current_user=u)
    out = ctrl.serialize_dossier_details(ctrl.get_dossier_details(d.patient_id))
    assert out["accessMode"] == "readonly" and len(out["transfers"]) == 1


def test_chain_a_to_b_to_a(env):
    users = env["users"]
    d = _new(env)
    t1 = _transfer(env, d, "psy_b")
    t2 = _transfer(env, d, "psy_a")
    rows = _transfers(env, d.id)
    assert [r.id for r in rows] == [t1.id, t2.id]
    assert t2.from_psychologist_id == t1.to_psychologist_id == users["psy_b"].user_id
    assert env["db"].get(ToxicoDossier, d.id).psychologist_id == users["psy_a"].user_id


def test_pdf_context_lists_transfers(env):
    users = env["users"]
    d = _new(env)
    _transfer(env, d, reason="Conge maternite")
    env["db"].expire_all()
    ctrl = _ctrl(env)
    detail = ctrl.serialize_dossier_details(ctrl.get_dossier_details(d.patient_id))
    rows = _build_dossier_pdf_context(detail)["transfers"]
    assert rows == [{"date": business_now().strftime("%d/%m/%Y"), "from": users["psy_a"].full_name,
                     "to": users["psy_b"].full_name, "by": users["manager"].full_name,
                     "reason": "Conge maternite"}]
    assert _build_dossier_pdf_context(dict(detail, transfers=[]))["transfers"] == []


# --------------------------------------------------------------------------- readmission (ruling a)

def test_readmission_with_other_psychologist_records_automatic_transfer(env):
    users = env["users"]
    d = _new(env)
    env["repo"].discharge(d.id, "guerison", None, users["manager"].user_id)
    _readmit(env, d, "psy_b", by_key="admin")
    rows = _transfers(env, d.id)
    assert len(rows) == 1
    t = rows[0]
    s2 = _stays(env, d.id)[1]
    assert (t.from_psychologist_id, t.to_psychologist_id, t.decided_by, t.reason, t.stay_id) == (
        users["psy_a"].user_id, users["psy_b"].user_id, users["admin"].user_id, "Readmission", s2.id)
    assert abs((t.decided_at - business_now()).total_seconds()) < 60


def test_readmission_with_same_psychologist_records_nothing(env):
    d = _new(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["manager"].user_id)
    _readmit(env, d, "psy_a")
    assert _transfers(env, d.id) == []


def test_readmission_referent_change_without_author_refused(env):
    """Aucune reassignation non tracee : sans auteur, la readmission qui change
    de referent est refusee et rien n'est ecrit."""
    d = _new(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["manager"].user_id)
    with pytest.raises(ToxicoValidationError):
        _readmit(env, d, "psy_b", by_key=None)
    env["db"].expire_all()
    assert len(_stays(env, d.id)) == 1 and _transfers(env, d.id) == []
    assert env["db"].get(ToxicoDossier, d.id).is_active is False


def test_readmission_commits_once_with_transfer(env):
    db = env["db"]
    d = _new(env)
    env["repo"].discharge(d.id, "guerison", None, env["users"]["manager"].user_id)
    real = db.commit
    with mock.patch.object(db, "commit", side_effect=real) as spy:
        _readmit(env, d, "psy_b")
    assert spy.call_count == 1 and len(_transfers(env, d.id)) == 1


def test_http_readmission_records_author(env, http):
    users = env["users"]
    d = _new(env)
    env["repo"].discharge(d.id, "guerison", None, users["manager"].user_id)
    _as(users["manager"], "ToxicoManager")
    r = http.post("/toxico/admission", data={
        "patientId": str(d.patient_id), "admissionDate": date.today().isoformat(), "substance": "Alcool",
        "psychologist": str(users["psy_b"].user_id), "guardianName": "T", "guardianContact": "1"})
    assert r.status_code == 201, r.text
    rows = _transfers(env, d.id)
    assert len(rows) == 1 and rows[0].decided_by == users["manager"].user_id
