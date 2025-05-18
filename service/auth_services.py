from ..models.user import User, pwd_context  # Importez pwd_context depuis le modèle User

class AuthService:
    def __init__(self, db_session):
        self.session = db_session
    
    def authenticate(self, username: str, password: str) -> User:
        user = self.session.query(User).filter_by(username=username).first()
        if not user or not user.check_password(password):  # Utilisez la méthode de vérification de User
            return None
        return user