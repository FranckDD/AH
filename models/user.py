#model user
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
    retraits = relationship(
        "CaisseRetrait",
        back_populates="user",
        foreign_keys="[CaisseRetrait.handled_by]"
    )

    # Retraits qu'il a annulés
    cancelled_retraits = relationship(
        "CaisseRetrait",
        back_populates="cancelled_by_user",
        foreign_keys="[CaisseRetrait.cancelled_by]"
    )

    def set_password(self, password):
        """Hash le mot de passe avec CryptContext"""
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, str(self.password_hash)) # type: ignore
    
    # Ajouter une propriété pour les permissions
    @property
    def roles(self) -> list[str]:
        # Si on a explicitement défini _roles (ex: lors du decode du token), on le retourne.
        if hasattr(self, "_roles") and self._roles is not None:
            return self._roles
        # Sinon, dériver depuis la relation application_role.role_name (si présente)
        if self.application_role and getattr(self.application_role, "role_name", None):
            from api_backend.app.security.role_map import normalize_role_name
            canon = normalize_role_name(self.application_role.role_name)
            return [canon] if canon else []
        return []

    @roles.setter
    def roles(self, value: list[str]):
        self._roles = value
