# models/caisse.py
from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Caisse(Base):
    __tablename__ = 'caisse'

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    amount = Column(Numeric(10,2), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    created_by_name = Column(String(100), nullable=False)
    handled_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)

    # Relationships
    handler = relationship('User')
    patient_by_id = relationship(
        'Patient',
        back_populates='caisse_entries_by_id',
        foreign_keys=[patient_id]
    )
   
