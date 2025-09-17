#!/usr/bin/env python3
"""
main_test_auth.py
Test rapide de l'authentification via la factory (online/offline).

Usage (exemples):
  python main_test_auth.py --mode offline --sqlite offline.db --username Med3 --password secret
  python main_test_auth.py --mode auto --username admin --password secret

Si username/password non fournis en args, le script te les demandera en entrée.
"""

import sys
import os
import argparse
import logging
from getpass import getpass

# --- Ajuste le path pour trouver les modules du projet (si tu lances depuis AH2/) ---
# place ce script à la racine AH2/ ; on ajoute le dossier courant au sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Si ton code est dans un sous-dossier, adapte ci-dessus (par ex. os.path.join(HERE, "AH2"))
# --- /adjust path ---

# Import la factory
try:
    from controller.controller_offline.auth_controller_factory import get_auth_controller
except Exception as e:
    print("Erreur import factory get_auth_controller:", e)
    raise

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Test Auth (online/offline) via factory")
    parser.add_argument("--mode", choices=["auto", "online", "offline"], default="auto",
                        help="Mode : auto|online|offline")
    parser.add_argument("--sqlite", default="offline.db", help="Chemin vers offline sqlite db")
    parser.add_argument("--pg", default=None, help="Optional Postgres connection string (pour online)")
    parser.add_argument("--username", help="Nom d'utilisateur à tester")
    parser.add_argument("--password", help="Mot de passe (non recommandé en CLI)")

    args = parser.parse_args()

    username = args.username or input("Username: ")
    password = args.password or getpass("Password: ")

    # Instancie la factory
    try:
        auth_ctrl, backend = get_auth_controller(mode=args.mode,
                                                pg_conn_string=args.pg,
                                                sqlite_path=args.sqlite)
    except Exception as e:
        logging.exception("Impossible d'instancier l'auth controller")
        return 2

    logging.info("Factory a renvoyé backend=%s controller=%s", backend, type(auth_ctrl).__name__)

    # Appel authentication
    try:
        user = auth_ctrl.authenticate(username, password)
        if user:
            print("==> Authentification OK (backend=%s)" % backend)
            # Essaye d'afficher les infos pertinentes de l'utilisateur
            try:
                # Pour OfflineUser ou User: affiche ce qu'on a
                vals = {
                    "user_id": getattr(user, "user_id", None),
                    "username": getattr(user, "username", None),
                    "full_name": getattr(user, "full_name", None),
                    "postgres_role": getattr(user, "postgres_role", None),
                }
                for k, v in vals.items():
                    print(f"  {k}: {v}")
            except Exception:
                print("Utilisateur (objet):", user)
        else:
            print("==> Authentification échouée (user introuvable ou mot de passe incorrect)")
    except Exception as e:
        logging.exception("Erreur pendant l'authentification: %s", e)
    finally:
        # Ferme proprement si possible
        try:
            if hasattr(auth_ctrl, "close"):
                auth_ctrl.close()
            # Si l'auth_ctrl expose sqlite_manager, on peut fermer aussi
            if getattr(auth_ctrl, "sqlite_manager", None) is not None:
                mgr = auth_ctrl.sqlite_manager
                if hasattr(mgr, "close"):
                    try:
                        mgr.close()
                    except Exception:
                        pass
        except Exception:
            logging.exception("Erreur lors du close final")

    return 0


if __name__ == "__main__":
    sys.exit(main())
