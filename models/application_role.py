from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .database import Base

# Import retardé
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User

class ApplicationRole(Base):
    __tablename__ = 'application_roles'

    role_id = Column(Integer, primary_key=True)
    name = Column('role_name', String(50), unique=True, nullable=False)
    
    # Relation avec User
    users = relationship("User", back_populates="role")