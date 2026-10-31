"""Visibilite et ecriture des donnees de grossesse (donnee de sante sensible).

Regle : la secretaire (et tout role non liste ici) ne voit ni n'ecrit JAMAIS ces champs.
  - lecture : medecin, nurse, laborantin, admin, promoteur ;
  - ecriture : medecin, nurse, laborantin, admin (le promoteur lit seulement, pour le rapport).

Points d'application :
  - `strip_pregnancy_fields` : filtre central de toute sortie JSON (middleware de l'API, voir
    `api_backend/backend_app/main.py`), aussi disponible pour les rapports/exports construits a la main ;
  - `require_pregnancy_write` : 403 pour un role non ecrivain qui envoie ces champs ;
  - `clean_pregnancy_input` / `clean_external_pregnancy` : validation des valeurs.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional

# Noms exacts des colonnes (patients + lab_results) ; les memes cles voyagent dans external_patient_info.
PATIENT_PREGNANCY_FIELDS = ("pregnancy_status", "expected_delivery_date", "pregnancy_program_number")
PREGNANCY_FIELDS = PATIENT_PREGNANCY_FIELDS + ("gestational_age_weeks",)
# Colonnes lab_results propres a la grossesse : `external_pregnancy_info` (patient externe, jamais livre par un
# flux PowerSync) et `pregnancy_status_at_result` (statut a la reception, cliche du rapport de subvention).
EXTERNAL_PREGNANCY_COLUMN = "external_pregnancy_info"
RESULT_STATUS_COLUMN = "pregnancy_status_at_result"

PREGNANCY_STATUSES = ("enceinte", "non_enceinte", "inconnu")
DEFAULT_PREGNANCY_STATUS = "inconnu"
PROGRAM_NUMBER_MAX = 50
GESTATIONAL_WEEKS_MIN = 0
GESTATIONAL_WEEKS_MAX = 45

# Codes canoniques (voir api_backend/backend_app/security/role_map.py)
READ_ROLES = frozenset({"medecin", "nurse", "laborantin", "admin", "promoteur"})
WRITE_ROLES = frozenset({"medecin", "nurse", "laborantin", "admin"})

FORBIDDEN_WRITE_DETAIL = (
    "Acces refuse : les informations de grossesse ne peuvent etre saisies que par "
    "un medecin, un infirmier, le laboratoire ou l'administration."
)


def _canonical_roles(user: Any) -> set:
    """Roles canoniques de l'utilisateur (get_current_user pose `user.roles`, deja canoniques)."""
    from api_backend.backend_app.security.role_map import normalize_role_name

    out = set()
    roles = getattr(user, "roles", None) or []
    if isinstance(roles, str):
        roles = [roles]
    for r in roles:
        if not r:
            continue
        c = normalize_role_name(str(r)) or str(r).strip().lower()
        out.add(c)
    return out


def can_see_pregnancy(user: Any) -> bool:
    if user is None:
        return False
    return bool(_canonical_roles(user) & READ_ROLES)


def can_write_pregnancy(user: Any) -> bool:
    if user is None:
        return False
    return bool(_canonical_roles(user) & WRITE_ROLES)


# Epellations reconnues (comparaison insensible a la casse, sans espaces, tirets ni underscores) :
# les 4 noms de colonnes, leurs equivalents francais courants, et tout nom commencant par un radical
# propre a la grossesse. Volontairement restreint : "prenatal_note" n'est PAS une donnee de grossesse.
_PREGNANCY_KEYS_NORMALIZED = frozenset(
    {"pregnancystatus", "expecteddeliverydate", "pregnancyprogramnumber", "gestationalageweeks",
     "grossesse", "enceinte", "dpa", "externalpregnancyinfo"}
)
_PREGNANCY_KEY_PREFIXES = ("pregnancy", "gestational", "grossesse", "enceinte")
_MAX_DEPTH = 8


def _normalize_key(key: Any) -> str:
    return "".join(ch for ch in str(key).lower() if ch not in " _-	")


def is_pregnancy_key(key: Any) -> bool:
    n = _normalize_key(key)
    return n in _PREGNANCY_KEYS_NORMALIZED or n.startswith(_PREGNANCY_KEY_PREFIXES)


def _json_container(text: str) -> Any:
    """Objet/liste JSON contenu dans une chaine (valeur de cle), sinon None."""
    t = text.strip()
    if len(t) < 2 or t[0] not in "{[":
        return None
    try:
        parsed = json.loads(t)
    except (ValueError, RecursionError):
        return None
    return parsed if isinstance(parsed, (dict, list)) else None


def _strip(obj: Any, depth: int = 0) -> Any:
    if isinstance(obj, dict):
        return {k: _strip(v, depth) for k, v in obj.items() if not is_pregnancy_key(k)}
    if isinstance(obj, (list, tuple)):
        return [_strip(v, depth) for v in obj]
    if isinstance(obj, str) and depth < 3:
        parsed = _json_container(obj)
        if parsed is not None:
            stripped = _strip(parsed, depth + 1)
            if stripped != parsed:
                return json.dumps(stripped, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return obj


def contains_pregnancy_input(obj: Any, depth: int = 0) -> bool:
    """Vrai si `obj` porte, a n'importe quelle profondeur (dict, listes, JSON dans une chaine), une cle
    de grossesse (toute epellation reconnue) avec une valeur non nulle. Trop profond = refuse (ferme)."""
    if depth > _MAX_DEPTH:
        return True
    if isinstance(obj, dict):
        for k, v in obj.items():
            if is_pregnancy_key(k) and v is not None:
                return True
            if contains_pregnancy_input(v, depth + 1):
                return True
        return False
    if isinstance(obj, (list, tuple)):
        return any(contains_pregnancy_input(v, depth + 1) for v in obj)
    if isinstance(obj, str) and depth < 4:
        parsed = _json_container(obj)
        if parsed is not None:
            return contains_pregnancy_input(parsed, depth + 1)
    return False


def strip_pregnancy_fields(payload: Any, user: Any) -> Any:
    """Retire recursivement toute cle de PREGNANCY_FIELDS (y compris dans external_patient_info) si
    l'utilisateur n'a pas le droit de les voir. Renvoie une copie ; le payload d'origine n'est pas modifie."""
    if can_see_pregnancy(user):
        return payload
    return _strip(payload)


def strip_pregnancy_fields_always(payload: Any) -> Any:
    """Comme `strip_pregnancy_fields` pour un destinataire non autorise (rapport anonyme, journal)."""
    return _strip(payload)


def has_pregnancy_input(data: Optional[Dict[str, Any]], fields: Iterable[str] = PREGNANCY_FIELDS) -> bool:
    """Vrai si `data` porte au moins un champ de grossesse avec une valeur (None = absent)."""
    if not isinstance(data, dict):
        return False
    return any(data.get(f) is not None for f in fields)


def require_pregnancy_write(user: Any, *payloads: Optional[Dict[str, Any]]) -> None:
    """403 si un payload (ou son external_patient_info) porte des champs de grossesse alors que
    l'utilisateur n'est pas un ecrivain."""
    if can_write_pregnancy(user):
        return
    from fastapi import HTTPException

    for p in payloads:
        if not isinstance(p, dict):
            continue
        if contains_pregnancy_input(p):
            raise HTTPException(status_code=403, detail=FORBIDDEN_WRITE_DETAIL)


def _to_date(v: Any) -> Optional[date]:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        raise ValueError("Date presumee d'accouchement invalide (format AAAA-MM-JJ).")


def validate_gestational_weeks(v: Any) -> Optional[int]:
    if v in (None, ""):
        return None
    if isinstance(v, bool):
        raise ValueError("Age gestationnel invalide.")
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        raise ValueError("Age gestationnel invalide (nombre entier de semaines).")
    if not (GESTATIONAL_WEEKS_MIN <= n <= GESTATIONAL_WEEKS_MAX):
        raise ValueError(
            f"Age gestationnel hors limites ({GESTATIONAL_WEEKS_MIN} a {GESTATIONAL_WEEKS_MAX} semaines)."
        )
    return n


CLEARABLE_PATIENT_FIELDS = PATIENT_PREGNANCY_FIELDS


def clean_clear_fields(data: Dict[str, Any]) -> list:
    """Champs de grossesse a effacer sur la fiche (cle `clear_pregnancy_fields`, liste de noms). ValueError si un
    nom est inconnu. Un champ ne peut pas etre efface et ecrit dans la meme requete."""
    raw = data.get("clear_pregnancy_fields")
    if raw in (None, [], ()):
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("clear_pregnancy_fields doit etre une liste de champs.")
    out = []
    for name in raw:
        if name not in CLEARABLE_PATIENT_FIELDS:
            raise ValueError(f"Champ de grossesse inconnu : {name}.")
        if data.get(name) is not None:
            raise ValueError(f"Le champ {name} ne peut pas etre efface et modifie en meme temps.")
        if name not in out:
            out.append(name)
    return out


def clean_pregnancy_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valide et normalise les champs PATIENT presents dans `data` (cles absentes ignorees).
    Leve ValueError (message francais) si une valeur est invalide. Une valeur None est ignoree."""
    out: Dict[str, Any] = {}
    if data.get("pregnancy_status") is not None:
        s = str(data["pregnancy_status"]).strip().lower()
        if s not in PREGNANCY_STATUSES:
            raise ValueError("Statut de grossesse invalide (enceinte, non_enceinte ou inconnu).")
        out["pregnancy_status"] = s
    if "expected_delivery_date" in data and data["expected_delivery_date"] is not None:
        out["expected_delivery_date"] = _to_date(data["expected_delivery_date"])
    if data.get("pregnancy_program_number") is not None:
        n = str(data["pregnancy_program_number"]).strip()
        if len(n) > PROGRAM_NUMBER_MAX:
            raise ValueError(f"Numero de suivi de grossesse trop long ({PROGRAM_NUMBER_MAX} caracteres maximum).")
        out["pregnancy_program_number"] = n or None
    return out


def extract_external_pregnancy(info: Optional[Dict[str, Any]], extra: Optional[Dict[str, Any]] = None):
    """Separe les donnees de grossesse d'un patient externe de son `external_patient_info`.

    `info` est le JSON d'identite (qui est livre par un flux PowerSync) ; `extra` est le bloc de grossesse
    envoye a part (`external_pregnancy_info`). Les anciennes cles de grossesse restees dans `info` (clients
    anciens, operations deja en file) sont deplacees vers le bloc de grossesse. Renvoie
    (identite sans aucune cle de grossesse, grossesse validee ou None). Leve ValueError si une valeur est invalide.
    Un JSON qui n'est pas un objet est traite comme vide."""
    base = dict(info) if isinstance(info, dict) else {}
    legacy = {k: v for k, v in base.items() if is_pregnancy_key(k)}
    identity = {k: v for k, v in base.items() if k not in legacy}
    merged = {**legacy, **(extra if isinstance(extra, dict) else {})}
    cleaned = clean_external_pregnancy(merged) or {}
    cleaned = {k: v for k, v in cleaned.items() if v is not None}
    return identity, (cleaned or None)


def snapshot_pregnancy_status(explicit: Any, weeks: Optional[int], current: Optional[str]) -> str:
    """Statut de grossesse a enregistrer sur le resultat a la reception : une SA superieure a 0 vaut grossesse ;
    sinon le statut choisi a la reception ; sinon le statut du dossier au moment de la reception ; sinon inconnu."""
    if isinstance(weeks, int) and not isinstance(weeks, bool) and weeks > 0:
        return "enceinte"
    for cand in (explicit, current):
        c = str(cand).strip().lower() if cand not in (None, "") else ""
        if c in PREGNANCY_STATUSES:
            return c
    return DEFAULT_PREGNANCY_STATUS


def clean_external_pregnancy(info: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Valide les champs de grossesse d'un external_patient_info et renvoie une copie normalisee
    (dates en ISO texte, car ce dictionnaire est stocke en JSON). Les cles absentes ou nulles sont retirees."""
    if not isinstance(info, dict):
        return info
    out = dict(info)
    cleaned = clean_pregnancy_input(out)
    for f in PATIENT_PREGNANCY_FIELDS:
        out.pop(f, None)
    # Epellations non canoniques (Grossesse, DPA, ...) : jamais stockees, on ne garde que les cles normalisees.
    for k in [k for k in out if is_pregnancy_key(k) and k != "gestational_age_weeks"]:
        out.pop(k, None)
    for k, v in cleaned.items():
        out[k] = v.isoformat() if isinstance(v, date) else v
    if "gestational_age_weeks" in out:
        w = validate_gestational_weeks(out.pop("gestational_age_weeks"))
        if w is not None:
            out["gestational_age_weeks"] = w
    return out
