"""Export / import des donnees de reference, sur des bases JETABLES (jamais la base de dev).

Les bases sont creees sur le Postgres local (meme serveur que DATABASE_URL) a partir de
ci/schema_only.sql + ci/seed_application_roles.sql, puis supprimees en fin de test.
"""
import json
import os
import shutil
import subprocess
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from api_backend.backend_app.config import DATABASE_URL
from scripts import export_reference_data as exp
from scripts import import_reference_data as imp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
pytestmark = pytest.mark.skipif(shutil.which("psql") is None, reason="psql requis")


def _url(dbname):
    return make_url(DATABASE_URL).set(database=dbname).render_as_string(hide_password=False)


def _admin_exec(sql):
    conn = psycopg2.connect(exp.normalize_url(_url("postgres")))
    conn.autocommit = True
    try:
        conn.cursor().execute(sql)
    finally:
        conn.close()


@pytest.fixture(scope="module")
def template_db():
    name = "ah2_t6_tpl_" + uuid.uuid4().hex[:8]
    _admin_exec('CREATE DATABASE "%s"' % name)
    try:
        for f in ("ci/schema_only.sql", "ci/seed_application_roles.sql"):
            subprocess.run(["psql", exp.normalize_url(_url(name)), "-X", "-q", "-v", "ON_ERROR_STOP=1",
                            "-f", os.path.join(ROOT, f)], check=True, capture_output=True)
        yield name
    finally:
        _admin_exec('DROP DATABASE IF EXISTS "%s" WITH (FORCE)' % name)


@pytest.fixture
def make_db(template_db):
    created = []

    def _make():
        name = "ah2_t6_ref_" + uuid.uuid4().hex[:8]
        _admin_exec('CREATE DATABASE "%s" TEMPLATE "%s"' % (name, template_db))
        created.append(name)
        return _url(name)

    yield _make
    for name in created:
        _admin_exec('DROP DATABASE IF EXISTS "%s" WITH (FORCE)' % name)


def _run(url, sql, params=None, fetch=False):
    conn = psycopg2.connect(exp.normalize_url(url))
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


SEED_SQL = """
INSERT INTO examens (id, code, nom, categorie, prix) VALUES
  (7,  'NFS',  'Numération formule sanguine', 'Hématologie', 3500.50),
  (12, 'GLY',  'Glycémie à jeun', 'Biochimie', 1500),
  (20, 'ECBU', 'ECBU', 'Bactériologie', NULL);
INSERT INTO parametres (id, examen_id, nom_parametre, unite, type_valeur, input_type, options_list, ordre) VALUES
  (3, 7,  'Hémoglobine', 'g/dL', 'numeric', 'numeric', NULL, 1),
  (9, 7,  'Leucocytes', '/mm3', 'numeric', 'numeric', NULL, 2),
  (15, 12, 'Glycémie', 'g/L', 'numeric', 'numeric', NULL, 1),
  (16, 20, 'Aspect', '', 'texte', 'select', 'Clair,Trouble', 1);
INSERT INTO reference_ranges (id, parametre_id, sexe, age_min, age_max, valeur_min, valeur_max) VALUES
  (5, 3, 'M', 18, 120, 13.5, 17.5),
  (8, 3, 'F', 18, 120, 12.0, 15.5),
  (11, 15, 'X', 0, 120, 0.70, 1.10);
INSERT INTO reference_ranges (id, parametre_id, sexe, age_min_days, age_max_days, ga_min_weeks, ga_max_weeks,
                              valeur_min, valeur_max) VALUES
  (12, 3, 'X', 0, 28, NULL, NULL, 16, 21.5),
  (13, 15, 'F', NULL, NULL, 14, 27, 0.60, 0.95);
UPDATE examens SET section = 'HEMATOLOGIE', method = 'Methode X', layout_family = 'table',
  signature_label = 'Le Biologiste', print_title = 'HEMOGRAMME', sort_order = 10 WHERE id = 7;
UPDATE examens SET is_active = false WHERE id = 20;
UPDATE examens SET fixed_notes = '[{"position": "before_body", "text": "NOTE FIXE", "style": "bold"}]'::jsonb WHERE id = 7;
UPDATE parametres SET group_label = 'NUMERATION GLOBULAIRE', norm_text = 'H: 12 - 17 F: 12 - 15' WHERE id = 3;
UPDATE reference_ranges SET display_text = '16 - 21,5' WHERE id = 12;
UPDATE parametres SET print_label = '- Taux d''HB (Hb)', result_kind = 'numeric' WHERE id = 3;
UPDATE parametres SET result_kind = 'choice', choices = '["Clair", "Trouble"]'::jsonb, is_active = false
  WHERE id = 16;
INSERT INTO prayer_book_type (type_code, label) VALUES ('MPI', 'Prière I'), ('MPII', 'Prière II');
INSERT INTO staff_discount_rules (id, category, min_invoice_amount, rate_percent, is_active)
  VALUES (30, 'examen', 2000, 15, true);
INSERT INTO permissions (permission_id, permission_name, procedure_name, description_procedure)
  VALUES (4, 'create_patient', 'create_patient', 'Création de patients');
INSERT INTO role_permissions (role_id, permission_id)
  SELECT role_id, 4 FROM application_roles WHERE role_name IN ('admin', 'medecin');
INSERT INTO medical_specialties (specialty_id, name) VALUES (6, 'Généraliste'), (9, 'ORL');
INSERT INTO organization_config (id, name, slogan, logo_url, ticket_logo_url, ticket_print_token, city,
                                 agrement_number, footer_text, signature_label_default)
  VALUES (1, 'Centre Test', 'Slogan', '/static/uploads/logos/a.png', '/static/uploads/ticket_logos/b.jpg',
          'SECRET-TOKEN-VALUE', 'Yaounde', 'N 0001/TEST', 'Ligne 1
Ligne 2', 'Le Biologiste');
INSERT INTO users (username, password_hash, full_name, role_id)
  SELECT 'secret_user_t6', 'HASH-SECRET', 'Secret User', role_id FROM application_roles WHERE role_name='admin';
"""

TABLES = ["examens", "parametres", "reference_ranges", "prayer_book_type", "staff_discount_rules",
          "permissions", "role_permissions", "medical_specialties", "organization_config"]
ORDER = {"examens": "id", "parametres": "id", "reference_ranges": "id", "prayer_book_type": "type_code",
         "staff_discount_rules": "id", "permissions": "permission_id", "role_permissions": "role_id, permission_id",
         "medical_specialties": "specialty_id", "organization_config": "id"}


@pytest.fixture
def seeded_source(make_db):
    url = make_db()
    _run(url, SEED_SQL)
    return url


def _export(url, tmp_path, *extra):
    path = str(tmp_path / "ref.json")
    assert exp.main([path, "--source-url", url, "--with-ranges"] + list(extra)) == 0
    return path


def _dump(url, table, cols="*"):
    return _run(url, "SELECT %s FROM %s ORDER BY %s" % (cols, table, ORDER[table]), fetch=True)


def test_export_then_import_gives_identical_rows_except_prix(seeded_source, make_db, tmp_path, capsys):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    capsys.readouterr()

    for t in TABLES:
        src, dst = _dump(seeded_source, t), _dump(target, t)
        if t == "examens":
            assert [r[:4] + r[5:] for r in src] == [r[:4] + r[5:] for r in dst]
            assert all(r[4] == 0 for r in dst)
        elif t == "organization_config":
            cols = ("id, name, slogan, address, city, label_width_mm, label_height_mm, agrement_number, "
                    "footer_text, signature_label_default")
            assert _dump(seeded_source, t, cols) == _dump(target, t, cols)
        elif t == "staff_discount_rules":
            cols = "id, category, min_invoice_amount, rate_percent, is_active"
            assert _dump(seeded_source, t, cols) == _dump(target, t, cols)
        else:
            assert src == dst, t


def test_prices_all_zero_after_import(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    assert _run(target, "select count(*) from examens where prix <> 0", fetch=True) == [(0,)]
    assert _run(target, "select count(*) from examens", fetch=True) == [(3,)]


def test_extended_catalogue_columns_carried_over(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    data = json.load(open(path, encoding="utf-8"))
    assert data["_meta"]["version"] == 3
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    assert _run(target, "select section, method, layout_family, signature_label, print_title, sort_order, is_active "
                        "from examens order by id", fetch=True) == [
        ("HEMATOLOGIE", "Methode X", "table", "Le Biologiste", "HEMOGRAMME", 10, True),
        (None, None, "label_value", None, None, 0, True),
        (None, None, "label_value", None, None, 0, False)]
    assert _run(target, "select id, print_label, result_kind, choices, is_active from parametres order by id",
                fetch=True) == [
        (3, "- Taux d'HB (Hb)", "numeric", None, True), (9, None, "numeric", None, True),
        (15, None, "numeric", None, True), (16, None, "choice", ["Clair", "Trouble"], False)]
    assert _run(target, "select id, age_min_days, age_max_days, ga_min_weeks, ga_max_weeks from reference_ranges "
                        "where id in (12, 13) order by id", fetch=True) == [(12, 0, 28, None, None), (13, None, None, 14, 27)]
    # migration 045 : sous-titre, texte de norme, texte de plage, notes fixes
    assert _run(target, "select fixed_notes from examens where id = 7", fetch=True) == [
        ([{"position": "before_body", "text": "NOTE FIXE", "style": "bold"}],)]
    assert _run(target, "select id, group_label, norm_text from parametres where id in (3, 9) order by id",
                fetch=True) == [(3, "NUMERATION GLOBULAIRE", "H: 12 - 17 F: 12 - 15"), (9, None, None)]
    assert _run(target, "select display_text from reference_ranges where id in (12, 13) order by id",
                fetch=True) == [("16 - 21,5",), (None,)]


def test_org_logo_and_token_not_carried_over(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    assert _run(target, "select logo_url, ticket_logo_url, ticket_print_token from organization_config",
                fetch=True) == [(None, None, None)]


def test_examen_parametre_range_links_identical_and_no_orphans(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    q = ("select e.code, p.nom_parametre, r.sexe, r.valeur_min, r.valeur_max from examens e "
         "join parametres p on p.examen_id = e.id left join reference_ranges r on r.parametre_id = p.id "
         "order by e.code, p.id, r.id")
    assert _run(seeded_source, q, fetch=True) == _run(target, q, fetch=True)
    assert _run(target, "select count(*) from reference_ranges r left join parametres p on p.id=r.parametre_id "
                        "where p.id is null", fetch=True) == [(0,)]


def test_sequences_reset_to_max_id(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    assert _run(target, "insert into examens (code, nom, categorie, prix) values ('NEW','n','c',1) returning id",
                fetch=True) == [(21,)]
    assert _run(target, "insert into parametres (examen_id, nom_parametre, unite, type_valeur) "
                        "values (7,'x','u','numeric') returning id", fetch=True) == [(17,)]
    assert _run(target, "insert into reference_ranges (parametre_id, sexe, age_min, age_max, valeur_min, valeur_max) "
                        "values (3,'M',0,1,0,1) returning id", fetch=True) == [(14,)]
    assert _run(target, "insert into medical_specialties (name) values ('Nouvelle') returning specialty_id",
                fetch=True) == [(10,)]


def test_file_has_no_user_or_patient_data_and_no_secrets(seeded_source, tmp_path):
    path = _export(seeded_source, tmp_path)
    raw = open(path, encoding="utf-8").read()
    data = json.loads(raw)
    forbidden = ("user", "patient", "caisse", "lab_result", "prescription", "hospital",
                 "notification", "audit", "spiritual", "stock", "product", "pharmac")
    for key in data:
        assert not any(w in key.lower() for w in forbidden), key
    assert set(data) - {"_meta"} == set(TABLES)
    for needle in ("secret_user_t6", "HASH-SECRET", "SECRET-TOKEN-VALUE", "/static/uploads", "logo_url",
                   "ticket_print_token"):
        assert needle not in raw, needle
    assert data["organization_config"][0]["name"] == "Centre Test"


def test_unknown_new_org_column_is_not_exported(seeded_source, tmp_path):
    _run(seeded_source, "ALTER TABLE organization_config ADD COLUMN smtp_pass text")
    _run(seeded_source, "UPDATE organization_config SET smtp_pass = 'MAIL-SECRET-VALUE'")
    raw = open(_export(seeded_source, tmp_path), encoding="utf-8").read()
    assert "smtp_pass" not in raw and "MAIL-SECRET-VALUE" not in raw
    assert set(json.loads(raw)["organization_config"][0]) <= exp.ORG_ALLOWED


def test_export_uses_a_read_only_transaction(seeded_source):
    conn = exp.connect_readonly(seeded_source)
    try:
        with pytest.raises(psycopg2.Error):
            conn.cursor().execute("DELETE FROM examens")
        conn.rollback()
        cur = conn.cursor()
        cur.execute("SHOW transaction_isolation")
        assert cur.fetchone()[0] == "repeatable read"
    finally:
        conn.rollback()
        conn.close()


def test_importing_twice_is_refused_and_writes_nothing(seeded_source, make_db, tmp_path, capsys):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    before = {t: _dump(target, t) for t in TABLES}
    assert imp.main([path, "--database-url", target]) == 2
    assert {t: _dump(target, t) for t in TABLES} == before
    assert "REFUSE" in capsys.readouterr().err


def test_import_refused_when_any_target_table_has_rows(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    target = make_db()
    _run(target, "insert into medical_specialties (name) values ('Deja la')")
    assert imp.main([path, "--database-url", target]) == 2
    assert _run(target, "select count(*) from examens", fetch=True) == [(0,)]


def test_error_midway_rolls_back_everything(seeded_source, make_db, tmp_path, capsys):
    path = _export(seeded_source, tmp_path)
    data = json.load(open(path, encoding="utf-8"))
    data["parametres"].append({"id": 99, "examen_id": 9999, "nom_parametre": "x", "unite": "u",
                               "type_valeur": "numeric", "input_type": "numeric", "options_list": None,
                               "ordre": 1, "print_label": None, "result_kind": "numeric", "choices": None,
                               "is_active": True, "group_label": None, "norm_text": None})
    bad = str(tmp_path / "bad.json")
    json.dump(data, open(bad, "w", encoding="utf-8"))
    target = make_db()
    assert imp.main([bad, "--database-url", target]) == 1
    for t in TABLES:
        assert _run(target, "select count(*) from %s" % t, fetch=True) == [(0,)], t
    assert "annule" in capsys.readouterr().err


def test_corrupted_file_leaves_target_empty(make_db, tmp_path):
    target = make_db()
    bad = tmp_path / "corrupt.json"
    bad.write_text('{"_meta": {"format": "ah2-reference-data", "version": 1}, "examens": [{"id": 1,',
                   encoding="utf-8")
    assert imp.main([str(bad), "--database-url", target]) == 1
    wrong = tmp_path / "wrongformat.json"
    wrong.write_text("[1, 2, 3]", encoding="utf-8")
    assert imp.main([str(wrong), "--database-url", target]) == 1
    for t in TABLES:
        assert _run(target, "select count(*) from %s" % t, fetch=True) == [(0,)], t


def test_unknown_role_in_role_permissions_rolls_back(seeded_source, make_db, tmp_path):
    path = _export(seeded_source, tmp_path)
    data = json.load(open(path, encoding="utf-8"))
    data["role_permissions"].append({"role_name": "no_such_role", "permission_name": "create_patient"})
    bad = str(tmp_path / "bad2.json")
    json.dump(data, open(bad, "w", encoding="utf-8"))
    target = make_db()
    assert imp.main([bad, "--database-url", target]) == 1
    assert _run(target, "select count(*) from examens", fetch=True) == [(0,)]


def test_inventory_lists_exams_with_counts_and_writes_no_file(seeded_source, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert exp.main(["--inventory", "--source-url", seeded_source, "--with-ranges"]) == 0
    out = capsys.readouterr().out
    assert out.isascii()
    line = [ln for ln in out.splitlines() if ln.startswith("7 ")][0]
    cells = line.split()
    assert "NFS" in cells and "3500.50" in cells
    assert cells[-3:-1] == ["2", "3"]  # 2 parametres, 3 plages
    assert "specialites" in out and "JAMAIS REPRIS" in out
    assert not list(tmp_path.iterdir())


TEST_EXAMS_SQL = """
INSERT INTO examens (id, code, nom, categorie, prix) VALUES
  (90, 'VERIFX', 'Examen de verification', 'Test', 100),
  (91, 'demo_test', 'Examen demo', 'Test', 100);
INSERT INTO parametres (id, examen_id, nom_parametre, unite, type_valeur) VALUES
  (80, 90, 'p-verifx', 'u', 'numeric'), (81, 91, 'p-demo', 'u', 'numeric');
INSERT INTO reference_ranges (id, parametre_id, sexe, age_min, age_max, valeur_min, valeur_max) VALUES
  (70, 80, 'M', 0, 120, 1, 2), (71, 81, 'F', 0, 120, 1, 2);
"""


def test_default_exclusion_cascades_and_leaves_nothing_orphaned(seeded_source, tmp_path):
    _run(seeded_source, TEST_EXAMS_SQL)
    data = json.load(open(_export(seeded_source, tmp_path), encoding="utf-8"))
    assert sorted(e["code"] for e in data["examens"]) == ["ECBU", "GLY", "NFS"]
    exam_ids = {e["id"] for e in data["examens"]}
    assert all(p["examen_id"] in exam_ids for p in data["parametres"])
    assert len(data["parametres"]) == 4
    param_ids = {p["id"] for p in data["parametres"]}
    assert all(r["parametre_id"] in param_ids for r in data["reference_ranges"])
    assert {r["id"] for r in data["reference_ranges"]} == {5, 8, 11, 12, 13}


def test_empty_exclude_codes_exports_everything(seeded_source, tmp_path):
    _run(seeded_source, TEST_EXAMS_SQL)
    data = json.load(open(_export(seeded_source, tmp_path, "--exclude-codes", ""), encoding="utf-8"))
    assert len(data["examens"]) == 5 and len(data["parametres"]) == 6 and len(data["reference_ranges"]) == 7


def test_custom_exclude_codes(seeded_source, tmp_path):
    data = json.load(open(_export(seeded_source, tmp_path, "--exclude-codes", "nfs, GLY"), encoding="utf-8"))
    assert [e["code"] for e in data["examens"]] == ["ECBU"]
    assert [p["id"] for p in data["parametres"]] == [16]
    assert data["reference_ranges"] == []


def test_ranges_not_exported_by_default(seeded_source, make_db, tmp_path, capsys):
    path = str(tmp_path / "noranges.json")
    assert exp.main([path, "--source-url", seeded_source]) == 0
    data = json.load(open(path, encoding="utf-8"))
    assert data["reference_ranges"] == [] and len(data["parametres"]) == 4
    assert exp.main(["--inventory", "--source-url", seeded_source]) == 0
    assert "NON reprises" in capsys.readouterr().out
    target = make_db()
    assert imp.main([path, "--database-url", target]) == 0
    assert _run(target, "select count(*) from reference_ranges", fetch=True) == [(0,)]
