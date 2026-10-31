# tests/test_lab_pregnancy_separation.py
"""B4 (tour de correction) : la grossesse d'un patient externe vit dans sa propre colonne (jamais livree par un flux
PowerSync), le statut de grossesse est fige a la reception, le rapport de subvention s'appuie sur ce cliche,
audit et absence de cache du rapport nominatif, effacement d'un champ de la fiche. Donnees inventees."""
import importlib.util
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import pytest
import yaml

from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.labo import lab_endpoints, pregnancy_report_endpoints
from api_backend.backend_app.routes.patients import patients_endpoints
from models.audit import AuditUserAction
from models.lab import Examen, LabResult
from models.patient import Patient
from repositories.patient_repo import PatientRepository
from tests.conftest import create_test_user, create_test_patient, auth_headers

ROOT = Path(__file__).resolve().parents[1]
PWD = "Correct123!"
PREG_TOKENS = re.compile(r"pregnan|gestation|expected_delivery|grossesse|enceinte", re.I)
LEGACY_KEYS = ("pregnancy_status", "expected_delivery_date", "pregnancy_program_number", "gestational_age_weeks")


# ---------------------------------------------------------------- flux PowerSync : projection de chaque requete

def _streams():
    return yaml.safe_load((ROOT / "powersync" / "sync-config.yaml").read_text(encoding="utf-8"))["streams"]


def _select_list(query: str) -> str:
    m = re.search(r"select\s+(.*?)\s+from\s", query, re.I | re.S)
    assert m, query
    return m.group(1)


def test_no_stream_projects_a_pregnancy_column_or_a_wildcard():
    streams = _streams()
    assert "lab_active_results" in streams
    n = 0
    for name, spec in streams.items():
        for q in spec.get("queries", []):
            n += 1
            projection = _select_list(q)
            assert "*" not in projection, f"{name}: SELECT * / table.* interdit ({projection})"
            assert not PREG_TOKENS.search(projection), f"{name}: colonne de grossesse selectionnee"
            for col in re.findall(r"(\w+)\.(\w+)", projection):
                assert not PREG_TOKENS.search(col[1]), (name, col)
    assert n >= 10


def test_streamed_identity_blob_is_selected_but_carries_no_pregnancy_key():
    """Le flux lab_active_results livre external_patient_info : c'est donc ce JSON qui ne doit rien contenir."""
    q = " ".join(_streams()["lab_active_results"]["queries"])
    assert "external_patient_info" in _select_list(q)
    assert "external_pregnancy_info" not in _select_list(q)


# ---------------------------------------------------------------- monde de test

def _user(db, role, tag="u"):
    u = create_test_user(db, f"ps_{tag}_{uuid.uuid4().hex[:6]}", role, password=PWD)
    u.postgres_role = "app_laborantin"  # contrainte chk_technician_role : le technicien est un role labo en base
    db.flush()
    return u


def _exam(db, nom="Hemogramme S"):
    ex = Examen(code=f"PS-{uuid.uuid4().hex[:8]}", nom=nom, categorie="Bio", prix=0)
    db.add(ex)
    db.flush()
    return ex


@pytest.fixture
def env(db_session, api_client):
    db = db_session
    admin = _user(db, "admin", "adm")
    ex = _exam(db)
    client = api_client(auth_endpoints, lab_endpoints, pregnancy_report_endpoints, patients_endpoints)
    return {"db": db, "client": client, "admin": admin, "ex": ex}


def _headers(env, role):
    u = _user(env["db"], role, role[:4])
    return auth_headers(env["client"], u.username, PWD)


def _post_batch(env, role, body):
    body = {"batch_uuid": str(uuid.uuid4()), "results": [{"examen_id": env["ex"].id}], **body}
    return env["client"].post("/labo/results/batch", headers=_headers(env, role), json=body)


def _post_single(env, role, body):
    """Route unitaire : accessible a un role qui n'ecrit pas la grossesse (ToxicoManager)."""
    body = {"examen_id": env["ex"].id, **body}
    return env["client"].post("/labo/results", headers=_headers(env, role), json=body)


def _external(env, **extra):
    return {"external_patient_info": {"nom": "Exta", "prenom": "Zed", "age": 30, "sexe": "F",
                                       "telephone": f"69{uuid.uuid4().int % 10**7:07d}"}, **extra}


# ---------------------------------------------------------------- C1' : colonne separee

def test_external_pregnancy_goes_to_its_own_column(env):
    r = _post_batch(env, "laborantin", _external(
        env, gestational_age_weeks=20,
        external_pregnancy_info={"pregnancy_status": "enceinte", "pregnancy_program_number": "SUIVI-SEP-1",
                                 "expected_delivery_date": "2027-04-02"}))
    assert r.status_code == 201, r.text
    row = env["db"].query(LabResult).filter(LabResult.gestational_age_weeks == 20, LabResult.patient_id.is_(None)).one()
    info = row.external_patient_info
    assert info["nom"] == "Exta"
    for k in LEGACY_KEYS + ("external_pregnancy_info",):
        assert k not in info, k
    assert row.external_pregnancy_info["pregnancy_program_number"] == "SUIVI-SEP-1"
    assert row.external_pregnancy_info["pregnancy_status"] == "enceinte"
    assert row.pregnancy_status_at_result == "enceinte"


def test_legacy_keys_inside_external_patient_info_are_moved_out(env):
    body = _external(env)
    body["external_patient_info"].update({"pregnancy_status": "enceinte", "pregnancy_program_number": "OLD-1",
                                          "Grossesse": "oui", "DPA": "2027-01-01"})
    r = _post_batch(env, "laborantin", body)
    assert r.status_code == 201, r.text
    row = env["db"].query(LabResult).filter(LabResult.patient_id.is_(None)).order_by(LabResult.result_id.desc()).first()
    assert not [k for k in row.external_patient_info if re.search(r"pregnan|gestation|grossesse|dpa", k, re.I)]
    assert row.external_pregnancy_info["pregnancy_program_number"] == "OLD-1"
    assert row.pregnancy_status_at_result == "enceinte"


@pytest.mark.parametrize("body", [
    {"external_pregnancy_info": {"pregnancy_status": "enceinte"}},
    {"gestational_age_weeks": 12},
    {"pregnancy_status_at_result": "enceinte"},
    {"external_patient_info": {"nom": "A", "sexe": "F", "age": 3, "telephone": "699000001",
                               "pregnancy_status": "enceinte"}},
    {"external_patient_info": {"nom": "A", "sexe": "F", "age": 3, "telephone": "699000002",
                               "deep": {"x": [{"Pregnancy_Status": "enceinte"}]}}},
])
def test_non_writer_is_refused_whatever_the_nesting(env, body):
    body = {**_external(env), **body} if "external_patient_info" not in body else body
    r = _post_single(env, "ToxicoManager", body)
    assert r.status_code == 403, r.text
    assert env["db"].query(LabResult).filter(LabResult.external_pregnancy_info.isnot(None)).count() == 0


def test_non_writer_reception_without_pregnancy_keys_is_unaffected(env):
    r = _post_single(env, "ToxicoManager", _external(env))
    assert r.status_code == 201, r.text
    row = env["db"].query(LabResult).filter(LabResult.result_id == r.json()["result_id"]).one()
    assert row.external_pregnancy_info is None and row.pregnancy_status_at_result == "inconnu"


def test_invalid_pregnancy_values_are_422(env):
    assert _post_batch(env, "laborantin", _external(env, pregnancy_status_at_result="peut-etre")).status_code == 422
    assert _post_batch(env, "laborantin", _external(env, external_pregnancy_info={"pregnancy_status": "x"})).status_code == 422
    assert _post_batch(env, "laborantin", _external(env, gestational_age_weeks=99)).status_code == 422


def test_pregnancy_column_never_reaches_non_viewers(env):
    from api_backend.backend_app.security.pregnancy_filter import strip_pregnancy_fields_always  # noqa: F401
    from utils.pregnancy_visibility import strip_pregnancy_fields_always as strip
    out = strip({"external_pregnancy_info": {"x": 1}, "pregnancy_status_at_result": "enceinte", "nom": "A"})
    assert out == {"nom": "A"}


# ---------------------------------------------------------------- I2 / I4 : statut a la reception

def _patient(env, status="inconnu", gender="F", **kw):
    pid, code = create_test_patient(env["db"], env["admin"], first_name="Prega", last_name=f"Snap{uuid.uuid4().hex[:5]}",
                                    gender=gender, **kw)
    if status != "inconnu":
        PatientRepository(env["db"]).set_pregnancy(pid, {"pregnancy_status": status})
    env["db"].flush()
    return pid


def _status_of(env, pid):
    return env["db"].query(LabResult).filter(LabResult.patient_id == pid).order_by(LabResult.result_id.desc()).first()


def test_internal_snapshot_uses_file_status_at_that_moment(env):
    pid = _patient(env, "enceinte")
    assert _post_batch(env, "laborantin", {"patient_id": pid}).status_code == 201
    assert _status_of(env, pid).pregnancy_status_at_result == "enceinte"
    PatientRepository(env["db"]).set_pregnancy(pid, {"pregnancy_status": "non_enceinte"})
    env["db"].flush()
    assert _post_batch(env, "laborantin", {"patient_id": pid}).status_code == 201
    assert _status_of(env, pid).pregnancy_status_at_result == "non_enceinte"


def test_internal_unknown_status_lab_can_declare_pregnancy_without_touching_the_file(env):
    pid = _patient(env, "inconnu")
    r = _post_batch(env, "laborantin", {"patient_id": pid, "gestational_age_weeks": 18,
                                         "pregnancy_status_at_result": "enceinte"})
    assert r.status_code == 201, r.text
    res = _status_of(env, pid)
    assert res.gestational_age_weeks == 18 and res.pregnancy_status_at_result == "enceinte"
    env["db"].expire_all()
    p = env["db"].get(Patient, pid)
    assert p.pregnancy_status == "inconnu" and p.expected_delivery_date is None


def test_weeks_above_zero_force_pregnant_snapshot(env):
    pid = _patient(env, "non_enceinte")
    assert _post_batch(env, "laborantin", {"patient_id": pid, "gestational_age_weeks": 9,
                                            "pregnancy_status_at_result": "non_enceinte"}).status_code == 201
    assert _status_of(env, pid).pregnancy_status_at_result == "enceinte"


def test_non_writer_reception_records_server_side_snapshot(env):
    pid = _patient(env, "enceinte")
    assert _post_single(env, "ToxicoManager", {"patient_id": pid}).status_code == 201
    assert _status_of(env, pid).pregnancy_status_at_result == "enceinte"


# ---------------------------------------------------------------- rapport : appartenance, audit, cache

def _result(db, ex, when, *, patient_id=None, ext=None, preg=None, snap=None, sa=None, status="completed", batch=None):
    r = LabResult(patient_id=patient_id, test_type="Analyse Labo", test_date=when, status=status, examen_id=ex.id,
                  code_lab_patient=f"PSR-{uuid.uuid4().hex[:10]}", external_patient_info=ext,
                  external_pregnancy_info=preg, pregnancy_status_at_result=snap, gestational_age_weeks=sa,
                  batch_id=batch or uuid.uuid4())
    db.add(r)
    db.flush()
    return r


def _report(env, role="promoteur", frm="2026-01-01", to="2026-12-31", pdf=False):
    h = _headers(env, role)
    url = f"/labo/reports/pregnancy{'.pdf' if pdf else ''}?from={frm}&to={to}"
    return env["client"].get(url, headers=h)


def test_report_uses_status_at_reception_not_current_status(env):
    db, ex = env["db"], env["ex"]
    pid = _patient(env, "enceinte")
    _result(db, ex, datetime(2026, 1, 15, 9, 0), patient_id=pid, snap="inconnu")        # janvier, avant la grossesse connue
    _result(db, ex, datetime(2026, 6, 20, 9, 0), patient_id=pid, snap="enceinte")       # juin
    body = _report(env).json()
    assert [r["validated_on"] for r in body["rows"]] == ["2026-06-20"]
    assert _report(env, frm="2026-01-01", to="2026-01-31").json()["rows"] == []


def test_patient_set_non_enceinte_after_delivery_still_in_earlier_months(env):
    db, ex = env["db"], env["ex"]
    pid = _patient(env, "enceinte")
    _result(db, ex, datetime(2026, 3, 5, 9, 0), patient_id=pid, snap="enceinte")
    PatientRepository(db).set_pregnancy(pid, {"pregnancy_status": "non_enceinte"})
    db.flush()
    _result(db, ex, datetime(2026, 8, 5, 9, 0), patient_id=pid, snap="non_enceinte")
    days = [r["validated_on"] for r in _report(env).json()["rows"]]
    assert days == ["2026-03-05"]


def test_report_excludes_deleted_unvalidated_and_unflagged(env):
    db, ex = env["db"], env["ex"]
    gone, ok, other = _patient(env, "enceinte"), _patient(env, "enceinte"), _patient(env, "enceinte")
    _result(db, ex, datetime(2026, 4, 1, 9), patient_id=gone, snap="enceinte")
    db.get(Patient, gone).is_deleted = True
    _result(db, ex, datetime(2026, 4, 1, 9), patient_id=ok, snap="enceinte")
    _result(db, ex, datetime(2026, 4, 1, 9), patient_id=other, snap="enceinte", status="pending")
    _result(db, ex, datetime(2026, 4, 2, 9), patient_id=other, snap="enceinte", status="partial")
    _result(db, ex, datetime(2026, 4, 3, 9), patient_id=other)                       # sans cliche ni SA (ancienne ligne)
    _result(db, ex, datetime(2026, 4, 4, 9), patient_id=other, sa=24)                # ancienne ligne avec SA : compte
    db.flush()
    body = _report(env).json()
    assert sorted(r["validated_on"] for r in body["rows"]) == ["2026-04-01", "2026-04-04"]
    assert body["total_patients"] == 2


def test_report_robust_to_odd_external_json_and_name_keys(env):
    db, ex = env["db"], env["ex"]
    when = datetime(2026, 5, 6, 9)
    _result(db, ex, when, ext=["pas", "un", "objet"], preg={"pregnancy_status": "enceinte"}, snap="enceinte")
    _result(db, ex, when.replace(hour=10), ext="texte brut", preg=["x"], snap="enceinte")
    _result(db, ex, when.replace(hour=11), ext={"name": "Anglaise", "first_name": "Ann"}, snap="enceinte")
    _result(db, ex, when.replace(hour=12), ext={"nom": "Francaise", "prenom": "Fanny"}, snap="enceinte")
    r = _report(env)
    assert r.status_code == 200, r.text
    names = sorted(x["patient_name"] for x in r.json()["rows"])
    assert names == sorted(["Nom non renseigne", "Nom non renseigne", "Anglaise Ann", "Francaise Fanny"])
    pdf = _report(env, pdf=True)
    assert pdf.status_code == 200


def test_same_name_externals_in_different_receptions_do_not_merge(env):
    db, ex = env["db"], env["ex"]
    when = datetime(2026, 5, 6, 9)
    ext = {"nom": "Homonyme", "prenom": "Ada"}
    _result(db, ex, when, ext=ext, preg={"pregnancy_program_number": "P-1"}, snap="enceinte", batch=uuid.uuid4())
    _result(db, ex, when.replace(hour=10), ext=ext, preg={"pregnancy_program_number": "P-2"}, snap="enceinte", batch=uuid.uuid4())
    # meme reception, deux examens : une seule ligne
    b = uuid.uuid4()
    _result(db, ex, when.replace(hour=11), ext={"nom": "Unique", "prenom": "U"}, preg={"pregnancy_program_number": "P-3"},
            snap="enceinte", batch=b)
    _result(db, ex, when.replace(hour=11, minute=5), ext={"nom": "Unique", "prenom": "U"}, snap="enceinte", batch=b)
    body = _report(env).json()
    assert body["total_rows"] == 3
    progs = sorted(r["pregnancy_program_number"] for r in body["rows"])
    assert progs == ["P-1", "P-2", "P-3"]


def test_admin_role_gets_the_fields_through_the_filter(env):
    db, ex = env["db"], env["ex"]
    pid = _patient(env, "enceinte")
    _result(db, ex, datetime(2026, 2, 2, 9), patient_id=pid, snap="enceinte", sa=22)
    body = _report(env, "admin").json()
    assert body["rows"][0]["gestational_age_weeks"] == 22
    assert "pregnancy_program_number" in body["rows"][0]


def test_row_cap_gives_a_clear_message(env, monkeypatch):
    db, ex = env["db"], env["ex"]
    monkeypatch.setattr(pregnancy_report_endpoints, "MAX_ROWS", 2)
    for i in range(3):
        _result(db, ex, datetime(2026, 7, 1 + i, 9), ext={"nom": f"Cap{i}"}, snap="enceinte")
    for pdf in (False, True):
        r = _report(env, pdf=pdf)
        assert r.status_code == 422
        assert "Trop de lignes" in r.json()["detail"] and "periode" in r.json()["detail"].lower()


def test_report_is_audited_without_names_and_never_cached(env):
    db, ex = env["db"], env["ex"]
    pid = _patient(env, "enceinte")
    _result(db, ex, datetime(2026, 9, 9, 9), patient_id=pid, snap="enceinte")
    _result(db, ex, datetime(2026, 9, 9, 10), ext={"nom": "SecretNom", "prenom": "SecretPrenom"}, snap="enceinte")
    before = db.query(AuditUserAction).filter(AuditUserAction.resource_type == "PregnancyReport").count()
    rj = _report(env, frm="2026-09-01", to="2026-09-30")
    rp = _report(env, frm="2026-09-01", to="2026-09-30", pdf=True)
    for r in (rj, rp):
        assert r.status_code == 200
        assert r.headers["cache-control"] == "no-store, private"
        assert r.headers.get("pragma") == "no-cache"
    db.expire_all()
    logs = (db.query(AuditUserAction).filter(AuditUserAction.resource_type == "PregnancyReport")
            .order_by(AuditUserAction.action_id).all())
    assert len(logs) == before + 2
    last_two = logs[-2:]
    assert sorted(l.new_values["format"] for l in last_two) == ["json", "pdf"]
    for l in last_two:
        assert l.new_values["from"] == "2026-09-01" and l.new_values["to"] == "2026-09-30"
        assert l.new_values["rows"] == 2
        blob = str(l.new_values) + str(l.action_performed)
        assert "SecretNom" not in blob and "SecretPrenom" not in blob and "Snap" not in blob


def test_forbidden_report_is_not_audited(env):
    before = env["db"].query(AuditUserAction).filter(AuditUserAction.resource_type == "PregnancyReport").count()
    assert _report(env, "laborantin").status_code == 403
    assert env["db"].query(AuditUserAction).filter(AuditUserAction.resource_type == "PregnancyReport").count() == before


# ---------------------------------------------------------------- minor : effacement d'un champ de la fiche

def test_clear_pregnancy_fields_on_patient_file(env):
    db = env["db"]
    pid = _patient(env, "enceinte")
    PatientRepository(db).set_pregnancy(pid, {"expected_delivery_date": date(2027, 3, 1),
                                              "pregnancy_program_number": "CLR-1"})
    db.flush()
    h = _headers(env, "medecin")
    r = env["client"].put(f"/patients/{pid}", headers=h, json={
        "pregnancy_status": "non_enceinte", "clear_pregnancy_fields": ["expected_delivery_date", "pregnancy_program_number"]})
    assert r.status_code == 200, r.text
    db.expire_all()
    p = db.get(Patient, pid)
    assert p.pregnancy_status == "non_enceinte" and p.expected_delivery_date is None and p.pregnancy_program_number is None
    # un null seul reste ignore (comportement inchange)
    PatientRepository(db).set_pregnancy(pid, {"pregnancy_program_number": "KEEP"})
    db.flush()
    r = env["client"].put(f"/patients/{pid}", headers=h, json={"pregnancy_program_number": None})
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.get(Patient, pid).pregnancy_program_number == "KEEP"


def test_clear_pregnancy_fields_rules(env):
    pid = _patient(env, "enceinte")
    med = _headers(env, "medecin")
    assert env["client"].put(f"/patients/{pid}", headers=med, json={"clear_pregnancy_fields": ["nom"]}).status_code == 400
    assert env["client"].put(f"/patients/{pid}", headers=med, json={
        "pregnancy_program_number": "A", "clear_pregnancy_fields": ["pregnancy_program_number"]}).status_code == 400
    sec = _headers(env, "secretaire")
    r = env["client"].put(f"/patients/{pid}", headers=sec, json={"clear_pregnancy_fields": ["expected_delivery_date"]})
    assert r.status_code == 403
    assert env["db"].get(Patient, pid).pregnancy_status == "enceinte"


# ---------------------------------------------------------------- migration 042 : deplacement des donnees, idempotent

def test_migration_042_moves_keys_and_is_idempotent(env):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location("m042", ROOT / "alembic" / "versions" / "042_lab_pregnancy_separation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    db = env["db"]
    r = _result(db, env["ex"], datetime(2026, 1, 1), ext={"nom": "Mig", "pregnancy_status": "enceinte",
                                                           "Gestational_Age_Weeks": 12, "age": 3, "prenatal_note": "ok"})
    plain = _result(db, env["ex"], datetime(2026, 1, 1), ext={"nom": "Plain"})
    odd = _result(db, env["ex"], datetime(2026, 1, 1), ext=["liste"])
    db.flush()
    conn = db.connection()
    for _ in range(2):  # idempotent
        with Operations.context(MigrationContext.configure(conn)):
            mod.upgrade()
        db.expire_all()
        assert r.external_patient_info == {"nom": "Mig", "age": 3, "prenatal_note": "ok"}
        assert r.external_pregnancy_info == {"pregnancy_status": "enceinte", "Gestational_Age_Weeks": 12}
        assert r.pregnancy_status_at_result == "enceinte"
        assert plain.external_patient_info == {"nom": "Plain"} and plain.external_pregnancy_info is None
        assert odd.external_patient_info == ["liste"]
