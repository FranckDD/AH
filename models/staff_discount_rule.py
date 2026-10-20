# models/staff_discount_rule.py
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey,
    CheckConstraint, Index, text,
)
from sqlalchemy.sql import func
from .database import Base

STAFF_DISCOUNT_CATEGORIES = ("medicament", "examen", "consultation", "carnet", "autre_soin")


class StaffDiscountRule(Base):
    __tablename__ = 'staff_discount_rules'

    id = Column(Integer, primary_key=True)
    category = Column(String(30), nullable=False)
    min_invoice_amount = Column(Numeric(10, 2), nullable=False, default=0, server_default=text('0'))
    rate_percent = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "category IN ('medicament','examen','consultation','carnet','autre_soin')",
            name='staff_discount_rules_category_check'),
        CheckConstraint('rate_percent BETWEEN 1 AND 100', name='staff_discount_rules_rate_check'),
        CheckConstraint('min_invoice_amount >= 0', name='staff_discount_rules_min_amount_check'),
        Index('uq_staff_discount_rules_active_category', 'category', unique=True,
              postgresql_where=text('is_active')),
    )
