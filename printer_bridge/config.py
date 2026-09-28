# printer_bridge/config.py
import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Charge la config du pont depuis un fichier JSON local (jamais commite
    en clair - config.json est dans .gitignore, seul config.example.json
    est versionne). Leve FileNotFoundError explicitement si absent, plutot
    que de demarrer silencieusement avec des valeurs par defaut dangereuses
    (ex. token vide qui accepterait n'importe quelle requete)."""
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Fichier de configuration introuvable : {path}. "
            f"Copiez config.example.json vers config.json et renseignez-le."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
