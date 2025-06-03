# models/stock_movement.py

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from .database import Base

class StockMovement(Base):
    __tablename__ = 'stock_movement'

    movement_id   = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(Integer, ForeignKey('pharmacy.medication_id', ondelete='CASCADE'), nullable=False)
    change_qty    = Column(Integer, nullable=False)
    movement_type = Column(String(50), nullable=False)
    note          = Column(Text, nullable=True)
    created_by    = Column(String(100), nullable=False)
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)

    product = relationship('Pharmacy', back_populates='movements')

    def __repr__(self):
        return (
            f"<StockMovement(id={self.movement_id}, med_id={self.medication_id}, "
            f"change={self.change_qty}, type={self.movement_type})>"
        )
