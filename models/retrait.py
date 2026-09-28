import uuid
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
from sqlalchemy.dialects.postgresql import UUID
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

    # 🟢 AJOUTS
    category = Column(String(50), nullable=True)       # Peut être null
    payment_method = Column(String(50), nullable=True) # Peut être null
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

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



