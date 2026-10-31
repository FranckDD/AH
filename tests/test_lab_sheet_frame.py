# tests/test_lab_sheet_frame.py
"""Cadre commun des fiches de resultats du laboratoire (D1). Patients inventes uniquement.
Texte lu via pypdf (WeasyPrint sous-ensemble les polices: jamais d'octets bruts)."""
import copy
import io
import os
import sys
from datetime import date
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api_backend.backend_app.utils import lab_sheet
from api_backend.backend_app.utils.lab_sheet import (
    FAMILY_TEMPLATES, UnknownSnapshotVersionError, format_date_letters, render_lab_sheet)
from utils.lab_dossier import DossierNumber, format_dossier


def _structure(**kw):
    base = dict(name="Centre Test Alpha", slogan=None, address="Rue 1", city="Douala", po_box=None,
                phone="600000001", phone2=None, email="c@example.org", website=None,
                agrement_number="N 123/AGR", niu=None, rccm=None, legal_info=None,
                footer_text=None, signature_label_default=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _snapshot(**over):
    snap = {
        "version": 1,
        "exam": {"code": "GLY", "title": "GLYCEMIE", "section": "BIOCHIMIE", "method": None,
                 "family": "label_value", "signature_label": None, "sort_order": 1},
        "patient": {"age_label": "6 Mois", "age_days": 180, "sex": "F"},
        "pregnancy": {"status_at_result": "enceinte", "gestational_age_weeks": 22},
        "dossier": {"year": 2026, "counter": 289, "rank": 2},
        "parameters": [{"id": 1, "label": "Glycemie", "unit": "g/L", "kind": "numeric", "order": 1,
                        "value_text": "0.95", "value_num": 0.95, "flagged": False, "interpretation": None,
                        "norm": {"text": "0.7 - 1.1", "min": 0.7, "max": 1.1, "sex": "X",
                                 "age_min_days": None, "age_max_days": None,
                                 "ga_min_weeks": None, "ga_max_weeks": None}, "group": None}],
        "conclusion": None,
        "note": None,
    }
    snap.update(over)
    return snap


def _render(snap=None, structure=None, patient=None, show_pregnancy=False, **ctx):
    context = {"structure": structure or _structure(), "logo_path": None,
               "validation_date": date(2026, 10, 8),
               "dossier_label": format_dossier(DossierNumber(2026, 289, 2), date(2026, 10, 8))}
    context.update(ctx)
    return render_lab_sheet(snap or _snapshot(), patient or {"name": "DUPONT Alice", "prescriber": "Dr. Martin"},
                            context, show_pregnancy=show_pregnancy)


def _pages(pdf):
    return [" ".join((p.extract_text() or "").split()) for p in PdfReader(io.BytesIO(pdf)).pages]


def _text(pdf):
    return "\n".join(_pages(pdf))


def test_une_page_lettre_us():
    pages = PdfReader(io.BytesIO(_render())).pages
    assert len(pages) == 1
    w, h = float(pages[0].mediabox.width), float(pages[0].mediabox.height)
    assert (round(w), round(h)) == (612, 792)


def test_en_tete_depuis_la_configuration():
    a = _text(_render(structure=_structure(name="Centre Test Alpha")))
    b = _text(_render(structure=_structure(name="Clinique Beta Zeta", agrement_number="N 999/BETA")))
    assert "Centre Test Alpha" in a and "N 123/AGR" in a and "Clinique Beta Zeta" not in a
    assert "Clinique Beta Zeta" in b and "N 999/BETA" in b and "Centre Test Alpha" not in b


def test_ville_de_la_configuration_puis_repli():
    assert "Douala, le 08 OCTOBRE 2026" in _text(_render())
    assert "Yaoundé, le 08 OCTOBRE 2026" in _text(_render(structure=_structure(city=None)))
    assert "Garoua, le" in _text(_render(city="Garoua"))


def test_bloc_patient():
    txt = _text(_render())
    assert "DOSSIER N° 289/02 du 08/10/2026" in txt
    assert "Nom du Patient : DUPONT Alice" in txt
    assert "Age : 6 Mois" in txt and "Sexe : F" in txt
    assert "Examen demande par : Dr. Martin" in txt
    assert "RESULTATS D'ANALYSES DE BIOLOGIE CLINIQUE" in txt


def test_numero_de_dossier_calcule_depuis_la_copie():
    txt = _text(render_lab_sheet(_snapshot(), {"name": "X", "prescriber": "Y"},
                                 {"structure": _structure(), "dossier_day": date(2026, 10, 8)},
                                 show_pregnancy=False))
    assert "289/02 du 08/10/2026" in txt


def test_titre_variable():
    assert "LABORATOIRE D'ANALYSES DE BIOLOGIE CLINIQUE" in _text(
        _render(title="LABORATOIRE D'ANALYSES DE BIOLOGIE CLINIQUE"))


def test_prescripteur_et_nom_echappes():
    pdf = _render(patient={"name": "<script>alert(1)</script>", "prescriber": "<b>Dr & Co</b>"})
    txt = _text(pdf)
    assert "<script>alert(1)</script>" in txt and "<b>Dr & Co</b>" in txt


def test_conclusion_et_nb_separes_puis_omis():
    txt = _text(_render(_snapshot(conclusion="Anemie legere <i>x</i>", note="Controle dans 1 mois")))
    assert "CONCLUSION : Anemie legere <i>x</i>" in txt and "NB : Controle dans 1 mois" in txt
    txt = _text(_render(_snapshot(conclusion="Seule conclusion")))
    assert "CONCLUSION : Seule conclusion" in txt and "NB :" not in txt
    txt = _text(_render(_snapshot(conclusion="  ", note="")))
    assert "CONCLUSION" not in txt and "NB :" not in txt


def test_texte_multiligne_conserve():
    pdf = _render(_snapshot(conclusion="Ligne un\nLigne deux"))
    lines = [ln.strip() for ln in (PdfReader(io.BytesIO(pdf)).pages[0].extract_text() or "").splitlines()]
    assert any(ln.endswith("Ligne un") for ln in lines) and "Ligne deux" in lines


def test_grossesse_seulement_si_autorisee():
    shown = _text(_render(show_pregnancy=True))
    assert "Grossesse : Enceinte - 22 SA" in shown
    hidden = _text(_render(show_pregnancy=False))
    assert "Grossesse" not in hidden and "22 SA" not in hidden and "Enceinte" not in hidden
    # autorise mais sans donnee: pas de ligne
    assert "Grossesse" not in _text(_render(_snapshot(pregnancy=None), show_pregnancy=True))
    assert "Grossesse : Non enceinte" in _text(_render(
        _snapshot(pregnancy={"status_at_result": "non_enceinte", "gestational_age_weeks": None}), show_pregnancy=True))


def test_signature_snapshot_defaut_et_repli():
    snap = _snapshot()
    snap["exam"]["signature_label"] = "Le Responsable du Laboratoire"
    assert "Le Responsable du Laboratoire" in _text(_render(snap))
    txt = _text(_render(structure=_structure(signature_label_default="Le Chef du Labo")))
    assert "Le Chef du Labo" in txt and "Le Biologiste" not in txt
    assert "Le Biologiste" in _text(_render())


def test_pied_de_page():
    assert "BONNE GUERISON" not in _text(_render())
    txt = _text(_render(structure=_structure(footer_text="BONNE GUERISON\n\nWISHES YOU WELL <b>")))
    assert "BONNE GUERISON" in txt and "WISHES YOU WELL <b>" in txt
    assert "BONNE GUERISON" not in _pages(_render(structure=_structure(footer_text="BONNE GUERISON")))[0][:200]


def test_longs_textes_ne_plantent_pas():
    long = "mot " * 1250  # 5000 caracteres
    pdf = _render(_snapshot(conclusion=long[:5000], note="n" * 1000),
                  patient={"name": "N" * 300, "prescriber": "P" * 300})
    assert len(PdfReader(io.BytesIO(pdf)).pages) >= 1  # debordement sur une 2e page admis pour du texte extreme
    # une conclusion raisonnable reste sur une page
    assert len(_pages(_render(_snapshot(conclusion="Phrase de conclusion " * 10)))) == 1


def test_signature_jamais_coupee():
    pdf = _render(_snapshot(conclusion="x " * 2400))
    pages = _pages(pdf)
    assert sum("Le Biologiste" in p for p in pages) == 1


@pytest.mark.parametrize("month,name", list(enumerate(lab_sheet.MONTHS_FR, start=1)))
def test_format_date_letters_chaque_mois(month, name):
    assert format_date_letters(date(2026, month, 5)) == f"05 {name} 2026"


def test_format_date_letters_bornes():
    assert format_date_letters(date(2026, 1, 1)) == "01 JANVIER 2026"
    assert format_date_letters(date(2026, 12, 31)) == "31 DECEMBRE 2026"
    assert format_date_letters(date(2027, 1, 1)) == "01 JANVIER 2027"
    assert format_date_letters(date(2026, 10, 8)) == "08 OCTOBRE 2026"


def test_version_inconnue_leve():
    snap = _snapshot()
    snap["version"] = 99
    with pytest.raises(UnknownSnapshotVersionError):
        _render(snap)
    with pytest.raises(UnknownSnapshotVersionError):
        render_lab_sheet({}, {"name": "X"}, {"structure": _structure()}, show_pregnancy=False)


def test_famille_inconnue_repli_generique_et_enregistrement():
    snap = _snapshot()
    snap["exam"]["family"] = "famille_inconnue"  # non enregistree: repli label_value (D2: virgule decimale)
    assert "Glycemie : 0,95 g/L" in _text(_render(snap))
    assert "label_value" in FAMILY_TEMPLATES


def test_donnees_snapshot_non_modifiees():
    snap = _snapshot()
    before = copy.deepcopy(snap)
    _render(snap)
    assert snap == before
