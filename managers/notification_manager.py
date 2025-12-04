# managers/notification_manager.py
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
import os
from typing import Optional

class NotificationManager(QObject):
    """Gestionnaire de notifications toast (system tray) pour actions importantes."""
    def __init__(self, parent=None, app_name: str = "Glostone-Kare"):
        super().__init__(parent)
        self.app_name = app_name
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self._init_tray()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide_notification)

    def _init_tray(self):
        """Init tray icon si supporté."""
        try:
            icon_path = resource_path(os.path.join("assets", "icon.png"))  # Assume resource_path global
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path if os.path.exists(icon_path) else ""), self.parent())
            menu = QMenu()
            menu.addAction("Ouvrir", lambda: self.parent().show() if self.parent() else None)
            menu.addAction("Quitter", self.parent().close if self.parent() else None)
            self.tray_icon.setContextMenu(menu)
            self.tray_icon.show()
            print("[NOTIF] Tray icon activé")
        except Exception as e:
            print(f"[NOTIF ERROR] Tray non supporté : {e} – Fallback QMessageBox")

    def show_notification(self, title: str, message: str, icon_type: str = "info"):
        """Affiche toast : title = 'Sync', message = 'Réussie !'."""
        if self.tray_icon:
            # Tray toast (discret)
            self.tray_icon.showMessage(
                title, message,
                self._get_icon(icon_type),  # Success/error/info
                3000  # 3s auto-hide
            )
            print(f"[NOTIF] Toast : {title} - {message}")
        else:
            # Fallback QMessageBox (modal, mais simple)
            icon = QMessageBox.Information if icon_type == "info" else QMessageBox.Warning if icon_type == "warning" else QMessageBox.Critical
            QMessageBox(icon, title, message, QMessageBox.StandardButton.Ok).exec()

    def _get_icon(self, icon_type: str):
        """Icon par type."""
        icon_path = resource_path(os.path.join("assets", f"{icon_type}.png"))  # ex. success.png, error.png
        return QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    def _hide_notification(self):
        if self.tray_icon:
            self.tray_icon.hide()  # Optionnel : Cache après timer

# Utilisation globale (injecte dans controllers ou vues)
# Ex. : self.notif_manager = NotificationManager(self) in AuthView __init__
# self.notif_manager.show_notification("Sync", "Réussie !", "success")