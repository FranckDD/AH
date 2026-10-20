import json
from decimal import Decimal
from pathlib import Path

import pytest

from utils.staff_discount import compute_staff_discount, normalize_item_category

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "staff_discount_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fixture_cases(case):
    res = compute_staff_discount(case["lines"], case["is_staff"], case["rules"])
    assert res["amount"] == Decimal(str(case["expected_amount"]))
    cats = {d["category"] for d in (res["details"] or [])}
    assert cats == set(case["expected_categories"])


def test_normalize_item_category_variants():
    labels = ["Sale Medication", "Médicament", "Vente Carnet", "Examen",
              "Consultation Spirituel", "Consultation Médical", "Désintox"]
    expected = ["medicament", "medicament", "carnet", "examen",
                "consultation", "consultation", "autre_soin"]
    assert [normalize_item_category(x) for x in labels] == expected
    assert normalize_item_category("Service") == "autre_soin"
    assert normalize_item_category("Truc") == "autre_soin"
    assert normalize_item_category("") == "autre_soin"
    assert normalize_item_category(None) == "autre_soin"
    assert normalize_item_category("EXAMENS") == "examen"


def test_details_none_when_no_discount():
    res = compute_staff_discount([{"item_type": "Examen", "line_total": 10}], True, [])
    assert res == {"amount": Decimal("0"), "details": None}
    res = compute_staff_discount([], True, [{"category": "examen", "min_invoice_amount": 0,
                                             "rate_percent": 10, "is_active": True}])
    assert res["amount"] == 0 and res["details"] is None


def test_float_noise_line_total_matches_js():
    lt = 0.1 * 3  # 0.30000000000000004, comme en JS
    res = compute_staff_discount(
        [{"item_type": "Examen", "line_total": lt}], True,
        [{"category": "examen", "min_invoice_amount": 0.3, "rate_percent": 100, "is_active": True}])
    assert res["amount"] == Decimal("0.30")


def test_detail_shape():
    res = compute_staff_discount(
        [{"item_type": "Examen", "line_total": 100}], True,
        [{"category": "examen", "min_invoice_amount": 50, "rate_percent": 10, "is_active": True}])
    d = res["details"][0]
    assert set(d) == {"category", "rate_percent", "base", "discount", "min_invoice_amount"}
    assert d["discount"] == Decimal("10.00")
