from sqlalchemy.orm import Session
from models.application_role import ApplicationRole
from models.medical_speciality import MedicalSpecialty
from models.database import DatabaseManager


class RoleRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_roles(self) -> list[ApplicationRole]:
        return (
            self.session
                .query(ApplicationRole)
                .order_by(ApplicationRole.role_name)
                .all()
        )

    def list_specialties(self) -> list[MedicalSpecialty]:
        return (
            self.session
                .query(MedicalSpecialty)
                .order_by(MedicalSpecialty.name)
                .all()
        )
