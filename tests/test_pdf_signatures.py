# tests/test_pdf_signatures.py
"""Zones de signature des PDF (2026-10-22) + validation de sortie toxico par
le promoteur. Texte extrait via pypdf (WeasyPrint sous-ensemble les polices :
jamais de recherche dans les octets bruts)."""
import io
import os
import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, meta
from pypdf import PdfReader

from api_backend.backend_app.main import app
from api_backend.backend_app.routes.auth import auth_endpoints
from api_backend.backend_app.routes.toxico import toxico_endpoint
from api_backend.backend_app.security.role_map import normalize_role_name
from api_backend.backend_app.utils.pdf_generator import render_pdf_from_template
from models.toxico import ToxicoDossier
from repositories.toxico_repo import ToxicoRepository
from tests.conftest import auth_headers, create_test_user, create_test_patient

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'api_backend', 'backend_app', 'utils', 'templates')
PWD = "TestPass123!"
HEADER = {"structure": SimpleNamespace(name="Centre Signatures", slogan=None), "logo_path": None}
DATE_LINE = "Date : ____"
DISCHARGER_TITLE = "Le responsable administratif (promoteur ou manager)"


def _pages(content: bytes):
    # espaces normalises : un titre long peut etre coupe sur deux lignes
    return [" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(content)).pages]


def _text(content: bytes) -> str:
    return "\n".join(_pages(content))


def _after(txt: str, marker: str) -> str:
    assert marker in txt, marker
    return txt[txt.rindex(marker):]


def _assert_block_on_one_page(content: bytes, titles):
    """Le bloc n'est jamais coupe : tous les titres et toutes les lignes
    'Date :' sont sur une meme page, et le bloc n'apparait qu'une fois."""
    pages = _pages(content)
    holders = [i for i, p in enumerate(pages) if DATE_LINE in p]
    assert len(holders) == 1, holders
    page = pages[holders[0]]
    assert page.count(DATE_LINE) == len(titles)
    for t in titles:
        assert _text(content).count(t) == 1, t
        assert t in page, t


class _Any:
    """Valeur neutre pour rendre un template sans contexte metier."""
    def __getattr__(self, n): return _Any()
    def __getitem__(self, k): return _Any()
    def __iter__(self): return iter(())
    def __str__(self): return ""
    def __bool__(self): return False
    def __len__(self): return 0


def _neutral_ctx(template, **extra):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    src = open(os.path.join(TEMPLATE_DIR, template), encoding="utf-8").read()
    ctx = {n: _Any() for n in meta.find_undeclared_variables(env.parse(src))}
    ctx.update(HEADER)
    ctx.update(extra)
    return ctx


# --- Partial direct ---

def test_partial_noms_optionnels_et_echappes():
    tpl = Environment(loader=FileSystemLoader(TEMPLATE_DIR)).from_string(
        "{% from '_pdf_signatures.html' import signature_block %}"
        "{{ signature_block([{'title': 'A', 'name': n}, {'title': 'B'}]) }}")
    html = tpl.render(n="<b>Jo & Co</b>")
    assert "&lt;b&gt;Jo &amp; Co&lt;/b&gt;" in html and "<b>Jo" not in html
    assert "page-break-inside: avoid" in html
    assert html.count('class="sig-name"') == 1  # B sans nom : rien d'imprime
    assert html.count("sig-space") >= 2


def test_partial_mise_en_page_gauche_ligne_courte():
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    one = env.from_string("{% from '_pdf_signatures.html' import signature_block %}"
                          "{{ signature_block([{'title': 'A'}]) }}").render()
    two = env.from_string("{% from '_pdf_signatures.html' import signature_block %}"
                          "{{ signature_block([{'title': 'A'}, {'title': 'B'}]) }}").render()
    assert "text-align: left" in one and "sig-box-right" in one  # classe definie dans le CSS
    assert 'class="sig-box"' in one and 'class="sig-box sig-box-right"' not in one
    assert 'class="sig-box"' in two and two.count('class="sig-box sig-box-right"') == 1
    assert "width: 58mm" in one and "width: 85mm" in one
    assert "height: 1.7cm" in one


# --- Templates a une case, sans nom ---

def test_lettre_de_sortie_hospitalisation_medecin_referent_sans_nom():
    stay = {"patient_name": "Patient Lettre", "admitted_at": "01/01/2026", "admitted_by_name": "NurseCreatorX",
            "admission_reason": "Motif", "discharged_at": "05/01/2026", "duration_label": "4 jour(s) 0 h",
            "disposition_label": "Domicile", "discharged_by_name": "DocDischargeX", "discharge_note": None,
            "status_updates": [{"created_at": "02/01/2026", "status": "stable", "status_label": "Stable",
                                "created_by_name": "NurseUpdateX", "note": "ok"}]}
    pdf = render_pdf_from_template("hospitalization_discharge_letter_template.html",
                                   {**HEADER, "date_impression": "x", "stay": stay})
    txt = _text(pdf)
    zone = _after(txt, "Le médecin référent")
    for n in ("NurseCreatorX", "DocDischargeX", "NurseUpdateX"):
        assert n in txt and n not in zone
    _assert_block_on_one_page(pdf, ["Le médecin référent"])


def test_dossier_medical_medecin_referent_sans_nom():
    ctx = _neutral_ctx("dossier_export_template.html",
                       historique_spirituel=[{"consultation_date": "01/01/2026", "type_consultation": "Visite",
                                              "created_by_name": "CreatorDossierX"}])
    pdf = render_pdf_from_template("dossier_export_template.html", ctx)
    txt = _text(pdf)
    assert "CreatorDossierX" in txt and "CreatorDossierX" not in _after(txt, "Le médecin référent")
    _assert_block_on_one_page(pdf, ["Le médecin référent"])


def _lab_ctx(n_rows=3):
    return {**HEADER,
            "patient": {"nom": "Patient Labo", "sexe": "M", "age": 30, "type": "interne", "code": "P1"},
            "examen": {"code": "EX1", "nom": "NFS"},
            "result_info": {"date_test": "01/01/2026", "status": "valide", "prescripteur": "DocPrescripteurX",
                            "note": "Conclusion"},
            "details": [{"parametre_nom": f"Param{i}", "valeur": "1", "unite": "g", "reference_str": "0-2",
                         "is_abnormal": False, "interpretation": "N"} for i in range(n_rows)]}


def test_resultat_labo_chef_du_laboratoire_fusionne():
    pdf = render_pdf_from_template("lab_result_template.html", _lab_ctx())
    txt = _text(pdf)
    zone = _after(txt, "Le chef du laboratoire")
    assert "DocPrescripteurX" in txt and "DocPrescripteurX" not in zone
    assert "Le Biologiste / Responsable Labo" not in txt  # ancien bloc remplace, pas duplique
    assert "Document généré numériquement" in txt  # information existante conservee
    pages = _pages(pdf)
    assert any("Le chef du laboratoire" in p and "Document généré numériquement" in p for p in pages)
    _assert_block_on_one_page(pdf, ["Le chef du laboratoire"])


def test_resultat_labo_long_bloc_jamais_coupe():
    pdf = render_pdf_from_template("lab_result_template.html", _lab_ctx(n_rows=60))
    assert len(_pages(pdf)) >= 2
    assert any("Le chef du laboratoire" in p and "Document généré numériquement" in p for p in _pages(pdf))
    _assert_block_on_one_page(pdf, ["Le chef du laboratoire"])


def test_liste_toxico_sortis_visa_direction_sans_nom():
    rows = [{"name": "PatSortiX", "code": "C1", "admission": "a", "discharge": "b", "reason": "Guérison",
             "psychologist": "PsyListeX", "stays_count": 1}]
    pdf = render_pdf_from_template("toxico_discharged_export_template.html",
                                   {**HEADER, "rows": rows, "total": 1, "truncated": False, "cap": 2000,
                                    "filters_label": "", "date_impression": "x"})
    txt = _text(pdf)
    zone = _after(txt, "Visa de la direction")
    assert "PsyListeX" in txt and "PsyListeX" not in zone and "PatSortiX" not in zone
    _assert_block_on_one_page(pdf, ["Visa de la direction"])


# --- Pas de signature ---

@pytest.mark.parametrize("template", ["invoice_template.html", "cs_export_template.html",
                                      "patients_export_template.html"])
def test_pas_de_signature_sources(template):
    src = open(os.path.join(TEMPLATE_DIR, template), encoding="utf-8").read()
    assert "_pdf_signatures" not in src and "signature_block" not in src


@pytest.mark.parametrize("template", ["cs_export_template.html", "patients_export_template.html"])
def test_pas_de_signature_rendu(template):
    txt = _text(render_pdf_from_template(template, _neutral_ctx(template)))
    assert DATE_LINE not in txt and "médecin référent" not in txt


def test_pas_de_signature_facture(db_session, monkeypatch):
    from tests.test_invoice_pdf_staff_discount import _make_tx, _capture_context
    tx = _make_tx(db_session)
    ctx = _capture_context(db_session, tx, monkeypatch)
    monkeypatch.undo()
    txt = _text(render_pdf_from_template(ctx["template"], ctx["context"]))
    assert DATE_LINE not in txt and "Visa" not in txt


# --- Dossier toxico : deux cases avec noms ---

def _stay(n, psy, by, discharged=True):
    return {"stay_number": n, "admission_date": date(2026, 1, n), "discharge_date": date(2026, 2, n) if discharged else None,
            "discharge_reason": "guerison" if discharged else None, "discharge_note": None,
            "psychologist_name": psy, "substance": "Alcool", "discharged_by_name": by if discharged else None}


def test_contexte_dossier_toxico_noms_du_dernier_sejour():
    d = {"isActive": False, "firstName": "A", "lastName": "B",
         "stays": [_stay(2, "PsyDernier", "PromoDernier"), _stay(1, "PsyPremier", "MgrPremier")]}
    ctx = toxico_endpoint._build_dossier_pdf_context(d)
    assert ctx["sig_psychologist"] == "PsyDernier" and ctx["sig_discharger"] == "PromoDernier"
    d["isActive"] = True
    d["stays"][0] = _stay(2, "PsyDernier", None, discharged=False)
    ctx = toxico_endpoint._build_dossier_pdf_context(d)
    assert ctx["sig_psychologist"] == "PsyDernier" and ctx["sig_discharger"] == ""


def test_contexte_dossier_toxico_sans_sejour_repli_psychologue_du_dossier():
    d = {"isActive": True, "firstName": "A", "lastName": "B", "stays": [], "psychologist": "PsyLegacy"}
    assert toxico_endpoint._build_dossier_pdf_context(d)["sig_psychologist"] == "PsyLegacy"
    d["psychologist"] = "Non assigné"
    assert toxico_endpoint._build_dossier_pdf_context(d)["sig_psychologist"] == ""


def test_dossier_toxico_noms_html_echappes():
    d = {"isActive": False, "firstName": "A", "lastName": "B",
         "stays": [_stay(1, "<b>Psy&Co</b>", "<i>Promo</i>")]}
    pdf = render_pdf_from_template("toxico_dossier_export_template.html",
                                   {**HEADER, **toxico_endpoint._build_dossier_pdf_context(d), "date_impression": "x"})
    zone = _after(_text(pdf), "Le psychologue")
    assert "<b>Psy&Co</b>" in zone and "<i>Promo</i>" in zone
    _assert_block_on_one_page(pdf, ["Le psychologue", DISCHARGER_TITLE])


ROLES = ("Psychologist", "SpiritualCounsellor", "admin", "ToxicoManager", "Assistant",
         "medecin", "nurse", "secretaire", "laborantin", "promoteur", "StockController")
STAFF = {"ToxicoManager", "Psychologist", "SpiritualCounsellor", "Assistant", "admin"}
READ_ALLOWED = STAFF | {"promoteur"}
DISCHARGE_ALLOWED = {"ToxicoManager", "admin", "promoteur"}


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
    mark = "Sg" + uuid.uuid4().hex[:8]
    users = {}
    for r in ROLES:
        u = create_test_user(db_session, f"t_sig_{r.lower()}", r, password=PWD)
        users[r] = u
    users["Psychologist"].full_name = f"PsyNom{mark}"
    users["promoteur"].full_name = f"PromoNom{mark}"
    users["ToxicoManager"].full_name = f"MgrNom{mark}"
    db_session.flush()
    return {"db": db_session, "users": users, "repo": ToxicoRepository(db_session), "mark": mark}


@pytest.fixture
def http(env, api_client):
    return api_client(auth_endpoints, toxico_endpoint)


def _as(user, *roles):
    user.roles = [normalize_role_name(r) for r in roles]
    app.dependency_overrides[auth_endpoints.get_current_user] = lambda: user


def _new(env, n_evals=0):
    pid, _ = create_test_patient(env["db"], env["users"]["Assistant"], first_name=f"{env['mark']}P", last_name="Sig")
    d = env["repo"].create_dossier_after_patient_commit(pid, {
        "admission_date": date.today() - timedelta(days=60), "substance": "Alcool",
        "psychologist_id": env["users"]["Psychologist"].user_id})
    for i in range(n_evals):
        env["repo"].process_evaluation(d.id, {"target_phase": 1, "decision": "MAINTAIN",
                                              "observation": f"Obs{i}{env['mark']} " + "texte long " * 30,
                                              "recommendation": f"Reco{env['mark']}"},
                                       env["users"]["Psychologist"].user_id)
    return pid, d.id


def test_dossier_toxico_sorti_par_promoteur_noms_imprimes(env, http):
    pid, did = _new(env)
    _as(env["users"]["promoteur"], "promoteur")
    r = http.post(f"/toxico/discharge/{did}", json={"reason": "guerison"})
    assert r.status_code == 200, r.text
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    pdf = http.get(f"/toxico/patients/{pid}/export")
    assert pdf.status_code == 200, pdf.text
    zone = _after(_text(pdf.content), "Le psychologue")
    assert f"PsyNom{env['mark']}" in zone and f"PromoNom{env['mark']}" in zone
    assert f"MgrNom{env['mark']}" not in zone  # l'exporteur n'est jamais imprime
    _assert_block_on_one_page(pdf.content, ["Le psychologue", DISCHARGER_TITLE])


def test_dossier_toxico_actif_case_responsable_vierge(env, http):
    pid, _ = _new(env)
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    pdf = http.get(f"/toxico/patients/{pid}/export")
    txt = _text(pdf.content)
    zone = _after(txt, DISCHARGER_TITLE)
    assert f"PsyNom{env['mark']}" in _after(txt, "Le psychologue")
    assert f"PromoNom{env['mark']}" not in zone and f"MgrNom{env['mark']}" not in zone
    # apres le titre : seulement la ligne Date (aucun nom parasite)
    rest = zone[len(DISCHARGER_TITLE):].strip()
    assert rest.startswith("Date :"), rest[:80]


def test_dossier_toxico_long_bloc_jamais_coupe(env, http):
    pid, _ = _new(env, n_evals=12)
    _as(env["users"]["admin"], "admin")
    pdf = http.get(f"/toxico/patients/{pid}/export")
    assert pdf.status_code == 200
    assert len(_pages(pdf.content)) >= 2
    _assert_block_on_one_page(pdf.content, ["Le psychologue", DISCHARGER_TITLE])


# --- Droits du promoteur ---

def test_promoteur_lecture_sans_texte_des_evaluations(env, http):
    pid, did = _new(env, n_evals=1)
    _as(env["users"]["promoteur"], "promoteur")
    assert http.get("/toxico/patients", params={"search": env["mark"]}).status_code == 200
    assert http.get("/toxico/dossiers/discharged").status_code == 200
    assert http.get("/toxico/stats/dashboard").status_code == 200
    r = http.get(f"/toxico/patients/{pid}")
    assert r.status_code == 200, r.text
    ev = r.json()["evaluations"]
    assert ev and ev[0]["observation"] is None and ev[0]["recommendation"] is None
    assert ev[0]["decision"] == "MAINTAIN"
    _as(env["users"]["ToxicoManager"], "ToxicoManager")
    ev = http.get(f"/toxico/patients/{pid}").json()["evaluations"]
    assert ev[0]["observation"].startswith(f"Obs0{env['mark']}")


def test_promoteur_ni_admission_ni_evaluation_ni_exports(env, http):
    pid, did = _new(env)
    _as(env["users"]["promoteur"], "promoteur")
    assert http.post("/toxico/admission", data={}).status_code == 403
    assert http.post("/toxico/evaluation", json={"patientId": pid, "target_phase": 1,
                                                 "decision": "MAINTAIN", "observation": "x"}).status_code == 403
    assert http.get(f"/toxico/patients/{pid}/export").status_code == 403
    assert http.get("/toxico/dossiers/discharged/export").status_code == 403
    assert http.get("/toxico/psychologists").status_code == 403
    env["db"].expire_all()
    assert env["db"].get(ToxicoDossier, did).is_active is True


@pytest.mark.parametrize("role", ROLES)
def test_matrice_sortie_11_roles(env, http, role):
    _, did = _new(env)
    _as(env["users"][role], role)
    r = http.post(f"/toxico/discharge/{did}", json={"reason": "guerison"})
    assert r.status_code == (200 if role in DISCHARGE_ALLOWED else 403), (role, r.text)


@pytest.mark.parametrize("role", ROLES)
def test_matrice_lectures_11_roles(env, http, role):
    pid, _ = _new(env)
    _as(env["users"][role], role)
    exp = 200 if role in READ_ALLOWED else 403
    for url in ("/toxico/patients", f"/toxico/patients/{pid}", "/toxico/dossiers/discharged",
                "/toxico/stats/dashboard"):
        assert http.get(url).status_code == exp, (role, url)
    assert http.get("/toxico/dossiers/discharged/export").status_code == (200 if role in STAFF else 403), role
    assert http.get(f"/toxico/patients/{pid}/export").status_code ==         (200 if role in {"Psychologist", "ToxicoManager", "admin"} else 403), role


def test_sortie_promoteur_trace_discharged_by(env, http):
    from models.toxico import ToxicoStay
    _, did = _new(env)
    _as(env["users"]["promoteur"], "promoteur")
    assert http.post(f"/toxico/discharge/{did}", json={"reason": "guerison"}).status_code == 200
    env["db"].expire_all()
    stay = env["db"].query(ToxicoStay).filter_by(dossier_id=did).order_by(ToxicoStay.stay_number.desc()).first()
    assert stay.discharged_by == env["users"]["promoteur"].user_id


def test_promoteur_et_psychologue_voit_le_texte(env, http):
    pid, _ = _new(env, n_evals=1)
    _as(env["users"]["promoteur"], "promoteur", "Psychologist")
    ev = http.get(f"/toxico/patients/{pid}").json()["evaluations"]
    assert ev[0]["observation"].startswith(f"Obs0{env['mark']}") and ev[0]["recommendation"]


@pytest.fixture
def http_dossier(env, api_client):
    from api_backend.backend_app.routes.patient_dossier import patient_dossier_endpoint
    return api_client(auth_endpoints, patient_dossier_endpoint)


@pytest.mark.parametrize("roles,masked", [(("promoteur",), True), (("ToxicoManager",), False),
                                          (("promoteur", "Psychologist"), False), (("admin",), False)])
def test_dossier_consolide_meme_regle_de_masquage(env, http_dossier, roles, masked):
    pid, _ = _new(env, n_evals=1)
    _as(env["users"][roles[0]], *roles)
    r = http_dossier.get(f"/patients/{pid}/dossier")
    assert r.status_code == 200, r.text
    ev = r.json()["dossier_toxico"]["evaluations"]
    assert ev and ev[0]["decision"] == "MAINTAIN"
    if masked:
        assert ev[0]["observation"] is None and ev[0]["recommendation"] is None
    else:
        assert ev[0]["observation"].startswith(f"Obs0{env['mark']}")


def test_dossier_consolide_exports_sans_texte_d_evaluation(env, http_dossier):
    """Exports PDF/Excel du dossier consolide : passent par get_full_dossier
    (masque) et n'impriment de toute facon pas le texte des evaluations."""
    pid, _ = _new(env, n_evals=1)
    _as(env["users"]["promoteur"], "promoteur")
    r = http_dossier.get(f"/patients/{pid}/dossier/export", params={"format": "pdf"})
    assert r.status_code == 200, r.text
    assert f"Obs0{env['mark']}" not in _text(r.content)


def test_promoteur_jeton_reel(env, http):
    _, did = _new(env)
    h = auth_headers(http, "t_sig_promoteur", PWD)
    assert http.get("/toxico/patients", headers=h).status_code == 200
    assert http.post(f"/toxico/discharge/{did}", json={"reason": "guerison"}, headers=h).status_code == 200
    assert http.post("/toxico/admission", data={}, headers=h).status_code == 403
