"""Catalogue du laboratoire aligne sur les fiches (scripts/seed_lab_catalogue.py), sur des bases JETABLES.

Les bases sont creees a partir de ci/schema_only.sql + ci/seed_application_roles.sql puis supprimees.
Les donnees attendues sont lues dans scripts/data/lab_catalogue.json (source de verite du chargement).
"""
import json
import os
import shutil
import subprocess
import sys
import uuid
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
import pytest
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.engine import make_url

from api_backend.backend_app.config import DATABASE_URL
from scripts import seed_lab_catalogue as seedmod
from utils.lab_reference import select_range

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CATALOGUE = seedmod.load_catalogue()
EXAMS = {e["code"]: e for e in CATALOGUE["exams"]}
pytestmark = pytest.mark.skipif(shutil.which("psql") is None, reason="psql requis")


def _url(dbname):
    return make_url(DATABASE_URL).set(database=dbname).render_as_string(hide_password=False)


def _pg(url):
    return seedmod._database_url(url)


def _admin_exec(sql):
    conn = psycopg2.connect(_pg(_url("postgres")))
    conn.autocommit = True
    try:
        conn.cursor().execute(sql)
    finally:
        conn.close()


@pytest.fixture(scope="module")
def template_db():
    name = "ah2_c1_tpl_" + uuid.uuid4().hex[:8]
    _admin_exec('CREATE DATABASE "%s"' % name)
    try:
        for f in ("ci/schema_only.sql", "ci/seed_application_roles.sql"):
            subprocess.run(["psql", _pg(_url(name)), "-X", "-q", "-v", "ON_ERROR_STOP=1",
                            "-f", os.path.join(ROOT, f)], check=True, capture_output=True)
        yield name
    finally:
        _admin_exec('DROP DATABASE IF EXISTS "%s" WITH (FORCE)' % name)


@pytest.fixture
def make_db(template_db):
    created = []

    def _make():
        name = "ah2_c1_db_" + uuid.uuid4().hex[:8]
        _admin_exec('CREATE DATABASE "%s" TEMPLATE "%s"' % (name, template_db))
        created.append(name)
        return _url(name)

    yield _make
    for name in created:
        _admin_exec('DROP DATABASE IF EXISTS "%s" WITH (FORCE)' % name)


def _run(url, sql, params=None, fetch=False):
    conn = psycopg2.connect(_pg(url))
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


# Petit catalogue "ancien" (comme la base de dev) avec un resultat lie a ses parametres. Patient invente.
OLD_SQL = """
INSERT INTO examens (id, code, nom, categorie, prix) VALUES
  (1, 'NFS', 'Numération Formule Sanguine', 'Hematologie', 3500),
  (8, 'TYPHOIDE', 'Typhoïde (IgG / IgM)', 'Serologie', NULL),
  (32, 'GLY_JEUN', 'Glycémie à jeun', 'Biochimie', 1500),
  (38, 'CREAT', 'Créatinine', 'Biochimie', 2000),
  (90, 'DEMO_TEST', 'Demo test exam', 'Biochimie', 7500);
INSERT INTO parametres (id, examen_id, nom_parametre, unite, type_valeur, input_type, ordre) VALUES
  (1, 1, 'Erythrocytes', '10^12/L', 'numeric', 'numeric', 1),
  (2, 1, 'Leucocytes', '/mm^3', 'numeric', 'numeric', 2),
  (4, 1, 'Hémoglobine', 'g/dL', 'numeric', 'numeric', 4),
  (9, 1, 'RDW', '%', 'numeric', 'numeric', 9),
  (11, 1, 'Lymphocytes', '10^9/L', 'numeric', 'numeric', 11),
  (35, 8, 'IgM Typhoïde', 'IU/mL', 'numeric', 'numeric', 1),
  (36, 8, 'IgG Typhoïde', 'IU/mL', 'numeric', 'numeric', 2),
  (26, 32, 'Glucose', 'g/L', 'numeric', 'numeric', 1),
  (77, 32, 'Glucose à jeun', 'g/L', 'numeric', 'numeric', 2),
  (83, 38, 'Créatinine', 'mg/dL', 'numeric', 'numeric', 1),
  (979, 90, 'Hemoglobin', 'g/dL', 'numeric', 'numeric', 1);
SELECT setval(pg_get_serial_sequence('public.examens', 'id'), 1000);
SELECT setval(pg_get_serial_sequence('public.parametres', 'id'), 1000);
INSERT INTO lab_results (result_id, test_type, status, examen_id, code_lab_patient, external_patient_info)
  VALUES (500, 'NFS', 'completed', 1, 'EXT-0101-0001', '{"nom": "PATIENT FICTIF", "age": 30, "sexe": "M"}');
INSERT INTO lab_result_details (detail_id, result_id, parametre_id, valeur_text, valeur_num) VALUES
  (700, 500, 1, '4.5', 4.5), (701, 500, 4, '13', 13), (702, 500, 11, '2.1', 2.1), (703, 500, 9, '12', 12);
"""
OLD_RANGES_SQL = """
INSERT INTO reference_ranges (id, parametre_id, sexe, age_min, age_max, valeur_min, valeur_max) VALUES
  (5, 1, 'M', 12, 18, 1.2, 1.8), (310, 979, 'M', 18, 120, 13, 17);
"""


@pytest.fixture
def old_db(make_db):
    url = make_db()
    _run(url, OLD_SQL)
    return url


def _seed(url, **kw):
    conn = psycopg2.connect(_pg(url))
    try:
        s = seedmod.seed(conn, CATALOGUE, **kw)
        conn.commit()
        return s
    finally:
        conn.close()


def _counts(url):
    return tuple(_run(url, "select count(*) from %s" % t, fetch=True)[0][0]
                 for t in ("examens", "parametres", "reference_ranges", "lab_results", "lab_result_details"))


def _active_labels(url, code):
    return [r[0] for r in _run(url, "select p.print_label from parametres p join examens e on e.id = p.examen_id "
                                    "where e.code = %s and p.is_active order by p.ordre, p.id", (code,), fetch=True)]


def test_seed_is_idempotent(old_db):
    first = _seed(old_db)
    after_first = _counts(old_db)
    snapshot = _run(old_db, "select * from parametres order by id", fetch=True)
    second = _seed(old_db)
    assert _counts(old_db) == after_first
    assert second["exams_added"] == [] and second["params_added"] == 0
    assert _run(old_db, "select * from parametres order by id", fetch=True) == snapshot
    assert len(first["exams_added"]) == len(CATALOGUE["exams"]) - 4


def test_no_link_broken_nothing_deleted_prices_untouched(old_db):
    before_ids = set(r[0] for r in _run(old_db, "select id from parametres", fetch=True))
    links = _run(old_db, "select d.detail_id, d.parametre_id, p.examen_id, r.examen_id from lab_result_details d "
                         "join parametres p on p.id = d.parametre_id join lab_results r on r.result_id = d.result_id "
                         "order by 1", fetch=True)
    _seed(old_db)
    after_ids = set(r[0] for r in _run(old_db, "select id from parametres", fetch=True))
    assert before_ids <= after_ids
    assert _run(old_db, "select d.detail_id, d.parametre_id, p.examen_id, r.examen_id from lab_result_details d "
                        "join parametres p on p.id = d.parametre_id join lab_results r on r.result_id = d.result_id "
                        "order by 1", fetch=True) == links
    prices = dict(_run(old_db, "select code, prix from examens", fetch=True))
    assert prices["NFS"] == 3500 and prices["GLY_JEUN"] == 1500 and prices["CREAT"] == 2000
    assert prices["TYPHOIDE"] is None and prices["DEMO_TEST"] == 7500
    new_codes = [c for c in EXAMS if c not in ("NFS", "TYPHOIDE", "GLY_JEUN", "CREAT")]
    assert all(prices[c] == 0 for c in new_codes)
    # nom_parametre jamais renomme ; le parametre hors fiche est garde mais desactive
    assert _run(old_db, "select nom_parametre, print_label, is_active from parametres where id in (1, 9) order by id",
                fetch=True) == [("Erythrocytes", "- Globules rouges (RBC)", True), ("RDW", None, False)]
    assert _run(old_db, "select is_active from parametres where id = 26", fetch=True) == [(False,)]
    assert _run(old_db, "select nom, categorie from examens where code = 'NFS'", fetch=True) == [
        ("Numération Formule Sanguine", "Hematologie")]


def test_every_exam_of_the_sheets_exists_with_family_and_ordered_parameters(old_db):
    _seed(old_db)
    rows = {r[0]: r[1:] for r in _run(old_db, "select code, layout_family, section, print_title, signature_label, "
                                              "method, sort_order from examens", fetch=True)}
    for code, e in EXAMS.items():
        assert code in rows, code
        assert rows[code] == (e["layout_family"], e["section"], e["print_title"], e["signature_label"],
                              e["method"], e["sort_order"]), code
        assert _active_labels(old_db, code) == [p["print_label"] for p in e["parameters"]], code
    for code in ("G_TEST", "TOXICO_UR", "AMYLASE", "PAL", "GGT", "AFP", "PSA", "PROLACTINE", "CULOT_UR", "PCV",
                 "PU", "FCU", "MYCOPLASMES", "ALB_SUCRE_UR", "HEPB_AGHBS", "TDR_PALU"):
        assert code in rows, code
    assert len(_active_labels(old_db, "TOXICO_UR")) == 13
    assert _active_labels(old_db, "TYPHOIDE") == ["Anticorps Typhoide IgG", "Anticorps Typhoide IgM"]


def test_serologies_pos_neg_with_titre_where_printed(old_db):
    _seed(old_db)
    kinds = _run(old_db, "select e.code, p.result_kind, p.input_type, p.options_list, p.choices from parametres p "
                         "join examens e on e.id = p.examen_id where p.is_active", fetch=True)
    by = {}
    for code, kind, it, ol, ch in kinds:
        by.setdefault(code, []).append((kind, it, ol, ch))
    for code in ("TYPHOIDE", "HEPC", "SYPHILIS", "HPYLORI", "HEPB_5EN1", "HEPB_AGHBS", "G_TEST", "TOXICO_UR"):
        assert all(k == ("pos_neg", "select", "POSITIF,NEGATIF", ["POSITIF", "NEGATIF"]) for k in by[code]), code
    for code in ("TOXO", "RUBE"):
        assert sorted(k[0] for k in by[code]) == ["numeric", "numeric", "pos_neg", "pos_neg"]
    # la typhoide du catalogue (IgM puis IgG numeriques) devient IgG puis IgM en POSITIF/NEGATIF
    assert _run(old_db, "select id, ordre, result_kind, type_valeur from parametres where examen_id = 8 order by ordre",
                fetch=True) == [(36, 1, "pos_neg", "text"), (35, 2, "pos_neg", "text")]


def test_units_mg_dl_for_the_variants(old_db):
    _seed(old_db)
    q = ("select p.unite from parametres p join examens e on e.id = p.examen_id where e.code = %s and p.print_label = %s")
    for code, label in [("UREE", "UREE"), ("CREAT", "CREAT"), ("ACIDE_URIQUE", "Acide Urique"),
                        ("CALCIUM", "CALCEMIE"), ("MAGNESIUM", "MAGNESEMIE"), ("PHOSPHORE", "PHOSPHORE"),
                        ("IONO_EXT", "CALCEMIE"), ("IONO_EXT", "MAGNESEMIE"), ("LIPIDES", "CHOLESTEROL"),
                        ("LIPIDES", "HDL"), ("LIPIDES", "LDL"), ("LIPIDES", "TRIGLICERIDES"),
                        ("BIL_TOTAL", "BILIRUBINE TOTALE")]:
        assert _run(old_db, q, (code, label), fetch=True) == [("mg/dl",)], (code, label)


def _ranges_for(url, code, label):
    rows = _run(url, "select r.id, r.sexe, r.age_min, r.age_max, r.age_min_days, r.age_max_days, r.ga_min_weeks, "
                     "r.ga_max_weeks, r.valeur_min, r.valeur_max from reference_ranges r "
                     "join parametres p on p.id = r.parametre_id join examens e on e.id = p.examen_id "
                     "where e.code = %s and p.print_label = %s", (code, label), fetch=True)
    keys = ("id", "sexe", "age_min", "age_max", "age_min_days", "age_max_days", "ga_min_weeks", "ga_max_weeks",
            "valeur_min", "valeur_max")
    return [SimpleNamespace(**dict(zip(keys, r))) for r in rows]


def _pick(url, code, label, sex, age_days):
    r = select_range(_ranges_for(url, code, label), sex, age_days)
    return None if r is None else (float(r.valeur_min), float(r.valeur_max))


def test_ranges_loaded_on_empty_table_and_selected_by_age(make_db):
    url = make_db()
    s = _seed(url)
    assert s["ranges_mode"] == "loaded"
    assert s["ranges_written"] == sum(len(p["ranges"]) for e in CATALOGUE["exams"] for p in e["parameters"])
    NB, CHILD, ADULT = 10, 3 * 365, 40 * 365
    hb = "- Taux d'HB (Hb)"
    assert _pick(url, "NFS", hb, "M", NB) == (16, 21.5)
    assert _pick(url, "NFS", hb, "M", CHILD) == (12, 17)
    assert _pick(url, "NFS", hb, "F", ADULT) == (12, 15)
    wbc = "- Globules blancs (WBC)"
    assert _pick(url, "NFS", wbc, "F", NB) == (5, 15)
    assert _pick(url, "NFS", wbc, "M", CHILD) == (5, 15)
    assert _pick(url, "NFS", wbc, "M", ADULT) == (5, 10)
    ret = "- Taux de Réticulocytes (RC)"
    assert _pick(url, "NFS", ret, "M", NB) == (2, 6)
    assert _pick(url, "NFS", ret, "M", CHILD) is None
    assert _pick(url, "NFS", ret, "F", ADULT) == (0.5, 2.5)
    rbc = "- Globules rouges (RBC)"
    assert _pick(url, "NFS", rbc, "M", ADULT) == (4.0, 5.5)
    assert _pick(url, "NFS", rbc, "F", CHILD) == (4.0, 5.0)
    assert _pick(url, "PSA", "PSA T", "M", 45 * 365) == (0, 2.5)
    assert _pick(url, "PSA", "PSA T", "M", 60 * 365) == (0, 4.0)
    assert _pick(url, "PSA", "PSA T", "F", 60 * 365) is None
    assert _pick(url, "PROLACTINE", "PROLACTINE", "F", ADULT) == (2, 20)
    assert _pick(url, "UREE", "UREE", "X", NB) == (10, 50)
    assert _pick(url, "UREE", "UREE", "M", None) == (10, 50)
    # plages ecrites en jours, sans annees
    assert _run(url, "select count(*) from reference_ranges where age_min is not null or age_max is not null",
                fetch=True) == [(0,)]


def test_existing_ranges_kept_unless_replace_flag(old_db):
    _run(old_db, OLD_RANGES_SQL)
    s = _seed(old_db)
    assert s["ranges_mode"] == "unchanged"
    assert _run(old_db, "select id from reference_ranges order by id", fetch=True) == [(5,), (310,)]
    s = _seed(old_db, replace_ranges=True)
    assert s["ranges_mode"] == "replaced" and s["ranges_deleted"] == 2
    n = _run(old_db, "select count(*) from reference_ranges", fetch=True)[0][0]
    assert n == s["ranges_written"] and not _run(old_db, "select 1 from reference_ranges where parametre_id = 979 or (parametre_id = 1 and valeur_max = 1.8)", fetch=True)
    _seed(old_db, replace_ranges=True)
    assert _run(old_db, "select count(*) from reference_ranges", fetch=True)[0][0] == n


def test_dry_run_writes_nothing(old_db, capsys):
    before = _run(old_db, "select * from examens order by id", fetch=True), _counts(old_db)
    assert seedmod.main(["--database-url", old_db, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "ESSAI" in out and "examens ajoutes" in out
    assert (_run(old_db, "select * from examens order by id", fetch=True), _counts(old_db)) == before


def test_check_constraints_reject_bad_family_and_kind(old_db):
    with pytest.raises(psycopg2.errors.CheckViolation):
        _run(old_db, "update examens set layout_family = 'poster' where id = 1")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _run(old_db, "update parametres set result_kind = 'boolean' where id = 1")
    assert _run(old_db, "insert into examens (code, nom, categorie) values ('NEW1', 'n', 'c') "
                        "returning layout_family, sort_order, is_active", fetch=True) == [("label_value", 0, True)]
    assert _run(old_db, "insert into parametres (examen_id, nom_parametre, unite, type_valeur) "
                        "values (1, 'x', 'u', 'numeric') returning result_kind, is_active, choices",
                fetch=True) == [("numeric", True, None)]


def test_catalogue_file_is_consistent():
    codes = [e["code"] for e in CATALOGUE["exams"]]
    assert len(codes) == len(set(codes)) and all(len(c) <= 20 for c in codes)
    for e in CATALOGUE["exams"]:
        assert e["layout_family"] in seedmod.FAMILIES
        for p in e["parameters"]:
            assert p["result_kind"] in seedmod.KINDS
            if p["result_kind"] in ("choice", "pos_neg"):
                assert p["choices"]
            for r in p["ranges"]:
                assert r["sexe"] in ("M", "F", "X") and r["min"] <= r["max"]
    doc = open(os.path.join(ROOT, "docs", "laboratory-templates.md"), encoding="utf-8").read()
    for code in codes:
        assert "`%s`" % code in doc, code


# --- organization_config : champs des fiches ---------------------------------------------------------

def test_config_fields_exposed():
    from api_backend.backend_app.routes.admin.config_endpoints import normalize_config_data
    from models.organization_config import OrganizationConfig
    cfg = OrganizationConfig(id=1, name="Centre", agrement_number="N 0001", footer_text="L1\nL2",
                             signature_label_default="Le Biologiste")
    out = normalize_config_data(cfg)
    assert out["agrement_number"] == "N 0001" and out["footer_text"] == "L1\nL2"
    assert out["signature_label_default"] == "Le Biologiste"


def _render_header(**fields):
    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "api_backend", "backend_app", "utils", "templates")))
    base = dict(name="Centre", slogan=None, address=None, city=None, po_box=None, phone=None, phone2=None,
                email=None, website=None, niu=None, rccm=None, legal_info=None)
    base.update(fields)
    html = env.get_template("_pdf_header.html").render(structure=SimpleNamespace(**base), logo_path=None)
    return html.split("</style>", 1)[1]


def test_pdf_header_prints_new_fields_only_when_filled():
    empty = _render_header(agrement_number=None, footer_text=None, signature_label_default=None)
    assert "agrement" not in empty and "footer-text" not in empty
    # une configuration ancienne (sans les attributs) donne le meme rendu
    assert _render_header() == empty
    filled = _render_header(agrement_number="N 0705/ST/TEST", footer_text="LIGNE UN\n\nLIGNE DEUX")
    assert "N 0705/ST/TEST" in filled
    assert "<p>LIGNE UN</p><p>LIGNE DEUX</p>" in filled


# --- ajouts du parcours navigateur (2026-10-31) : 12 parametres manquants, 2 examens de crachats ----------------

MISSING_PARAMS = [
    # code, libelle imprime, unite, type, sous-titre, libelle qui precede
    ("CYTO_SANG", "Hématies", "/mm3", "numeric", None, "CYTOLOGIE"),
    ("CYTO_SANG", "Leucocytes", "/mm3", "numeric", None, "Hématies"),
    ("CULOT_UR", "Cellules épithéliales", "/mm3", "text", None, "Leucocytes"),
    ("CULOT_UR", "Levures", "/mm3", "numeric", None, "Cellules épithéliales"),
    ("CULOT_UR", "BACTERIURIE QUANTITATIVE", "", "text", None, "CYTOLOGIE"),
    ("ECBU", "Cellules épithéliales", "/mm3", "text", "CYTOLOGIE", "Leucocytes"),
    ("CULT_ATB", "Hématies", "/mm3", "text", "CYTOLOGIE", "EXAMEN MICROSCOPIQUE"),
    ("CULT_ATB", "Leucocytes", "/mm3", "text", "CYTOLOGIE", "Hématies"),
    ("CULT_ATB", "Cellules épithéliales", "/mm3", "text", "CYTOLOGIE", "Leucocytes"),
    ("SPH_PUS", "Pyocytes", "/mm3", "text", "CYTOLOGIE", "EXAMEN MICROSCOPIQUE"),
    ("SPH_PUS", "Leucocytes", "/mm3", "text", "CYTOLOGIE", "Pyocytes"),
    ("TDR_PALU", "Parasitemie", "", "text", None, "RESULTAT"),
]


def test_catalogue_file_has_the_twelve_missing_parameters_in_printed_order():
    for code, label, unit, kind, group, before in MISSING_PARAMS:
        params = EXAMS[code]["parameters"]
        labels = [p["print_label"] for p in params]
        assert label in labels, (code, label)
        p = params[labels.index(label)]
        assert (p["unite"], p["result_kind"], p.get("group")) == (unit, kind, group), (code, label)
        assert labels.index(label) == labels.index(before) + 1, (code, label)
    assert len(MISSING_PARAMS) == 12


def test_sputum_exams_in_catalogue_file():
    plain, atb = EXAMS["ECBC_CRACHATS"], EXAMS["ECBC_CRACHATS_ATB"]
    for e in (plain, atb):
        assert e["layout_family"] == "narrative" and e["section"] == "LABORATOIRE DE BACTERIOLOGIE"
        assert e["categorie"] == "Bacteriologie" and e["existing_code"] is False
        assert e["signature_label"] == "LE RESPONSABLE DE LABORATOIRE"
    assert plain["print_title"] == "EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS"
    assert atb["print_title"] == "EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS + ATB"
    assert [p["print_label"] for p in plain["parameters"]] == ["Aspect", "Cytologie", "Gram"]
    assert [(p["print_label"], p.get("group")) for p in atb["parameters"]] == [
        ("Aspect", None), ("Cytologie", None), ("Gram", None), ("Culture sur milieux usuels", None),
        ("Sensible à", "ANTIBIOGRAMME (ATB)"), ("Intermédiaire à", "ANTIBIOGRAMME (ATB)"),
        ("Résistant à", "ANTIBIOGRAMME (ATB)"), ("ANTIFONGIGRAMME (AFG)", None)]
    # aucune norme ni plage inventee
    assert all(not p["ranges"] and not p["norm_text"] for e in (plain, atb) for p in e["parameters"])
    orders = [e["sort_order"] for e in CATALOGUE["exams"]]
    assert len(orders) == len(set(orders))
    assert EXAMS["CRACHAT_BAAR"]["sort_order"] < plain["sort_order"] < atb["sort_order"] < EXAMS["MYCOPLASMES"]["sort_order"]


def test_prolactine_ranges_unchanged_and_phase_question_documented():
    ranges = EXAMS["PROLACTINE"]["parameters"][0]["ranges"]
    assert [(r["sexe"], r["min"], r["max"]) for r in ranges] == [("M", 2, 15), ("F", 2, 20)]
    doc = open(os.path.join(ROOT, "docs", "laboratory-templates.md"), encoding="utf-8").read()
    assert "A confirmer par la cheffe du laboratoire: phase de 2-20 et 2-15" in doc
    assert "## Examens (%d)" % len(CATALOGUE["exams"]) in doc


def test_seed_adds_missing_items_without_touching_results_or_prices(old_db):
    results_before = _run(old_db, "select * from lab_results order by 1", fetch=True)
    details_before = _run(old_db, "select * from lab_result_details order by 1", fetch=True)
    s = _seed(old_db)
    assert {"ECBC_CRACHATS", "ECBC_CRACHATS_ATB"} <= set(s["exams_added"])
    assert _run(old_db, "select * from lab_results order by 1", fetch=True) == results_before
    assert _run(old_db, "select * from lab_result_details order by 1", fetch=True) == details_before
    for code, label, unit, kind, group, before in MISSING_PARAMS:
        labels = _active_labels(old_db, code)
        assert labels.index(label) == labels.index(before) + 1, (code, label)
    assert _active_labels(old_db, "ECBC_CRACHATS") == ["Aspect", "Cytologie", "Gram"]
    assert len(_active_labels(old_db, "ECBC_CRACHATS_ATB")) == 8
    assert _run(old_db, "select prix from examens where code in ('ECBC_CRACHATS', 'ECBC_CRACHATS_ATB')",
                fetch=True) == [(0,), (0,)]
    again = _seed(old_db)
    assert again["exams_added"] == [] and again["params_added"] == 0
