import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from view_pyqt6.factory.dashboard_factory import get_dashboard_class


class AuthView(QMainWindow):
    def __init__(self, controllers):
        super().__init__()
        self.controller = controllers
        self.setWindowTitle("One Health - Authentification")
        self.setFixedSize(400, 600)
        self.setWindowIcon(QIcon(os.path.join("assets", "icon.png")))
        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #e8f5e9, stop:1 #81c784); }
            QLineEdit { padding: 12px; border: none; border-radius: 8px;
                background: #ffffff; font-size: 14px; }
            QPushButton { padding: 12px; border-radius: 8px;
                background: #4caf50; color: white;
                font-weight: bold; font-size: 16px; }
            QPushButton:hover { background: #388e3c; }
            QLabel#titleLabel { font-size: 24px; font-weight: bold;
                color: #2e7d32; }
        """)

        # Animation d'ouverture
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(800)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._create_login_ui()

    def showEvent(self, event):
        self.setWindowOpacity(0.0)
        self.opacity_anim.start()
        super().showEvent(event)

    def _create_login_ui(self):
        self.login_widget = QWidget()
        layout = QVBoxLayout(self.login_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Titre
        title = QLabel("Bienvenue sur One Health")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Logo
        logo_path = os.path.join("assets", "logo_light.png")
        if not os.path.isfile(logo_path):
            logo_path = os.path.join("assets", "logo_dark.png")
        pixmap = QPixmap(logo_path)
        logo = pixmap.scaled(120, 120,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        logo_label = QLabel()
        logo_label.setPixmap(logo)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # Username
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Nom d'utilisateur")
        layout.addWidget(self.username_entry)

        # Password
        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("Mot de passe")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_entry)

        # Bouton Connexion
        login_button = QPushButton("Se connecter")
        login_button.clicked.connect(self._on_login)
        layout.addWidget(login_button)

        # Erreur label
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            "background-color: rgba(200, 230, 201, 0.8); color: #1b5e20;"
            " padding: 8px; border-radius: 6px;"
        )
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.setCentralWidget(self.login_widget)

    def _on_login(self):
        self.error_label.hide()
        username = self.username_entry.text().strip()
        password = self.password_entry.text().strip()
        try:
            tmp = self.controller.user_repo.get_user_by_username(username)
            if tmp and not tmp.is_active:
                self._show_error("Votre compte a été désactivé. Contactez l'administrateur.")
                return

            user = self.controller.authenticate(username, password)
            if not user:
                raise ValueError("Identifiants incorrects")

            role_key = user.application_role.role_name
            DashboardCls = get_dashboard_class(role_key)
            self.dashboard_widget = DashboardCls(
                parent=self,
                user=user,
                controllers=self.controller,
                on_logout=self._on_logout
            )
            self.setCentralWidget(self.dashboard_widget)
            self.resize(1024, 768)
            self.setMinimumSize(800, 600)

        except Exception as e:
            self._show_error(str(e))

    def _show_error(self, message):
        self.error_label.setText(message)
        self.error_label.show()

    def _on_logout(self):
        self.dashboard_widget.deleteLater()
        self._create_login_ui()
        self.resize(400, 600)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'Quitter', 'Voulez-vous vraiment quitter ?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()



