from models.database import DatabaseManager
from view.auth_view import AuthView
from controller.auth_controller import AuthController
import sys
import models

def main():
    # Initialisation de la base de données
    db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
    db.create_tables()

    # Initialisation du contrôleur
    auth_controller = AuthController()

    # Création de la vue
    app = AuthView(auth_controller)
    
    try:
        app.mainloop()
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
    finally:
        db.engine.dispose()

if __name__ == "__main__":
    main()

    