# tests/test_lab_norm_text_seed.py
"""Chargement des textes imprimes du catalogue (migration 045, tache C5) sur des bases JETABLES :
sous-titres, textes de norme, textes de plage, notes fixes. Donnees lues dans scripts/data/lab_catalogue.json."""
import copy
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
import pytest

from scripts import seed_lab_catalogue as seedmod
from tests.test_lab_catalogue_seed import (  # noqa: F401  (fixtures et aides partagees)
    CATALOGUE, EXAMS, OLD_RANGES_SQL, OLD_SQL, _counts, _pg, _run, _seed, make_db, old_db, template_db)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _dump(url):
    return {t: _run(url, "select * from %s order by 1" % t, fetch=True)
            for t in ("examens", "parametres", "reference_ranges", "lab_results", "lab_result_details")}


# ---------- le fichier ----------

def test_fichier_respecte_les_limites():
    for e in CATALOGUE["exams"]:
        notes = e.get("fixed_notes") or []
        assert len(notes) <= 12, e["code"]
        for n in notes:
            assert set(n) == {"position", "text", "style"}
            assert n["position"] in ("before_body", "after_body", "after_conclusion")
            assert n["style"] in ("normal", "bold", "italic")
            assert 0 < len(n["text"]) <= 1000
        for p in e["parameters"]:
            assert len(p.get("group") or "") <= 80 and len(p.get("norm_text") or "") <= 200
            for r in p["ranges"]:
                assert len(r.get("display_text") or "") <= 60


def test_textes_fixes_extraits_et_normes_separees():
    assert [n["text"] for n in EXAMS["TYPHOIDE"]["fixed_notes"]] == [
        "NB : Une réaction positive peut correspondre à une infection récente ou ancienne."]
    assert [n["text"] for n in EXAMS["CRP"]["fixed_notes"]] == [
        "C.R.P (Protéine C - Réactive)", "Valeur Seuil = 6 mg/l", "Valeur à 20 mg/l si syndrome inflammatoire"]
    assert EXAMS["CRP"]["parameters"][0]["norm_text"] == "(V.N. <= 6 mg/L)"       # le reste est en notes
    assert len(EXAMS["CHLAMYDIA"]["fixed_notes"]) == 5 and len(EXAMS["TOXO"]["fixed_notes"]) == 4
    assert EXAMS["TOXO"]["fixed_notes"][0] == {"position": "after_conclusion", "text": "INFORMATIONS", "style": "bold"}
    assert len(EXAMS["TP_TCA"]["fixed_notes"]) == 6 and EXAMS["NFS"]["fixed_notes"][0]["style"] == "bold"
    rbc = EXAMS["NFS"]["parameters"][0]
    assert rbc["norm_text"] == "H: 4,0 - 5,5 F: 4,0 - 5,0"
    assert [r["display_text"] for r in rbc["ranges"]] == ["4,0 - 5,5", "4,0 - 5,0"]
    assert EXAMS["SPERMOGRAMME"]["parameters"][-2]["norm_text"] == "VN > 20 M/ml"


def test_refus_d_un_fichier_invalide(tmp_path):
    base = json.load(open(seedmod.DEFAULT_DATA, encoding="utf-8"))

    def broken(mutate):
        data = copy.deepcopy(base)
        mutate(data)
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ValueError):
            seedmod.load_catalogue(str(path))

    broken(lambda d: d["exams"][0]["parameters"][0].__setitem__("norm_text", "x" * 201))
    broken(lambda d: d["exams"][0]["parameters"][0].__setitem__("group", "x" * 81))
    broken(lambda d: d["exams"][0]["parameters"][0]["ranges"][0].__setitem__("display_text", "x" * 61))
    broken(lambda d: d["exams"][0].__setitem__("fixed_notes", [{"position": "after_body", "text": "a", "style": "normal"}] * 13))
    broken(lambda d: d["exams"][0].__setitem__("fixed_notes", [{"position": "milieu", "text": "a", "style": "normal"}]))
    broken(lambda d: d["exams"][0].__setitem__("fixed_notes", [{"position": "after_body", "text": " ", "style": "normal"}]))


# ---------- chargement ----------

def test_les_textes_sont_charges(old_db):
    s = _seed(old_db, replace_ranges=True)
    assert s["notes_exams"] == sum(1 for e in CATALOGUE["exams"] if e.get("fixed_notes"))
    groups = dict(_run(old_db, "select p.id, p.group_label from parametres p join examens e on e.id = p.examen_id "
                               "where e.code = 'NFS' and p.is_active and p.print_label is not null", fetch=True))
    assert sorted(set(groups.values())) == ["FORMULE SANGUINE (Coloration MGG)", "NUMERATION GLOBULAIRE"]
    rows = _run(old_db, "select p.print_label, p.norm_text from parametres p join examens e on e.id = p.examen_id "
                        "where e.code = 'NFS' and p.is_active order by p.ordre", fetch=True)
    assert rows[0] == ("- Globules rouges (RBC)", "H: 4,0 - 5,5 F: 4,0 - 5,0")
    assert _run(old_db, "select count(*) from parametres where norm_text is not null", fetch=True)[0][0] == sum(
        1 for e in CATALOGUE["exams"] for p in e["parameters"] if p.get("norm_text"))
    assert _run(old_db, "select count(*) from parametres where group_label is not null", fetch=True)[0][0] == sum(
        1 for e in CATALOGUE["exams"] for p in e["parameters"] if p.get("group"))
    assert _run(old_db, "select count(*) from reference_ranges where display_text is not null", fetch=True)[0][0] == sum(
        1 for e in CATALOGUE["exams"] for p in e["parameters"] for r in p["ranges"] if r.get("display_text"))
    notes = _run(old_db, "select fixed_notes from examens where code = 'CHLAMYDIA'", fetch=True)[0][0]
    assert notes == EXAMS["CHLAMYDIA"]["fixed_notes"]
    assert _run(old_db, "select fixed_notes from examens where code = 'GR_ABO_RH'", fetch=True) == [(None,)]
    assert _run(old_db, "select display_text from reference_ranges r join parametres p on p.id = r.parametre_id "
                        "join examens e on e.id = p.examen_id where e.code = 'NFS' and p.print_label like '%RBC%' "
                        "order by r.sexe", fetch=True) == [("4,0 - 5,0",), ("4,0 - 5,5",)]


def test_chargement_idempotent(old_db):
    _seed(old_db, replace_ranges=True)
    first = _dump(old_db)
    second = _seed(old_db)
    assert second["range_texts"] == 0 and second["exams_added"] == [] and second["params_added"] == 0
    assert _dump(old_db) == first


def test_plages_deja_en_base_recoivent_leur_texte_sans_etre_remplacees(old_db):
    _run(old_db, OLD_RANGES_SQL)
    _seed(old_db, replace_ranges=True)
    ids = [r[0] for r in _run(old_db, "select id from reference_ranges order by id", fetch=True)]
    _run(old_db, "update reference_ranges set display_text = null")
    s = _seed(old_db)                                   # sans --replace-ranges
    assert s["ranges_mode"] == "unchanged" and s["range_texts"] > 0
    assert [r[0] for r in _run(old_db, "select id from reference_ranges order by id", fetch=True)] == ids
    assert _run(old_db, "select count(*) from reference_ranges where display_text is not null", fetch=True)[0][0] \
        == s["range_texts"]


def test_rien_d_autre_ne_change(old_db):
    before = _dump(old_db)
    prices = dict(_run(old_db, "select code, prix from examens", fetch=True))
    _seed(old_db, replace_ranges=True)
    after = _dump(old_db)
    assert after["lab_results"] == before["lab_results"] and after["lab_result_details"] == before["lab_result_details"]
    assert dict(_run(old_db, "select code, prix from examens where code = any(%s)", (list(prices),), fetch=True)) == prices
    new_codes = [c for c in EXAMS if c not in prices]
    assert all(p == 0 for c, p in _run(old_db, "select code, prix from examens", fetch=True) if c in new_codes)
    # les ids et les noms de parametre existants sont inchanges
    names_before = {r[0]: r[2] for r in before["parametres"]}
    assert all({r[0]: r[2] for r in after["parametres"]}[i] == n for i, n in names_before.items())


def test_effacer_un_texte_du_fichier_vide_la_colonne(old_db, tmp_path):
    _seed(old_db, replace_ranges=True)
    data = copy.deepcopy(CATALOGUE)
    for e in data["exams"]:
        if e["code"] == "CHLAMYDIA":
            e["fixed_notes"] = []
        if e["code"] == "NFS":
            e["parameters"][0]["norm_text"] = ""
            e["parameters"][0]["group"] = None
    conn = psycopg2.connect(_pg(old_db))
    try:
        seedmod.seed(conn, data)
        conn.commit()
    finally:
        conn.close()
    assert _run(old_db, "select fixed_notes from examens where code = 'CHLAMYDIA'", fetch=True) == [(None,)]
    assert _run(old_db, "select norm_text, group_label from parametres p join examens e on e.id = p.examen_id "
                        "where e.code = 'NFS' and p.print_label like '%RBC%'", fetch=True) == [(None, None)]


def test_contraintes_de_longueur_en_base(old_db):
    _seed(old_db)
    for sql in ("update parametres set group_label = repeat('x', 81) where id = 1",
                "update parametres set norm_text = repeat('x', 201) where id = 1",
                "update reference_ranges set display_text = repeat('x', 61)",
                "update examens set fixed_notes = '{}'::jsonb where code = 'NFS'"):
        with pytest.raises(psycopg2.errors.CheckViolation):
            _run(old_db, sql)
