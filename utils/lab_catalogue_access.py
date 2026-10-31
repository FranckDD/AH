"""Droit d'editer le catalogue des examens du laboratoire (examens, parametres, plages de reference).

Reserve a l'admin et a la cheffe du laboratoire (role laborantin avec `users.is_head_lab`).
Le prix d'un examen n'est jamais modifiable par ce droit (il reste a l'admin, route /labo/exams).
"""
from __future__ import annotations

from typing import Any


def _roles(user: Any) -> set:
    return {str(r).strip().lower() for r in (getattr(user, "roles", None) or []) if r}


def can_edit_lab_catalogue(user: Any) -> bool:
    if user is None:
        return False
    roles = _roles(user)
    if "admin" in roles:
        return True
    return "laborantin" in roles and bool(getattr(user, "is_head_lab", False))
