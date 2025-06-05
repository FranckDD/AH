from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    Text,
    DateTime,
    ForeignKey,
    String
)
from sqlalchemy.orm import relationship
from models.database import Base  # ou l’équivalent de votre Base SQLAlchemy


class CaisseRetrait(Base):
    __tablename__ = "caisse_retrait"

    retrait_id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Numeric(10, 2), nullable=False)
    justification = Column(Text, nullable=True)
    retrait_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    handled_by = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    cancelled_by          = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    cancelled_at          = Column(DateTime, nullable=True)
    cancel_justification  = Column(Text, nullable=True)

    # Relation SQLAlchemy vers l’utilisateur
    user                  = relationship(
    "User", 
    back_populates="retraits", 
    foreign_keys=[handled_by]
    )
    cancelled_by_user     = relationship(
        "User", 
        foreign_keys=[cancelled_by]
    )



