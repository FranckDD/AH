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

    def create_user(self, username, password, full_name,email=None, contact=None, **kwargs):
        user = User(username=username, full_name=full_name,email=email,       # Ajout
            contact=contact, **kwargs)
        user.set_password(password)
        self.session.add(user)
        try:
            self.session.commit()
            self.session.refresh(user)
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
            User.email.ilike(pattern),   # Ajout recherche par email
            User.contact.ilike(pattern),
        ])
        filters.append(ApplicationRole.role_name.ilike(pattern))
        filters.append(MedicalSpecialty.name.ilike(pattern))

        try:
            #  ici, on évite d’écraser `query`
            user_query = (
                self.session.query(User)
                .join(ApplicationRole, User.role_id == ApplicationRole.role_id, isouter=True)
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

    def list_users(self, page: int = 1, per_page: int = 50) -> list[User]:
        """
        Renvoie une page d'utilisateurs.
        """
        # Calculer le décalage (offset)
        offset = (page - 1) * per_page
        
        return (
            self.session
                .query(User)
                .options(
                    joinedload(User.application_role),
                    joinedload(User.specialty)
                )
                .offset(offset)  # ⬅️ NOUVEAU : Décalage
                .limit(per_page) # ⬅️ NOUVEAU : Limite (taille de la page)
                .all()
        )
    
    def list_users_paginated(self, page: int = 1, per_page: int = 50) -> tuple[list[User], int]:
        """Comme list_users(), mais renvoie aussi le nombre total de comptes.
        Le total est calcule AVANT offset/limit - sinon il vaudrait la taille
        de la page, ce qui bloquait la pagination sur un seul ecran."""
        requete = (
            self.session.query(User)
            .options(
                joinedload(User.application_role),
                joinedload(User.specialty),
            )
        )
        total = requete.order_by(None).count()
        items = requete.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    def search_users_paginated(self, term: str, page: int = 1, per_page: int = 50) -> tuple[list[User], int]:
        """Recherche paginee. L'ancienne search_users() renvoyait tous les
        resultats d'un coup : page et per_page etaient ignores."""
        q = term.strip()
        filters = []
        if q.isdigit():
            filters.append(User.user_id == int(q))
        pattern = f"%{q}%"
        filters.extend([
            User.username.ilike(pattern),
            User.full_name.ilike(pattern),
            User.email.ilike(pattern),
            User.contact.ilike(pattern),
        ])
        filters.append(ApplicationRole.role_name.ilike(pattern))
        filters.append(MedicalSpecialty.name.ilike(pattern))

        requete = (
            self.session.query(User)
            .join(ApplicationRole, User.role_id == ApplicationRole.role_id, isouter=True)
            .join(MedicalSpecialty, User.specialty_id == MedicalSpecialty.specialty_id, isouter=True)
            .options(
                joinedload(User.application_role),
                joinedload(User.specialty),
            )
            .filter(or_(*filters))
        )
        total = requete.order_by(None).count()
        items = requete.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

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

    def get_users_by_role_name(self, role_name_pattern: str) -> list[User]:
        try:
            return (
                self.session.query(User)
                .join(ApplicationRole)
                .options(joinedload(User.specialty)) # Pour avoir le nom de la spécialité
                .filter(ApplicationRole.role_name.ilike(f"%{role_name_pattern}%"))
                .filter(User.is_active == True)
                .all()
            )
        except Exception:
            raise

    def get_users_by_role_names(self, role_names: list[str]) -> list[User]:
        """Comme get_users_by_role_name, mais correspondance exacte sur
        plusieurs roles a la fois (ex: ['admin', 'promoteur']) - utilise
        .in_() plutot que .ilike() car on veut une liste fermee de roles
        precis, pas un motif partiel."""
        return (
            self.session.query(User)
            .join(ApplicationRole)
            .filter(ApplicationRole.role_name.in_(role_names))
            .filter(User.is_active == True)
            .all()
        )