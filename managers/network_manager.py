# managers/network_manager.py
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

class NetworkManager:
    def __init__(self, gateway, check_interval_ms: int = 30_000):
        """
        gateway: RemoteGateway
        check_interval_ms: intervalle de vérification (ms)
        """
        self.gateway = gateway
        self.offline_mode = False
        self._warning_shown = False
        self.check_interval_ms = check_interval_ms
        self._start_timer()

    def _start_timer(self):
        QTimer.singleShot(100, self.check_connection)  # 1er check rapide

    def check_connection(self):
        res = self.gateway.request("GET", "/health")
        print("DEBUG network check:", res)   # <-- affiche le dict retourné
        if not res.get("success"):
            # Passe en mode hors-ligne si ce n'était pas déjà le cas
            if not self.offline_mode:
                self.offline_mode = True
                if not self._warning_shown:
                    # message unique pour éviter le spam
                    QMessageBox.warning(None, "Hors ligne", "Mode hors-ligne activé — certaines fonctionnalités seront désactivées.")
                    self._warning_shown = True
        else:
            # si on revient en ligne on reset l'état
            if self.offline_mode:
                QMessageBox.information(None, "Connexion restaurée", "Connexion API rétablie.")
            self.offline_mode = False
            self._warning_shown = False

        # replanifie le check
        QTimer.singleShot(self.check_interval_ms, self.check_connection)
