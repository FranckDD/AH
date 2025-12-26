from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt


class DoctorsDashboardView(QWidget):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Tableau de bord Médecins")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Statistiques globales
        stats = controller.get_doctor_statistics() if controller else {}
        # Exemple: stats = {'total': 10, 'active': 8}
        total_lbl = QLabel(f"Total Médecins : {stats.get('total', 0)}")
        active_lbl = QLabel(f"Médecins Actifs : {stats.get('active', 0)}")
        inactive_lbl = QLabel(f"Médecins Inactifs : {stats.get('inactive', 0)}")
        for lbl in (total_lbl, active_lbl, inactive_lbl):
            lbl.setStyleSheet("font-size: 14px;")
            layout.addWidget(lbl)
        layout.addStretch()