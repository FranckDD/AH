# api_backend/backend_app/routes/labo/lab_catalogue_schemas.py
"""Schemas d'ecriture du catalogue du laboratoire (cheffe du laboratoire et admin).

Aucun schema n'accepte le prix : une charge utile qui le porte est refusee (422).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LayoutFamily = Literal["table", "three_columns", "label_value", "narrative", "boxed"]
ResultKind = Literal["numeric", "text", "choice", "pos_neg"]
NotePosition = Literal["before_body", "after_body", "after_conclusion"]
NoteStyle = Literal["normal", "bold", "italic"]
# Limites des textes imprimes (identiques aux CHECK de la migration 045 et au seed).
MAX_GROUP_LABEL, MAX_NORM_TEXT, MAX_DISPLAY_TEXT, MAX_NOTE_TEXT, MAX_FIXED_NOTES = 80, 200, 60, 1000, 12
LAYOUT_FAMILIES = ("table", "three_columns", "label_value", "narrative", "boxed")
RESULT_KINDS = ("numeric", "text", "choice", "pos_neg")


class _NoPrice(BaseModel):
    """Base : refuse tout champ inconnu et, en particulier, le prix."""
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _reject_price(cls, data: Any):
        if isinstance(data, dict) and ("prix" in data or "price" in data):
            raise ValueError("Le prix d'un examen ne se modifie pas dans le catalogue (administrateur, ecran des prix).")
        return data


def _clean_text(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _no_control_chars(v: str, allow_newline: bool = False) -> str:
    """Texte imprime : jamais interprete comme du HTML (le rendu l'echappe), mais pas de caractere de controle
    (le NUL fait echouer PostgreSQL)."""
    for ch in v:
        if ord(ch) < 32 and not (allow_newline and ch in "\n\r\t"):
            raise ValueError("Caractere de controle interdit")
    return v


class FixedNote(_NoPrice):
    """Un bloc de texte fixe de la fiche (examens.fixed_notes), imprime tel quel (echappe)."""
    position: NotePosition
    text: str = Field(..., max_length=MAX_NOTE_TEXT)
    style: NoteStyle = "normal"

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = _no_control_chars(v.strip(), allow_newline=True)
        if not v:
            raise ValueError("Le texte de la note est obligatoire")
        return v


def _check_notes(notes: Optional[List[FixedNote]]) -> Optional[List[FixedNote]]:
    if notes is not None and len(notes) > MAX_FIXED_NOTES:
        raise ValueError("Au plus %d notes fixes par examen" % MAX_FIXED_NOTES)
    return notes


def _print_text(v: Optional[str]) -> Optional[str]:
    v = _clean_text(v)
    return None if v is None else _no_control_chars(v)


# ---------------------------------------------------------------- examens
class ExamCatalogueCreate(_NoPrice):
    code: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_\-]+$")
    nom: str = Field(..., min_length=1, max_length=200)
    categorie: str = Field(..., min_length=1, max_length=100)
    section: Optional[str] = Field(None, max_length=120)
    print_title: Optional[str] = Field(None, max_length=200)
    method: Optional[str] = Field(None, max_length=1000)
    layout_family: LayoutFamily = "label_value"
    signature_label: Optional[str] = Field(None, max_length=200)
    sort_order: int = Field(0, ge=0, le=100000)
    is_active: bool = True
    fixed_notes: Optional[List[FixedNote]] = None

    @field_validator("fixed_notes")
    @classmethod
    def _notes(cls, v):
        return _check_notes(v)

    @field_validator("nom", "categorie")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Valeur obligatoire")
        return v

    @field_validator("code")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("section", "print_title", "method", "signature_label")
    @classmethod
    def _trim(cls, v):
        return _clean_text(v)


class ExamCataloguePut(_NoPrice):
    """Modification : le code est immuable (il identifie l'examen dans les donnees de reference)."""
    nom: Optional[str] = Field(None, min_length=1, max_length=200)
    categorie: Optional[str] = Field(None, min_length=1, max_length=100)
    section: Optional[str] = Field(None, max_length=120)
    print_title: Optional[str] = Field(None, max_length=200)
    method: Optional[str] = Field(None, max_length=1000)
    layout_family: Optional[LayoutFamily] = None
    signature_label: Optional[str] = Field(None, max_length=200)
    sort_order: Optional[int] = Field(None, ge=0, le=100000)
    is_active: Optional[bool] = None
    fixed_notes: Optional[List[FixedNote]] = None   # null ou [] efface les notes fixes

    @field_validator("fixed_notes")
    @classmethod
    def _notes(cls, v):
        return _check_notes(v)

    @field_validator("nom", "categorie")
    @classmethod
    def _not_blank(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Valeur obligatoire")
        return v

    @field_validator("section", "print_title", "method", "signature_label")
    @classmethod
    def _trim(cls, v):
        return _clean_text(v)


class PositionIn(_NoPrice):
    """Nouvelle position (1 = premier) parmi les elements freres ; les autres sont renumerotes."""
    position: int = Field(..., ge=1, le=100000)


class IdsIn(_NoPrice):
    """Ordre complet : les ids dans l'ordre voulu (chaque id une seule fois)."""
    ids: List[int] = Field(..., min_length=1, max_length=2000)


# ------------------------------------------------------------- parametres
def _check_choices(choices: Optional[List[str]]) -> Optional[List[str]]:
    if choices is None:
        return None
    out: List[str] = []
    for c in choices:
        c = (c or "").strip()
        if not c:
            raise ValueError("Un choix ne peut pas etre vide")
        if "," in c:
            raise ValueError("Un choix ne peut pas contenir de virgule")
        if len(c) > 60:
            raise ValueError("Un choix est limite a 60 caracteres")
        if c in out:
            raise ValueError("Choix en double")
        out.append(c)
    if len(out) > 30:
        raise ValueError("Au plus 30 choix")
    return out


class ParameterCreate(_NoPrice):
    examen_id: int
    nom_parametre: str = Field(..., min_length=1, max_length=200)
    unite: str = Field("", max_length=40)
    print_label: Optional[str] = Field(None, max_length=200)
    result_kind: ResultKind = "numeric"
    choices: Optional[List[str]] = None
    is_active: bool = True
    group_label: Optional[str] = Field(None, max_length=MAX_GROUP_LABEL)
    norm_text: Optional[str] = Field(None, max_length=MAX_NORM_TEXT)

    @field_validator("group_label", "norm_text")
    @classmethod
    def _printed(cls, v):
        return _print_text(v)

    @field_validator("nom_parametre")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Valeur obligatoire")
        return v

    @field_validator("unite")
    @classmethod
    def _unit(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("print_label")
    @classmethod
    def _trim(cls, v):
        return _clean_text(v)

    @field_validator("choices")
    @classmethod
    def _choices(cls, v):
        return _check_choices(v)

    @model_validator(mode="after")
    def _kind_choices(self):
        if self.result_kind == "choice" and not self.choices:
            raise ValueError("Un parametre a choix doit lister ses choix")
        return self


class ParameterPut(_NoPrice):
    nom_parametre: Optional[str] = Field(None, min_length=1, max_length=200)
    unite: Optional[str] = Field(None, max_length=40)
    print_label: Optional[str] = Field(None, max_length=200)
    result_kind: Optional[ResultKind] = None
    choices: Optional[List[str]] = None
    is_active: Optional[bool] = None
    group_label: Optional[str] = Field(None, max_length=MAX_GROUP_LABEL)
    norm_text: Optional[str] = Field(None, max_length=MAX_NORM_TEXT)

    @field_validator("group_label", "norm_text")
    @classmethod
    def _printed(cls, v):
        return _print_text(v)

    @field_validator("nom_parametre")
    @classmethod
    def _not_blank(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Valeur obligatoire")
        return v

    @field_validator("unite")
    @classmethod
    def _unit(cls, v):
        return None if v is None else v.strip()

    @field_validator("print_label")
    @classmethod
    def _trim(cls, v):
        return _clean_text(v)

    @field_validator("choices")
    @classmethod
    def _choices(cls, v):
        return _check_choices(v)


# ----------------------------------------------------------------- plages
class _RangeBounds(_NoPrice):
    sexe: Literal["M", "F", "X"]
    age_min_days: Optional[int] = Field(None, ge=0, le=60000)
    age_max_days: Optional[int] = Field(None, ge=0, le=60000)
    ga_min_weeks: Optional[int] = Field(None, ge=0, le=45)
    ga_max_weeks: Optional[int] = Field(None, ge=0, le=45)
    valeur_min: Decimal
    valeur_max: Decimal
    display_text: Optional[str] = Field(None, max_length=MAX_DISPLAY_TEXT)

    @field_validator("display_text")
    @classmethod
    def _printed(cls, v):
        return _print_text(v)

    @model_validator(mode="after")
    def _bounds(self):
        if (self.age_min_days is not None and self.age_max_days is not None
                and self.age_min_days > self.age_max_days):
            raise ValueError("age_min_days doit etre inferieur ou egal a age_max_days")
        if (self.ga_min_weeks is not None and self.ga_max_weeks is not None
                and self.ga_min_weeks > self.ga_max_weeks):
            raise ValueError("ga_min_weeks doit etre inferieur ou egal a ga_max_weeks")
        if self.valeur_min > self.valeur_max:
            raise ValueError("valeur_min doit etre inferieure ou egale a valeur_max")
        return self


class RangeCreate(_RangeBounds):
    parametre_id: int


class RangePut(_RangeBounds):
    """Remplacement complet de la plage (le parametre ne change pas)."""
