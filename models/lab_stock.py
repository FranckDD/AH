# models/lab_stock.py
"""Stock labo (migration 021)."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text, Boolean, Numeric, ForeignKey,
    CheckConstraint, Index, func, text,
)
from sqlalchemy.orm import relationship
from .database import Base


class LabStockProduct(Base):
    __tablename__ = 'lab_stock_products'
    __table_args__ = (
        CheckConstraint("alert_threshold >= 0", name="lab_stock_products_threshold_check"),
        CheckConstraint("quantity >= 0", name="lab_stock_products_quantity_check"),
        Index("uq_lab_stock_products_name_active", func.lower(text("name")),
              unique=True, postgresql_where=text("is_active")),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    packaging = Column(String(100), nullable=True)
    alert_threshold = Column(Integer, nullable=False, default=0, server_default='0')
    supplier = Column(String(150), nullable=True)
    quantity = Column(Integer, nullable=False, default=0, server_default='0')
    last_counted_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text('true'))
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())


class LabStockReceipt(Base):
    __tablename__ = 'lab_stock_receipts'
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="lab_stock_receipts_total_check"),
        Index("idx_lab_stock_receipts_delivery_date", "delivery_date"),
        CheckConstraint("status IN ('valide','annule')", name="lab_stock_receipts_status_check"),
        Index("uq_lab_stock_receipts_supplier_invoice",
              func.lower(text("supplier")), func.lower(text("invoice_number")),
              unique=True, postgresql_where=text("status = 'valide'")),
    )

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100), nullable=False)
    supplier = Column(String(150), nullable=False)
    delivery_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0, server_default='0')
    status = Column(String(20), nullable=False, default='valide', server_default='valide')
    cancel_reason = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    cancelled_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    lines = relationship('LabStockReceiptLine', back_populates='receipt',
                         cascade='all, delete-orphan', passive_deletes=True)


class LabStockReceiptLine(Base):
    __tablename__ = 'lab_stock_receipt_lines'
    __table_args__ = (
        CheckConstraint("ordered_qty IS NULL OR ordered_qty >= 0",
                        name="lab_stock_receipt_lines_ordered_check"),
        CheckConstraint("received_qty > 0", name="lab_stock_receipt_lines_received_check"),
        CheckConstraint("unit_price >= 0", name="lab_stock_receipt_lines_price_check"),
        CheckConstraint("line_total >= 0", name="lab_stock_receipt_lines_total_check"),
        Index("idx_lab_stock_receipt_lines_receipt", "receipt_id"),
        Index("idx_lab_stock_receipt_lines_product", "product_id"),
    )

    id = Column(Integer, primary_key=True)
    receipt_id = Column(Integer, ForeignKey('lab_stock_receipts.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('lab_stock_products.id'), nullable=False)
    ordered_qty = Column(Integer, nullable=True)
    received_qty = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0, server_default='0')
    line_total = Column(Numeric(10, 2), nullable=False, default=0, server_default='0')
    lot_number = Column(String(50), nullable=False)
    expiry_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)

    receipt = relationship('LabStockReceipt', back_populates='lines')
    product = relationship('LabStockProduct')


class LabStockCount(Base):
    __tablename__ = 'lab_stock_counts'

    id = Column(Integer, primary_key=True)
    counted_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    counted_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    lines = relationship('LabStockCountLine', back_populates='count',
                         cascade='all, delete-orphan', passive_deletes=True)


class LabStockCountLine(Base):
    __tablename__ = 'lab_stock_count_lines'
    __table_args__ = (
        CheckConstraint("previous_qty >= 0", name="lab_stock_count_lines_previous_check"),
        CheckConstraint("counted_qty >= 0", name="lab_stock_count_lines_counted_check"),
        Index("idx_lab_stock_count_lines_count", "count_id"),
        Index("idx_lab_stock_count_lines_product", "product_id"),
    )

    id = Column(Integer, primary_key=True)
    count_id = Column(Integer, ForeignKey('lab_stock_counts.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('lab_stock_products.id'), nullable=False)
    previous_qty = Column(Integer, nullable=False)
    counted_qty = Column(Integer, nullable=False)

    count = relationship('LabStockCount', back_populates='lines')
    product = relationship('LabStockProduct')


class LabStockMovement(Base):
    __tablename__ = 'lab_stock_movements'
    __table_args__ = (
        CheckConstraint("movement_type IN ('reception','comptage','annulation_reception')",
                        name="lab_stock_movements_type_check"),
        CheckConstraint("quantity_after >= 0", name="lab_stock_movements_after_check"),
        Index("idx_lab_stock_movements_product_date", "product_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('lab_stock_products.id'), nullable=False)
    change_qty = Column(Integer, nullable=False)
    movement_type = Column(String(30), nullable=False)
    ref_type = Column(String(30), nullable=True)
    ref_id = Column(Integer, nullable=True)
    quantity_after = Column(Integer, nullable=False)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    product = relationship('LabStockProduct')


class LabStockRequest(Base):
    __tablename__ = 'lab_stock_requests'
    __table_args__ = (
        CheckConstraint("origin IN ('signalement','seuil','peremption')",
                        name="lab_stock_requests_origin_check"),
        CheckConstraint("level IS NULL OR level IN ('bientot_fini','fini')",
                        name="lab_stock_requests_level_check"),
        CheckConstraint("status IN ('a_commander','commande','recu','annule')",
                        name="lab_stock_requests_status_check"),
        Index("idx_lab_stock_requests_status", "status"),
        Index("idx_lab_stock_requests_product", "product_id"),
        Index("idx_lab_stock_requests_closed_receipt", "closed_by_receipt_id"),
        Index("uq_lab_stock_requests_open_product", "product_id", unique=True,
              postgresql_where=text("status IN ('a_commander','commande')")),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('lab_stock_products.id'), nullable=False)
    origin = Column(String(20), nullable=False)
    level = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default='a_commander', server_default='a_commander')
    requested_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    ordered_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    expected_date = Column(Date, nullable=True)
    closed_by_receipt_id = Column(Integer, ForeignKey('lab_stock_receipts.id'), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    ordered_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    product = relationship('LabStockProduct')
