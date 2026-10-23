# models/fabrication.py
"""Fabrication : intrants, achats, lots de fabrication, consommations, parametres (migration 023)."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text, Boolean, Numeric, ForeignKey,
    CheckConstraint, Index,
)
from sqlalchemy import func
from sqlalchemy.orm import relationship
from .database import Base


class FabIntrant(Base):
    __tablename__ = 'fab_intrants'
    __table_args__ = (
        CheckConstraint("alert_threshold >= 0", name="fab_intrants_threshold_check"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    unit = Column(String(20), nullable=False)
    is_container = Column(Boolean, nullable=False, default=False, server_default='false')
    alert_threshold = Column(Numeric(12, 3), nullable=False, default=0, server_default='0')
    is_active = Column(Boolean, nullable=False, default=True, server_default='true')


class FabIntrantPurchase(Base):
    __tablename__ = 'fab_intrant_purchases'
    __table_args__ = (
        CheckConstraint("quantity > 0", name="fab_intrant_purchases_quantity_check"),
        CheckConstraint("unit_cost >= 0", name="fab_intrant_purchases_unit_cost_check"),
        CheckConstraint("remaining_qty >= 0 AND remaining_qty <= quantity",
                        name="fab_intrant_purchases_remaining_check"),
        CheckConstraint("status IN ('actif','annule')", name="fab_intrant_purchases_status_check"),
        Index("idx_fab_intrant_purchases_status", "status"),
        Index("idx_fab_intrant_purchases_intrant", "intrant_id"),
    )

    id = Column(Integer, primary_key=True)
    intrant_id = Column(Integer, ForeignKey('fab_intrants.id'), nullable=False)
    supplier = Column(String(150), nullable=True)
    delivery_ref = Column(String(100), nullable=True)
    purchase_date = Column(Date, nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    remaining_qty = Column(Numeric(12, 3), nullable=False)
    status = Column(String(20), nullable=False, default='actif', server_default='actif')
    cancel_reason = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    intrant = relationship('FabIntrant')


class FabBatch(Base):
    __tablename__ = 'fab_batches'
    __table_args__ = (
        CheckConstraint("status IN ('brouillon','en_production','termine','expedie','annule')",
                        name="fab_batches_status_check"),
        CheckConstraint("qty_good >= 0", name="fab_batches_qty_good_check"),
        CheckConstraint("qty_damaged >= 0", name="fab_batches_qty_damaged_check"),
        CheckConstraint("qty_rejected >= 0", name="fab_batches_qty_rejected_check"),
        CheckConstraint("liquid_lost >= 0", name="fab_batches_liquid_lost_check"),
        Index("idx_fab_batches_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    batch_number = Column(String(30), nullable=False, unique=True)
    product_id = Column(Integer, ForeignKey('pharmacy.medication_id'), nullable=False)
    status = Column(String(20), nullable=False, default='brouillon', server_default='brouillon')
    production_date = Column(Date, nullable=False)
    producer_name = Column(String(150), nullable=True)
    qty_good = Column(Integer, nullable=False, default=0, server_default='0')
    qty_damaged = Column(Integer, nullable=False, default=0, server_default='0')
    qty_rejected = Column(Integer, nullable=False, default=0, server_default='0')
    liquid_lost = Column(Numeric(12, 3), nullable=False, default=0, server_default='0')
    expected_qty = Column(Integer, nullable=True)
    found_qty = Column(Integer, nullable=True)
    missing_qty = Column(Integer, nullable=True)
    missing_pct = Column(Numeric(6, 2), nullable=True)
    tolerance_applied = Column(Numeric(5, 2), nullable=True)
    out_of_tolerance = Column(Boolean, nullable=False, default=False, server_default='false')
    justification = Column(Text, nullable=True)
    total_cost = Column(Numeric(12, 2), nullable=True)
    unit_cost = Column(Numeric(12, 2), nullable=True)
    delivery_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    production_lot_id = Column(Integer, ForeignKey('production_lots.id'), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    expedited_at = Column(DateTime, nullable=True)
    expedited_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)

    product = relationship('Pharmacy')
    production_lot = relationship('ProductionLot')
    consumptions = relationship('FabConsumption', back_populates='batch')


class FabConsumption(Base):
    __tablename__ = 'fab_consumptions'
    __table_args__ = (
        CheckConstraint("quantity > 0", name="fab_consumptions_quantity_check"),
        CheckConstraint("unit_cost_snapshot IS NULL OR unit_cost_snapshot >= 0",
                        name="fab_consumptions_cost_check"),
        Index("idx_fab_consumptions_batch", "batch_id"),
        Index("idx_fab_consumptions_purchase", "purchase_id"),
    )

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey('fab_batches.id'), nullable=False)
    purchase_id = Column(Integer, ForeignKey('fab_intrant_purchases.id'), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_cost_snapshot = Column(Numeric(12, 2), nullable=True)
    restored_at = Column(DateTime, nullable=True)

    batch = relationship('FabBatch', back_populates='consumptions')
    purchase = relationship('FabIntrantPurchase')


class FabSettings(Base):
    __tablename__ = 'fab_settings'
    __table_args__ = (
        CheckConstraint("id = 1", name="fab_settings_single_row_check"),
        CheckConstraint("tolerance_pct >= 0", name="fab_settings_tolerance_check"),
        CheckConstraint("stale_days > 0", name="fab_settings_stale_days_check"),
    )

    id = Column(Integer, primary_key=True)
    tolerance_pct = Column(Numeric(5, 2), nullable=False, default=2, server_default='2.00')
    stale_days = Column(Integer, nullable=False, default=7, server_default='7')
    updated_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    updated_at = Column(DateTime, nullable=True)
