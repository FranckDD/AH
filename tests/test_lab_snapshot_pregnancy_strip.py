# tests/test_lab_snapshot_pregnancy_strip.py
"""Confidentialite : pour un role qui ne voit pas la grossesse, la copie figee ne laisse aucune trace qu'une
norme est une plage de semaines de grossesse (bornes ga_*, plage, marqueur `selected`). Donnees inventees."""
import copy

from tests.test_lab_sheet_families import CATALOGUE, build, render, text
from utils.lab_snapshot import strip_pregnancy

GA_TEXT = "12 - 20 SA grossesse semaines de grossesse"


def _snap_with_ga():
    code = next(c for c, e in CATALOGUE.items()
                if e["layout_family"] == "label_value" and e["parameters"] and e["parameters"][0]["result_kind"] == "numeric")
    e = CATALOGUE[code]
    snap = build(code, ["5"] * len(e["parameters"]), sex="F", age_days=12000, pregnancy=("PREGNANT", 14))
    p = snap["parameters"][0]
    for n in p["norms"]:
        n["selected"] = False
    ga = {"sex": "F", "age_min_days": None, "age_max_days": None, "ga_min_weeks": 12, "ga_max_weeks": 20,
          "min": 1.0, "max": 9.0, "text": GA_TEXT, "selected": True}
    p["norms"].append(ga)
    p["norm"] = dict(ga, ga_min_weeks=12, ga_max_weeks=20)
    p["norm_text"] = GA_TEXT
    p["flagged"] = True
    return snap


def _has_key(obj, key):
    if isinstance(obj, dict):
        return key in obj or any(_has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(_has_key(v, key) for v in obj)
    return False


def test_non_viewer_gets_no_ga_trace():
    snap = _snap_with_ga()
    before = copy.deepcopy(snap)
    out = strip_pregnancy(snap)
    assert snap == before  # pure
    assert out["pregnancy"] is None
    assert not _has_key(out, "ga_min_weeks") and not _has_key(out, "ga_max_weeks")
    p = out["parameters"][0]
    assert all("SA" not in n["text"] and "grossesse" not in n["text"] for n in p["norms"])
    assert not any(n.get("selected") for n in p["norms"])
    assert p["norm_text"] is None
    assert p["flagged"] is True  # la valeur reste


def test_viewer_keeps_everything():
    snap = _snap_with_ga()
    assert snap["parameters"][0]["norms"][-1]["ga_min_weeks"] == 12
    assert snap["parameters"][0]["norms"][-1]["selected"] is True


def test_pdf_text_for_non_viewer_has_no_pregnancy_norm():
    snap = _snap_with_ga()
    out = text(render(strip_pregnancy(snap), show_pregnancy=False))
    assert "semaines de grossesse" not in out
    assert " SA" not in out
    full = text(render(snap, show_pregnancy=True))
    assert "semaines de grossesse" in full or "SA" in full
