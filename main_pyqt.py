# main.py (client)
import sys
import os
from types import SimpleNamespace


# Assure les imports relatifs fonctionnent (ajoute la racine du projet au PYTHONPATH)
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication, QMessageBox
from api_backend.app.gateway.remote_gateway import RemoteGateway
from managers.auth_manager import AuthManager
from managers.network_manager import NetworkManager
from view_pyqt6.auth_view import AuthView
from view_pyqt6.api_controller import ApiControllerProxy


def main():
    app = QApplication(sys.argv)

    # Adresse de l'API (modifie si besoin)
    API_BASE = os.environ.get("AH2_API_BASE", "http://127.0.0.1:8000")

    # Initialise les composants
    gateway = RemoteGateway(API_BASE)
    auth_manager = AuthManager(gateway)
    network_manager = NetworkManager(gateway)

    controllers = SimpleNamespace(
        gateway=gateway,
        auth_manager=auth_manager,
        network_manager=network_manager
    )

    # Essayer un auto-login si token sauvegardé (ne bloque pas)
    try:
        authed = auth_manager.auto_login()
        if authed:
            # Optionnel : si tu veux ouvrir directement le dashboard,
            # tu peux créer et afficher le dashboard ici.
            pass
    except Exception as e:
        # Si l'API est indisponible, on affiche un avertissement mais on laisse l'UI s'ouvrir.
        QMessageBox.warning(None, "Avertissement",
                            f"Impossible de joindre l'API au démarrage : {e}\nL'application continue en mode hors-ligne.")

    # Ouvre la vue d'authentification
    auth_view = AuthView(controllers)
    auth_view.show()

    # Exécute l'application
    try:
        exit_code = app.exec()
    except Exception as e:
        print("Erreur d'exécution PyQt :", e)
        exit_code = 1

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
