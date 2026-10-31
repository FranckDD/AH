# tests/test_lab_sheet_norms_groups.py
"""Fiches : toutes les normes du laboratoire, sous-titres, textes de norme verbatim et notes fixes
(copie figee version 2, tache C5). Copies construites comme le serveur a partir du catalogue seme
(scripts/data/lab_catalogue.json). Patients inventes uniquement."""
import copy
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.utils.lab_sheet import display_norm, paren_norm
from tests.test_lab_sheet_families import (
    CATALOGUE, NFS_VALUES, TEMPLATES_DIR, build, in_order, lab_sheet_html, one_page_letter, render, text)


def _strip_texts(snap):
    """Copie sans texte de norme imprime : le rendu retombe sur la liste `norms`."""
    snap = copy.deepcopy(snap)
    for p in snap["parameters"]:
        p["norm_text"] = None
    return snap


# ---------- toutes les normes ----------

def test_les_deux_sexes_sont_imprimes_quel_que_soit_le_patient():
    for sex in ("M", "F"):
        t = text(render(build("NFS", NFS_VALUES, sex=sex)))
        assert "H: 4,0 - 5,5 F: 4,0 - 5,0" in t           # zeros de precision gardes
        assert "H: 12 - 17 F: 12 - 15" in t and "H: 40 - 54 F: 36 - 52" in t
        assert "H: 76 - 96 F: 76 - 100" in t


def test_normes_composees_depuis_la_liste_sans_texte_imprime():
    snap = _strip_texts(build("NFS", NFS_VALUES, sex="F"))
    t = text(render(snap))
    assert "H: 4,0 - 5,5 F: 4,0 - 5,0" in t               # display_text de chaque plage
    assert "H: 12 - 17 F: 12 - 15 / Nouveau-né: 16 - 21,5" in t
    assert "Adulte: 5,0 - 10,0 / Enfant: 5,0 - 15,0" in t
    assert "Adulte: 0,5 - 2,5 / Nouveau-né: 2 - 6" in t
    assert "H: 40 - 54 F: 36 - 52" in t
    one_page_letter(render(snap))


def test_texte_de_norme_verbatim():
    assert display_norm({"unit": "", "norm_text": "VN > 20 M/ml", "norms": [
        {"sex": "X", "min": 0, "max": 5, "text": "0 - 5"}]}) == "VN > 20 M/ml"
    assert display_norm({"unit": "", "norm_text": ">= 70%"}) == ">= 70%"
    assert display_norm({"unit": "", "norm_text": "<= 200"}) == "<= 200"
    assert display_norm({"unit": "g/l", "norm_text": "0,60 - 1,2 g/L"}, unit_in_norm=True) == "0,60 - 1,2 g/L"


def test_textes_de_norme_du_catalogue_imprimes_tels_quels():
    t = text(render(build("SPERMOGRAMME", [{"numeric": "30", "text": "normal"}[p["result_kind"]]
                                           for p in CATALOGUE["SPERMOGRAMME"]["parameters"]])))
    assert "(VN > 20 M/ml)" in t and "(VN : 1 - 7)" in t
    in_order(text(render(build("ASLO", ["150"]))), ["Valeur du malade : 150 UI/ml", "(V.N. <= 200 UI/mL)"])
    t = text(render(build("TP_TCA", ["12", "13.5", "85", "1.1", "32", "34.2"])))
    in_order(t, ["(VN >/= 70%)", "(VN 0,8 - 1,2)", "(VN 27,1 - 36,6)"])
    assert "V.N. VN" not in t and "V .N. VN" not in t        # pas de double prefixe


def test_une_norme_par_age_et_unite_en_trois_colonnes():
    p = {"unit": "g/dl", "norms": [
        {"sex": "X", "age_min_days": None, "age_max_days": 28, "min": 16, "max": 21.5, "text": "16 - 21,5"},
        {"sex": "F", "age_min_days": None, "age_max_days": None, "min": 12, "max": 15, "text": "12 - 15"},
        {"sex": "M", "age_min_days": None, "age_max_days": None, "min": 12, "max": 17, "text": "12 - 17"}]}
    assert display_norm(p) == "H: 12 - 17 F: 12 - 15 / Nouveau-né: 16 - 21,5"
    assert display_norm(p, unit_in_norm=True) == "H: 12 - 17 g/dl F: 12 - 15 g/dl / Nouveau-né: 16 - 21,5 g/dl"


def test_seuil_et_borne_basse_depuis_la_liste():
    assert display_norm({"unit": "", "norms": [{"sex": "X", "min": 0, "max": 500, "text": "0 - 500"}]}) == "< 500"
    assert display_norm({"unit": "", "norms": [{"sex": "X", "min": 0, "max": 500, "text": "< 500"}]}) == "< 500"
    assert display_norm({"unit": "", "norms": [{"sex": "X", "min": 20, "max": None}]}) == "> 20"
    assert display_norm({"unit": "", "norms": []}) == ""


def test_norme_hors_age_du_patient_imprimee_aussi():
    """Un nourrisson : la fiche garde la norme de l'adulte (le signalement vient de la norme choisie)."""
    snap = build("NFS", NFS_VALUES, sex="M", age_days=12000, flagged=(2,))
    hb = snap["parameters"][2]["norms"]
    assert [(n["sex"], n["selected"]) for n in hb if n["age_max_days"] == 28] == [("X", False)]
    assert [n["sex"] for n in hb if n["selected"]] == ["M"]
    assert "Nouveau-né: 16 - 21,5" in text(render(snap))


def test_paren_norm():
    assert paren_norm("VN > 20 M/ml") == "(VN > 20 M/ml)"
    assert paren_norm("Vn : <= 10 UI/ml") == "(Vn : <= 10 UI/ml)"
    assert paren_norm("(V.N. <= 6 mg/L)") == "(V.N. <= 6 mg/L)"
    assert paren_norm("< 15mm") == "(V.N. < 15mm)"
    assert paren_norm("NEGATIF") == "(V.N. NEGATIF)"
    assert paren_norm("") == ""


# ---------- sous-titres (group) ----------

def test_sous_titres_de_la_nfs_dans_l_ordre():
    snap = build("NFS", NFS_VALUES, sex="F")
    assert snap["parameters"][0]["group"] == "NUMERATION GLOBULAIRE"
    assert snap["parameters"][9]["group"] == "FORMULE SANGUINE (Coloration MGG)"
    t = text(render(snap))
    in_order(t, ["HEMOGRAMME", "NUMERATION GLOBULAIRE", "Globules rouges (RBC)", "Plaquettes (Platelets)",
                 "FORMULE SANGUINE (Coloration MGG)", "ELEMENTS", "PN Neutrophiles", "Monocytes"])


def test_rubriques_ecbu_hemostase_et_spermogramme():
    ecbu = text(render(build("ECBU", ["Trouble", "6", "00", "05", "x", "y", "z", "w", "Escherichia coli", "a", "b", "c"])))
    in_order(ecbu, ["ASPECT", "CYTOLOGIE", "EXAMEN GRAM", "CULTURE", "ANTIBIOGRAMME (ATB)", "Sensible"])
    hem = text(render(build("TP_TCA", ["12", "13.5", "85", "1.1", "32", "34.2"])))
    in_order(hem, ["TAUX DE PROTHROMBINE / TEMPS DE QUICK", "Taux de Prothrombine", "TEMPS DE CEPHALINE ACTIVEE"])
    sp = CATALOGUE["SPERMOGRAMME"]["parameters"]
    sperm = text(render(build("SPERMOGRAMME", [{"numeric": "30", "text": "normal"}[p["result_kind"]] for p in sp])))
    in_order(sperm, ["RENSEIGNEMENTS GENERAUX", "II) ETUDE PHYSICO - CHIMIQUE", "III) ETUDE DYNAMIQUE", "IV) CYTOLOGIE"])


def test_sans_sous_titre_pas_de_bandeau():
    snap = build("NFS", NFS_VALUES, keep_group=False)
    t = text(render(snap))
    assert "NUMERATION GLOBULAIRE" not in t and "FORMULE SANGUINE (Coloration" not in t
    assert "Globules rouges (RBC)" in t


# ---------- notes fixes ----------

def _with_notes(notes):
    snap = build("GR_ABO_RH", ["A", "Positif"], conclusion="CONCLUSION DE TEST", note="NB DE TEST")
    snap["exam"]["fixed_notes"] = notes
    return snap


def test_positions_des_notes_fixes():
    snap = _with_notes([
        {"position": "after_conclusion", "text": "NOTE APRES CONCLUSION", "style": "normal"},
        {"position": "after_body", "text": "NOTE APRES CORPS", "style": "normal"},
        {"position": "before_body", "text": "NOTE AVANT CORPS", "style": "normal"}])
    t = text(render(snap))
    in_order(t, ["GROUPAGE SANGUIN", "NOTE AVANT CORPS", "RESULTATS", "GS : A", "Rhésus : POSITIF",
                 "NOTE APRES CORPS", "CONCLUSION : CONCLUSION DE TEST", "NB : NB DE TEST", "NOTE APRES CONCLUSION",
                 "LE RESPONSABLE DE LABORATOIRE"])


def test_styles_et_echappement_des_notes():
    snap = _with_notes([
        {"position": "after_body", "text": "gras", "style": "bold"},
        {"position": "after_body", "text": "italique", "style": "italic"},
        {"position": "after_body", "text": "<script>alert(1)</script> & <b>x</b>", "style": "normal"},
        {"position": "après", "text": "position inconnue", "style": "inconnu"}])
    html = lab_sheet_html(snap)
    assert '<p class="fixed-note bold">gras</p>' in html
    assert '<p class="fixed-note italic">italique</p>' in html
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html and "&lt;b&gt;x&lt;/b&gt;" in html
    assert '<p class="fixed-note normal">position inconnue</p>' in html      # repli : apres le corps, normal


def test_texte_fixe_des_examens_du_catalogue():
    t = text(render(build("CRP", ["12"], conclusion="Présence de la protéine C-réactive dans cet échantillon")))
    in_order(t, ["TECHNIQUE UTILISEE : Agglutination sur latex", "C.R.P (Protéine C - Réactive)",
                 "Valeur Seuil = 6 mg/l", "Valeur à 20 mg/l si syndrome inflammatoire", "RESULTATS",
                 "Valeur du malade : 12", "(V.N. <= 6 mg/L)"])
    t = text(render(build("TP_TCA", ["12", "13.5", "85", "1.1", "32", "34.2"])))
    in_order(t, ["Temps du sujet : 34,2 s", "Zones thérapeutiques :",
                 "Prévention de thromboses veineuses : 2,0 - 3,0", "Prévention de thromboses récidivantes : 2,0 - 4,0",
                 "Phlébites, embolies pulmonaire : 2,0 - 4,0", "Prophylaxie artérielle, valve cardiaque : 3,0 - 4,5",
                 "Valeurs usuelles : Temps du témoin + ou - 10s", "LE RESPONSABLE DE LABORATOIRE"])
    t = text(render(build("TYPHOIDE", ["Négatif", "Négatif"], conclusion="Absence des anticorps IgG et IgM")))
    in_order(t, ["CONCLUSION : Absence", "NB : Une réaction positive peut correspondre à une infection récente ou ancienne.",
                 "LE RESPONSABLE DU LABORATOIRE"])
    t = text(render(build("TOXO", ["Négatif", "Négatif", "< 10", "< 10"])))
    in_order(t, ["INFORMATIONS", "La Toxoplasmose est une maladie systémique", "femmes enceintes.",
                 "La détermination quantitative des anticorps IgG", "nouveau-né.",
                 "Du fait de la persistance des anticorps anti-toxo IgG", "infection active."])
    t = text(render(build("NFS", NFS_VALUES, sex="F")))
    in_order(t, ["HEMOGRAMME", "NUMERATION FORMULE SANGUINE (N.F.S)", "EXAMENS"])


def test_interpretation_chlamydiae_vient_des_donnees():
    with open(os.path.join(TEMPLATES_DIR, "lab_sheet_boxed.html"), encoding="utf-8") as fh:
        gabarit = fh.read()
    assert "Titre compris" not in gabarit and "INTERPRETATION" not in gabarit.replace("INTERPRETATION de la fiche", "")
    snap = build("CHLAMYDIA", ["", "> 8", "< 8", "< 8", "Sérologie moyennement positive"], sex="F")
    assert [n["position"] for n in snap["exam"]["fixed_notes"]] == ["after_body"] * 5
    html = lab_sheet_html(snap)
    assert html.count("fixed-note normal chosen") == 1
    assert "sérologie moyennement positive. Cette valeur peut correspondre" in html.split("fixed-note normal chosen")[1][:200]
    # sans note en base (catalogue modifie), plus aucun texte d'interpretation
    snap["exam"]["fixed_notes"] = []
    assert "INTERPRETATION" not in text(render(snap))


def test_copie_v1_aucune_note_ni_liste_de_normes():
    snap = build("CHLAMYDIA", ["", "> 8", "< 8", "< 8", "Sérologie négative"], sex="F")
    snap["version"] = 1
    snap["exam"].pop("fixed_notes")
    for p in snap["parameters"]:
        for k in ("norms", "norm_text"):
            p.pop(k, None)
        p["group"] = None
    t = text(render(snap))
    assert "Sérologie négative" in t and "INTERPRETATION" not in t
    nfs = build("NFS", NFS_VALUES, sex="F")
    nfs["version"] = 1
    nfs["exam"].pop("fixed_notes")
    for p in nfs["parameters"]:
        p.pop("norms"), p.pop("norm_text"), p.__setitem__("group", None)
    t = text(render(nfs))
    assert "F: 12 - 15" in t and "H: 12 - 17" not in t        # v1 : la norme choisie seulement
    assert "NUMERATION GLOBULAIRE" not in t
