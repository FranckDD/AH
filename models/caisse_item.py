# models/caisse_item.py

from sqlalchemy import ( Column, Integer,Numeric, String, Text, ForeignKey,)
from sqlalchemy.orm import relationship
from .database import Base


class CaisseItem(Base):
    __tablename__ = "caisse_item"

    item_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        Integer,
        ForeignKey("caisse.transaction_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type = Column(String(50), nullable=False)   # 'Consultation' ou 'Médicament'
    item_ref_id = Column(Integer, nullable=False)    # ID de la consultation ou du médicament
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)
    note = Column(Text, nullable=True)
    status          = Column(String, nullable=False, default='active')

    # Relation vers Caisse
    transaction = relationship("Caisse", back_populates="items")

    def __repr__(self):
        return (
            f"<CaisseItem(id={self.item_id}, txn={self.transaction_id}, "
            f"type={self.item_type}, ref_id={self.item_ref_id}, "
            f"qty={self.quantity}, total={self.line_total})>"
        )
