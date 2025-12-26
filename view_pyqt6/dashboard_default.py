import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class DefaultDashboardView(QWidget):
    """
    Vue par défaut pour les utilisateurs n'ayant pas de dashboard spécifique.
    Affiche un message et un bouton de déconnexion.
    """
    def __init__(self, parent, user, controller, on_logout=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.user = user
        self.controller = controller
        self.on_logout = on_logout

        # Thème vert/bleu dégradé sur fond
        self.setStyleSheet("""
            QWidget { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #e8f5e9, stop:1 #81c784 ); }
            QLabel { color: #2e7d32; font-size: 18px; }
            QPushButton { padding: 12px; border-radius: 8px;
                background: #4caf50; color: white;
                font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #388e3c; }
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Message d'information centré
        message = (
            f"Utilisateur '{self.user.username}'\n"
            "n'a pas encore de dashboard associé à son rôle."
        )
        label = QLabel(message, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setFont(QFont('Arial', 16))
        layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Bouton de déconnexion
        btn_logout = QPushButton("Se déconnecter", self)
        btn_logout.setFixedHeight(40)
        btn_logout.clicked.connect(self.on_logout)
        layout.addWidget(btn_logout, alignment=Qt.AlignmentFlag.AlignCenter)
