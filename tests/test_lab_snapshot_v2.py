# tests/test_lab_snapshot_v2.py
"""Copie figee version 2 (migration 045, tache C5) : toutes les normes du parametre, sous-titre, texte de
norme imprime et notes fixes de l'examen. Constructeur pur (objets simules, aucune base). Patients inventes."""
import json
import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

from api_backend.backend_app.utils.lab_sheet import (
    SUPPORTED_SNAPSHOT_VERSIONS, UnknownSnapshotVersionError, render_lab_sheet)
from utils.lab_snapshot import SNAPSHOT_VERSION, build_print_snapshot


def _range(i, sexe, lo, hi, amin=None, amax=None, text=None):
    return SimpleNamespace(id=i, sexe=sexe, age_min_days=amin, age_max_days=amax, ga_min_weeks=None,
                           ga_max_weeks=None, valeur_min=Decimal(str(lo)), valeur_max=Decimal(str(hi)),
                           display_text=text)


def _param(pid, ranges, group=None, norm_text=None, label="Globules rouges (RBC)"):
    return SimpleNamespace(id=pid, print_label=label, nom_parametre=label, unite="x10^6/mm3", result_kind="numeric",
                           ordre=pid, reference_ranges=ranges, group_label=group, norm_text=norm_text)


def _exam(notes=None):
    return SimpleNamespace(code="NFS", print_title="HEMOGRAMME", nom="NFS", section="HEMATOLOGIE", method=None,
                           layout_family="table", signature_label=None, sort_order=10, fixed_notes=notes)


def _build(params, sex="F", age_days=12000, notes=None, conclusion=None):
    details = [SimpleNamespace(parametre=p, valeur_text="4.1", valeur_num=4.1, flagged=False, interpretation=None)
               for p in params]
    result = SimpleNamespace(dossier_year=None, dossier_counter=None, dossier_rank=None,
                             pregnancy_status_at_result=None, gestational_age_weeks=None,
                             conclusion=conclusion, note=None)
    bio = SimpleNamespace(age_days=age_days, sex=sex, ga_weeks=None, age_label="33 Ans")
    return build_print_snapshot(result, _exam(notes), details, bio)


RBC = [_range(1, "M", 4.0, 5.5, text="4,0 - 5,5"), _range(2, "F", 4.0, 5.0, text="4,0 - 5,0")]


def test_version_2_et_lecteur_accepte_1_et_2():
    assert SNAPSHOT_VERSION == 2
    assert _build([_param(1, RBC)])["version"] == 2
    assert SUPPORTED_SNAPSHOT_VERSIONS == (1, 2)
    with pytest.raises(UnknownSnapshotVersionError):
        render_lab_sheet({"version": 3, "exam": {}, "parameters": []}, {}, {}, show_pregnancy=False)


def test_toutes_les_normes_dont_celle_choisie_marquee():
    s = _build([_param(1, RBC, group="NUMERATION GLOBULAIRE", norm_text="H: 4,0 - 5,5   F: 4,0 - 5,0")], sex="F")
    p = s["parameters"][0]
    assert set(p) == {"id", "label", "unit", "kind", "order", "value_text", "value_num", "flagged",
                      "interpretation", "norm", "group", "norm_text", "norms"}
    assert p["group"] == "NUMERATION GLOBULAIRE" and p["norm_text"] == "H: 4,0 - 5,5   F: 4,0 - 5,0"
    assert len(p["norms"]) == 2
    assert {n["sex"] for n in p["norms"]} == {"M", "F"}
    assert all(set(n) == {"sex", "age_min_days", "age_max_days", "ga_min_weeks", "ga_max_weeks", "min", "max",
                          "text", "selected"} for n in p["norms"])
    chosen = [n for n in p["norms"] if n["selected"]]
    assert len(chosen) == 1 and chosen[0]["sex"] == "F" and chosen[0]["text"] == "4,0 - 5,0"
    # `norm` (v1) reste la norme choisie, forme mecanique
    assert p["norm"]["sex"] == "F" and p["norm"]["text"] == "4 - 5" and (p["norm"]["min"], p["norm"]["max"]) == (4.0, 5.0)
    # l'autre sexe : meme parametre, l'autre plage est la choisie
    s = _build([_param(1, RBC)], sex="M")
    assert [n["sex"] for n in s["parameters"][0]["norms"] if n["selected"]] == ["M"]


def test_texte_de_norme_mecanique_sans_display_text_et_aucune_choisie():
    rngs = [_range(1, "M", 12, 17), _range(2, "X", 16, 21.5, amax=28)]
    s = _build([_param(1, rngs)], sex="F", age_days=12000)       # une femme adulte : ni la plage 'M' ni celle de 28 j
    p = s["parameters"][0]
    assert [n["text"] for n in p["norms"]] == ["16 - 21.5", "12 - 17"]       # sans display_text : forme mecanique
    assert not any(n["selected"] for n in p["norms"]) and p["norm"] is None
    assert p["norm_text"] is None and p["group"] is None


def test_normes_triees_de_facon_stable():
    rngs = [_range(3, "X", 5, 15, amax=1825), _range(1, "X", 5, 10, amin=1826), _range(2, "M", 1, 2)]
    a = _build([_param(1, rngs)])["parameters"][0]["norms"]
    b = _build([_param(1, list(reversed(rngs)))])["parameters"][0]["norms"]
    assert a == b


def test_notes_fixes_copiees_et_nettoyees():
    notes = [{"position": "before_body", "text": "NUMERATION", "style": "bold", "extra": 1},
             {"position": "after_body", "text": "  ", "style": "normal"},          # vide : ignoree
             {"text": "sans position"}]
    s = _build([_param(1, RBC)], notes=notes)
    assert s["exam"]["fixed_notes"] == [
        {"position": "before_body", "text": "NUMERATION", "style": "bold"},
        {"position": "after_body", "text": "sans position", "style": "normal"}]
    assert _build([_param(1, RBC)], notes=None)["exam"]["fixed_notes"] == []


def test_copie_serialisable_json_et_sans_identite():
    s = _build([_param(1, RBC)])
    text = json.dumps(s)
    assert "nom" not in s["patient"] and json.loads(text) == s


def test_une_copie_v1_ancienne_se_rend_toujours():
    """Une copie de la version 1 (norme choisie seulement, pas de norms ni de notes) reste lisible."""
    v1 = {"version": 1,
          "exam": {"code": "GLY", "title": "GLYCEMIE A JEUN", "section": None, "method": None, "family": "three_columns",
                   "signature_label": None, "sort_order": 1},
          "patient": {"age_label": "33 Ans", "age_days": 12000, "sex": "M"}, "pregnancy": None, "dossier": None,
          "parameters": [{"id": 1, "label": "Glycemie", "unit": "g/l", "kind": "numeric", "order": 1,
                          "value_text": "0.95", "value_num": 0.95, "flagged": False, "interpretation": None,
                          "norm": {"text": "0.6 - 1.2", "min": 0.6, "max": 1.2, "sex": "X", "age_min_days": None,
                                   "age_max_days": None, "ga_min_weeks": None, "ga_max_weeks": None},
                          "group": None}],
          "conclusion": None, "note": None}
    from pypdf import PdfReader
    import io
    pdf = render_lab_sheet(v1, {"name": "TESTEUR Jean", "prescriber": None},
                           {"structure": None, "logo_path": None}, show_pregnancy=False)
    t = " ".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(pdf)).pages)
    assert "0,95" in t and "0,6 - 1,2 g/l" in t
