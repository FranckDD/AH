from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(60), nullable=False)  # BCrypt hash
    full_name = Column(String(100), nullable=False)
    postgres_role = Column(String(20))
    is_active = Column(Boolean, default=True)
    specialty_id = Column(Integer, ForeignKey('medical_specialties.specialty_id'))
    role_id = Column(Integer, ForeignKey('application_roles.role_id'))

    from models.application_role import ApplicationRole
    application_role = relationship("ApplicationRole", back_populates="users", lazy="joined")

    appointments = relationship(
        "Appointment",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )
    specialty = relationship(
        "MedicalSpecialty",
        back_populates="doctors"
    )

    def set_password(self, password):
        """Hash le mot de passe avec CryptContext"""
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password):
        """Vérifie le mot de passe avec CryptContext"""
        return pwd_context.verify(password, self.password_hash)