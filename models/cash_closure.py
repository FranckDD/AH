# models/cash_closure.py
"""Cloture de caisse : modes de paiement, clotures, lignes par mode, corrections, depart (migration 024)."""
from sqlalchemy import (
    Column, Integer, SmallInteger, String, Date, DateTime, Text, Boolean, Numeric, ForeignKey,
    CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy import func
from .database import Base


class PaymentMode(Base):
    __tablename__ = 'payment_modes'

    code = Column(String(30), primary_key=True)
    label = Column(String(80), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default='true')
    sort_order = Column(Integer, nullable=False, default=0, server_default='0')


class CashClosure(Base):
    __tablename__ = 'cash_closures'
    __table_args__ = (
        CheckConstraint("kind IN ('manual','auto')", name="cash_closures_kind_check"),
        CheckConstraint("period_end > period_start", name="cash_closures_period_check"),
        CheckConstraint("counted_cash IS NULL OR counted_cash >= 0", name="cash_closures_counted_check"),
        CheckConstraint("opening_cash >= 0", name="cash_closures_opening_check"),
        CheckConstraint("kind = 'auto' OR closed_by IS NOT NULL", name="cash_closures_closed_by_check"),
        UniqueConstraint("period_end", name="cash_closures_period_end_key"),
        Index("idx_cash_closures_business_date", "business_date"),
    )

    id = Column(Integer, primary_key=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    business_date = Column(Date, nullable=False)
    kind = Column(String(10), nullable=False)
    closed_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    opening_cash = Column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    expected_cash = Column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    counted_cash = Column(Numeric(14, 2), nullable=True)
    difference = Column(Numeric(14, 2), nullable=True)
    opening_from_auto = Column(Boolean, nullable=False, default=False, server_default='false')
    comment = Column(Text, nullable=True)
    unsynced_ignored = Column(Boolean, nullable=False, default=False, server_default='false')


class CashClosureLine(Base):
    __tablename__ = 'cash_closure_lines'
    __table_args__ = (
        CheckConstraint("source IN ('physical','operator_statement')", name="cash_closure_lines_source_check"),
        CheckConstraint("counted IS NULL OR counted >= 0", name="cash_closure_lines_counted_check"),
        UniqueConstraint("closure_id", "mode_code", name="cash_closure_lines_closure_mode_key"),
        Index("idx_cash_closure_lines_closure", "closure_id"),
    )

    id = Column(Integer, primary_key=True)
    closure_id = Column(Integer, ForeignKey('cash_closures.id'), nullable=False)
    mode_code = Column(String(30), nullable=False)
    source = Column(String(20), nullable=False)
    opening = Column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    entries = Column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    exits = Column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    expected = Column(Numeric(14, 2), nullable=False, default=0, server_default='0')
    counted = Column(Numeric(14, 2), nullable=True)
    difference = Column(Numeric(14, 2), nullable=True)
    comment = Column(Text, nullable=True)


class CashClosureCorrection(Base):
    __tablename__ = 'cash_closure_corrections'
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')",
                        name="cash_closure_corrections_status_check"),
        CheckConstraint("length(btrim(reason)) > 0", name="cash_closure_corrections_reason_check"),
        Index("idx_cash_closure_corrections_closure", "closure_id"),
    )

    id = Column(Integer, primary_key=True)
    closure_id = Column(Integer, ForeignKey('cash_closures.id'), nullable=False)
    mode_code = Column(String(30), nullable=False)
    amount_delta = Column(Numeric(14, 2), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='pending', server_default='pending')
    requested_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)


class CashClosureStart(Base):
    """Ligne unique (id = 1) : debut du suivi de caisse et solde d'ouverture initial. Immuable."""
    __tablename__ = 'cash_closure_start'
    __table_args__ = (
        CheckConstraint("id = 1", name="cash_closure_start_single_row_check"),
        CheckConstraint("opening_cash >= 0", name="cash_closure_start_opening_check"),
    )

    id = Column(SmallInteger, primary_key=True, default=1)
    started_at = Column(DateTime(timezone=True), nullable=False)
    opening_cash = Column(Numeric(14, 2), nullable=False)
    set_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
