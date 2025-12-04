# views/auth_view.py
import os
import inspect
from typing import Any, Optional, cast
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QToolButton
)
from PyQt6.QtGui import QPixmap, QIcon, QKeyEvent, QCloseEvent, QShowEvent
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from view_pyqt6.controller_resolver import ControllerResolver
from view_pyqt6.factory.dashboard_factory import get_dashboard_class
import sys  # ← Ajout pour resource_path


def resource_path(relative_path: str) -> str:
    """Retourne chemin absolu pour assets/DB en dev ou EXE bundled (PyInstaller)."""
    try:
        # PyInstaller temp dir
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class PasswordLineEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Mot de passe")
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #ffffff;
                font-size: 14px;
                color: black;
            }
        """)

        self.toggle_button = QToolButton()
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        eye_off_path = resource_path(os.path.join("assets", "eye-off.png"))  # ← Fix : resource_path
        self.toggle_button.setIcon(QIcon(eye_off_path if os.path.exists(eye_off_path) else ""))
        self.toggle_button.setIconSize(QSize(20, 20))
        self.toggle_button.setStyleSheet("""
            QToolButton { background: transparent; border: none; padding: 0px 8px; }
        """)
        self.toggle_button.clicked.connect(self.toggle_password_visibility)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.toggle_button)

    def toggle_password_visibility(self):
        if self.line_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            eye_path = resource_path(os.path.join("assets", "eye.png"))  # ← Fix : resource_path
            self.toggle_button.setIcon(QIcon(eye_path if os.path.exists(eye_path) else ""))
        else:
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            eye_off_path = resource_path(os.path.join("assets", "eye-off.png"))  # ← Fix : resource_path
            self.toggle_button.setIcon(QIcon(eye_off_path if os.path.exists(eye_off_path) else ""))

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str):
        self.line_edit.setText(text)

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)


class AuthView(QMainWindow):
    def __init__(self, controllers: Any):
        """
        controllers: object contenant (au minimum)
            - controllers.gateway
            - controllers.auth_manager
            - controllers.network_manager
            - controllers.controller
            - controllers.fallback_controller
        """
        super().__init__()
        self.controllers = controllers
        self.gateway = getattr(controllers, "gateway", None)
        self.auth_manager = getattr(controllers, "auth_manager", None)
        self.network_manager = getattr(controllers, "network_manager", None)
        self.controller_resolver = ControllerResolver(controllers)

        self.setWindowTitle("Glostone-Kare - Authentification")
        self.resize(400, 600)
        self.setMinimumSize(360, 520)
        icon_path = resource_path(os.path.join("assets", "icon.png"))  # ← Fix : resource_path pour icon
        self.setWindowIcon(QIcon(icon_path if os.path.exists(icon_path) else ""))

        # style global (dégradé blanc -> vert léger)
        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e8f5e9, stop:1 #81c784); }
            QLabel#titleLabel { font-size: 22px; font-weight: bold; color: #2e7d32; }
            QLineEdit { padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: #ffffff; font-size: 14px; color: black; }
            QPushButton { padding: 10px; border-radius: 8px; background: #2e7d32; color: white; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #256028; }
            QLabel { color: #2e7d32; }
            QToolButton { background: transparent; border: none; }
        """)

        # animation d'ouverture
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(600)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._create_login_ui()

    # signatures acceptant Optional[...] pour éviter warnings pylance (base peut fournir None)
    def showEvent(self, a0: Optional[QShowEvent]) -> None:
        # démarrer animation d'opacité sur show
        try:
            self.setWindowOpacity(0.0)
            self.opacity_anim.start()
        except Exception:
            pass
        super().showEvent(a0)

    def keyPressEvent(self, a0: Optional[QKeyEvent]) -> None:
            # On déclenche login sur Enter
            if a0 is not None and a0.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                try:
                    self._on_login()
                except Exception as e:
                    # protège contre crash si l'UI a changé pendant le traitement
                    print("KeyPress login handler error (ignored):", e)
            super().keyPressEvent(a0)



    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        reply = QMessageBox.question(
            self, 'Quitter', 'Voulez-vous vraiment quitter ?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if a0 is not None:
                a0.accept()
            else:
                super().closeEvent(a0)
        else:
            if a0 is not None:
                a0.ignore()

    def _create_login_ui(self):
        """Crée (ou recrée) l'UI de login"""
        # supprimer l'ancien widget central si présent
        try:
            old = self.centralWidget()
            if old:
                old.deleteLater()
        except Exception:
            pass

        self.login_widget = QWidget()
        layout = QVBoxLayout(self.login_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(18)

        title = QLabel("Bienvenue sur Glostone-Kare")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # logo
        logo_path = resource_path(os.path.join("assets", "ahlogo.png"))  # ← Fix : resource_path
        if not os.path.isfile(logo_path):
            logo_path = resource_path(os.path.join("assets", "ahlogo.png"))  # Double check
        pix = QPixmap(logo_path) if os.path.exists(logo_path) else QPixmap()
        if pix.isNull():
            print("[AUTHVIEW] Logo null – Vérifie bundle assets")  # Debug
        logo = pix.scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label = QLabel()
        logo_label.setPixmap(logo)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # username
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Nom d'utilisateur")
        self.username_entry.returnPressed.connect(self._on_login)
        layout.addWidget(self.username_entry)

        # password widget
        self.password_widget = PasswordLineEdit()
        layout.addWidget(self.password_widget)

        # login button
        login_button = QPushButton("Se connecter")
        login_button.clicked.connect(self._on_login)
        layout.addWidget(login_button)

        # error label (rouge, fond léger)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            "background-color: rgba(255, 235, 238, 0.95); color: #b71c1c; padding: 8px; border-radius: 6px;"
        )
        if getattr(self, "error_label", None) is not None:
            try:
                self.error_label.hide()
            except RuntimeError:
                # le widget a été supprimé — on ignore silencieusement
                pass
        layout.addWidget(self.error_label)

        # spacer pour que le contenu reste centré quand la fenêtre est grande
        layout.addStretch()

        self.setCentralWidget(self.login_widget)

    def _instantiate_dashboard(self, cls, parent, user, controllers, on_logout):
        """
        Instancie `cls` en respectant l'ordre réel des paramètres du __init__.
        Mappe automatiquement noms courants -> valeurs.
        Lève RuntimeError si un param requis ne peut être fourni.
        """
        try:
            sig = inspect.signature(cls.__init__)
        except Exception as e:
            raise RuntimeError(f"Impossible d'analyser la signature de {cls}: {e}") from e

        params = list(sig.parameters.values())[1:]  # skip 'self'
        mapping = {
            "parent": parent,
            "parent_window": parent,
            "parent_widget": parent,
            "window": parent,
            "master": parent,
            "user": user,
            "current_user": user,
            "controller": controllers,
            "controllers": controllers,
            "controllers_obj": controllers,
            "on_logout": on_logout,
            "on_logout_cb": on_logout,
            "logout_callback": on_logout,
        }

        args = []
        for p in params:
            name = p.name
            if name in mapping:
                args.append(mapping[name])
            else:
                if p.default is inspect._empty:
                    raise RuntimeError(f"Constructeur de {cls.__name__} requiert le paramètre '{name}' que je ne sais pas fournir.")
                # param a un défaut, on ignore

        # tenter instanciation
        try:
            return cls(*args)
        except TypeError as e_pos:
            # fallback patterns
            fallbacks = [
                (parent, user, controllers, on_logout),
                (parent, user, controllers),
                (parent, controllers, on_logout),
                (parent, controllers),
                (parent, user),
                (parent,)
            ]
            last_exc = e_pos
            for f in fallbacks:
                try:
                    return cls(*f)
                except TypeError as e:
                    last_exc = e
                    continue
                except Exception as e:
                    raise RuntimeError(f"Erreur lors de l'instanciation de {cls}: {e}") from e
            raise RuntimeError(f"Impossible d'instancier {cls!r}. Dernière erreur: {last_exc}") from last_exc

    def _on_login(self):
        """Traite la tentative de connexion"""
        try:
            self.error_label.hide()
        except RuntimeError:
            pass

        username = self.username_entry.text().strip()
        password = self.password_widget.text().strip()

        if not username or not password:
            self._show_error("Veuillez saisir le nom d'utilisateur et le mot de passe.")
            return

        user_info = None
        token = None

        # Vérifier le mode online/offline
        is_offline = getattr(self.network_manager, "offline_mode", False) if self.network_manager else False
        print(f"[AUTHVIEW DEBUG] Mode offline : {is_offline}")  # ← Debug pour tracer

        if not is_offline and self.auth_manager:
            # Mode online : Utiliser AuthManager
            try:
                success, payload = self.auth_manager.login(username, password)
                if success:
                    user_info = payload.get("user")
                    token = payload.get("token")
                    print(f"[AUTHVIEW DEBUG] Online login OK : {user_info.get('username', 'unknown')}")  # Debug
                else:
                    err = payload.get("error") or payload.get("details") or "Erreur d'authentification"
                    self._show_error(f"Erreur de connexion : {err}")
                    return
            except Exception as e:
                print(f"[AUTHVIEW DEBUG] Online login fail : {e}")  # Debug
                self._show_error(f"Erreur réseau lors de la connexion : {e}")
                is_offline = True  # Bascule vers offline si l'API échoue

        if is_offline:
            # Mode offline : Utiliser AuthController via ControllerResolver
            try:
                auth_controller = self.controller_resolver.auth_controller()
                print(f"[AUTHVIEW DEBUG] Auth controller résolu : {type(auth_controller).__name__ if auth_controller else 'None'}")  # ← Debug clé
                if auth_controller is None:
                    self._show_error("Erreur critique : Offline mode non disponible (resolver échoué). Vérifiez bundle EXE.")
                    print("[AUTHVIEW ERROR] auth_controller None – Check resolver logs")
                    return
                
                # Guard explicite pour Pylance et runtime : check hasattr
                if not hasattr(auth_controller, 'authenticate'):
                    self._show_error("Erreur critique : Auth controller sans méthode 'authenticate'.")
                    print("[AUTHVIEW ERROR] No 'authenticate' attr")
                    return
                
                user_info = auth_controller.authenticate(username, password) # type: ignore
                print(f"[AUTHVIEW DEBUG] Offline auth result : {user_info is not None}")  # Debug
                if not user_info:
                    self._show_error("Nom d'utilisateur ou mot de passe incorrect.")
                    return
                token = "offline_token"  # Token fictif pour mode offline
            except Exception as e:
                print(f"[AUTHVIEW ERROR] Offline exception : {e}")  # Debug
                self._show_error(f"Erreur interne lors de la connexion offline : {e}")
                return

        if not user_info:
            self._show_error("Échec de l'authentification : utilisateur non trouvé.")
            return

        # Injecter token dans la gateway (pour mode online)
        if not is_offline and self.gateway and hasattr(self.gateway, "set_token") and token:
            try:
                self.gateway.set_token(token)
            except Exception:
                pass

        # Normaliser user_info/application_role
        if not isinstance(user_info, dict):
            try:
                user_info = vars(user_info)
            except Exception:
                user_info = {}

        app_role = user_info.get("application_role") or {}
        if not isinstance(app_role, dict):
            try:
                app_role = vars(app_role)
            except Exception:
                app_role = {"role_name": None}

        role_key = (app_role.get("role_name") or "") if isinstance(app_role, dict) else ""

        # Obtenir la classe dashboard
        DashboardCls = get_dashboard_class(role_key)
        if DashboardCls is None:
            self._show_error(f"Impossible d'ouvrir le dashboard : rôle inconnu ({role_key})")
            return

        try:
            dashboard_instance = self._instantiate_dashboard(
                DashboardCls,
                parent=self,
                user=user_info,
                controllers=self.controllers,
                on_logout=self._on_logout
            )
        except Exception as e:
            self._show_error(f"Impossible d'ouvrir le dashboard : {e}")
            print("DEBUG dashboard instantiation error:", repr(e))
            return

        try:
            if isinstance(dashboard_instance, QWidget):
                self.dashboard_widget = dashboard_instance
                self.setCentralWidget(self.dashboard_widget)
            else:
                widget_candidate = getattr(dashboard_instance, "widget", None) or getattr(dashboard_instance, "get_widget", None)
                if callable(widget_candidate):
                    widget_candidate = widget_candidate()
                if isinstance(widget_candidate, QWidget):
                    self.dashboard_widget = widget_candidate
                    self.setCentralWidget(self.dashboard_widget)
                else:
                    try:
                        self.dashboard_widget = dashboard_instance
                        self.setCentralWidget(self.dashboard_widget)
                    except Exception:
                        self._show_error("Dashboard instancié mais impossible de l'afficher (non QWidget).")
                        print("DEBUG dashboard not displayable:", type(dashboard_instance))
                        return
        except Exception as e:
            self._show_error(f"Erreur affichage dashboard : {e}")
            print("DEBUG dashboard display error:", repr(e))
            return

        try:
            self.resize(1024, 768)
            self.setMinimumSize(800, 600)
        except Exception:
            pass





    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def _on_logout(self):
        # logout via auth_manager si disponible
        try:
            if getattr(self.controllers, "auth_manager", None):
                self.controllers.auth_manager.logout()
        except Exception:
            pass

        # retirer dashboard si présent
        try:
            if getattr(self, "dashboard_widget", None):
                self.dashboard_widget.deleteLater()
        except Exception:
            pass

        # recréer UI login
        self._create_login_ui()
        try:
            self.resize(400, 600)
            self.setMinimumSize(360, 520)
        except Exception:
            pass