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


def select_range(ranges: Iterable[Any], sex_code: str, age: Optional[int]):
    """Plage applicable : celle du sexe du patient, sinon la plage generique 'X'. Jamais la plage
    d'un autre sexe, et aucun choix arbitraire quand le sexe est inconnu. Age inconnu (None) : pas
    de filtre sur l'age."""
    def fits(rr) -> bool:
        if age is None:
            return True
        lo = getattr(rr, "age_min", None)
        hi = getattr(rr, "age_max", None)
        return (lo is None or lo <= age) and (hi is None or age <= hi)

    candidates = [rr for rr in ranges if fits(rr)]
    if sex_code in ("M", "F"):
        for rr in candidates:
            if rr.sexe == sex_code:
                return rr
    for rr in candidates:
        if rr.sexe == "X":
            return rr
    return None


def flag_word(flag: Optional[str]) -> str:
    return FLAG_WORDS.get((flag or "").strip().upper(), "")
