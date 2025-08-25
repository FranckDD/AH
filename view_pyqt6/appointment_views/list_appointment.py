from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QLabel
)
from PyQt6.QtCore import Qt

class AppointmentsListView(QWidget):
    def __init__(self, parent=None, controller=None, *, on_book=None, on_edit=None, per_page=20, target_date=None):
        super().__init__(parent)
        self.controller = controller
        self.on_book = on_book
        self.on_edit = on_edit
        self.page = 1
        self.per_page = per_page
        self.target_date = target_date

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Barre de contrôle
        ctrl_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher nom ou code")
        self.search_edit.returnPressed.connect(self.refresh)
        ctrl_layout.addWidget(self.search_edit)

        self.search_btn = QPushButton("🔍")
        self.search_btn.clicked.connect(self.refresh)
        ctrl_layout.addWidget(self.search_btn)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tous", "pending", "cancelled"])
        self.status_filter.currentIndexChanged.connect(self.refresh)
        ctrl_layout.addWidget(self.status_filter)

        self.date_filter = QComboBox()
        self.date_filter.addItems(["Toutes", "Aujourd'hui"])
        self.date_filter.currentIndexChanged.connect(self.refresh)
        ctrl_layout.addWidget(self.date_filter)

        ctrl_layout.addStretch()

        self.book_btn = QPushButton("Book Appointment")
        self.book_btn.clicked.connect(self.on_book)
        ctrl_layout.addWidget(self.book_btn)

        main_layout.addLayout(ctrl_layout)

        # Tableau
        cols = ["ID","Patient","Code Patient","Téléphone","Médecin","Date","Heure","Raison","Statut"]
        self.table = QTableWidget()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_select)
        main_layout.addWidget(self.table)

        # Actions & pagination
        bottom_layout = QHBoxLayout()
        self.accept_btn = QPushButton("Accepter")
        self.accept_btn.setEnabled(False)
        self.accept_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.accept_btn)

        self.reject_btn = QPushButton("Refuser")
        self.reject_btn.setEnabled(False)
        self.reject_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.reject_btn)

        self.edit_btn = QPushButton("Éditer")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(lambda: self.on_edit(self.selected_id))
        bottom_layout.addWidget(self.edit_btn)

        bottom_layout.addStretch()

        self.prev_btn = QPushButton("← Précédent")
        self.prev_btn.clicked.connect(self.prev_page)
        bottom_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Suivant →")
        self.next_btn.clicked.connect(self.next_page)
        bottom_layout.addWidget(self.next_btn)

        main_layout.addLayout(bottom_layout)

        # Initial load
        self.refresh()

    def refresh(self):
        # Récupère tous les RDV
        rdvs = self.controller.repo.list_all()
        # Filtres status
        st = self.status_filter.currentText()
        if st != "Tous":
            rdvs = [r for r in rdvs if r.status == st]
        # Filtre date
        if self.date_filter.currentText() == "Aujourd'hui":
            today = date.today()
            rdvs = [r for r in rdvs if r.appointment_date == today]
        # Recherche texte
        term = self.search_edit.text().lower().strip()
        if term:
            rdvs = [r for r in rdvs if term in getattr(r.patient, 'code_patient', '').lower() 
                    or term in getattr(r.patient, 'full_name', f"{r.patient.first_name} {r.patient.last_name}").lower()]
        # Pagination
        total = len(rdvs)
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        page_items = rdvs[start:end]

        # Remplissage table
        self.table.setRowCount(len(page_items))
        for row, appt in enumerate(page_items):
            p = appt.patient
            name = getattr(p, 'full_name', f"{p.first_name} {p.last_name}")
            code = getattr(p, 'code_patient', '')
            phone = getattr(p, 'contact_phone', '')
            doc = getattr(appt.doctor, 'full_name', appt.doctor.username)
            values = [str(appt.id), name, code, phone,
                      doc, appt.appointment_date.strftime("%Y-%m-%d"),
                      appt.appointment_time.strftime("%H:%M"), appt.reason, appt.status]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col == len(values)-1:  # statut
                    if val == 'pending':
                        item.setBackground(Qt.GlobalColor.yellow)
                    elif val == 'cancelled':
                        item.setBackground(Qt.GlobalColor.red)
                self.table.setItem(row, col, item)
        self.on_select()

    def on_select(self):
        selected = self.table.selectionModel().selectedRows()
        has = bool(selected)
        if has:
            self.selected_id = int(self.table.item(selected[0].row(), 0).text())
        else:
            self.selected_id = None
        for btn in (self.accept_btn, self.reject_btn, self.edit_btn):
            btn.setEnabled(has)

    def accept(self):
        if self.selected_id:
            self.controller.modify_appointment(self.selected_id, status="pending")
            self.refresh()

    def reject(self):
        if self.selected_id:
            self.controller.cancel_appointment(self.selected_id)
            self.refresh()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        total = len(self.controller.repo.list_all())
        maxp = (total - 1) // self.per_page + 1
        if self.page < maxp:
            self.page += 1
            self.refresh()
