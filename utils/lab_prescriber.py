# utils/lab_prescriber.py
"""Prescripteur libre d'un patient externe a la reception du laboratoire."""
import re

PRESCRIBER_TITLES = ("Dr", "I.D.E.", "Fr", "Br", "M.", "Mme", "Volontaire", "Autre")
NAME_MAX = 80

_TAGS = re.compile(r"<[^>]*>")
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
# Surcharges bidirectionnelles et caracteres de largeur nulle (usurpation visuelle de nom).
_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
_SPACES = re.compile(r"\s+")


def clean_prescriber_name(name) -> str:
    """Nom sans balises HTML ni caracteres de controle, espaces ramenes a un seul, borne a 80 caracteres."""
    text = _TAGS.sub(" ", str(name or ""))
    text = _CONTROL.sub(" ", text)
    text = _INVISIBLE.sub("", text)
    text = text.replace("<", " ").replace(">", " ")
    return _SPACES.sub(" ", text).strip()[:NAME_MAX].strip()


def split_prescriber(title, name):
    """Valide et normalise (titre, nom) ; leve ValueError si invalide."""
    if title not in PRESCRIBER_TITLES:
        raise ValueError("Titre du prescripteur invalide.")
    clean = clean_prescriber_name(name)
    if not clean and title != "Volontaire":
        raise ValueError("Le nom du prescripteur est obligatoire.")
    return title, clean


def format_prescriber(title: str, name: str) -> str:
    """Forme enregistree dans lab_results.prescribed_by_name : `<titre> <nom>` (max 100 caracteres)."""
    title, clean = split_prescriber(title, name)
    if title == "Autre":
        return clean
    return f"{title} {clean}".strip()
