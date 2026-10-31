# api_backend/backend_app/utils/lab_sheet.py
"""Fiche de resultats du laboratoire (PDF Lettre US) rendue a partir de la copie figee
(`lab_results.print_snapshot`, versions 1 et 2 ; voir utils/lab_snapshot.py pour le schema).

Cadre commun : lab_sheet_base.html + lab_sheet.css. Chaque famille de mise en page (table,
three_columns, label_value, narrative, boxed) est un gabarit qui etend la base et remplit le
bloc `body`; elle s'enregistre dans FAMILY_TEMPLATES (D2 ajoute les autres familles ici).
"""
import os
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, Optional

from markupsafe import Markup, escape

from .pdf_generator import render_pdf_from_template

SUPPORTED_SNAPSHOT_VERSIONS = (1, 2)

DEFAULT_TITLE = "RESULTATS D'ANALYSES DE BIOLOGIE CLINIQUE"
DEFAULT_SIGNATURE_LABEL = "Le Biologiste"
DEFAULT_CITY = "Yaoundé"
DEFAULT_FAMILY = "label_value"

# famille -> gabarit (dossier utils/templates).
FAMILY_TEMPLATES: Dict[str, str] = {
    "label_value": "lab_sheet_label_value.html",
    "table": "lab_sheet_table.html",
    "three_columns": "lab_sheet_three_columns.html",
    "narrative": "lab_sheet_narrative.html",
    "boxed": "lab_sheet_boxed.html",
}

# Titre au singulier du formulaire en cases (Chlamydiae), quand le contexte n'impose pas de titre.
BOXED_DEFAULT_TITLE = "RESULTAT D'ANALYSE DE BIOLOGIE CLINIQUE"

# Bornes pediatriques retenues (spec, question 4) : nouveau-ne <= 28 jours, enfant < 5 ans.
NEWBORN_MAX_DAYS = 28
CHILD_MAX_DAYS = 1825

# Au-dela de ce nombre de parametres, la fiche passe en mise en page serree (spermogramme : 61).
DENSE_PARAMETER_COUNT = 30

_NUMBER_RE = re.compile(r"^\s*-?\d+\.\d+\s*$")
_TIME_SUFFIX_RE = re.compile(r"^(.*\S)\s+(\d+H)$")
_POS_RE = re.compile(r"^(\s*)positi(f|ve|fs|ves)\b", re.IGNORECASE)
_NEG_RE = re.compile(r"^(\s*)n[ée]gati(f|ve|fs|ves)\b", re.IGNORECASE)
_SUP_RE = re.compile(r"\^(\d+)")
_CUBE_RE = re.compile(r"(mm|cm|dm|m)([23])(?![0-9])")


def _comma(value_text: str) -> str:
    """`0.95` -> `0,95` (separateur decimal des fiches) ; tout autre texte est rendu tel quel."""
    if value_text and _NUMBER_RE.match(value_text):
        return value_text.strip().replace(".", ",")
    return value_text


def _upper_pos_neg(text: str) -> str:
    """Valeur qui COMMENCE par positif / negatif : ce mot en capitales comme sur les fiches
    (« Négatif » -> NEGATIF, « Positif (+ 0,3g/L) » -> POSITIF (+ 0,3g/L)) ; un mot au milieu d'une
    phrase (« Bacilles gram négatif », « Sérologie faiblement positive ») reste tel quel."""
    if not text:
        return text
    text = _POS_RE.sub(lambda m: m.group(1) + "POSITI" + m.group(2).upper(), text)
    return _NEG_RE.sub(lambda m: m.group(1) + "NEGATI" + m.group(2).upper(), text)


def display_value(value_text: Any) -> str:
    text = "" if value_text is None else str(value_text)
    return _upper_pos_neg(_comma(text))


def _num_text(v: Any) -> str:
    s = format(Decimal(str(v)).normalize(), "f")
    return s.replace(".", ",")


def _mechanical_norm_text(norm: dict) -> Optional[str]:
    lo, hi = norm.get("min"), norm.get("max")
    if lo is None or hi is None:
        return None
    return f"{_num_text(lo)} - {_num_text(hi)}".replace(",", ".")


def display_norm(param: dict, unit_in_norm: bool = False) -> str:
    """Norme telle que la fiche l'imprime, lue dans la copie seulement.

    Priorite : `norm_text` du parametre (texte imprime du catalogue, tel quel), puis (copie v2) TOUTES les
    normes du laboratoire pour le parametre (`norms`), puis (copie v1) la seule `norm` choisie. Une norme
    s'imprime avec son texte `text` quand ce n'est pas la simple forme « min - max » calculee par la copie
    (zeros de precision, seuils), sinon en forme composee : prefixe sexe (« H: » / « F: ») ou age
    (« Nouveau-né: » / « Enfant: » / « Adulte: »), seuil « < max » quand la borne basse est 0, « > min »
    sans borne haute, virgule decimale."""
    if param.get("norm_text"):
        return str(param["norm_text"])
    norms = [n for n in (param.get("norms") or []) if n]
    if norms:
        return _join_norms(norms, param.get("unit") or "", unit_in_norm)
    norm = param.get("norm") or None
    if not norm:
        return ""
    return _one_norm(norm, param.get("unit") or "", unit_in_norm, decorate=False)


def _norm_order(n: dict):
    has_age = n.get("age_min_days") is not None or n.get("age_max_days") is not None
    sex_rank = {"M": 0, "F": 1}.get((n.get("sex") or "X").upper(), 2)
    if not has_age:
        return (0, 0, 0, sex_rank)
    # tranches d'age : adulte d'abord, puis enfant, puis nouveau-ne (comme les fiches)
    amax = n.get("age_max_days") if n.get("age_max_days") is not None else 10 ** 9
    amin = n.get("age_min_days") if n.get("age_min_days") is not None else 0
    return (1, -amax, -amin, sex_rank)


def _join_norms(norms: list, unit: str, unit_in_norm: bool) -> str:
    """Toutes les normes comme sur les fiches : sexes cote a cote (« H: 4,0 - 5,5 F: 4,0 - 5,0 »), puis
    une norme par tranche d'age separee par « / » (« ADULTE ... / Enfant ... »)."""
    ordered = sorted(norms, key=_norm_order)
    parts = [_one_norm(n, unit, unit_in_norm, decorate=True) for n in ordered]
    sex_only = [p for n, p in zip(ordered, parts)
                if n.get("age_min_days") is None and n.get("age_max_days") is None]
    aged = [p for n, p in zip(ordered, parts)
            if n.get("age_min_days") is not None or n.get("age_max_days") is not None]
    blocks = ([" ".join(sex_only)] if sex_only else []) + aged
    return " / ".join(b for b in blocks if b)


def _one_norm(norm: dict, unit: str, unit_in_norm: bool, decorate: bool) -> str:
    """Une norme. `decorate` (copie v2, toutes les normes) : le texte imprime de la plage est complete du
    prefixe sexe / age et de l'unite ; sinon (copie v1) un texte saisi a la main est rendu tel quel."""
    text = norm.get("text")
    lo, hi = norm.get("min"), norm.get("max")
    if text and text.strip() and text.strip().replace(",", ".") != (_mechanical_norm_text(norm) or ""):
        if not decorate:
            return str(text)
        core = str(text).strip()
    elif lo is None and hi is None:
        return str(text or "")
    elif hi is None:
        core = f"> {_num_text(lo)}"
    elif lo is None or float(lo) == 0:
        core = f"< {_num_text(hi)}"
    else:
        core = f"{_num_text(lo)} - {_num_text(hi)}"
    if unit_in_norm and unit:
        core = f"{core} {unit}"
    prefix = ""
    amax = norm.get("age_max_days")
    amin = norm.get("age_min_days")
    sex = (norm.get("sex") or "X").upper()
    if amin is not None and int(amin) > CHILD_MAX_DAYS and sex not in ("M", "F"):
        prefix = "Adulte: "
    elif amax is not None and int(amax) <= NEWBORN_MAX_DAYS:
        prefix = "Nouveau-né: "
    elif amax is not None and int(amax) <= CHILD_MAX_DAYS:
        prefix = "Enfant: "
    elif sex == "M":
        prefix = "H: "
    elif sex == "F":
        prefix = "F: "
    return prefix + core


def unit_html(unit: Any) -> Markup:
    """Unite echappee, puissances en exposant (`x10^6/mm3` -> x10<sup>6</sup>/mm<sup>3</sup>)."""
    escaped = str(escape(unit or ""))
    escaped = _SUP_RE.sub(r"<sup>\1</sup>", escaped)
    escaped = _CUBE_RE.sub(r"\1<sup>\2</sup>", escaped)
    return Markup(escaped)


_PAREN_NORM_RE = re.compile(r"^\s*(\(|v\.?\s?n(?![a-z]))", re.IGNORECASE)


def paren_norm(norm: str) -> str:
    """Norme entre parentheses pour la famille « Libelle : valeur » : un texte deja entre parentheses ou
    commencant par « VN » / « V.N. » est garde tel quel (entoure de parentheses si besoin), sinon « (V.N. ... ) »."""
    if not norm:
        return ""
    text = norm.strip()
    if text.startswith("("):
        return text
    if _PAREN_NORM_RE.match(text):
        return f"({text})"
    return f"(V.N. {text})"


NOTE_POSITIONS = ("before_body", "after_body", "after_conclusion")
NOTE_STYLES = ("normal", "bold", "italic")


def _plain(text: Any) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return text.lower()


def _chosen_notes(notes: list, rows: list) -> set:
    """Formulaire en cases : si un parametre « Validation » a une valeur, la note du texte fixe qui la porte
    (« Sérologie faiblement positif. » pour « Sérologie faiblement positive ») est marquee en gras.
    Rapprochement par la racine du mot le plus long de la valeur (hors « serologie »)."""
    validation = next((r for r in rows if r["label"] == "Validation" and r["value"]), None)
    if not validation:
        return set()
    words = [w for w in re.findall(r"[a-z]+", _plain(validation["value"])) if w != "serologie"]
    if not words:
        return set()
    stem = max(words, key=len)[:6]
    return {i for i, n in enumerate(notes) if stem in _plain(n["text"]) and " : " in n["text"]}


def _notes_html(fixed_notes: Any, rows: list, family: Optional[str]) -> Dict[str, Markup]:
    """Notes fixes de l'examen (copie v2) -> HTML par position ; texte echappe, jamais interprete."""
    notes = [n for n in (fixed_notes or [])
             if isinstance(n, dict) and str(n.get("text") or "").strip()]
    chosen = _chosen_notes(notes, rows) if family == "boxed" else set()
    out: Dict[str, list] = {pos: [] for pos in NOTE_POSITIONS}
    for i, n in enumerate(notes):
        pos = n.get("position") if n.get("position") in NOTE_POSITIONS else "after_body"
        style = n.get("style") if n.get("style") in NOTE_STYLES else "normal"
        cls = f"fixed-note {style}" + (" chosen" if i in chosen else "")
        out[pos].append(f'<p class="{cls}">{escape(str(n["text"]))}</p>')
    return {pos: Markup("".join(items)) for pos, items in out.items()}


def _row(p: dict, unit_in_norm: bool) -> Dict[str, Any]:
    norm = display_norm(p, unit_in_norm=unit_in_norm)
    return {
        "label": p.get("label") or "",
        "value": display_value(p.get("value_text")),
        "unit": p.get("unit") or "",
        "unit_html": unit_html(p.get("unit")),
        "norm": norm,
        "norm_paren": paren_norm(norm),
        "flagged": bool(p.get("flagged")),
        "kind": p.get("kind") or "numeric",
        "group": p.get("group") or None,
        "multiline": "\n" in (p.get("value_text") or "") or len(p.get("value_text") or "") > 70,
    }


def _groups(rows):
    """Lignes consecutives de meme groupe -> [{title, rows}] (titre None = sans sous-titre)."""
    out = []
    for r in rows:
        if not out or out[-1]["title"] != r["group"]:
            out.append({"title": r["group"], "rows": []})
        out[-1]["rows"].append(r)
    return out


def _table_blocks(group: dict) -> list:
    """Decoupe un groupe de la famille tableau en blocs :
    - `matrix` : libelles finissant par un temps (« Immobiles 0H ») -> tableau libelle x temps ;
    - `vam` : paires « - X » / « V.A.M. X » -> tableau a 5 colonnes de la formule sanguine ;
    - `rows` : lignes ordinaires libelle / resultat / norme ;
    - `lines` : groupe sans aucune norme -> lignes « Libelle : valeur »."""
    rows = group["rows"]
    blocks: list = []

    def push(kind, item):
        if not blocks or blocks[-1]["kind"] != kind:
            blocks.append({"kind": kind, "items": [], "times": []})
        blocks[-1]["items"].append(item)
        return blocks[-1]

    has_norm = any(r["norm"] for r in rows)
    i = 0
    while i < len(rows):
        r = rows[i]
        m = _TIME_SUFFIX_RE.match(r["label"])
        if m:
            block = blocks[-1] if blocks and blocks[-1]["kind"] == "matrix" else None
            if block is None:
                block = push("matrix", {"label": m.group(1), "cells": {}})
            elif block["items"][-1]["label"] != m.group(1):
                block["items"].append({"label": m.group(1), "cells": {}})
            if m.group(2) not in block["times"]:
                block["times"].append(m.group(2))
            block["items"][-1]["cells"][m.group(2)] = r
            i += 1
            continue
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        base = r["label"].lstrip("- ").strip()
        if nxt and nxt["label"].startswith("V.A.M.") and nxt["label"][6:].strip() == base:
            push("vam", {"pct": r, "abs": nxt})
            i += 2
            continue
        push("rows" if has_norm else "lines", r)
        i += 1
    return blocks

# Mois en capitales sans accent, comme les fiches du laboratoire (« 08 OCTOBRE 2026 »).
MONTHS_FR = ("JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOUT",
             "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE")

PREGNANCY_LABELS = {"enceinte": "Enceinte", "non_enceinte": "Non enceinte", "inconnu": "Inconnu"}

_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "lab_sheet.css")


class UnknownSnapshotVersionError(ValueError):
    """La copie figee a une version que ce rendu ne sait pas lire."""


def format_date_letters(value) -> str:
    """`date(2026, 10, 8)` -> `08 OCTOBRE 2026` (jour a 2 chiffres, mois en lettres capitales)."""
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        raise TypeError("format_date_letters attend une date")
    return f"{value.day:02d} {MONTHS_FR[value.month - 1]} {value.year}"


class _HeaderWithoutFooter:
    """Enveloppe de la structure pour le partiel d'en-tete: meme valeurs, sans footer_text
    (la fiche l'imprime en bas de page, pas sous l'en-tete)."""

    def __init__(self, structure):
        self._structure = structure

    def __getattr__(self, name):
        if name == "footer_text":
            return None
        return getattr(self._structure, name, None)

    def __bool__(self):
        return bool(self._structure)


def _pregnancy_line(pregnancy: Optional[dict]) -> Optional[str]:
    if not pregnancy:
        return None
    status = pregnancy.get("status_at_result")
    weeks = pregnancy.get("gestational_age_weeks")
    parts = []
    if status:
        parts.append(PREGNANCY_LABELS.get(status, str(status)))
    if weeks is not None:
        parts.append(f"{weeks} SA")
    return " - ".join(parts) if parts else None


def _dossier_label(snapshot: dict, context: dict) -> Optional[str]:
    if context.get("dossier_label"):
        return context["dossier_label"]
    dossier = snapshot.get("dossier")
    day = context.get("dossier_day")
    if not dossier or not day:
        return None
    from utils.lab_dossier import DossierNumber, format_dossier
    return format_dossier(DossierNumber(dossier["year"], dossier["counter"], dossier["rank"]), day)


def render_lab_sheet(snapshot: dict, patient: dict, context: dict, *, show_pregnancy: bool) -> bytes:
    """PDF d'une fiche (Lettre US) a partir de la copie figee.

    snapshot: JSON de lab_results.print_snapshot (version 1 ou 2).
    patient: {"name": str, "prescriber": str|None}; l'age et le sexe viennent de snapshot["patient"].
    context: sortie de get_pdf_header_context (structure, logo_path) + facultatifs:
        validation_date (date; defaut: aujourd'hui), dossier_label (str) ou dossier_day (date, avec
        snapshot["dossier"]), title (defaut DEFAULT_TITLE), city (defaut: structure.city, puis Yaoundé).
    show_pregnancy: resultat de can_see_pregnancy(user); faux = rien de la grossesse n'est imprime.
    """
    version = (snapshot or {}).get("version")
    if version not in SUPPORTED_SNAPSHOT_VERSIONS:
        raise UnknownSnapshotVersionError(f"Version de copie figee inconnue: {version!r}")

    exam = snapshot.get("exam") or {}
    structure = context.get("structure")
    family = exam.get("family")
    template = FAMILY_TEMPLATES.get(family) or FAMILY_TEMPLATES[DEFAULT_FAMILY]

    pregnancy = _pregnancy_line(snapshot.get("pregnancy")) if show_pregnancy else None
    snap_patient = snapshot.get("patient") or {}
    sex = snap_patient.get("sex")
    validation_date = context.get("validation_date") or date.today()
    city = context.get("city") or (getattr(structure, "city", None) if structure else None) or DEFAULT_CITY
    signature = (exam.get("signature_label")
                 or (getattr(structure, "signature_label_default", None) if structure else None)
                 or DEFAULT_SIGNATURE_LABEL)

    with open(_CSS_PATH, encoding="utf-8") as fh:
        css = fh.read()

    parameters = snapshot.get("parameters") or []
    unit_in_norm = family == "three_columns"
    rows = [_row(p, unit_in_norm) for p in parameters]
    groups = _groups(rows)
    for g in groups:
        g["blocks"] = _table_blocks(g)
    if any(b["kind"] == "matrix" for g in groups for b in g["blocks"]):
        # compte rendu a matrice (spermogramme) : le reste s'imprime en lignes, comme sur la fiche
        for g in groups:
            for b in g["blocks"]:
                if b["kind"] == "rows":
                    b["kind"] = "lines"
    notes_html = _notes_html(exam.get("fixed_notes"), rows, family)
    title = context.get("title") or (BOXED_DEFAULT_TITLE if family == "boxed" else DEFAULT_TITLE)

    render_ctx: Dict[str, Any] = {
        "css": css,
        "structure": _HeaderWithoutFooter(structure) if structure else SimpleNamespace(name=""),
        "footer_text": getattr(structure, "footer_text", None) if structure else None,
        "logo_path": context.get("logo_path"),
        "title": title,
        "city": city,
        "date_letters": format_date_letters(validation_date),
        "dossier_label": _dossier_label(snapshot, context),
        "patient_name": (patient or {}).get("name"),
        "prescriber": (patient or {}).get("prescriber"),
        "age_label": snap_patient.get("age_label"),
        "sex": sex if sex in ("M", "F") else None,
        "pregnancy_line": pregnancy,
        "exam": exam,
        "parameters": parameters,
        "rows": rows,
        "groups": groups,
        "notes_html": notes_html,
        "dense": len(parameters) > DENSE_PARAMETER_COUNT,
        "dossier_date": context.get("dossier_day").strftime("%d / %m / %Y") if context.get("dossier_day") else None,
        "conclusion": snapshot.get("conclusion"),
        "note": snapshot.get("note"),
        "signature_label": signature,
    }
    return render_pdf_from_template(template, render_ctx)
