# controller/staff_discount_controller.py
import math
from decimal import Decimal
from typing import Any, Dict
from repositories.staff_discount_repo import StaffDiscountRepository
from models.staff_discount_rule import STAFF_DISCOUNT_CATEGORIES

MAX_MIN_INVOICE_AMOUNT = Decimal('99999999.99')  # Numeric(10,2)


def _rule_dict(rule) -> Dict[str, Any]:
    return {
        "category": rule.category,
        "min_invoice_amount": float(rule.min_invoice_amount),
        "rate_percent": int(rule.rate_percent),
        "is_active": bool(rule.is_active),
    }


class StaffDiscountController:
    def __init__(self, repo: StaffDiscountRepository, current_user, audit_repo):
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo

    def list_rules(self):
        return [_rule_dict(r) for r in self.repo.list_rules()]

    def update_rule(self, category: str, min_invoice_amount, rate_percent: int, is_active: bool) -> Dict[str, Any]:
        if category not in STAFF_DISCOUNT_CATEGORIES:
            raise ValueError(f"Catégorie inconnue : {category}")
        if not isinstance(rate_percent, int) or isinstance(rate_percent, bool) or not (1 <= rate_percent <= 100):
            raise ValueError("Le taux doit être un entier entre 1 et 100.")
        try:
            amount = Decimal(str(min_invoice_amount))
        except Exception:
            raise ValueError("Le seuil minimum est invalide.")
        if not amount.is_finite():
            raise ValueError("Le seuil minimum doit être un nombre fini.")
        if amount < 0:
            raise ValueError("Le seuil minimum ne peut pas être négatif.")
        if amount > MAX_MIN_INVOICE_AMOUNT:
            raise ValueError("Le seuil minimum dépasse le maximum autorisé (99 999 999,99).")

        existing = self.repo.get_by_category(category)
        old_values = _rule_dict(existing) if existing else None

        rule = self.repo.upsert_rule(category, min_invoice_amount, rate_percent, is_active, self.user.user_id)
        new_values = _rule_dict(rule)

        self.audit_repo.log_user_action(
            current_user=self.user,
            resource_type="StaffDiscountRule",
            action_performed="UPDATE" if existing else "CREATE",
            resource_id=rule.id,
            old_values=old_values,
            new_values=new_values,
        )
        self.repo.session.commit()
        return new_values
