# tests/test_toxico_exports.py
"""Exports PDF toxico (2026-10-22) :
- GET /toxico/dossiers/discharged/export : liste des patients sortis, memes
  filtres et memes roles que la liste, toutes les lignes (plafond signale).
- GET /toxico/patients/{patient_id}/export : dossier toxico complet (sejours,
  phases, evaluations) - Psychologist/ToxicoManager/admin uniquement.
Base de dev partagee : marqueurs uniques, assertions bornees a nos donnees."""
import io
import uuid
from types import SimpleNamespace
from datetime import date, timedelta

import pytest
from pypdf import PdfReader

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from models.toxico import ToxicoStay
from repositories.toxico_repo import ToxicoRepository
from tests.conftest import auth_headers, create_test_user, create_test_patient

PWD = "TestPass123!"
ROLES = ("Psychologist", "SpiritualCounsellor", "admin", "ToxicoManager", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "promoteur", "StockController")
LIST_ALLOWED = {"ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin"}
DOSSIER_ALLOWED = {"Psychologist", "ToxicoManager", "admin"}
LIST_URL = "/toxico/dossiers/discharged/export"


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


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
    users = {r: create_test_user(db, f"t_toxexp_{r.lower()}", r, password=PWD) for r in ROLES}
    return {"db": db, "users": users, "repo": ToxicoRepository(db),
            "mark": "Ex" + uuid.uuid4().hex[:10]}


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, role):
    user.roles = [normalize_role_name(role)]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _new(env, suffix="A", last_name="Sortie", first_name=None):
    pid, code = create_test_patient(env["db"], env["users"]["Assistant"],
                                    first_name=first_name or f"{env['mark']}{suffix}",
                                    last_name=last_name)
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


def _two_stays(env):
    """Patient sorti, readmis, evalue a chaque sejour, de nouveau sorti."""
    repo, users = env["repo"], env["users"]
    pid, code, did = _new(env, "Deux", last_name="Hélène-Éloïse")
    repo.process_evaluation(did, {"target_phase": 2, "decision": "PROGRESS",
                                  "observation": f"ObsUn{env['mark']}",
                                  "recommendation": "Continuer l'accompagnement"},
                            users["Psychologist"].user_id)
    _discharge(env, did, "abandon", "départ volontaire", on=date.today() - timedelta(days=20))
    repo.create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=10), "substance": "Cannabis",
        "psychologist_id": users["Psychologist"].user_id})
    repo.process_evaluation(did, {"target_phase": 1, "decision": "REGRESS",
                                  "observation": f"ObsDeux{env['mark']}"},
                            users["Psychologist"].user_id)
    _discharge(env, did, "exclusion", "règlement intérieur")
    return pid, code, did


# --- Liste des patients sortis ---

def test_liste_applique_les_filtres(env, http):
    today = date.today()
    _, _, a = _new(env, "Gue")
    _, _, b = _new(env, "Aba")
    _, _, _act = _new(env, "Act")  # actif : jamais liste
    _discharge(env, a, "guerison", on=today - timedelta(days=10))
    _discharge(env, b, "abandon", on=today - timedelta(days=2))
    _as(env["users"]["Assistant"], "Assistant")
    r = http.get(LIST_URL, params={"search": env["mark"], "reason": "guerison"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    txt = _pdf_text(r.content)
    assert f"{env['mark']}Gue" in txt and f"{env['mark']}Aba" not in txt
    assert f"{env['mark']}Act" not in txt
    assert "Guérison" in txt and "1 patient(s)" in txt and "Motif : Guérison" in txt
    assert "Substance" not in txt and "Alcool" not in txt  # colonne retiree de la liste
    r2 = http.get(LIST_URL, params={"search": env["mark"],
                                    "discharged_from": (today - timedelta(days=5)).isoformat()})
    txt2 = _pdf_text(r2.content)
    assert f"{env['mark']}Aba" in txt2 and f"{env['mark']}Gue" not in txt2


def test_liste_toutes_les_lignes_au_dela_d_une_page(env, http):
    n = 22  # > per_page par defaut (20) de la liste paginee
    for i in range(n):
        _, _, d = _new(env, f"N{i:02d}x")
        _discharge(env, d)
    _as(env["users"]["admin"], "admin")
    txt = _pdf_text(http.get(LIST_URL, params={"search": env["mark"]}).content)
    assert f"{n} patient(s)" in txt
    for i in range(n):
        assert f"{env['mark']}N{i:02d}x" in txt
    assert "tronqué" not in txt


def test_liste_plafond_signale(env, http, monkeypatch):
    monkeypatch.setattr(toxico_endpoint, "DISCHARGED_EXPORT_CAP", 2)
    for i in range(3):
        _, _, d = _new(env, f"C{i}x")
        _discharge(env, d)
    _as(env["users"]["admin"], "admin")
    txt = _pdf_text(http.get(LIST_URL, params={"search": env["mark"]}).content)
    assert "tronqué" in txt and "3 patient(s)" in txt
    assert sum(f"{env['mark']}C{i}x" in txt for i in range(3)) == 2


def test_liste_dates_inversees_422(env, http):
    _as(env["users"]["admin"], "admin")
    r = http.get(LIST_URL, params={"discharged_from": "2026-05-02", "discharged_to": "2026-05-01"})
    assert r.status_code == 422


@pytest.mark.parametrize("role", ROLES)
def test_liste_matrice_de_roles(env, http, role):
    _as(env["users"][role], role)
    r = http.get(LIST_URL, params={"search": env["mark"]})
    assert r.status_code == (200 if role in LIST_ALLOWED else 403), (role, r.text)


# --- Dossier toxico ---

def test_dossier_deux_sejours_contenu(env, http, monkeypatch):
    centre = f"Centre{env['mark']}"
    monkeypatch.setattr(toxico_endpoint, "get_pdf_header_context",
                        lambda _cfg: {"structure": SimpleNamespace(name=centre, slogan=None),
                                      "logo_path": None})
    pid, code, _ = _two_stays(env)
    _as(env["users"]["Psychologist"], "Psychologist")
    r = http.get(f"/toxico/patients/{pid}/export")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert f"dossier_toxico_{pid}.pdf" in r.headers["content-disposition"]
    txt = _pdf_text(r.content)
    assert centre in txt  # en-tete du centre (contexte d'en-tete force)
    assert f"{env['mark']}Deux" in txt and code in txt
    assert "Hélène-Éloïse" in txt  # accents preserves
    assert "Séjour 1" in txt and "Séjour 2" in txt
    assert "Abandon" in txt and "départ volontaire" in txt
    assert "Exclusion" in txt and "règlement intérieur" in txt
    assert f"ObsUn{env['mark']}" in txt and f"ObsDeux{env['mark']}" in txt
    assert "Progression" in txt and "Régression" in txt
    assert "Sorti" in txt and "Cannabis" in txt
    # l'evaluation 1 est sous le sejour 1, la 2 sous le sejour 2
    assert txt.index(f"ObsUn{env['mark']}") < txt.index("Séjour 2") < txt.index(f"ObsDeux{env['mark']}")


def test_dossier_actif_exportable(env, http):
    pid, _, _ = _new(env, "Actif")
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    r = http.get(f"/toxico/patients/{pid}/export")
    assert r.status_code == 200, r.text
    txt = _pdf_text(r.content)
    assert "Actif" in txt and "En cours" in txt


def test_dossier_inconnu_404(env, http):
    _as(env["users"]["admin"], "admin")
    assert http.get("/toxico/patients/999999999/export").status_code == 404


def test_injection_html_rendue_en_texte(env, http):
    pid, _, did = _new(env, first_name=f"<b>{env['mark']}</b>", last_name="<i>Inj</i>")
    _discharge(env, did, "autre", "<script>x</script>note")
    _as(env["users"]["admin"], "admin")
    txt = _pdf_text(http.get(f"/toxico/patients/{pid}/export").content)
    assert f"<b>{env['mark']}</b>" in txt and "<i>Inj</i>" in txt
    assert "<script>x</script>note" in txt
    txt_list = _pdf_text(http.get(LIST_URL, params={"search": env["mark"]}).content)
    assert f"<b>{env['mark']}</b>" in txt_list


@pytest.mark.parametrize("role", ROLES)
def test_dossier_matrice_de_roles(env, http, role):
    pid, _, _ = _new(env, "Role")
    _as(env["users"][role], role)
    r = http.get(f"/toxico/patients/{pid}/export")
    assert r.status_code == (200 if role in DOSSIER_ALLOWED else 403), (role, r.text)


def test_sans_authentification_401(env, http):
    app.dependency_overrides.pop(auth_endpoints.get_current_user, None)
    assert http.get(LIST_URL).status_code == 401
    assert http.get("/toxico/patients/1/export").status_code == 401


def test_jetons_reels(env, http):
    """2 vraies connexions : psychologue autorise, assistant refuse sur le dossier."""
    pid, _, _ = _new(env, "Tok")
    h_psy = auth_headers(http, "t_toxexp_psychologist", PWD)
    h_ast = auth_headers(http, "t_toxexp_assistant", PWD)
    assert http.get(f"/toxico/patients/{pid}/export", headers=h_psy).status_code == 200
    assert http.get(f"/toxico/patients/{pid}/export", headers=h_ast).status_code == 403
    assert http.get(LIST_URL, params={"search": "zz"}, headers=h_ast).status_code == 200
