import sys
from PyQt6.QtWidgets import QApplication
from models.database import DatabaseManager
from controller.auth_controller import AuthController
from view_pyqt6.auth_view import AuthView


def main():
    # Initialisation de la base de données (optionnelle)
    db = None
    # Pour activer la base, décommentez ci-dessous :
    # db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
    # db.create_tables()

    # Contrôleur d'authentification
    auth_controller = AuthController()

    # Création de l'application Qt et de la vue
    app = QApplication(sys.argv)
    auth_view = AuthView(auth_controller)
    auth_view.show()

    # Boucle d'événements
    exit_code = app.exec()

    # Nettoyage
    if db is not None:
        db.engine.dispose()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
