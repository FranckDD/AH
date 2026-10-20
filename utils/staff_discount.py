"""Calcul pur de la reduction personnel (aucune dependance DB).

Miroir JS a garder synchronise; les deux sont testes avec
tests/fixtures/staff_discount_cases.json.
"""
import unicodedata
from decimal import Decimal, ROUND_HALF_UP

CATEGORIES = ("medicament", "examen", "consultation", "carnet", "autre_soin")


def normalize_item_category(item_type):
    s = unicodedata.normalize("NFKD", str(item_type or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    if "consult" in s:  # avant "medic": "Consultation Medical"
        return "consultation"
    if "medic" in s:
        return "medicament"
    if "carnet" in s or "booklet" in s:
        return "carnet"
    if "exam" in s:
        return "examen"
    return "autre_soin"


def _line_amount(line):
    # Chaque line_total est arrondi au centime (demi-superieur) AVANT tout
    # calcul - meme regle cote JS (staffDiscount.js toCents), qui protege du
    # bruit flottant (0.1*3) et des totaux a 3 decimales envoyes par l'UI.
    return Decimal(str(line.get("line_total") or 0)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_staff_discount(lines, is_staff, rules):
    zero = Decimal("0")
    if not is_staff or not lines:
        return {"amount": zero, "details": None}
    active = [l for l in lines if l.get("status") != "cancelled"]
    total = sum((_line_amount(l) for l in active), zero)
    bases = {}
    for l in active:
        cat = normalize_item_category(l.get("item_type"))
        bases[cat] = bases.get(cat, zero) + _line_amount(l)

    details = []
    raw_sum = zero
    for rule in rules or []:
        if not rule.get("is_active"):
            continue
        minimum = Decimal(str(rule.get("min_invoice_amount") or 0))
        if total < minimum:
            continue
        cat = rule.get("category")
        base = bases.get(cat, zero)
        if base <= 0:
            continue
        rate = Decimal(str(rule.get("rate_percent") or 0))
        raw = base * rate / Decimal(100)
        raw_sum += raw
        details.append({
            "category": cat,
            "rate_percent": int(rate),
            "base": base,
            "discount": raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "min_invoice_amount": minimum,
        })
    amount = raw_sum.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount == 0:
        return {"amount": zero, "details": None}
    return {"amount": amount, "details": details}
