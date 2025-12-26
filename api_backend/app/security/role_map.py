# app/security/role_map.py
from typing import Dict, Set

# Codes canoniques utilisés dans ton projet (conservés tels quels)
ADMIN = "admin"
MEDECIN = "medecin"
NURSE = "nurse"
SECRETAIRE = "secretaire"
LABORANTIN = "laborantin"

ROLE_CANONICALS = {ADMIN, MEDECIN, NURSE, SECRETAIRE, LABORANTIN}

# mapping canonical -> set d'alias (fr, en, variations possibles)
ROLE_ALIASES: Dict[str, Set[str]] = {
    ADMIN: {"admin", "administrateur", "administrator", "adm"},
    MEDECIN: {"medecin", "médecin", "doctor", "dr", "physician"},
    NURSE: {"nurse", "infirmier", "infirmiere", "infirmière", "nurse_fr"},
    SECRETAIRE: {"secretaire", "secrétaire", "secretary", "secretary_fr"},
    LABORANTIN: {"laborantin", "lab_tech", "laboratory", "laboratory_technician", "technicien_lab"}
}

# Construire reverse map alias (lowercase) -> canonical
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canon, aliases in ROLE_ALIASES.items():
    for a in aliases:
        _ALIAS_TO_CANONICAL[a.strip().lower()] = canon

def normalize_role_name(name: str | None) -> str | None:
    """
    Retourne le code canonique (ex: 'medecin') pour un alias donné (insensible à la casse),
    ou None si inconnu.
    """
    if not name:
        return None
    key = name.strip().lower()
    # si on reçoit déjà un canonical connu, le retourner directement
    if key in ROLE_CANONICALS:
        return key
    return _ALIAS_TO_CANONICAL.get(key)

def normalize_roles_list(names: list[str] | None) -> list[str]:
    """
    Normalise une liste d'aliases en codes canoniques (déduplique et enlève les inconnus).
    """
    out: list[str] = []
    for n in names or []:
        canon = normalize_role_name(n)
        if canon and canon not in out:
            out.append(canon)
    return out
