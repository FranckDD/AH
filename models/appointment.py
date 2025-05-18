from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from .database import Base

class Appointment(Base):
    __tablename__ = 'appointments'

    id = Column(Integer, primary_key=True)
    patient_id = Column(
        Integer,
        ForeignKey('patients.patient_id', ondelete='CASCADE'),
        nullable=False
    )
    doctor_id = Column(
        Integer,
        ForeignKey('users.user_id', ondelete='CASCADE'),
        nullable=False
    )
    specialty = Column(String(100))
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    reason = Column(Text)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("User", back_populates="appointments")