# AH2
git pour le projet de systeme de gestion hospitalier

def __init__(self, db_session=None):
        # Utilise la session passée par FastAPI ou crée la sienne
        if db_session:
            self.session = db_session
        else:
            self.db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
            self.session = self.db.get_session()

Admin123!  admin_test


