# models/stock_count.py
"""Comptage physique du stock de la pharmacie : comptages, lignes, reglages (migration 026)."""
from sqlalchemy import (
    Column, Integer, SmallInteger, String, DateTime, Text, ForeignKey,
    CheckConstraint, UniqueConstraint, Index, text,
)
from sqlalchemy import func
from .database import Base


class StockCount(Base):
    __tablename__ = 'stock_counts'
    __table_args__ = (
        CheckConstraint("status IN ('en_cours','valide','abandonne')", name="stock_counts_status_check"),
        CheckConstraint("scope IN ('tous','selection')", name="stock_counts_scope_check"),
        Index("uq_stock_counts_one_open_per_user", "started_by", unique=True,
              postgresql_where=text("status = 'en_cours'")),
        Index("idx_stock_counts_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    status = Column(String(20), nullable=False, default='en_cours', server_default='en_cours')
    started_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    started_at = Column(DateTime, nullable=False,
                        server_default=text("(now() AT TIME ZONE 'UTC')"))
    submitted_at = Column(DateTime, nullable=True)
    scope = Column(String(20), nullable=False, default='tous', server_default='tous')


class StockCountLine(Base):
    __tablename__ = 'stock_count_lines'
    __table_args__ = (
        CheckConstraint("counted_qty >= 0", name="stock_count_lines_counted_check"),
        CheckConstraint("previous_qty >= 0", name="stock_count_lines_previous_check"),
        CheckConstraint("movements_during >= 0", name="stock_count_lines_movements_check"),
        UniqueConstraint("count_id", "product_id", name="stock_count_lines_count_product_key"),
        Index("idx_stock_count_lines_count", "count_id"),
    )

    id = Column(Integer, primary_key=True)
    count_id = Column(Integer, ForeignKey('stock_counts.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('pharmacy.medication_id'), nullable=False)
    counted_qty = Column(Integer, nullable=False)
    previous_qty = Column(Integer, nullable=False)
    difference = Column(Integer, nullable=False)
    observation = Column(Text, nullable=True)
    movements_during = Column(Integer, nullable=False, default=0, server_default='0')
    counted_at = Column(DateTime, nullable=False)  # UTC naif, heure ou la ligne a ete comptee (027)
    movements_net = Column(Integer, nullable=False, default=0, server_default='0')  # somme des mouvements apres counted_at
    adjustment_request_id = Column(Integer, ForeignKey('stock_adjustment_requests.id'), nullable=True)


class StockCountSettings(Base):
    __tablename__ = 'stock_count_settings'
    __table_args__ = (
        CheckConstraint("id = 1", name="stock_count_settings_single_row_check"),
        CheckConstraint("interval_days BETWEEN 1 AND 365", name="stock_count_settings_interval_check"),
    )

    id = Column(SmallInteger, primary_key=True)
    interval_days = Column(Integer, nullable=False, default=30, server_default='30')
    updated_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())
