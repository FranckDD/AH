# models/consultation_spirituel.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, ForeignKey,ARRAY
from sqlalchemy.orm import relationship
from .database import Base
from .prayer_book_type import PrayerBookType  # Import to ensure registry knows this class

class ConsultationSpirituel(Base):
    __tablename__ = 'consultation_spirituel'

    consultation_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.patient_id'), nullable=False)
    consultation_date = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    created_by_name = Column(String(100), nullable=False)
    notes = Column(Text)

    type_consultation = Column(String(30), nullable=False)
    presc_generic         = Column(ARRAY(String(20)))    # <--- devenu tableau
    presc_med_spirituel   = Column(ARRAY(String(10)))    # <--- devenu tableau
    mp_type               = Column(ARRAY(String(10))) 
    psaume = Column(String(50))  # Psaume choisi

    fr_registered_at = Column(DateTime)
    fr_appointment_at = Column(DateTime)
    fr_amount_paid = Column(Numeric(10,2))
    fr_observation = Column(Text)

    # Relationships
    patient = relationship('Patient', back_populates='spiritual_consultations')
    creator = relationship('User')
    prayer_book = relationship('PrayerBookType', back_populates='consultations')
    

    def __repr__(self):
        return f"<ConsultationSpirituel {self.consultation_id} - {self.type_consultation}>"
