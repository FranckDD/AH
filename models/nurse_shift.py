from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

SHIFT_TYPES = ("MATIN", "APRES_MIDI", "NUIT")


class NurseShift(Base):
    __tablename__ = 'nurse_shifts'

    id = Column(Integer, primary_key=True)
    shift_date = Column(Date, nullable=False)
    shift_type = Column(String(20), nullable=False)
    nurse_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    nurse = relationship("User", foreign_keys=[nurse_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
