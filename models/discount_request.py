# models/discount_request.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class DiscountRequest(Base):
    __tablename__ = "discount_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("caisse.transaction_id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    requested_to = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    original_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    decision_percent = Column(Integer, nullable=True)
    decision_echelonne_deadline = Column(Date, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    transaction = relationship("Caisse", foreign_keys=[transaction_id])
    requester = relationship("User", foreign_keys=[requested_by])
    recipient = relationship("User", foreign_keys=[requested_to])
    decider = relationship("User", foreign_keys=[decided_by])

    def __repr__(self):
        return f"<DiscountRequest(id={self.id}, transaction={self.transaction_id}, status={self.status})>"
