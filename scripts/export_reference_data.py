# scripts/export_reference_data.py
"""Export des donnees de reference (catalogue d'examens et reglages) vers UN fichier JSON.

    python scripts/export_reference_data.py [fichier.json] [--source-url URL]
    python scripts/export_reference_data.py --inventory [--source-url URL]

Options : --exclude-codes A,B (defaut VERIFX,DEMO_TEST ; "" = ne rien exclure) retire ces examens
de test, avec leurs parametres et plages (aucune ligne orpheline). --with-ranges (defaut: non)
inclut les plages de reference ; sans lui reference_ranges est exporte vide, car les plages
validees viendront du responsable du laboratoire.

La base source est lue en transaction LECTURE SEULE (DATABASE_URL par defaut). Contenu :
examens, parametres, reference_ranges (ids conserves pour garder les liens), prayer_book_type,
staff_discount_rules (sans created_by/updated_by), permissions, role_permissions (par nom de
role et nom de permission), medical_specialties, organization_config limitee a une liste blanche de colonnes metier
(ORG_COLUMNS: nom, adresse, telephone...), donc sans logos, jeton d'impression ni colonne ajoutee
plus tard.
Jamais exporte : utilisateurs, patients, caisse, resultats de laboratoire, prescriptions,
hospitalisations, notifications, audit, notes spirituelles, stock / produits / pharmacie.

--inventory affiche un tableau lisible (ASCII) de ce qui serait repris, sans ecrire de fichier.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from decimal import Decimal

if __package__ in (None, ""):  # lance comme fichier : la racine du projet dans le chemin d'import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FORMAT = "ah2-reference-data"
VERSION = 1
DEFAULT_EXCLUDE_CODES = "VERIFX,DEMO_TEST"

# Table -> (colonnes exportees, ORDER BY). Les ids sont conserves.
SIMPLE_TABLES = {
    "examens": (["id", "code", "nom", "categorie", "prix"], "id"),
    "parametres": (["id", "examen_id", "nom_parametre", "unite", "type_valeur", "input_type",
                    "options_list", "ordre"], "id"),
    "reference_ranges": (["id", "parametre_id", "sexe", "age_min", "age_max", "valeur_min",
                          "valeur_max"], "id"),
    "prayer_book_type": (["type_code", "label"], "type_code"),
    "staff_discount_rules": (["id", "category", "min_invoice_amount", "rate_percent",
                              "is_active"], "id"),
    "permissions": (["permission_id", "permission_name", "procedure_name",
                     "description_procedure"], "permission_id"),
    "medical_specialties": (["specialty_id", "name"], "specialty_id"),
}
# organization_config : LISTE BLANCHE des colonnes metier reprises (plus "id"). Une colonne ajoutee
# plus tard n'est PAS exportee tant qu'on ne l'ajoute pas ici (jamais de logo, jeton ni secret).
ORG_COLUMNS = ["name", "slogan", "address", "city", "po_box", "phone", "phone2", "email",
               "website", "niu", "rccm", "legal_info", "label_width_mm", "label_height_mm"]
ORG_ALLOWED = {"id"} | set(ORG_COLUMNS)

# Ordre de dependance pour l'import
TABLE_ORDER = ["examens", "parametres", "reference_ranges", "prayer_book_type",
               "staff_discount_rules", "permissions", "role_permissions",
               "medical_specialties", "organization_config"]


def normalize_url(url: str) -> str:
    """Retire le suffixe de pilote SQLAlchemy (postgresql+psycopg2://) pour psycopg2."""
    return re.sub(r"^postgres(?:ql)?\+[a-z0-9_]+://", "postgresql://", url or "")


def mask_url(url: str) -> str:
    return re.sub(r"(://[^:/@]*):[^@]*@", r"\1:***@", url or "")


def _jsonable(v):
    if isinstance(v, Decimal):
        return str(v)  # exact, repris tel quel a l'import
    return v


def _select(cur, table, columns, order_by):
    cols = ", ".join(columns)
    cur.execute(f"SELECT {cols} FROM public.{table} ORDER BY {order_by}")
    return [{c: _jsonable(v) for c, v in zip(columns, row)} for row in cur.fetchall()]


def parse_codes(raw) -> set:
    return {c.strip().upper() for c in (raw or "").split(",") if c.strip()}


def export_data(conn, exclude_codes=(), with_ranges=False) -> dict:
    """Lit la base (la connexion doit etre en lecture seule) et renvoie le dictionnaire exportable.

    exclude_codes : codes d'examens de test a retirer (parametres et plages en cascade).
    with_ranges : sinon reference_ranges est vide (plages validees fournies plus tard)."""
    out = {"_meta": {"format": FORMAT, "version": VERSION}}
    with conn.cursor() as cur:
        for table, (columns, order_by) in SIMPLE_TABLES.items():
            out[table] = _select(cur, table, columns, order_by)
        cur.execute(
            "SELECT r.role_name, p.permission_name FROM public.role_permissions rp "
            "JOIN public.application_roles r ON r.role_id = rp.role_id "
            "JOIN public.permissions p ON p.permission_id = rp.permission_id "
            "ORDER BY r.role_name, p.permission_name")
        excl = {str(c).strip().upper() for c in exclude_codes}
        if excl:
            gone = {e["id"] for e in out["examens"] if (e["code"] or "").strip().upper() in excl}
            out["examens"] = [e for e in out["examens"] if e["id"] not in gone]
            out["parametres"] = [p for p in out["parametres"] if p["examen_id"] not in gone]
        kept_params = {p["id"] for p in out["parametres"]}
        out["reference_ranges"] = ([r for r in out["reference_ranges"] if r["parametre_id"] in kept_params]
                                   if with_ranges else [])
        out["role_permissions"] = [{"role_name": a, "permission_name": b} for a, b in cur.fetchall()]
        cur.execute("SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='organization_config' "
                    "ORDER BY ordinal_position")
        present = {c for (c,) in cur.fetchall()}
        org_cols = ["id"] + [c for c in ORG_COLUMNS if c in present]
        out["organization_config"] = _select(cur, "organization_config", org_cols, "id")
    return out


def _ascii(s) -> str:
    s = "" if s is None else str(s)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def inventory_text(data: dict) -> str:
    """Tableau lisible (ASCII) de ce qui est repris, pour validation par le proprietaire."""
    params_by_exam, ranges_by_param = {}, {}
    for p in data["parametres"]:
        params_by_exam.setdefault(p["examen_id"], []).append(p["id"])
    for r in data["reference_ranges"]:
        ranges_by_param[r["parametre_id"]] = ranges_by_param.get(r["parametre_id"], 0) + 1
    lines = []
    lines.append("INVENTAIRE DES DONNEES DE REFERENCE (a valider avant la mise en production)")
    lines.append("")
    lines.append("EXAMENS (%d). Tous les prix seront remis a 0 a l'import: l'admin les fixe lui-meme."
                 % len(data["examens"]))
    head = "%-4s %-12s %-44s %-16s %6s %7s %10s" % (
        "id", "code", "nom", "categorie", "param.", "plages", "prix actuel")
    lines.append(head)
    lines.append("-" * len(head))
    for e in data["examens"]:
        pids = params_by_exam.get(e["id"], [])
        nb_ranges = sum(ranges_by_param.get(pid, 0) for pid in pids)
        prix = "" if e["prix"] is None else str(e["prix"])
        lines.append("%-4s %-12s %-44s %-16s %6d %7d %10s" % (
            e["id"], _ascii(e["code"])[:12], _ascii(e["nom"])[:44], _ascii(e["categorie"])[:16],
            len(pids), nb_ranges, prix))
    lines.append("")
    lines.append("AUTRES TABLES REPRISES")
    labels = [
        ("parametres", "parametres d'examen (total)"),
        ("reference_ranges", "plages de reference (total)"),
        ("prayer_book_type", "types de carnet de priere"),
        ("staff_discount_rules", "regles de reduction du personnel"),
        ("permissions", "permissions"),
        ("role_permissions", "liens role-permission"),
        ("medical_specialties", "specialites medicales"),
        ("organization_config", "configuration de l'organisation (sans logos ni jeton)"),
    ]
    for key, label in labels:
        lines.append("  %-58s %5d" % (label, len(data[key])))
    lines.append("")
    lines.append("Details:")
    for r in data["prayer_book_type"]:
        lines.append("  carnet de priere : %s = %s" % (_ascii(r["type_code"]), _ascii(r["label"])))
    for r in data["staff_discount_rules"]:
        lines.append("  reduction personnel : %s, %s%% des %s FCFA, %s" % (
            _ascii(r["category"]), r["rate_percent"], r["min_invoice_amount"],
            "active" if r["is_active"] else "inactive"))
    lines.append("  specialites : " + ", ".join(_ascii(r["name"]) for r in data["medical_specialties"]))
    for r in data["organization_config"]:
        lines.append("  organisation : %s (%s)" % (_ascii(r.get("name")), _ascii(r.get("city"))))
    lines.append("")
    if not data["reference_ranges"]:
        lines.append("Plages de reference: NON reprises (a fournir par le responsable du laboratoire).")
        lines.append("")
    lines.append("JAMAIS REPRIS: utilisateurs, patients, caisse, resultats de laboratoire, prescriptions,")
    lines.append("hospitalisations, notifications, audit, notes spirituelles, stock, produits et pharmacie.")
    lines.append("")
    return "\n".join(lines)


def connect_readonly(url: str):
    import psycopg2
    conn = psycopg2.connect(normalize_url(url))
    conn.set_session(isolation_level="REPEATABLE READ", readonly=True, autocommit=False)
    return conn


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export des donnees de reference en JSON.")
    ap.add_argument("path", nargs="?", default="reference_data.json")
    ap.add_argument("--source-url", default=None, help="base source (defaut: DATABASE_URL)")
    ap.add_argument("--exclude-codes", default=DEFAULT_EXCLUDE_CODES,
                    help="codes d'examens de test a exclure, separes par des virgules "
                         "(defaut: %s ; vide = tout exporter)" % DEFAULT_EXCLUDE_CODES)
    ap.add_argument("--with-ranges", action="store_true",
                    help="inclure reference_ranges (defaut: non, plages a fournir par le labo)")
    ap.add_argument("--inventory", action="store_true",
                    help="afficher l'inventaire lisible au lieu d'ecrire le fichier")
    args = ap.parse_args(argv)
    url = args.source_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERREUR: pas de base source (DATABASE_URL ou --source-url).", file=sys.stderr)
        return 1
    try:
        conn = connect_readonly(url)
    except Exception as exc:
        print("ERREUR: connexion impossible a %s (%s)" % (mask_url(url), type(exc).__name__),
              file=sys.stderr)
        return 1
    try:
        data = export_data(conn, parse_codes(args.exclude_codes), args.with_ranges)
    finally:
        conn.rollback()
        conn.close()
    if args.inventory:
        sys.stdout.write(inventory_text(data))
        return 0
    with open(args.path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("Export ecrit: %s (%s)" % (args.path, ", ".join(
        "%s=%d" % (t, len(data[t])) for t in TABLE_ORDER)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
