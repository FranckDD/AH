# scripts/import_reference_data.py
"""Import des donnees de reference dans une base de production NEUVE.

    python scripts/import_reference_data.py reference_data.json --database-url URL
    (ou DATABASE_URL dans l'environnement)

Une seule transaction : tout ou rien. Refuse de s'executer (code 2, rien n'est ecrit) si l'une
des tables cibles contient deja des lignes. Met examens.prix a 0 pour TOUS les examens (decision
du proprietaire : l'admin fixe lui-meme les prix ; un article a 0 ne peut pas etre vendu).
Verifie avant de valider : nombres de lignes egaux a ceux du fichier, aucun prix non nul,
aucun parametre ou plage orphelin. Remet les sequences a max(id). Code 0 si tout est valide,
2 si refuse, 1 sur toute erreur (annulation complete).
"""
import argparse
import json
import os
import sys

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.export_reference_data import (  # noqa: E402
    FORMAT, ORG_ALLOWED, SIMPLE_TABLES, TABLE_ORDER, VERSION, mask_url,
    normalize_url,
)

# Colonne serie a remettre a max(id) apres l'import
SERIAL_COLUMNS = {
    "examens": "id", "parametres": "id", "reference_ranges": "id",
    "staff_discount_rules": "id", "permissions": "permission_id",
    "medical_specialties": "specialty_id", "organization_config": "id",
}


class ImportRefused(Exception):
    """La base cible n'est pas vide (rien n'a ete ecrit)."""


class ImportFailed(Exception):
    pass


def load_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ImportFailed("fichier illisible ou invalide (%s)" % type(exc).__name__)
    if not isinstance(data, dict):
        raise ImportFailed("fichier invalide: objet JSON attendu")
    meta = data.get("_meta") or {}
    if meta.get("format") != FORMAT or meta.get("version") != VERSION:
        raise ImportFailed("fichier invalide: format ou version inconnus")
    for table in TABLE_ORDER:
        if not isinstance(data.get(table), list):
            raise ImportFailed("fichier invalide: table '%s' absente" % table)
    return data


def _check_columns(table, row, expected):
    if not isinstance(row, dict) or set(row) != set(expected):
        raise ImportFailed("fichier invalide: colonnes inattendues dans '%s'" % table)


# Colonnes jsonb : la valeur JSON (liste) est reecrite en texte JSON pour psycopg2.
JSON_COLUMNS = {("parametres", "choices"), ("examens", "fixed_notes")}


def _value(table, col, v):
    if (table, col) in JSON_COLUMNS and v is not None:
        return json.dumps(v, ensure_ascii=False)
    return v


def _insert(cur, table, columns, rows):
    if not rows:
        return
    cols = ", ".join(columns)
    marks = ", ".join("%s::jsonb" if (table, c) in JSON_COLUMNS else "%s" for c in columns)
    sql = "INSERT INTO public.%s (%s) VALUES (%s)" % (table, cols, marks)
    for row in rows:
        cur.execute(sql, [_value(table, c, row[c]) for c in columns])


def import_data(conn, data) -> dict:
    """Importe dans la transaction ouverte de `conn` (ne commit pas). Renvoie le resume."""
    cur = conn.cursor()
    # 1. refus si une table cible contient deja des lignes
    filled = {}
    for table in TABLE_ORDER:
        cur.execute("SELECT count(*) FROM public.%s" % table)
        n = cur.fetchone()[0]
        if n:
            filled[table] = n
    if filled:
        raise ImportRefused("tables deja remplies: " + ", ".join(
            "%s=%d" % kv for kv in sorted(filled.items())))

    # 2. validation du contenu du fichier (avant toute ecriture)
    for table, (columns, _o) in SIMPLE_TABLES.items():
        for row in data[table]:
            _check_columns(table, row, columns)
    for row in data["role_permissions"]:
        _check_columns("role_permissions", row, ["role_name", "permission_name"])
    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='organization_config'")
    org_allowed = {c for (c,) in cur.fetchall()} & ORG_ALLOWED
    for row in data["organization_config"]:
        if not isinstance(row, dict) or "id" not in row or not set(row) <= org_allowed:
            raise ImportFailed("fichier invalide: colonnes inattendues dans 'organization_config'")

    # 3. insertions dans l'ordre des dependances ; tous les prix a 0
    examens = [dict(r, prix=0) for r in data["examens"]]
    _insert(cur, "examens", SIMPLE_TABLES["examens"][0], examens)
    for table in ("parametres", "reference_ranges", "prayer_book_type", "staff_discount_rules",
                  "permissions"):
        _insert(cur, table, SIMPLE_TABLES[table][0], data[table])
    for row in data["role_permissions"]:
        cur.execute(
            "INSERT INTO public.role_permissions (role_id, permission_id) "
            "SELECT r.role_id, p.permission_id FROM public.application_roles r, public.permissions p "
            "WHERE r.role_name = %s AND p.permission_name = %s",
            (row["role_name"], row["permission_name"]))
        if cur.rowcount != 1:
            raise ImportFailed("role ou permission introuvable: %s / %s"
                               % (row["role_name"], row["permission_name"]))
    _insert(cur, "medical_specialties", SIMPLE_TABLES["medical_specialties"][0],
            data["medical_specialties"])
    for row in data["organization_config"]:
        _insert(cur, "organization_config", list(row), [row])

    # 4. sequences
    for table, col in SERIAL_COLUMNS.items():
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", ("public." + table, col))
        seq = cur.fetchone()[0]
        cur.execute("SELECT max(%s) FROM public.%s" % (col, table))
        mx = cur.fetchone()[0]
        if seq and mx is not None:
            cur.execute("SELECT setval(%s, %s, true)", (seq, mx))

    # 5. verifications
    summary = {}
    for table in TABLE_ORDER:
        cur.execute("SELECT count(*) FROM public.%s" % table)
        n = cur.fetchone()[0]
        if n != len(data[table]):
            raise ImportFailed("verification: %s contient %d lignes au lieu de %d"
                               % (table, n, len(data[table])))
        summary[table] = n
    cur.execute("SELECT count(*) FROM public.examens WHERE prix <> 0 OR prix IS NULL")
    if cur.fetchone()[0] != 0:
        raise ImportFailed("verification: des examens ont un prix non nul")
    cur.execute("SELECT count(*) FROM public.parametres p LEFT JOIN public.examens e "
                "ON e.id = p.examen_id WHERE e.id IS NULL")
    orphan_p = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM public.reference_ranges r LEFT JOIN public.parametres p "
                "ON p.id = r.parametre_id WHERE p.id IS NULL")
    orphan_r = cur.fetchone()[0]
    if orphan_p or orphan_r:
        raise ImportFailed("verification: orphelins (parametres=%d, plages=%d)" % (orphan_p, orphan_r))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Import des donnees de reference (base neuve).")
    ap.add_argument("path")
    ap.add_argument("--database-url", default=None, help="base cible (defaut: DATABASE_URL)")
    args = ap.parse_args(argv)
    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERREUR: pas de base cible (DATABASE_URL ou --database-url).", file=sys.stderr)
        return 1
    try:
        data = load_file(args.path)
    except ImportFailed as exc:
        print("ERREUR: %s. Rien n'a ete ecrit." % exc, file=sys.stderr)
        return 1
    import psycopg2
    try:
        conn = psycopg2.connect(normalize_url(url))
    except Exception as exc:
        print("ERREUR: connexion impossible a %s (%s)" % (mask_url(url), type(exc).__name__),
              file=sys.stderr)
        return 1
    try:
        conn.autocommit = False
        try:
            summary = import_data(conn, data)
            conn.commit()
        except ImportRefused as exc:
            conn.rollback()
            print("REFUSE: %s. Rien n'a ete ecrit." % exc, file=sys.stderr)
            return 2
        except (ImportFailed, psycopg2.Error) as exc:
            conn.rollback()
            detail = exc if isinstance(exc, ImportFailed) else type(exc).__name__
            print("ERREUR: %s. Tout a ete annule." % detail, file=sys.stderr)
            return 1
    finally:
        conn.close()
    print("Base cible: %s" % mask_url(url))
    print("Import termine (une transaction). Prix des examens remis a 0.")
    for table in TABLE_ORDER:
        print("  %-22s %5d" % (table, summary[table]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
