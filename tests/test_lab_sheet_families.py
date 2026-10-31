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
          pregnancy=None, conclusion=None, note=None, bio=None):
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
    bio = bio or SimpleNamespace(age_days=age_days, sex=sex, ga_weeks=ga, age_label=age_label)
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
    vals = ["Trouble", "6", "00", "05", "2 - 4", "Présence de cellules épithéliales", "Bacilles gram négatif",
            "Sur milieux usuels", "> 10^5 CFU/ml", "Escherichia coli", "Ceftriaxone", "Amoxicilline", "Ampicilline"]
    snap = build("ECBU", vals, note="MULTI-RESISTANCE AUX ANTIBIOTIQUES")
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["LABORATOIRE DE BACTERIOLOGIE", "EXAMEN CYTOBACTERIOLOGIQUE DES URINES / ATB", "RESULTATS",
                 "ASPECT : Trouble", "PH : 6", "CYTOLOGIE", "Hématies : 00", "Leucocytes : 05",
                 "Cellules épithéliales : 2 - 4 /mm3", "Présence de cellules épithéliales", "EXAMEN GRAM : Bacilles gram négatif",
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
    return lab_sheet.render_lab_sheet_html(
        snap, {"name": "TESTEUR Jean", "prescriber": "Dr. Exemple"},
        {"structure": structure or _structure(), "logo_path": logo_path,
         "validation_date": date(2026, 10, 8), "dossier_label": "301/04 du 08/10/2026",
         "dossier_day": date(2026, 10, 8)}, show_pregnancy=False)


# ---------- parcours navigateur 2026-10-31 : une fiche = une page, grossesse, variante, nouveaux examens ----------

def _realistic_values(code):
    """Valeurs courtes d'un resultat normal, une par parametre, selon le type du catalogue."""
    out = []
    for p in CATALOGUE[code]["parameters"]:
        kind = p["result_kind"]
        if kind == "numeric":
            out.append("12.5")
        elif kind == "pos_neg":
            out.append("NEGATIF")
        elif kind == "choice":
            out.append((p.get("choices") or ["X"])[0])
        else:
            out.append("Normal")
    return out


def _full_header(tmp_path):
    """En-tete le plus charge : logo, slogan, adresse, BP, e-mail, telephones, site, agrement, NIU/RCCM, pied sur 2 lignes."""
    from PIL import Image
    logo = tmp_path / "logo.png"
    Image.new("RGB", (400, 300), (30, 120, 60)).save(logo)
    structure = _structure(slogan="Transforming lives through holistic care.", po_box="BP: 06", phone2="694000002",
                           website="exemple.org", niu="M000000000000X", rccm="RC/XXX/2020/B/000",
                           footer_text="A HAND TO HUMANITY MEDICAL CENTER\nVOUS SOUHAITE BONNE GUERISON")
    return {"structure": structure, "logo_path": logo.as_uri()}


LONG_CONCLUSION = ("Conclusion de test pour la verification de la mise en page. " * 8)[:400]


def test_nfs_charge_toutes_normes_conclusion_longue_et_nb_tient_sur_une_page(tmp_path):
    values = _realistic_values("NFS")
    assert len(values) >= 14
    snap = build("NFS", values, sex="F", conclusion=LONG_CONCLUSION, note="NB de test pour verifier la page. " * 3)
    pdf = render(snap, **_full_header(tmp_path))
    one_page_letter(pdf)
    t = text(pdf)
    assert "H: 4,0 - 5,5 F: 4,0 - 5,0" in t                 # toutes les normes imprimees
    assert "CONCLUSION : Conclusion de test" in t and "NB : NB de test" in t and "Le Biologiste" in t


def test_toutes_les_fiches_des_familles_tableau_et_trois_colonnes_tiennent_sur_une_page(tmp_path):
    header = _full_header(tmp_path)
    codes = [c for c, e in CATALOGUE.items() if e["layout_family"] in ("table", "three_columns")]
    assert {"NFS", "SPERMOGRAMME", "HEPB_5EN1", "PROLACTINE", "GLY_JEUN", "LIPIDES"} <= set(codes)
    too_long = []
    for code in codes:
        snap = build(code, _realistic_values(code), conclusion=LONG_CONCLUSION, note="NB de test. " * 4)
        if len(pages(render(snap, **header))) != 1:
            too_long.append(code)
    assert too_long == []


def test_signature_jamais_seule_sur_une_page_vide_texte_extreme(tmp_path):
    snap = build("NFS", _realistic_values("NFS"), conclusion="Texte extreme. " * 340, note="NB. " * 50)
    pdf = render(snap, **_full_header(tmp_path))
    ps = pages(pdf)
    last = " ".join((ps[-1].extract_text() or "").split())
    assert len(ps) >= 2
    assert last.replace("Le Biologiste", "").strip() != ""   # la signature suit du texte (conclusion / NB)


# ---------- grossesse : jamais « Inconnu » sans donnee ----------

def test_ligne_grossesse_seulement_avec_une_donnee():
    t_unknown = text(render(build("GLY_JEUN", ["0.95"], sex="F", pregnancy=("inconnu", None)), show_pregnancy=True))
    assert "Grossesse" not in t_unknown and "Inconnu" not in t_unknown
    t_none = text(render(build("GLY_JEUN", ["0.95"], sex="M"), show_pregnancy=True))
    assert "Grossesse" not in t_none
    t_non = text(render(build("GLY_JEUN", ["0.95"], sex="F", pregnancy=("non_enceinte", None)), show_pregnancy=True))
    assert t_non.count("Grossesse : Non enceinte") == 1
    t_weeks = text(render(build("GLY_JEUN", ["0.95"], sex="F", pregnancy=("inconnu", 12)), show_pregnancy=True))
    assert t_weeks.count("Grossesse : 12 SA") == 1 and "Inconnu" not in t_weeks
    t_yes = text(render(build("GLY_JEUN", ["0.95"], sex="F", pregnancy=("enceinte", 20)), show_pregnancy=True))
    assert t_yes.count("Grossesse : Enceinte - 20 SA") == 1


def test_ancienne_copie_avec_statut_inconnu_n_imprime_plus_la_ligne():
    snap = build("GLY_JEUN", ["0.95"], sex="F")
    snap["pregnancy"] = {"status_at_result": "inconnu", "gestational_age_weeks": None}   # copie deja stockee
    assert "Grossesse" not in text(render(snap, show_pregnancy=True))


def test_constructeur_de_copie_traite_inconnu_sans_sa_comme_aucune_donnee():
    assert build("GLY_JEUN", ["0.95"], pregnancy=("inconnu", None))["pregnancy"] is None
    assert build("GLY_JEUN", ["0.95"], pregnancy=("inconnu", 14))["pregnancy"] == {
        "status_at_result": None, "gestational_age_weeks": 14}
    assert build("GLY_JEUN", ["0.95"], pregnancy=("enceinte", None))["pregnancy"] == {
        "status_at_result": "enceinte", "gestational_age_weeks": None}
    assert build("GLY_JEUN", ["0.95"])["pregnancy"] is None


# ---------- variante du titre et du bloc patient ----------

def _first_x(pdf, needle):
    """Abscisse (points) du premier fragment de texte contenant `needle`."""
    found = []

    def visitor(txt, cm, tm, font_dict, font_size):
        if needle in txt and not found:
            found.append(tm[4] * cm[0] + cm[4])

    pages(pdf)[0].extract_text(visitor_text=visitor)
    return found[0] if found else None


def test_variante_centree_par_defaut_et_variante_laboratoire_a_gauche():
    snap = build("GLY_JEUN", ["0.95"])
    centered = render(snap, structure=_structure(lab_sheet_title_variant="centered_results"))
    default = render(snap)                                    # colonne absente : variante par defaut
    left = render(snap, structure=_structure(lab_sheet_title_variant="left_laboratory"))
    for pdf in (centered, default):
        t = text(pdf)
        assert "RESULTATS D'ANALYSES DE BIOLOGIE CLINIQUE" in t and "LABORATOIRE D'ANALYSES" not in t
        assert _first_x(pdf, "Nom du Patient") > 150           # bloc patient centre
    tl = text(left)
    assert "LABORATOIRE D'ANALYSES DE BIOLOGIE CLINIQUE" in tl and "RESULTATS D'ANALYSES DE BIOLOGIE" not in tl
    margin = 2.2 / 2.54 * 72
    assert abs(_first_x(left, "LABORATOIRE D'ANALYSES") - margin) < 6
    assert abs(_first_x(left, "Nom du Patient") - margin) < 6
    assert abs(_first_x(left, "DOSSIER") - margin) < 6
    one_page_letter(left)


def test_variante_gauche_dossier_en_italique_bleu_dans_le_html():
    snap = build("GLY_JEUN", ["0.95"])
    ctx = {"structure": _structure(lab_sheet_title_variant="left_laboratory"), "logo_path": None,
           "validation_date": date(2026, 10, 8), "dossier_label": "301/04 du 08/10/2026"}
    html = lab_sheet.render_lab_sheet_html(snap, {"name": "TESTEUR Jean", "prescriber": None}, ctx, show_pregnancy=False)
    assert 'class="variant-left_laboratory"' in html and 'class="dossier-line"' in html
    css = html.split("<style>", 1)[1].split("</style>", 1)[0]
    rule = css.split(".patient-block .dossier-line", 1)[1].split("}", 1)[0]
    assert "italic" in rule and "color" in rule
    # une valeur inconnue retombe sur la variante par defaut
    ctx["structure"] = _structure(lab_sheet_title_variant="n_importe_quoi")
    html = lab_sheet.render_lab_sheet_html(snap, {"name": "T", "prescriber": None}, ctx, show_pregnancy=False)
    body = html.split("</style>", 1)[1]
    assert 'class="variant-centered_results"' in html and "RESULTATS D&#39;ANALYSES" in body and "LABORATOIRE D&#39;" not in body


# ---------- KOAP, autres comptes rendus narratifs, patient interne ----------

def test_tous_les_comptes_rendus_narratifs_une_page_libelles_dans_l_ordre(tmp_path):
    header = _full_header(tmp_path)
    codes = [c for c, e in CATALOGUE.items() if e["layout_family"] == "narrative"]
    assert {"COPRO", "FCU", "PCV", "HEMOCULTURE", "ECBC_CRACHATS", "ECBC_CRACHATS_ATB"} <= set(codes)
    for code in codes:
        e = CATALOGUE[code]
        snap = build(code, ["Valeur %d de test" % i for i, _ in enumerate(e["parameters"])],
                     conclusion="Conclusion de test.", note="NB de test.")
        pdf = render(snap, **header)
        assert len(pages(pdf)) == 1, code
        t = text(pdf)
        assert e["print_title"].replace("EXAMEN : ", "").replace("EXAMEN: ", "")[:12] in t or e["print_title"] in t, code
        assert "Conclusion de test." in t, code
        values = [t.find("Valeur %d de test" % i) for i in range(len(e["parameters"]))]
        assert all(v >= 0 for v in values), code
        assert values == sorted(values), code               # valeurs dans l'ordre des parametres


def test_koap_conclusion_et_libelle_de_signature():
    snap = build("COPRO", ["Liquide", "Absence de kystes."], conclusion="Recherche négative des KOAPs.")
    t = text(render(snap))
    in_order(t, ["COPROLOGIE / KOAP", "Consistance : Liquide", "Absence de kystes.",
                 "CONCLUSION : Recherche négative des KOAPs.", "LE RESPONSABLE DE LABORATOIRE"])


def test_ecbc_crachats_sans_atb_une_page_titre_et_ordre():
    snap = build("ECBC_CRACHATS", ["Muco-purulent, jaunâtre", "Présence de nombreux leucocytes (4-8 / champ).",
                                   "Cocci gram positif en chaînettes"], conclusion="Flore mixte.", note="NB libre.")
    pdf = render(snap)
    one_page_letter(pdf)
    t = text(pdf)
    in_order(t, ["LABORATOIRE DE BACTERIOLOGIE", "EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS", "RESULTATS",
                 "Aspect : Muco-purulent", "Cytologie :", "nombreux leucocytes", "Gram :", "Cocci gram positif",
                 "CONCLUSION : Flore mixte.", "NB : NB libre.", "LE RESPONSABLE DE LABORATOIRE"])
    assert "ANTIBIOGRAMME" not in t and "Culture" not in t


def test_ecbc_crachats_avec_atb_une_page_titre_et_ordre_des_lignes():
    vals = ["Muqueux", "Rares levures (0-1 / champ).", "Cocci gram positif", "Sur milieux usuels",
            "Amoxicilline", "Ofloxacine", "Cotrimoxazole", "//"]
    snap = build("ECBC_CRACHATS_ATB", vals, note="Généralement sensible à la pénicilline.")
    pdf = render(snap)
    one_page_letter(pdf)
    in_order(text(pdf), ["EXAMEN CYTOBACTERIOLOGIQUE DES CRACHATS + ATB", "Aspect : Muqueux", "Cytologie :",
                         "Gram :", "Culture sur milieux usuels : Sur milieux usuels", "ANTIBIOGRAMME (ATB)",
                         "Sensible à : Amoxicilline", "Intermédiaire à : Ofloxacine", "Résistant à : Cotrimoxazole",
                         "ANTIFONGIGRAMME (AFG) : //", "NB : Généralement sensible"])


def _internal_bio(birth, gender, test_date, ga=None):
    from repositories.lab_repo import patient_bio
    result = SimpleNamespace(patient=SimpleNamespace(birth_date=birth, gender=gender), external_patient_info=None,
                             test_date=test_date, gestational_age_weeks=ga)
    return patient_bio(result)


def test_patient_interne_age_exact_depuis_la_naissance_et_grossesse_selon_le_lecteur():
    from datetime import datetime
    bio = _internal_bio(date(1991, 3, 14), "Féminin", datetime(2026, 10, 8, 9, 0), ga=18)
    assert bio.sex == "F" and bio.age_label and bio.age_days > 12000
    snap = build("GLY_JEUN", ["0.95"], bio=bio, pregnancy=("enceinte", 18))
    assert snap["patient"]["age_label"] == bio.age_label and snap["patient"]["sex"] == "F"
    viewer = text(render(snap, show_pregnancy=True))
    other = text(render(snap, show_pregnancy=False))
    assert "Age : 35 ans" in viewer and "Age : 35 ans" in other and "Sexe : F" in viewer
    assert viewer.count("Grossesse : Enceinte - 18 SA") == 1
    assert "Grossesse" not in other
    # patiente interne sans donnee de grossesse : pas de ligne meme pour un lecteur autorise
    none = text(render(build("GLY_JEUN", ["0.95"], bio=bio), show_pregnancy=True))
    assert "Grossesse" not in none and "Age : 35 ans" in none
    # nouveau-ne interne : age en semaines et jours, jamais d'annees
    baby = _internal_bio(date(2026, 9, 21), "Masculin", datetime(2026, 10, 8, 9, 0))
    t = text(render(build("GLY_JEUN", ["0.95"], bio=baby), show_pregnancy=True))
    assert "Age : 2 semaines 3 jours" in t and "Grossesse" not in t
