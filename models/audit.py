from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base 

# Base = declarative_base() # Décommenter si vous utilisez cette méthode

class AuditAccess(Base):
    """ Modèle pour le suivi des connexions (Standard) """
    __tablename__ = "audit_access"

    access_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True) # Clé étrangère standard
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action_type = Column(String(50), nullable=False) # Ex: 'LOGIN_SUCCESS', 'LOGIN_FAILURE'
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(Text, nullable=True)

    # user = relationship("User", backref="access_audits") 

class AuditUserAction(Base):
    """ Modèle pour le suivi des actions CRUD (Standard) """
    __tablename__ = "audit_user_actions"

    action_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False) # Clé étrangère standard
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    resource_type = Column(String(50), nullable=False) # Ex: 'Patient', 'Admission'
    resource_id = Column(Integer, nullable=True)
    action_performed = Column(String(50), nullable=False) # Ex: 'CREATE', 'UPDATE'
    old_values = Column(JSONB, nullable=True) # JSONB pour les valeurs avant
    new_values = Column(JSONB, nullable=True) # JSONB pour les valeurs après
    ip_address = Column(String(45), nullable=True)
    username = Column(String(100), nullable=True)

    #user = relationship("User", back_populates="action_audits")