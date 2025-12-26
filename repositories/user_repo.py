# repositories/user_repo.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from models.user import User   
from models.application_role import ApplicationRole
from models.medical_speciality import MedicalSpecialty
import logging

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_username(self, username: str) -> User:
        try:
            return (
                self.session.query(User)
                    .options(joinedload(User.application_role))
                    .filter_by(username=username)
                    .one_or_none()
            )
        except Exception:
            logging.exception(f"Erreur récupération user « {username} »")
            raise

    def create_user(self, username, password, full_name, **kwargs):
        user = User(username=username, full_name=full_name, **kwargs)
        user.set_password(password)
        self.session.add(user)
        try:
            self.session.commit()
            return user
        except Exception:
            self.session.rollback()
            logging.exception("Erreur création user")
            raise


    def get_user_by_id(self, user_id: int) -> User | None:
        """
        Renvoie un utilisateur par ID, ou None s’il n’existe pas.
        """
        return (
            self.session
                .query(User)
                .options(
                    joinedload(User.application_role),
                    joinedload(User.specialty)
                )
                .filter(User.user_id == user_id)
                .one_or_none()
        )

    def search_users(self, query: str) -> list[User]:
        """
        Recherche les utilisateurs dont :
        - l'ID = query (si query est un entier)
        - ou le username, full_name, role_name ou specialty.name contient query (cas ILIKE).
        """
        q = query.strip()
        filters = []

        if q.isdigit():
            filters.append(User.user_id == int(q))

        pattern = f"%{q}%"
        filters.extend([
            User.username.ilike(pattern),
            User.full_name.ilike(pattern),
        ])
        filters.append(ApplicationRole.role_name.ilike(pattern))
        filters.append(MedicalSpecialty.name.ilike(pattern))

        try:
            #  ici, on évite d’écraser `query`
            user_query = (
                self.session.query(User)
                .join(ApplicationRole, User.role_id == ApplicationRole.role_id)
                .join(MedicalSpecialty, User.specialty_id == MedicalSpecialty.specialty_id, isouter=True)
                .options(
                    joinedload(User.application_role),
                    joinedload(User.specialty)
                )
                .filter(or_(*filters))
            )
            return user_query.all()
        except Exception:
            logging.exception(f"Erreur recherche users pour « {q} »")
            raise

    def list_users(self) -> list[User]:
        """
        Renvoie tous les utilisateurs.
        """
        return (
            self.session
                .query(User)
                .options(
                    joinedload(User.application_role),
                    joinedload(User.specialty)
                )
                .all()
        )
    
    def delete_user(self, user_id: int) -> bool:
        """
        Supprime l'utilisateur dont l'ID est user_id.
        Renvoie True si la suppression a réussi, False si l'utilisateur n'existait pas.
        """
        user = self.session.get(User, user_id)
        if not user:
            return False

        try:
            self.session.delete(user)
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logging.exception(f"Erreur suppression de l'utilisateur {user_id}")
            raise