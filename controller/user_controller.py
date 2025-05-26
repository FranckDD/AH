from repositories.user_repo import UserRepository
from repositories.role_repo import RoleRepository
from models.user import User
from sqlalchemy.exc import SQLAlchemyError

class UserController:
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository):
        self.user_repo = user_repo
        self.role_repo = role_repo

    def get_all_roles(self) -> list[str]:
        return [r.role_name for r in self.role_repo.list_roles()]

    def get_all_specialties(self) -> list[str]:
        return [s.name for s in self.role_repo.list_specialties()]

    def create_user(self, data: dict) -> User:
        try:
            return self.user_repo.create_user(
                username      = data['username'],
                password      = data['password'],
                full_name     = data['full_name'],
                postgres_role = data.get('postgres_role'),
                is_active     = data.get('is_active', True),
                role_id       = data.get('role_id'),
                specialty_id  = data.get('specialty_id')
            )
        except SQLAlchemyError as e:
            raise RuntimeError(f"Erreur création utilisateur : {e}")

    def update_user(self, user_id: int, data: dict) -> User:
        user = self.user_repo.session.query(User).get(user_id)
        if not user:
            raise ValueError(f"Utilisateur {user_id} introuvable")
        for field in ('full_name','postgres_role','is_active','role_id','specialty_id'):
            if field in data:
                setattr(user, field, data[field])
        if data.get('password'):
            user.set_password(data['password'])
        try:
            self.user_repo.session.commit()
            return user
        except SQLAlchemyError as e:
            self.user_repo.session.rollback()
            raise RuntimeError(f"Erreur mise à jour utilisateur : {e}")
        

    def get_user_by_id(self, user_id: int) -> User:
        """
        Récupère un utilisateur par son ID, ou lève ValueError s’il n’existe pas.
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"Utilisateur {user_id} introuvable")
        return user

    def search_users(self, term: str) -> list[User]:
            return self.user_repo.search_users(term)

    def list_users(self) -> list[User]:
            """
            Renvoie tous les utilisateurs.
            """
            return self.user_repo.list_users()

    def list_roles(self):
      
        return self.role_repo.list_roles()

    def list_specialties(self):
     
        return self.role_repo.list_specialties()