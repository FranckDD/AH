# models/prayer_book_type.py
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from .database import Base

class PrayerBookType(Base):
    __tablename__ = 'prayer_book_type'

    type_code = Column(String(10), primary_key=True)
    label = Column(String(100), nullable=False)

    consultations = relationship(
        'ConsultationSpirituel',
        back_populates='prayer_book',
        cascade='all, delete-orphan'
    )