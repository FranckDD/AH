# repositories/staff_discount_repo.py
from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.staff_discount_rule import StaffDiscountRule


class StaffDiscountRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_rules(self) -> List[StaffDiscountRule]:
        return self.session.query(StaffDiscountRule).order_by(StaffDiscountRule.category).all()

    def get_by_category(self, category: str) -> Optional[StaffDiscountRule]:
        """Une seule ligne par categorie est maintenue (upsert) ; on prefere
        la regle active si un jeu de donnees historique en contenait plusieurs."""
        return (
            self.session.query(StaffDiscountRule)
            .filter(StaffDiscountRule.category == category)
            .order_by(StaffDiscountRule.is_active.desc(), StaffDiscountRule.id)
            .first()
        )

    def list_active_rules(self) -> List[Dict[str, Any]]:
        """Forme attendue par utils.staff_discount.compute_staff_discount."""
        rules = (
            self.session.query(StaffDiscountRule)
            .filter(StaffDiscountRule.is_active.is_(True))
            .all()
        )
        return [
            {
                "category": r.category,
                "min_invoice_amount": float(r.min_invoice_amount),
                "rate_percent": int(r.rate_percent),
                "is_active": True,
            }
            for r in rules
        ]

    def upsert_rule(self, category: str, min_invoice_amount, rate_percent: int,
                    is_active: bool, user_id: Optional[int]) -> StaffDiscountRule:
        rule = self.get_by_category(category)
        if rule is None:
            rule = StaffDiscountRule(category=category, created_by=user_id)
            self.session.add(rule)
        rule.min_invoice_amount = min_invoice_amount
        rule.rate_percent = rate_percent
        rule.is_active = is_active
        rule.updated_by = user_id
        rule.updated_at = datetime.now()
        self.session.flush()
        return rule
