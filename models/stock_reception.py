# models/stock_reception.py
"""Fabrication, reception et avaries du stock (migration 019)."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Text, ForeignKey, CheckConstraint, Index,
)
from sqlalchemy import func
from sqlalchemy.orm import relationship
from .database import Base


class ProductionLot(Base):
    __tablename__ = 'production_lots'
    __table_args__ = (
        CheckConstraint("quantity_produced > 0", name="production_lots_quantity_check"),
        CheckConstraint("status IN ('produit','livre','recu','annule')",
                        name="production_lots_status_check"),
        Index("idx_production_lots_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    lot_number = Column(String(30), nullable=False, unique=True)
    product_id = Column(Integer, ForeignKey('pharmacy.medication_id'), nullable=False)
    quantity_produced = Column(Integer, nullable=False)
    production_date = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    producer = Column(String(150), nullable=True)
    status = Column(String(20), nullable=False, default='produit', server_default='produit')
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    product = relationship('Pharmacy')


class StockReceipt(Base):
    __tablename__ = 'stock_receipts'
    __table_args__ = (
        CheckConstraint("origin IN ('fabrication','fournisseur')",
                        name="stock_receipts_origin_check"),
        CheckConstraint("status IN ('a_controler','valide','rejete')",
                        name="stock_receipts_status_check"),
        CheckConstraint(
            "(origin = 'fabrication' AND production_lot_id IS NOT NULL) OR "
            "(origin = 'fournisseur' AND production_lot_id IS NULL)",
            name="stock_receipts_origin_lot_check"),
        Index("idx_stock_receipts_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    receipt_number = Column(String(30), nullable=False, unique=True)
    origin = Column(String(20), nullable=False)
    production_lot_id = Column(Integer, ForeignKey('production_lots.id'), nullable=True)
    supplier = Column(String(150), nullable=True)
    delivery_ref = Column(String(100), nullable=True)
    received_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default='a_controler', server_default='a_controler')
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    controlled_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    controlled_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)

    production_lot = relationship('ProductionLot')
    lines = relationship('StockReceiptLine', back_populates='receipt',
                         cascade='all, delete-orphan', passive_deletes=True)


class StockReceiptLine(Base):
    __tablename__ = 'stock_receipt_lines'
    __table_args__ = (
        CheckConstraint("qty_good >= 0", name="stock_receipt_lines_qty_good_check"),
        CheckConstraint("qty_damaged >= 0", name="stock_receipt_lines_qty_damaged_check"),
        CheckConstraint("qty_lost >= 0", name="stock_receipt_lines_qty_lost_check"),
        CheckConstraint("qty_defective >= 0", name="stock_receipt_lines_qty_defective_check"),
        Index("idx_stock_receipt_lines_receipt", "receipt_id"),
    )

    id = Column(Integer, primary_key=True)
    receipt_id = Column(Integer, ForeignKey('stock_receipts.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('pharmacy.medication_id'), nullable=False)
    qty_expected = Column(Integer, nullable=True)
    qty_good = Column(Integer, nullable=False, default=0, server_default='0')
    qty_damaged = Column(Integer, nullable=False, default=0, server_default='0')
    qty_lost = Column(Integer, nullable=False, default=0, server_default='0')
    qty_defective = Column(Integer, nullable=False, default=0, server_default='0')
    lot_number = Column(String(30), nullable=True)
    expiry_date = Column(Date, nullable=True)

    receipt = relationship('StockReceipt', back_populates='lines')
    product = relationship('Pharmacy')


class StockIncident(Base):
    __tablename__ = 'stock_incidents'
    __table_args__ = (
        CheckConstraint("kind IN ('endommage','perdu','defectueux')",
                        name="stock_incidents_kind_check"),
        CheckConstraint("quantity > 0", name="stock_incidents_quantity_check"),
        CheckConstraint("status IN ('a_controler','valide','rejete')",
                        name="stock_incidents_status_check"),
        Index("idx_stock_incidents_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('pharmacy.medication_id'), nullable=False)
    kind = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    incident_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default='a_controler', server_default='a_controler')
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    controlled_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    controlled_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)

    product = relationship('Pharmacy')


class StockAdjustmentRequest(Base):
    __tablename__ = 'stock_adjustment_requests'
    __table_args__ = (
        CheckConstraint("kind IN ('reapprovisionnement','correction')",
                        name="stock_adjustment_requests_kind_check"),
        CheckConstraint("quantity >= 0", name="stock_adjustment_requests_quantity_check"),
        CheckConstraint("kind <> 'reapprovisionnement' OR quantity > 0",
                        name="stock_adjustment_requests_reappro_qty_check"),
        CheckConstraint("status IN ('en_attente','approuve','refuse','annule')",
                        name="stock_adjustment_requests_status_check"),
        Index("idx_stock_adjustment_requests_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('pharmacy.medication_id'), nullable=False)
    kind = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='en_attente', server_default='en_attente')
    requested_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    requested_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    decided_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_note = Column(Text, nullable=True)
    stock_before = Column(Integer, nullable=True)
    stock_after = Column(Integer, nullable=True)
    # stock du systeme lu a la creation (NULL = demande anterieure a la migration 020)
    stock_at_request = Column(Integer, nullable=True)

    product = relationship('Pharmacy')
