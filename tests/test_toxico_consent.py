# tests/test_toxico_consent.py
"""Fichiers de consentement toxico : stockes hors /static, noms UUID, lecture authentifiee et journalisee.
Base de dev partagee : les donnees sont creees dans la transaction de test (rollback en fin de test)."""
import os
import re
import importlib.util
from datetime import date, timedelta

import pytest

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.audit import AuditUserAction
from models.toxico import ToxicoDossier
from repositories.toxico_repo import ToxicoRepository
from tests.conftest import create_test_user, create_test_patient

PWD = "TestPass123!"
ROLES = ("Psychologist", "SpiritualCounsellor", "admin", "ToxicoManager", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "promoteur", "StockController")
READ_ALLOWED = {"ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin"}
PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
ID_RE = re.compile(r"^[0-9a-f]{32}\.(pdf|jpg|png)$")


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    d = tmp_path / "consents"
    monkeypatch.setenv("CONSENT_STORAGE_DIR", str(d))
    return d


@pytest.fixture
def env(db_session):
    users = {r: create_test_user(db_session, f"t_tcons_{r.lower()}", r, password=PWD) for r in ROLES}
    return {"db": db_session, "users": users}


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _admit(env, http, content=PDF, name="consent.pdf", ctype="application/pdf"):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name="ConsentTest")
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    return http.post("/toxico/admission", data={
        "patientId": str(pid), "admissionDate": date.today().isoformat(), "substance": "Alcool",
        "psychologist": str(env["users"]["Psychologist"].user_id), "guardianName": "T", "guardianContact": "1"},
        files={"consentFile": (name, content, ctype)})


def _dossier(env, r):
    env["db"].expire_all()
    return env["db"].get(ToxicoDossier, r.json()["dossier_id"])


def _new_dossier(env, consent_file=None):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name="Legacy")
    data = {"admission_date": date.today() - timedelta(days=3), "substance": "Alcool",
            "psychologist_id": env["users"]["Psychologist"].user_id,
            "guardian_name": "T", "guardian_contact": "1"}
    if consent_file:
        data["consent_file"] = consent_file
    return ToxicoRepository(env["db"]).create_dossier_after_patient_commit(pid, data)


def test_upload_stocke_hors_static_sous_un_nom_uuid(env, http, storage):
    r = _admit(env, http)
    assert r.status_code == 201, r.text
    d = _dossier(env, r)
    assert ID_RE.match(d.consent_file), d.consent_file
    assert (storage / d.consent_file).read_bytes() == PDF
    assert not os.path.exists(os.path.join("static", "uploads", "toxico_consents", d.consent_file))


def test_static_n_expose_plus_le_consentement(env, http):
    r = _admit(env, http)
    name = _dossier(env, r).consent_file
    anon = http.get(f"/static/uploads/toxico_consents/{name}")
    assert anon.status_code in (401, 404)


def test_lecture_autorisee_contenu_type_et_audit(env, http):
    r = _admit(env, http)
    d = _dossier(env, r)
    q = env["db"].query(AuditUserAction).filter_by(resource_type="ToxicoConsent", resource_id=d.id)
    before = q.count()
    _as(env["users"]["Psychologist"], "Psychologist")
    g = http.get(f"/toxico/dossiers/{d.id}/consent")
    assert g.status_code == 200, g.text
    assert g.content == PDF and g.headers["content-type"].startswith("application/pdf")
    assert q.count() == before + 1


@pytest.mark.parametrize("role", ROLES)
def test_matrice_de_roles_lecture(env, http, role):
    r = _admit(env, http)
    d = _dossier(env, r)
    _as(env["users"][role], role)
    g = http.get(f"/toxico/dossiers/{d.id}/consent")
    assert g.status_code == (200 if role in READ_ALLOWED else 403), (role, g.status_code)


def test_lecture_sans_jeton_401(env, http):
    r = _admit(env, http)
    d = _dossier(env, r)
    app.dependency_overrides.pop(auth_endpoints.get_current_user, None)
    assert http.get(f"/toxico/dossiers/{d.id}/consent").status_code == 401


def test_dossier_sans_fichier_ou_inconnu_404(env, http):
    d = _new_dossier(env)
    _as(env["users"]["admin"], "admin")
    assert http.get(f"/toxico/dossiers/{d.id}/consent").status_code == 404
    assert http.get("/toxico/dossiers/99999999/consent").status_code == 404


def test_valeur_en_base_non_conforme_jamais_servie(env, http):
    """Une valeur type '../../x' ou un ancien chemin /static ne doit jamais sortir du dossier de stockage."""
    r = _admit(env, http)
    d = _dossier(env, r)
    _as(env["users"]["admin"], "admin")
    for bad in ("../../etc/passwd", "/static/uploads/toxico_consents/x.pdf", "None_None_1.pdf"):
        d.consent_file = bad
        env["db"].flush()
        assert http.get(f"/toxico/dossiers/{d.id}/consent").status_code == 404, bad


@pytest.mark.parametrize("content,name,ctype", [
    pytest.param(b"MZ not a pdf", "evil.pdf", "application/pdf", id="faux-pdf"),
    pytest.param(PDF + b"0" * (5 * 1024 * 1024), "big.pdf", "application/pdf", id="trop-gros"),
])
def test_fichier_invalide_ou_trop_gros_refuse(env, http, storage, content, name, ctype):
    r = _admit(env, http, content=content, name=name, ctype=ctype)
    assert r.status_code in (413, 422), r.text
    assert not storage.exists() or not list(storage.iterdir())


def _load_migration():
    path = os.path.join(os.path.dirname(__file__), "..", "scripts", "migrate_toxico_consents.py")
    spec = importlib.util.spec_from_file_location("migrate_toxico_consents", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_de_migration_deplace_renomme_et_met_a_jour(env, tmp_path, storage):
    mig = _load_migration()
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "None_None_1700000000.pdf").write_bytes(PDF)
    d = _new_dossier(env, "/static/uploads/toxico_consents/None_None_1700000000.pdf")
    moved = mig.migrate(env["db"], legacy_dir=str(legacy), storage_dir=str(storage))
    assert any(m[0] == "None_None_1700000000.pdf" for m in moved)
    env["db"].refresh(d)
    assert ID_RE.match(d.consent_file)
    assert (storage / d.consent_file).read_bytes() == PDF
    assert not (legacy / "None_None_1700000000.pdf").exists()
    # idempotent : le deuxieme passage ne trouve plus rien a deplacer
    assert not any(m[0] == "None_None_1700000000.pdf"
                   for m in mig.migrate(env["db"], legacy_dir=str(legacy), storage_dir=str(storage)))


def test_script_de_migration_fichier_manquant_laisse_la_ligne(env, tmp_path, storage):
    mig = _load_migration()
    legacy = tmp_path / "legacy2"
    legacy.mkdir()
    d = _new_dossier(env, "/static/uploads/toxico_consents/absent.pdf")
    mig.migrate(env["db"], legacy_dir=str(legacy), storage_dir=str(storage))
    env["db"].refresh(d)
    assert d.consent_file == "/static/uploads/toxico_consents/absent.pdf"
