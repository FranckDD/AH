import calendar
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout
)
from PyQt6.QtCore import Qt

class AppointmentsDashboardView(QWidget):
    def __init__(self, parent=None, controller=None, on_day_selected=None):
        super().__init__(parent)
        self.controller = controller
        self.on_day_selected = on_day_selected

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Navigation mois
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("<<")
        self.prev_btn.clicked.connect(self.prev_month)
        nav_layout.addWidget(self.prev_btn)

        self.lbl_month = QLabel()
        self.lbl_month.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.lbl_month, stretch=1)

        self.next_btn = QPushButton(">>")
        self.next_btn.clicked.connect(self.next_month)
        nav_layout.addWidget(self.next_btn)

        self.today_btn = QPushButton("Today")
        self.today_btn.clicked.connect(self.go_today)
        nav_layout.addWidget(self.today_btn)

        main_layout.addLayout(nav_layout)

        # Grille des jours
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(5)
        main_layout.addWidget(self.grid_widget, stretch=1)

        # Dessine le calendrier
        self.draw_calendar()

    def draw_calendar(self):
        # Clear grid
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        # Titre mois
        month_name = calendar.month_name[self.current_month]
        self.lbl_month.setText(f"{month_name} {self.current_year}")

        # En-têtes jours
        days = ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"]
        for col, d in enumerate(days):
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, col)

        # Semaine commence dimanche
        calendar.setfirstweekday(calendar.SUNDAY)
        weeks = calendar.monthcalendar(self.current_year, self.current_month)

        # Remplissage des jours
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    lbl = QLabel("")
                    self.grid_layout.addWidget(lbl, row, col)
                else:
                    dt = date(self.current_year, self.current_month, day)
                    count = len(self.controller.get_by_day(dt)) if self.controller else 0
                    btn = QPushButton(f"{day}\n{count} RDV")
                    btn.setFlat(True)
                    btn.setStyleSheet("border:1px solid #4caf50; border-radius:4px;")
                    btn.clicked.connect(lambda checked, d=dt: self.on_day_selected(d) if self.on_day_selected else None)
                    self.grid_layout.addWidget(btn, row, col)

    def prev_month(self):
        m = self.current_month - 1
        y = self.current_year
        if m < 1:
            m, y = 12, y - 1
        self.current_month, self.current_year = m, y
        self.draw_calendar()

    def next_month(self):
        m = self.current_month + 1
        y = self.current_year
        if m > 12:
            m, y = 1, y + 1
        self.current_month, self.current_year = m, y
        self.draw_calendar()

    def go_today(self):
        t = date.today()
        self.current_year, self.current_month = t.year, t.month
        self.draw_calendar()
