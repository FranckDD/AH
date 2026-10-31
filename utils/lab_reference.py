"""Sexe et plages de reference du laboratoire : une seule regle pour le banc et la fiche imprimee."""
from typing import Any, Iterable, Optional

_MALE = {"m", "male", "homme", "man", "masculin", "h"}
_FEMALE = {"f", "female", "femme", "woman", "feminin", "féminin"}

SEX_LABELS_FR = {"M": "Masculin", "F": "Féminin", "X": "Non renseigné"}
FLAG_WORDS = {"H": "Haut", "L": "Bas", "A": "Anormal", "N": "Normal"}
ABNORMAL_FALLBACK = "Anormal"


def normalize_sex(raw: Any) -> str:
    """'M', 'F' ou 'X' (inconnu / autre). 'X' est aussi le code des plages valables pour tous."""
    s = str(raw or "").strip().lower()
    if s in _MALE:
        return "M"
    if s in _FEMALE:
        return "F"
    return "X"


# Une borne haute d'au moins 120 ans (ancienne plage « 0 a 120 ans » des catalogues existants) ou
# une borne basse a 0 ne restreint rien : elles sont lues comme « sans borne ».
_OPEN_UPPER_DAYS = 120 * 365
_INF = float("inf")


def _int_or_none(v):
    return None if v is None else int(v)


def age_bounds_days(rr) -> tuple:
    """(min, max) en jours inclusifs, None = ouvert. Colonnes en jours si l'une est renseignee,
    sinon lecture heritee des colonnes en annees entieres : [age_min*365, (age_max+1)*365-1]."""
    lo = _int_or_none(getattr(rr, "age_min_days", None))
    hi = _int_or_none(getattr(rr, "age_max_days", None))
    if lo is None and hi is None:
        ymin = _int_or_none(getattr(rr, "age_min", None))
        ymax = _int_or_none(getattr(rr, "age_max", None))
        lo = None if ymin is None else ymin * 365
        hi = None if ymax is None else (ymax + 1) * 365 - 1
    if lo is not None and lo <= 0:
        lo = None
    if hi is not None and hi >= _OPEN_UPPER_DAYS:
        hi = None
    return lo, hi


def ga_bounds_weeks(rr) -> tuple:
    return _int_or_none(getattr(rr, "ga_min_weeks", None)), _int_or_none(getattr(rr, "ga_max_weeks", None))


def select_range(ranges: Iterable[Any], sex_code: str, age_days: Optional[int], ga_weeks: Optional[int] = None):
    """Plage de reference applicable, choix deterministe (independant de l'ordre d'entree).

    Une plage s'applique si : son sexe est celui du patient ou 'X'/vide (sexe inconnu : seulement
    les plages X) ; l'age en jours est dans ses bornes inclusives (age inconnu : seulement les
    plages sans borne d'age) ; si elle a des bornes de SA, la SA est connue et dedans (une plage
    avec SA ne s'applique jamais sans SA ; une plage sans SA s'applique a tous).
    Parmi les candidates : le plus de criteres renseignes (sexe, age, SA), puis l'intervalle d'age
    le plus etroit (borne ouverte = infini), puis la borne basse d'age la plus haute (la plus
    specifique : « des 18 ans » l'emporte sur « des 1 an » pour un adulte), puis le plus petit id."""
    sex = sex_code if sex_code in ("M", "F") else "X"
    best_key = None
    best = None
    for rr in ranges:
        rsex = str(getattr(rr, "sexe", None) or "X").strip().upper()
        sex_specific = rsex in ("M", "F")
        if sex_specific and rsex != sex:
            continue
        lo, hi = age_bounds_days(rr)
        has_age = lo is not None or hi is not None
        if has_age:
            if age_days is None:
                continue
            if (lo is not None and age_days < lo) or (hi is not None and age_days > hi):
                continue
        gmin, gmax = ga_bounds_weeks(rr)
        has_ga = gmin is not None or gmax is not None
        if has_ga:
            if ga_weeks is None:
                continue
            if (gmin is not None and ga_weeks < gmin) or (gmax is not None and ga_weeks > gmax):
                continue
        count = int(sex_specific) + int(has_age) + int(has_ga)
        width = (_INF if hi is None else hi) - (0 if lo is None else lo)
        rid = getattr(rr, "id", None)
        key = (-count, width, -(0 if lo is None else lo), rid if rid is not None else _INF)
        if best_key is None or key < best_key:
            best_key, best = key, rr
    return best


def flag_word(flag: Optional[str]) -> str:
    return FLAG_WORDS.get((flag or "").strip().upper(), "")
