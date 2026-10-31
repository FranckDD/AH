# tests/test_lab_sheet_families.py
"""Gabarits de famille des fiches de resultats (D2). Copies figees construites comme le serveur
(build_print_snapshot) a partir du catalogue seme (scripts/data/lab_catalogue.json). Patients
inventes uniquement. Texte lu via pypdf."""
import copy
import io
import json
import os
import re
import sys
from datetime import date
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from api_backend.backend_app.utils import lab_sheet
from api_backend.backend_app.utils.lab_sheet import (
    FAMILY_TEMPLATES, display_norm, display_value, render_lab_sheet)
from utils.lab_snapshot import build_print_snapshot

with open(os.path.join(ROOT, "scripts", "data", "lab_catalogue.json"), encoding="utf-8") as _fh:
    CATALOGUE = {e["code"]: e for e in json.load(_fh)["exams"]}

TEMPLATES_DIR = os.path.join(ROOT, "api_backend", "backend_app", "utils", "templates")


def _structure(**kw):
    base = dict(name="Centre Test Alpha", slogan=None, address="Rue 1", city="Douala", po_box=None,
                phone="600000001", phone2=None, email="c@example.org", website=None,
                agrement_number="N 123/AGR", niu=None, rccm=None, legal_info=None,
                footer_text="MERCI DE VOTRE CONFIANCE", signature_label_default=None)
    base.update(kw)
    return SimpleNamespace(**base)


def build(code, values, sex="M", age_days=12000, age_label="33 Ans", flagged=(), keep_group=True,
          pregnancy=None, conclusion=None, note=None):
    """Copie figee (version 2) d'un examen du catalogue seme : sous-titres, textes de norme, textes de plage
    et notes fixes viennent de la base (ici du JSON). `values` : liste de value_text dans l'ordre des
    parametres. `keep_group=False` retire les sous-titres de la copie."""
    e = CATALOGUE[code]
    exam = SimpleNamespace(code=code, print_title=e["print_title"], nom=e["nom"], section=e["section"],
                           method=e["method"], layout_family=e["layout_family"],
                           signature_label=e["signature_label"], sort_order=e["sort_order"],
                           fixed_notes=e.get("fixed_notes") or None)
    details = []
    for i, (p, v) in enumerate(zip(e["parameters"], values), start=1):
        ranges = [SimpleNamespace(id=j, sexe=r["sexe"], age_min_days=r["age_min_days"],
                                  age_max_days=r["age_max_days"], age_min=None, age_max=None,
                                  ga_min_weeks=None, ga_max_weeks=None, valeur_min=r["min"], valeur_max=r["max"],
                                  display_text=r.get("display_text"))
                  for j, r in enumerate(p["ranges"], start=1)]
        param = SimpleNamespace(id=i, print_label=p["print_label"], nom_parametre=p["name"], unite=p["unite"],
                                result_kind=p["result_kind"], ordre=i, reference_ranges=ranges,
                                group_label=p.get("group") or None, norm_text=p.get("norm_text") or None)
        num = None
        try:
            num = float(str(v).replace(",", "."))
        except ValueError:
            pass
        details.append(SimpleNamespace(parametre=param, valeur_text=v, valeur_num=num,
                                       flagged=(i - 1) in flagged, interpretation=None))
    status, ga = (pregnancy or (None, None))
    result = SimpleNamespace(dossier_year=2026, dossier_counter=301, dossier_rank=4,
                             pregnancy_status_at_result=status, gestational_age_weeks=ga,
                             conclusion=conclusion, note=note)
    bio = SimpleNamespace(age_days=age_days, sex=sex, ga_weeks=ga, age_label=age_label)
    snap = build_print_snapshot(result, exam, details, bio)
    if not keep_group:
        for row in snap["parameters"]:
            row["group"] = None
    return snap


def render(snap, show_pregnancy=False, **ctx):
    context = {"structure": _structure(), "logo_path": None, "validation_date": date(2026, 10, 8),
               "dossier_label": "301/04 du 08/10/2026", "dossier_day": date(2026, 10, 8)}
    context.update(ctx)
    return render_lab_sheet(snap, {"name": "TESTEUR Jean", "prescriber": "Dr. Exemple"}, context,
                            show_pregnancy=show_pregnancy)


def pages(pdf):
    return PdfReader(io.BytesIO(pdf)).pages


def text(pdf):
    return " ".join(" ".join((p.extract_text() or "").split()) for p in pages(pdf))


def one_page_letter(pdf):
    ps = pages(pdf)
    assert len(ps) == 1
    w, h = float(ps[0].mediabox.width), float(ps[0].mediabox.height)
    assert abs(w - 612) < 1.5 and abs(h - 792) < 1.5


def _squash(s):
    # pypdf insere ou retire des espaces selon le crenage (« V ALEURS ») : on compare sans blancs
    return re.sub(r"\s+", "", s)


def in_order(haystack, needles):
    hay = _squash(haystack)
    pos = 0
    for n in needles:
        i = hay.find(_squash(n), pos)
        assert i >= 0, f"{n!r} absent ou hors ordre"
        pos = i + len(_squash(n))


NFS_VALUES = ["4.09", "5.5", "10.6", "1.6", "32.6", "26.0", "79.8", "32.6", "221",
              "48", "2640", "02", "110", "00", "00", "28", "1540", "22", "1210"]


# ---------- familles ----------

def test_familles_enregistrees():
    for fam in ("table", "three_columns", "label_value", "narrative", "boxed"):
        assert fam in FAMILY_TEMPLATES
        assert os.path.exists(os.path.join(TEMPLATES_DIR, FAMILY_TEMPLATES[fam]))


def test_nfs_blocs_libelles_ordre_normes_sexe():
    snap = build("NFS", NFS_VALUES, sex="F", age_days=12000, flagged=(2, 4))
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["HEMATOLOGIE", "HEMOGRAMME", "EXAMENS", "RESULTATS", "VALEURS USUELLES",
                 "NUMERATION GLOBULAIRE", "FORMULE SANGUINE (Coloration MGG)"])
    labels = [p["label"] for p in snap["parameters"] if not p["label"].startswith("V.A.M.")]
    in_order(t, labels)
    assert "F: 12 - 15" in t and "F: 36 - 52" in t
    assert "H: 12 - 17" in t and "H: 4,0 - 5,5 F: 4,0 - 5,0" in t   # la fiche imprime TOUTES les normes
    assert "10,6" in t and "4,09" in t                     # virgule decimale, valeur inchangee
    assert "4.09" not in t


def test_nfs_valeurs_signalees_en_gras_rouge():
    snap = build("NFS", NFS_VALUES, sex="M", flagged=(2,))
    html = lab_sheet_html(snap)
    assert re.search(r'class="value flagged">10,6', html)
    assert not re.search(r'class="value flagged">4,09', html)


def test_nfs_normes_pediatriques():
    # Les normes pediatriques s'impriment pour tous les patients (texte du catalogue), quel que soit l'age.
    for days, label in ((10, "10 jours"), (1000, "2 Ans"), (12000, "33 Ans")):
        t = text(render(build("NFS", NFS_VALUES, sex="M", age_days=days, age_label=label)))
        assert "Nouveau-né: 16 - 21,5" in t                # Hb nouveau-ne
        assert "ADULTE: 5,0 - 10,0 / ENFT < 5ans: 5,0 - 15,0" in t   # globules blancs


def test_biochimie_trois_colonnes_glycemie_et_lipides():
    pdf = render(build("GLY_JEUN", ["0.95"]))
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["BIOCHIMIE SANGUINE", "GLYCEMIE A JEUN", "EXAMENS", "RESULTATS", "VALEURS NORMALES",
                 "GLYCEMIE A JEUN:", "0,95 g/l", "0,60 - 1,2 g/L"])
    snap = build("LIPIDES", ["2.10", "45", "130", "150"], flagged=(0,))
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["PROFILE LIPIDIQUE", "CHOLESTEROL:", "2,10 mg/dl", "< 200 mg/dl", "HDL:", "50 - 82 mg/dl",
                 "LDL:", "< 100 mg/dl", "TRIGLICERIDES:", "45 - 175 mg/dl"])
    assert "Liberation Mono" in lab_sheet_html(snap) or "Courier" in lab_sheet_html(snap)


def test_aslo_ligne_valeur_vn():
    pdf = render(build("ASLO", ["400"], flagged=(0,), conclusion="A.S.L.O POSITIVE"))
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["IMMUNO-SEROLOGIE", "A.S.L.O (Antistreptolysine O)", "RESULTATS",
                 "Valeur du malade : 400 UI/ml (V.N. <= 200 UI/mL)", "CONCLUSION : A.S.L.O POSITIVE",
                 "LE RESPONSABLE DU LABORATOIRE"])


def test_typhoide_positif_negatif_majuscules():
    snap = build("TYPHOIDE", ["Négatif", "positif"], flagged=(1,),
                 conclusion="Présence des anticorps IgM dans cet échantillon.",
                 note="Une réaction positive peut correspondre à une infection récente ou ancienne.")
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["DIAGNOSTIC DE TYPHOIDE : ANTICORPS IgG/IgM",
                 "METHODE UTILISEE : Technique rapide par immunochromatographie.",
                 "Anticorps Typhoide IgG : NEGATIF", "Anticorps Typhoide IgM : POSITIF",
                 "CONCLUSION : Présence", "NB : Une réaction positive"])


def test_koap_narratif():
    snap = build("COPRO", ["Molle", "Présence de kystes d'Entamoeba coli.\nAbsence d'oeufs."],
                 conclusion="Recherche positive des KOAPs.")
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["COPROLOGIE / KOAP (Kystes Oeufs Amibes Parasites)", "RESULTATS", "EXAMEN MACROSCOPIQUE",
                 "Consistance : Molle", "EXAMEN MICROSCOPIQUE DIRECT", "Présence de kystes", "Absence d'oeufs.",
                 "CONCLUSION : Recherche positive des KOAPs."])


def test_ecbu_narratif_rubriques():
    vals = ["Trouble", "6", "00", "05", "Présence de cellules épithéliales", "Bacilles gram négatif",
            "Sur milieux usuels", "> 10^5 CFU/ml", "Escherichia coli", "Ceftriaxone", "Amoxicilline", "Ampicilline"]
    snap = build("ECBU", vals, note="MULTI-RESISTANCE AUX ANTIBIOTIQUES")
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["LABORATOIRE DE BACTERIOLOGIE", "EXAMEN CYTOBACTERIOLOGIQUE DES URINES / ATB", "RESULTATS",
                 "ASPECT : Trouble", "PH : 6", "CYTOLOGIE", "Hématies : 00", "Leucocytes : 05",
                 "Présence de cellules épithéliales", "EXAMEN GRAM : Bacilles gram négatif",
                 "CULTURE : Sur milieux usuels", "BACTERIURIE QUANTITATIVE", "GERME ISOLE : Escherichia coli",
                 "ANTIBIOGRAMME (ATB)", "Sensible à : Ceftriaxone", "Intermédiaire à : Amoxicilline",
                 "Résistant à : Ampicilline", "NB : MULTI-RESISTANCE"])


def test_spermogramme_une_page_matrice():
    e = CATALOGUE["SPERMOGRAMME"]
    vals = []
    for p in e["parameters"]:
        vals.append({"numeric": "12", "text": "normal"}[p["result_kind"]])
    snap = build("SPERMOGRAMME", vals, conclusion="SPERMOGRAMME NORMAL")
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["COMPTE RENDU D'EXAMEN D'HISTO-CYTO-PATHOLOGIE DU SPERMOGRAMME", "RENSEIGNEMENTS GENERAUX",
                 "Motif : normal", "II) ETUDE PHYSICO - CHIMIQUE", "-Viscosité", "III) ETUDE DYNAMIQUE",
                 "0H", "1H", "2H", "6H", "12H", "24H", "Immobiles", "Rapide progressive", "Lente progressive",
                 "Mobilité non progressive", "Total mobiles", "IV) CYTOLOGIE - Morphologie", "Formes normales",
                 "V) CONCENTRATION : 12 million/ml (VN > 20 M/ml)", "VI) INDICE DE FERTILITE SPERMATIQUE : 12 (VN : 1 - 7)",
                 "CONCLUSION : SPERMOGRAMME NORMAL", "LE RESPONSABLE DE LABORATOIRE"])


def test_toxicologie_tableau_positif_negatif():
    vals = ["Négatif"] * 13
    vals[0] = "Positif"
    snap = build("TOXICO_UR", vals, flagged=(0,))
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["RECHERCHE DES DROGUES (TOXICOLOGIE URINAIRE)", "CANNABIS (THC)", "POSITIF", "TRAMADOL (TRA)",
                 "NEGATIF"] + [p["print_label"] for p in CATALOGUE["TOXICO_UR"]["parameters"][2:]])


def test_chlamydiae_formulaire_en_cases():
    snap = build("CHLAMYDIA", ["", "> 8", "< 8", "< 8", "Sérologie faiblement positive"], sex="F",
                 age_label="36 ans")
    html = lab_sheet_html(snap)
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["RESULTAT D'ANALYSE DE BIOLOGIE CLINIQUE", "SERODIAGNOSTIC DES CHLAMYDIAE", "N° :",
                 "301/04 du 08/10/2026", "N° de l'examen antérieur", "NOM :", "TESTEUR Jean", "Médecin Demandeur",
                 "Dr. Exemple", "AGE :", "36 ans", "date de prélèvement", "08 / 10 / 2026", "SEXE :", "RESULTATS",
                 "IMMUNOPEROXIDASE", "Titre en IgG :", "> 8", "Titre en IgM :", "Titre en IgA :", "Validation :",
                 "Sérologie faiblement positive", "INTERPRETATION", "N.B"])
    # une case par champ : 4 identite + 3 a droite + 4 parametres de resultat
    assert html.count('class="bvalue"') == 11
    assert ('<p class="fixed-note normal chosen">Titre compris entre 8 et 63 ou immuno peroxydase+ : '
            'Sérologie faiblement positif.</p>') in html
    assert html.count('fixed-note normal chosen') == 1       # une seule ligne d'interpretation en gras
    assert "Nom du Patient" not in t


def test_bandelette_urinaire_onze_parametres():
    vals = ["Clair", "Négatif", "Normal", "Négatif", "Négatif", "Positif (+ 0,3g/L)", "Négatif", "Négatif",
            "Négatif", "6.0", "1.015", "Négatif"]
    snap = build("BANDE_UR", vals)
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["CHIMIE URINAIRE (URS 11)", "RESULTATS", "Aspect : Clair", "Hématies : NEGATIF",
                 "Urobilinogène : Normal", "Bilirubine : NEGATIF", "Sucres (glucose) : NEGATIF",
                 "Protéine : POSITIF (+ 0,3g/L)", "Nitrites : NEGATIF", "Acide ascorbique : NEGATIF",
                 "Leucocytes : NEGATIF", "PH : 6,0", "Densité : 1,015", "Ketones : NEGATIF"])


def test_groupage_sanguin():
    pdf = render(build("GR_ABO_RH", ["A", "Positif"]))
    one_page_letter(pdf)
    in_order(text(pdf), ["HEMATOLOGIE", "GROUPAGE SANGUIN", "GS : A", "Rhésus : POSITIF"])


def test_hemostase_groupes_et_normes_texte():
    snap = build("TP_TCA", ["12", "13.5", "85", "1.1", "32", "34.2"])
    pdf = render(snap)
    one_page_letter(pdf)
    in_order(text(pdf), ["HEMOSTASE-COAGULATION", "Méthode utilisée", "Appareillage", "Réactifs",
                         "TAUX DE PROTHROMBINE / TEMPS DE QUICK", "Temps du témoin : 12 s", "Temps du Sujet : 13,5 s",
                         "Taux de Prothrombine : 85 %", "INR : 1,1 (VN 0,8 - 1,2)",
                         "TEMPS DE CEPHALINE ACTIVEE", "Temps du témoin : 32 s", "Temps du sujet : 34,2 s"])


def test_vs_trois_colonnes():
    pdf = render(build("VS", ["10", "25"], flagged=(1,)))
    one_page_letter(pdf)
    in_order(text(pdf), ["VITESSE DE SEDIMENTATION (VS)", "1ER Heure:", "10 mm", "< 15 mm", "2E Heure:", "25 mm",
                         "< 20 mm"])


# ---------- regles communes ----------

def test_famille_inconnue_repli_label_value():
    snap = build("ASLO", ["150"])
    snap["exam"]["family"] = "inconnue"
    in_order(text(render(snap)), ["Valeur du malade : 150 UI/ml"])


def test_norme_texte_prioritaire():
    snap = build("ASLO", ["150"])
    snap["parameters"][0]["norm"]["text"] = "≤ 200 UI/mL"
    snap["parameters"][0]["norm_text"] = None           # copie sans texte de norme imprime ni liste de normes
    snap["parameters"][0]["norms"] = []
    in_order(text(render(snap)), ["Valeur du malade : 150 UI/ml (V.N. ≤ 200 UI/mL)"])
    p = {"unit": "g/dl", "norm_text": "H: 12 - 17 F: 12 - 15", "norm": snap["parameters"][0]["norm"]}
    assert display_norm(p) == "H: 12 - 17 F: 12 - 15"


def test_display_helpers():
    assert display_value("0.95") == "0,95"
    assert display_value("1.2.3") == "1.2.3"
    assert display_value("négative") == "NEGATIVE"
    assert display_value("Positif (Trace +/-)") == "POSITIF (Trace +/-)"
    assert display_norm({"unit": "", "norm": {"text": "0 - 500", "min": 0, "max": 500, "sex": "X"}}) == "< 500"
    assert display_norm({"unit": "", "norm": {"text": "20", "min": 20, "max": None, "sex": "X"}}) == "20"
    assert display_norm({"unit": "", "norm": None}) == ""


def test_valeurs_longues_et_caracteres_speciaux():
    longue = "Présence de <germes> & levures " * 15
    snap = build("ECBU", ["Trouble & <rouge>", "6"] + ["x"] * 9 + [longue.strip()])
    html = lab_sheet_html(snap)
    assert "Trouble &amp; &lt;rouge&gt;" in html and "<rouge>" not in html
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["ASPECT : Trouble & <rouge>", "Présence de <germes> & levures"])
    # texte extreme : pas d'exception, une 2e page admise, la signature reste entiere sur la derniere
    extreme = build("ECBU", ["x"] * 11 + ["mot " * 1500])
    ps = pages(render(extreme))
    assert len(ps) >= 2 and "LE RESPONSABLE DE LABORATOIRE" in ps[-1].extract_text()


def test_grossesse_masquee_ou_imprimee_une_fois():
    snap = build("GLY_JEUN", ["0.95"], sex="F", pregnancy=("enceinte", 22))
    t = text(render(snap, show_pregnancy=False))
    assert "Grossesse" not in t and "SA" not in t.replace("SANGUINE", "")
    t = text(render(snap, show_pregnancy=True))
    assert t.count("Grossesse : Enceinte - 22 SA") == 1
    t = text(render(build("CHLAMYDIA", ["", "<8", "<8", "<8", "Sérologie négative"], sex="F",
                          pregnancy=("enceinte", 10)), show_pregnancy=True))
    assert t.count("Grossesse") == 1


def test_copie_non_modifiee_et_catalogue_non_lu(monkeypatch):
    snap = build("NFS", NFS_VALUES)
    before = copy.deepcopy(snap)
    import builtins
    real_open = builtins.open

    def guarded(path, *a, **kw):
        assert "lab_catalogue" not in str(path)
        return real_open(path, *a, **kw)

    monkeypatch.setattr(builtins, "open", guarded)
    render(snap)
    assert snap == before


# ---------- en-tete ----------

def test_en_tete_fiche_logo_a_gauche_donnees_dynamiques(tmp_path):
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n")
    html = lab_sheet_html(build("ASLO", ["150"]), logo_path=logo.as_uri(),
                          structure=_structure(name="Centre <b>&</b>", agrement_number="AGR & 9"))
    head = html[html.index('<table class="ls-header">'):]
    assert head.index('class="ls-logo"') < head.index('class="ls-info"')
    assert "Centre &lt;b&gt;&amp;&lt;/b&gt;" in head and "AGR &amp; 9" in head
    assert "<b>&</b>" not in html


def _header(structure):
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    return env.get_template("_pdf_header.html").render(structure=structure, logo_path="file:///l.png")


def test_en_tete_partage_echappe_et_inchange_sinon():
    plain = _structure(slogan="Soigner", po_box="12", phone2="600000002", website="www.example.org",
                       niu="N1", rccm="R2", legal_info="SA", footer_text="Ligne 1\nLigne 2")
    out = _header(plain)
    for frag in ("<h1>Centre Test Alpha</h1>", '<p class="slogan">Soigner</p>', "Rue 1", " - Douala",
                 " | BP: 12", "Tel: 600000001", " / 600000002", " &middot; c@example.org",
                 "<p>www.example.org</p>", '<p class="agrement">N 123/AGR</p>', "NIU: N1 | RCCM: R2 | SA",
                 "<p>Ligne 1</p><p>Ligne 2</p>", 'src="file:///l.png"'):
        assert frag in out
    evil = _header(_structure(name="<script>x</script>", footer_text="a & <i>b</i>"))
    assert "<script>" not in evil and "&lt;script&gt;" in evil and "a &amp; &lt;i&gt;b&lt;/i&gt;" in evil


def lab_sheet_html(snap, structure=None, logo_path=None):
    """HTML intermediaire de la fiche (memes donnees que render_lab_sheet) pour les assertions de balisage."""
    captured = {}

    def fake(template, ctx):
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        captured["html"] = env.get_template(template).render(**ctx)
        return b""

    orig = lab_sheet.render_pdf_from_template
    lab_sheet.render_pdf_from_template = fake
    try:
        render_lab_sheet(snap, {"name": "TESTEUR Jean", "prescriber": "Dr. Exemple"},
                         {"structure": structure or _structure(), "logo_path": logo_path,
                          "validation_date": date(2026, 10, 8), "dossier_label": "301/04 du 08/10/2026",
                          "dossier_day": date(2026, 10, 8)}, show_pregnancy=False)
    finally:
        lab_sheet.render_pdf_from_template = orig
    return captured["html"]
