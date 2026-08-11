# managers/auth_manager.py (corrigé)
from PyQt6.QtCore import QSettings
from typing import Tuple, Optional, Dict, Any

class AuthManager:
    def __init__(self, gateway):
        self.gateway = gateway
        self.settings = QSettings("Glostone-kare", "Auth")
        self.current_user: Optional[Dict[str, Any]] = None

    @staticmethod
    def _extract_error_message(res: Dict[str, Any]) -> str:
        """Extrait un message d'erreur lisible quel que soit le format renvoye :
        'detail' (FastAPI, ex: 401/429), liste de 'detail' (422 validation),
        ou 'error'/'details' (erreurs internes de la passerelle : reseau, JSON invalide)."""
        detail = res.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            msgs = [d.get("msg", str(d)) for d in detail if isinstance(d, dict)]
            if msgs:
                return "; ".join(msgs)
        if res.get("details"):
            return str(res["details"])
        if res.get("error"):
            return str(res["error"])
        return "Erreur inconnue du serveur"

    def login(self, username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
        res = self.gateway.login(username, password)
        if not isinstance(res, dict):
            return False, {"error": "invalid_response", "details": "Réponse inattendue du serveur"}

        # Extraire le token (plusieurs formats possibles gérés)
        token = res.get("access_token") or (res.get("data") or {}).get("access_token") or res.get("token")
        if not token:
            message = self._extract_error_message(res)
            return False, {"error": "login_failed", "details": message}

        # stocker token et l'injecter
        try:
            self.gateway.set_token(token)
        except Exception:
            pass
        self.settings.setValue("token", token)
        self.settings.sync()

        # Récupérer les infos utilisateur via /auth/me
        user_info_res = self.gateway.request("GET", "/auth/me")
        user_info = {}
        if isinstance(user_info_res, dict):
            # différentes formes possibles : { "id":..., "username":..., "application_role": {...} }
            # ou wrapped { "success": True, "data": {...} }
            user_info = user_info_res.get("data") or user_info_res
            # si il y a une clé "error", ignore
            if user_info.get("error"):
                user_info = {}
        return True, {"user": user_info or {}, "token": token}

    def auto_login(self) -> Tuple[bool, Dict[str, Any]]:
        token = self.settings.value("token", None)
        if not token:
            return False, {"error": "no_token", "details": "Aucun token enregistré"}
        try:
            self.gateway.set_token(token)
        except Exception:
            pass

        # Vérifier /auth/me
        res = self.gateway.request("GET", "/auth/me")
        if not isinstance(res, dict) or res.get("error"):
            return False, {"error": "invalid_token", "details": res.get("details") or res.get("error") or "Token invalide"}
        user_info = res.get("data") or res or {}
        return True, {"user": user_info, "token": token}

    def logout(self):
        self.settings.remove("token")
        self.settings.sync()
        try:
            self.gateway.set_token(None)
        except Exception:
            pass
        self.current_user = None
