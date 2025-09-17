from models.database import DatabaseManager
from view.auth_view import AuthView
from controller.auth_controller import AuthController
import sys
import models

from controller.controller_offline.auth_controller_factory import get_auth_controller
import sys

def main():
    # --- Récupère le controller selon la dispo du backend ---
    auth_controller, backend = get_auth_controller(
        mode="auto",  # auto = online si possible, offline sinon
        pg_conn_string="postgresql://postgres:Admin_2025@localhost/AH2",
        sqlite_path="offline.db"
    )
    print(f"Backend utilisé: {backend}")

    # --- Création de la vue ---
    app = AuthView(auth_controller)

    try:
        app.mainloop()
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
    finally:
        # ferme proprement la session si offline
        if backend == "offline" and hasattr(auth_controller, "close"):
            auth_controller.close()


if __name__ == "__main__":
    main()
