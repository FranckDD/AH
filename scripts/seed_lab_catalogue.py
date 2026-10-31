# scripts/seed_lab_catalogue.py
"""Aligne le catalogue du laboratoire sur les fiches du laboratoire (upsert idempotent).

    python scripts/seed_lab_catalogue.py [--database-url URL] [--data FICHIER] [--dry-run] [--replace-ranges]

Source de verite : scripts/data/lab_catalogue.json (decrit dans docs/laboratory-templates.md).

- Examen trouve par code (sinon par nom normalise) : section, methode, famille, signature, titre
  imprime et ordre sont alignes. Le nom, la categorie et le PRIX ne changent jamais.
- Examen absent : cree avec prix 0 (l'admin fixe le prix).
- Parametre trouve par nom normalise (nom actuel, nom de la fiche, anciens noms listes dans "match",
  ou libelle imprime) : libelle imprime, unite, type de resultat, choix, ordre alignes ; nom_parametre
  n'est pas renomme ; type_valeur / input_type / options_list suivent le type de resultat.
  Parametre absent : cree. Un parametre de l'examen absent du fichier n'est jamais supprime :
  il passe apres les autres, et il est desactive s'il est liste dans "deactivate".
- Textes imprimes (migration 045) : sous-titre ("group" -> parametres.group_label), texte de norme
  ("norm_text" -> parametres.norm_text), texte de chaque plage ("display_text" -> reference_ranges.display_text,
  aussi pour les plages deja en base) et notes fixes de l'examen ("fixed_notes" -> examens.fixed_notes) sont
  alignes a chaque passage ; un texte absent du fichier vide la colonne (NULL).
- Plages : ecrites seulement si la table reference_ranges est vide, ou avec --replace-ranges
  (toutes les plages existantes sont alors remplacees par celles du fichier). Sinon inchangees.
- --dry-run : tout est calcule dans une transaction annulee ; rien n'est ecrit.
Aucun lien lab_results / lab_result_details n'est modifie (aucune suppression d'examen ou de parametre).
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from decimal import Decimal

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA = os.path.join(ROOT, "scripts", "data", "lab_catalogue.json")
FAMILIES = {"table", "three_columns", "label_value", "narrative", "boxed"}
KINDS = {"numeric", "text", "choice", "pos_neg"}
# Limites des textes imprimes (identiques a celles de l'API du catalogue et aux CHECK de la migration 045).
MAX_GROUP, MAX_NORM_TEXT, MAX_DISPLAY_TEXT, MAX_NOTE_TEXT, MAX_NOTES = 80, 200, 60, 1000, 12
NOTE_POSITIONS = ("before_body", "after_body", "after_conclusion")
NOTE_STYLES = ("normal", "bold", "italic")


def norm(s) -> str:
    """Nom normalise : minuscules, sans accent, seulement lettres et chiffres."""
    s = str(s or "").replace("%", " pct ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def load_catalogue(path=DEFAULT_DATA) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if (data.get("_meta") or {}).get("format") != "ah2-lab-catalogue":
        raise ValueError("fichier de catalogue invalide")
    for e in data["exams"]:
        if e["layout_family"] not in FAMILIES:
            raise ValueError("famille inconnue: %s" % e["code"])
        for p in e["parameters"]:
            if p["result_kind"] not in KINDS:
                raise ValueError("type inconnu: %s / %s" % (e["code"], p["name"]))
            if len(p.get("group") or "") > MAX_GROUP or len(p.get("norm_text") or "") > MAX_NORM_TEXT:
                raise ValueError("texte trop long: %s / %s" % (e["code"], p["name"]))
            for r in p.get("ranges") or []:
                if len(r.get("display_text") or "") > MAX_DISPLAY_TEXT:
                    raise ValueError("texte de plage trop long: %s / %s" % (e["code"], p["name"]))
        notes = e.get("fixed_notes") or []
        if len(notes) > MAX_NOTES:
            raise ValueError("trop de notes fixes: %s" % e["code"])
        for n in notes:
            if (n.get("position") not in NOTE_POSITIONS or n.get("style") not in NOTE_STYLES
                    or not str(n.get("text") or "").strip() or len(n["text"]) > MAX_NOTE_TEXT):
                raise ValueError("note fixe invalide: %s" % e["code"])
    return data


def input_columns(kind, choices):
    """(type_valeur, input_type, options_list) attendus par le banc de saisie actuel."""
    if kind == "numeric":
        return "numeric", "numeric", None
    if kind in ("choice", "pos_neg"):
        return "text", "select", ",".join(choices or [])
    return "text", "text", None


def _dec(v):
    return None if v is None else Decimal(str(v))


def _text(v):
    """Texte facultatif : vide -> None."""
    v = v.strip() if isinstance(v, str) else v
    return v or None


def _notes_json(notes):
    """Liste de notes fixes -> jsonb (None si vide). Seules les cles position / text / style sont gardees."""
    clean = [{"position": n["position"], "text": n["text"], "style": n["style"]} for n in notes or []]
    return json.dumps(clean, ensure_ascii=False) if clean else None


def seed(conn, data, replace_ranges=False) -> dict:
    """Applique le catalogue dans la transaction ouverte de `conn` (ne commit pas). Renvoie le resume."""
    cur = conn.cursor()
    s = {"exams_added": [], "exams_updated": 0, "params_added": 0, "params_updated": 0,
         "params_deactivated": 0, "ranges_written": 0, "ranges_deleted": 0, "ranges_mode": "unchanged",
         "range_texts": 0, "notes_exams": 0}
    cur.execute("SELECT id, code, nom FROM public.examens")
    by_code, by_name = {}, {}
    for eid, code, nom in cur.fetchall():
        by_code[(code or "").strip().upper()] = eid
        by_name.setdefault(norm(nom), eid)

    param_ids = {}  # (code, name) -> parametre id
    for e in data["exams"]:
        eid = by_code.get(e["code"].upper())
        if eid is None:
            for n in [e["nom"]] + list(e.get("match_names") or []):
                eid = by_name.get(norm(n))
                if eid:
                    break
        vals = (e.get("section"), e.get("method"), e["layout_family"], e.get("signature_label"),
                e.get("print_title"), int(e.get("sort_order") or 0), _notes_json(e.get("fixed_notes")))
        s["notes_exams"] += int(vals[-1] is not None)
        if eid is None:
            cur.execute(
                "INSERT INTO public.examens (code, nom, categorie, prix, section, method, layout_family, "
                "signature_label, print_title, sort_order, fixed_notes, is_active) "
                "VALUES (%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s::jsonb,true) "
                "RETURNING id", (e["code"], e["nom"], e["categorie"]) + vals)
            eid = cur.fetchone()[0]
            by_code[e["code"].upper()] = eid
            s["exams_added"].append(e["code"])
        else:
            cur.execute(
                "UPDATE public.examens SET section=%s, method=%s, layout_family=%s, signature_label=%s, "
                "print_title=%s, sort_order=%s, fixed_notes=%s::jsonb WHERE id=%s", vals + (eid,))
            s["exams_updated"] += 1

        cur.execute("SELECT id, nom_parametre, print_label, ordre FROM public.parametres "
                    "WHERE examen_id=%s ORDER BY ordre, id", (eid,))
        existing = cur.fetchall()
        # Appariement en deux passes : d'abord le nom de la fiche, puis les anciens noms ("match").
        assigned, used = {}, set()
        for use_match in (False, True):
            for p in e["parameters"]:
                if p["name"] in assigned:
                    continue
                keys = [norm(m) for m in p.get("match") or []] if use_match else [norm(p["name"])]
                for k in keys:
                    hit = next((xid for (xid, xname, _l, _o) in existing
                                if xid not in used and norm(xname) == k), None)
                    if hit:
                        assigned[p["name"]] = hit
                        used.add(hit)
                        break
        for i, p in enumerate(e["parameters"], start=1):
            pid = assigned.get(p["name"])
            tv, it, ol = input_columns(p["result_kind"], p.get("choices"))
            choices = json.dumps(p["choices"], ensure_ascii=False) if p.get("choices") is not None else None
            if pid is None:
                cur.execute(
                    "INSERT INTO public.parametres (examen_id, nom_parametre, unite, type_valeur, input_type, "
                    "options_list, ordre, print_label, result_kind, choices, group_label, norm_text, is_active) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,true) RETURNING id",
                    (eid, p["name"], p.get("unite") or "", tv, it, ol, i, p["print_label"], p["result_kind"], choices,
                     _text(p.get("group")), _text(p.get("norm_text"))))
                pid = cur.fetchone()[0]
                s["params_added"] += 1
            else:
                cur.execute(
                    "UPDATE public.parametres SET unite=%s, type_valeur=%s, input_type=%s, options_list=%s, "
                    "ordre=%s, print_label=%s, result_kind=%s, choices=%s::jsonb, group_label=%s, norm_text=%s, "
                    "is_active=true WHERE id=%s",
                    (p.get("unite") or "", tv, it, ol, i, p["print_label"], p["result_kind"], choices,
                     _text(p.get("group")), _text(p.get("norm_text")), pid))
                s["params_updated"] += 1
            param_ids[(e["code"], p["name"])] = pid
        deact = {norm(n) for n in e.get("deactivate") or []}
        nxt = len(e["parameters"])
        for (xid, xname, _l, _o) in existing:
            if xid in used:
                continue
            nxt += 1
            off = norm(xname) in deact
            cur.execute("UPDATE public.parametres SET ordre=%s, is_active = CASE WHEN %s THEN false ELSE is_active END "
                        "WHERE id=%s", (nxt, off, xid))
            s["params_deactivated"] += int(off)

    cur.execute("SELECT count(*) FROM public.reference_ranges")
    n_ranges = cur.fetchone()[0]
    if n_ranges == 0 or replace_ranges:
        if n_ranges:
            cur.execute("DELETE FROM public.reference_ranges")
            s["ranges_deleted"] = n_ranges
        s["ranges_mode"] = "replaced" if n_ranges else "loaded"
        for e in data["exams"]:
            for p in e["parameters"]:
                for r in p.get("ranges") or []:
                    cur.execute(
                        "INSERT INTO public.reference_ranges (parametre_id, sexe, age_min_days, age_max_days, "
                        "ga_min_weeks, ga_max_weeks, valeur_min, valeur_max, display_text) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (param_ids[(e["code"], p["name"])], r.get("sexe") or "X",
                         0 if r.get("age_min_days") is None and r.get("age_max_days") is not None else r.get("age_min_days"),
                         r.get("age_max_days"), r.get("ga_min_weeks"), r.get("ga_max_weeks"),
                         _dec(r["min"]), _dec(r["max"]), _text(r.get("display_text"))))
                    s["ranges_written"] += 1
                    s["range_texts"] += int(_text(r.get("display_text")) is not None)
    else:
        # plages conservees : seul le texte imprime est aligne (meme parametre, criteres et bornes)
        for e in data["exams"]:
            for p in e["parameters"]:
                for r in p.get("ranges") or []:
                    cur.execute(
                        "UPDATE public.reference_ranges SET display_text=%s WHERE parametre_id=%s AND sexe=%s "
                        "AND age_min_days IS NOT DISTINCT FROM %s AND age_max_days IS NOT DISTINCT FROM %s "
                        "AND ga_min_weeks IS NOT DISTINCT FROM %s AND ga_max_weeks IS NOT DISTINCT FROM %s "
                        "AND valeur_min=%s AND valeur_max=%s AND display_text IS DISTINCT FROM %s",
                        (_text(r.get("display_text")), param_ids[(e["code"], p["name"])], r.get("sexe") or "X",
                         0 if r.get("age_min_days") is None and r.get("age_max_days") is not None else r.get("age_min_days"),
                         r.get("age_max_days"), r.get("ga_min_weeks"), r.get("ga_max_weeks"),
                         _dec(r["min"]), _dec(r["max"]), _text(r.get("display_text"))))
                    s["range_texts"] += cur.rowcount
    return s


def summary_text(s, dry_run) -> str:
    lines = ["Catalogue du laboratoire%s" % (" (ESSAI, rien n'est ecrit)" if dry_run else "")]
    lines.append("  examens ajoutes      : %d %s" % (len(s["exams_added"]), ", ".join(s["exams_added"])))
    lines.append("  examens alignes      : %d" % s["exams_updated"])
    lines.append("  parametres ajoutes   : %d" % s["params_added"])
    lines.append("  parametres alignes   : %d" % s["params_updated"])
    lines.append("  parametres desactives: %d" % s["params_deactivated"])
    lines.append("  plages               : %s (ecrites %d, supprimees %d)" % (
        s["ranges_mode"], s["ranges_written"], s["ranges_deleted"]))
    lines.append("  textes de plage      : %d" % s["range_texts"])
    lines.append("  examens avec notes   : %d" % s["notes_exams"])
    return "\n".join(lines)


def _database_url(arg):
    url = arg or os.environ.get("DATABASE_URL")
    if not url:
        from api_backend.backend_app.config import DATABASE_URL
        url = DATABASE_URL
    return re.sub(r"^postgres(?:ql)?\+[a-z0-9_]+://", "postgresql://", url or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aligne le catalogue du laboratoire sur les fiches.")
    ap.add_argument("--database-url", default=None)
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--replace-ranges", action="store_true",
                    help="remplacer toutes les plages existantes par celles du fichier")
    args = ap.parse_args(argv)
    try:
        data = load_catalogue(args.data)
    except (OSError, ValueError, KeyError) as exc:
        print("ERREUR: %s" % exc, file=sys.stderr)
        return 1
    import psycopg2
    conn = psycopg2.connect(_database_url(args.database_url))
    try:
        conn.autocommit = False
        try:
            s = seed(conn, data, replace_ranges=args.replace_ranges)
        except Exception:
            conn.rollback()
            raise
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()
    print(summary_text(s, args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
