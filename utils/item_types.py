"""Regle unique : une ligne de caisse touche-t-elle au stock pharmacie ?

Vente, modification et annulation d'une facture doivent decider de la meme
facon. S'appuie sur la normalisation deja utilisee pour la reduction personnel.
"""
from utils.staff_discount import normalize_item_category

_STOCK_CATEGORIES = ("medicament", "carnet")


def touches_stock(item_type) -> bool:
    try:
        if not item_type or not str(item_type).strip():
            return False
        return normalize_item_category(item_type) in _STOCK_CATEGORIES
    except Exception:
        return False
