import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit, QComboBox, QDateEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

# For charts
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class PatientsDashboardView(QWidget):
    def __init__(self, parent, stats_provider):
        super().__init__(parent)
        self.stats_provider = stats_provider
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Dashboard des Patients")
        title.setFont(QFont(None, 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Stats cards
        stats = self.stats_provider.get_patient_stats()
        cards_layout = QHBoxLayout()
        for label_text, value, color in [
            ("Nombre total de patients", stats['total_patients'], '#E0F7FA'),
            ("Moyenne de RDV / patient", f"{stats['avg_appts']:.1f}", '#F1F8E9'),
            ("Patients actifs ce mois", stats['active_this_month'], '#FFF3E0')
        ]:
            card = QWidget()
            card.setStyleSheet(f"background:{color}; border-radius:10px;")
            cl = QVBoxLayout(card)
            lbl = QLabel(label_text)
            lbl.setFont(QFont(None, 14))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lbl)
            val = QLabel(str(value))
            val.setFont(QFont(None, 20, QFont.Weight.Bold))
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val)
            cards_layout.addWidget(card)
        layout.addLayout(cards_layout)

        # Chart
        chart_data = self.stats_provider.get_weekly_appointments()
        fig = Figure(figsize=(6, 3))
        ax = fig.add_subplot(111)
        days, appts = zip(*chart_data.items())
        ax.plot(days, appts, marker='o')
        ax.set_title("RDV planifiés cette semaine")
        ax.set_xlabel("Jour")
        ax.set_ylabel("Nombre de RDV")
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas)

