"""Copie figee d'impression d'un resultat de laboratoire (migration 044).

`build_print_snapshot` est PUR : il lit des objets ORM (ou des doubles) et renvoie un dict JSON, sans
session ni ecriture. Le serveur l'appelle une seule fois, au moment ou le resultat devient valide
(LabRepository.freeze_print_snapshot) ; une correction (amendement) en cree une nouvelle et archive
l'ancienne dans lab_results.print_snapshot_history.

La copie ne contient AUCUNE identite (ni nom, ni telephone, ni date de naissance) : age, sexe et marqueur
de grossesse seulement ; les noms sont lus dans les tables patient a l'impression. La cle `pregnancy` ne
doit etre imprimee que si `can_see_pregnancy(user)` (utils/pregnancy_visibility.py) : le rendu la retire
pour les autres (voir `strip_pregnancy`).

Versions (le lecteur, api_backend/.../utils/lab_sheet.py, accepte les deux) :
- 1 : une seule norme par parametre (`norm`, celle choisie pour le patient), `group` toujours null.
- 2 (migration 045) : en plus, par parametre `group` (sous-titre de la fiche), `norm_text` (texte de norme
  imprime du parametre) et `norms` (TOUTES les plages du parametre au moment de la validation, dont
  `selected` marque celle choisie pour ce patient) ; par examen `fixed_notes`. `norm` est conservee.
  La feuille imprime toutes les normes du laboratoire et signale la valeur selon la norme choisie.
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from utils.lab_reference import select_range

SNAPSHOT_VERSION = 2


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    return float(v)


def _fmt(v: Any) -> str:
    d = Decimal(str(v))
    s = format(d.normalize(), "f")
    return s


def _norm_text(rng: Any) -> str:
    lo, hi = rng.valeur_min, rng.valeur_max
    return f"{_fmt(lo)} - {_fmt(hi)}"


def _norm_dict(rng: Any) -> Optional[Dict[str, Any]]:
    if rng is None:
        return None
    return {
        "text": _norm_text(rng),
        "min": _num(rng.valeur_min), "max": _num(rng.valeur_max),
        "sex": str(getattr(rng, "sexe", None) or "X").strip().upper(),
        "age_min_days": getattr(rng, "age_min_days", None), "age_max_days": getattr(rng, "age_max_days", None),
        "ga_min_weeks": getattr(rng, "ga_min_weeks", None), "ga_max_weeks": getattr(rng, "ga_max_weeks", None),
    }


def _norms_list(ranges: Any, selected: Any) -> list:
    """Toutes les plages du parametre (v2), triees de facon stable ; `selected` = la plage choisie."""
    items = list(ranges or [])
    items.sort(key=lambda r: (getattr(r, "age_min_days", None) if getattr(r, "age_min_days", None) is not None else -1,
                              getattr(r, "age_max_days", None) if getattr(r, "age_max_days", None) is not None else 10 ** 9,
                              str(getattr(r, "sexe", None) or "X"), int(getattr(r, "id", 0) or 0)))
    out = []
    for r in items:
        text = (getattr(r, "display_text", None) or "").strip() or _norm_text(r)
        out.append({
            "sex": str(getattr(r, "sexe", None) or "X").strip().upper(),
            "age_min_days": getattr(r, "age_min_days", None), "age_max_days": getattr(r, "age_max_days", None),
            "ga_min_weeks": getattr(r, "ga_min_weeks", None), "ga_max_weeks": getattr(r, "ga_max_weeks", None),
            "min": _num(r.valeur_min), "max": _num(r.valeur_max),
            "text": text,
            "selected": selected is not None and r is selected,
        })
    return out


def _fixed_notes(exam: Any) -> list:
    out = []
    for n in getattr(exam, "fixed_notes", None) or []:
        if isinstance(n, dict) and str(n.get("text") or "").strip():
            out.append({"position": n.get("position") or "after_body", "text": str(n["text"]),
                        "style": n.get("style") or "normal"})
    return out


def _dossier(result: Any) -> Optional[Dict[str, int]]:
    y = getattr(result, "dossier_year", None)
    c = getattr(result, "dossier_counter", None)
    r = getattr(result, "dossier_rank", None)
    if y is None or c is None or r is None:
        return None
    return {"year": int(y), "counter": int(c), "rank": int(r)}


def _pregnancy(result: Any) -> Optional[Dict[str, Any]]:
    status = getattr(result, "pregnancy_status_at_result", None)
    ga = getattr(result, "gestational_age_weeks", None)
    if status == "inconnu":
        status = None   # « inconnu » n'est pas une donnee : sans SA, la cle reste vide
    if status is None and ga is None:
        return None
    return {"status_at_result": status, "gestational_age_weeks": ga}


def build_print_snapshot(result: Any, exam: Any, details: Any, patient_bio: Any,
                         org_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Copie JSON de ce qui sera imprime, telle qu'au moment de la validation.

    `details` : lignes de resultat (valeur_text, valeur_num, flagged, interpretation, parametre) ;
    `patient_bio` : PatientBio(age_days, sex, ga_weeks, age_label) ; la norme de chaque parametre est
    celle choisie par `select_range` pour CE patient. `org_context` (facultatif) est copie sous `org`."""
    rows = []
    for d in details or []:
        p = d.parametre
        all_ranges = list(getattr(p, "reference_ranges", None) or [])
        norm = select_range(all_ranges, patient_bio.sex, patient_bio.age_days, patient_bio.ga_weeks)
        rows.append((int(getattr(p, "ordre", 0) or 0), int(getattr(p, "id", 0) or 0), {
            "id": p.id,
            "label": getattr(p, "print_label", None) or p.nom_parametre,
            "unit": getattr(p, "unite", None) or "",
            "kind": getattr(p, "result_kind", None) or "numeric",
            "order": int(getattr(p, "ordre", 0) or 0),
            "value_text": d.valeur_text if d.valeur_text is not None else "",
            "value_num": _num(d.valeur_num),
            "flagged": bool(d.flagged),
            "interpretation": d.interpretation,
            "norm": _norm_dict(norm),
            "group": (getattr(p, "group_label", None) or None),
            "norm_text": ((getattr(p, "norm_text", None) or "").strip() or None),
            "norms": _norms_list(all_ranges, norm),
        }))
    rows.sort(key=lambda t: (t[0], t[1]))

    snap: Dict[str, Any] = {
        "version": SNAPSHOT_VERSION,
        "exam": {
            "code": getattr(exam, "code", None),
            "title": getattr(exam, "print_title", None) or getattr(exam, "nom", None),
            "section": getattr(exam, "section", None),
            "method": getattr(exam, "method", None),
            "family": getattr(exam, "layout_family", None) or "label_value",
            "signature_label": getattr(exam, "signature_label", None),
            "sort_order": int(getattr(exam, "sort_order", 0) or 0),
            "fixed_notes": _fixed_notes(exam),
        },
        "patient": {"age_label": patient_bio.age_label, "age_days": patient_bio.age_days, "sex": patient_bio.sex},
        "pregnancy": _pregnancy(result),
        "dossier": _dossier(result),
        "parameters": [r[2] for r in rows],
        "conclusion": getattr(result, "conclusion", None),
        "note": getattr(result, "note", None),
    }
    if org_context:
        snap["org"] = dict(org_context)
    return snap


def _has_ga(n: Any) -> bool:
    return isinstance(n, dict) and (n.get("ga_min_weeks") is not None or n.get("ga_max_weeks") is not None)


def _strip_ga_keys(n: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in n.items() if k not in ("ga_min_weeks", "ga_max_weeks")}


def _strip_parameter(p: Dict[str, Any]) -> Dict[str, Any]:
    """Retire d'un parametre toute trace d'une norme de grossesse (plages avec bornes d'age gestationnel)."""
    q = dict(p)
    norms = q.get("norms")
    had_ga = False
    if isinstance(norms, list):
        kept = []
        for n in norms:
            if _has_ga(n):
                had_ga = True
                continue
            kept.append(_strip_ga_keys(n) if isinstance(n, dict) else n)
        selected_removed = any(_has_ga(n) and n.get("selected") for n in norms)
        if selected_removed:
            # la plage choisie etait une plage de grossesse : aucune plage n'est marquee choisie
            kept = [{**n, "selected": False} if isinstance(n, dict) else n for n in kept]
        q["norms"] = kept
    norm = q.get("norm")
    if isinstance(norm, dict):
        if _has_ga(norm):
            # la norme choisie est une plage de grossesse : son texte le dit, on ne garde que la valeur
            had_ga = True
            q["norm"] = None
        else:
            q["norm"] = _strip_ga_keys(norm)
    if had_ga:
        # le texte de norme du catalogue (imprime tel quel) decrit aussi les plages de grossesse
        q["norm_text"] = None
    return q


def strip_pregnancy(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Copie de la copie sans donnee de grossesse (a utiliser quand `can_see_pregnancy(user)` est faux).

    Retire aussi toute trace qu'une norme est une plage de semaines de grossesse : bornes `ga_*`, plages
    avec bornes gestationnelles, marqueur `selected` de ces plages. La valeur (`flagged`) reste."""
    out = dict(snapshot)
    out["pregnancy"] = None
    params = out.get("parameters")
    if isinstance(params, list):
        out["parameters"] = [_strip_parameter(p) if isinstance(p, dict) else p for p in params]
    return out
