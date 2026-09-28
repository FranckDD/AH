# models/caisse.py

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base


class Caisse(Base):
    __tablename__ = "caisse"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    advance_amount    = Column(Numeric(10,2), nullable=False, default=0)
    paid_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_name = Column(String(100), nullable=False)
    handled_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    payment_method = Column(String(50), nullable=False)    # ex. 'Espèces', 'Carte', 'Chèque', etc.
    transaction_type = Column(String(50), nullable=False)  # ex. 'Consultation', 'Vente Médicament', etc.
    patient_label     = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    status          = Column(String, nullable=False, default='active')
    cancelled_by         = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    cancelled_at         = Column(DateTime, nullable=True)
    cancel_justification = Column(Text, nullable=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    upload_error = Column(Text, nullable=True)

    # Relations

    handler = relationship('User', foreign_keys=[handled_by])
    patient_by_id = relationship(
        'Patient',
        back_populates='caisse_entries_by_id',
        foreign_keys=[patient_id]
    )
    items = relationship(
        "CaisseItem",
        back_populates="transaction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


    def __repr__(self):
        return (
            f"<Caisse(id={self.transaction_id}, amount={self.amount}, "
            f"paid_at={self.paid_at}, method={self.payment_method})>"
        )


   
   
