# config_local.py
import os
from pathlib import Path
import configparser

DEFAULT_API = "http://127.0.0.1:8000"
#DEFAULT_API = "https://web-production-d587.up.railway.app"
APP_NAME = "Glostone-Kare"

def get_api_base():
    # 1) env
    api = os.environ.get("AH2_API_BASE")
    if api:
        return api.rstrip("/")

    # 2) config file in %APPDATA%\Glostone-Kare\config.ini (Windows)
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    cfg_path = Path(appdata) / APP_NAME / "config.ini"
    if cfg_path.exists():
        config = configparser.ConfigParser()
        config.read(cfg_path)
        try:
            return config["DEFAULT"].get("AH2_API_BASE", DEFAULT_API).rstrip("/")
        except Exception:
            pass

    # 3) fallback
    return DEFAULT_API
