import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from view_pyqt6.patient_view.patient_profile import PatientProfileView
from view_pyqt6.patient_view.patient_edit_view import PatientsEditView
from utils.pdf_export import export_patients_to_pdf

class PatientListView(QWidget):
    def __init__(self, parent, controller=None, patients=None):
        super().__init__(parent)
        self.controller = controller
        self.patients_override = patients
        self.selected_patient = None
        self.page = 1

        self.setStyleSheet("""
            QLineEdit { padding:6px; border:1px solid #c8e6c9; border-radius:6px; }
            QPushButton { padding:6px; border-radius:6px; background:#4caf50; color:white; font-weight:bold; }
            QPushButton:hover { background:#388e3c; }
            QTableWidget { background:#ffffff; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top bar
        top_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Recherche...")
        top_layout.addWidget(self.search_entry)
        btn_search = QPushButton("🔍")
        btn_search.clicked.connect(self.refresh)
        top_layout.addWidget(btn_search)

        self.view_btn = QPushButton("Voir Profil")
        self.view_btn.setEnabled(False)
        self.view_btn.clicked.connect(self.view_profile)
        top_layout.addWidget(self.view_btn)

        self.edit_btn = QPushButton("Éditer")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_patient)
        top_layout.addWidget(self.edit_btn)

        btn_export = QPushButton("Export PDF")
        btn_export.clicked.connect(self.export_pdf)
        top_layout.addWidget(btn_export)

        main_layout.addLayout(top_layout)

        # Table
        self.table = QTableWidget()
        cols = ["ID","Code","Nom","Prénom","Naissance","Téléphone"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellClicked.connect(self.on_select)
        main_layout.addWidget(self.table)

        # Navigation
        nav_layout = QHBoxLayout()
        btn_prev = QPushButton("←")
        btn_prev.clicked.connect(self.prev_page)
        nav_layout.addWidget(btn_prev)
        btn_next = QPushButton("→")
        btn_next.clicked.connect(self.next_page)
        nav_layout.addWidget(btn_next)
        main_layout.addLayout(nav_layout)

        self.refresh()

    def refresh(self):
        self.selected_patient = None
        self.view_btn.setEnabled(False)
        self.edit_btn.setEnabled(False)

        search = self.search_entry.text().strip() or None
        data = self.patients_override or self.controller.list_patients(page=self.page, per_page=15, search=search)

        self.table.setRowCount(0)
        for p in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, val in enumerate((
                p.patient_id, p.code_patient, p.last_name,
                p.first_name, p.birth_date, p.contact_phone
            )):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def on_select(self, row, column):
        item = self.table.item(row, 0)
        if item:
            self.selected_patient = int(item.text())
            self.view_btn.setEnabled(True)
            self.edit_btn.setEnabled(True)

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        self.page += 1
        self.refresh()

    def export_pdf(self):
        try:
            data = self.controller.list_patients(page=self.page, per_page=1000)
            out_path = export_patients_to_pdf(data, title="Liste des Patients")
            QMessageBox.information(self, "Export PDF terminé", f"Fichier généré : {out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur Export PDF", str(e))

    def view_profile(self):
        if self.selected_patient is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Profil Patient")
        dlg.resize(600,400)
        view = PatientProfileView(dlg, self.controller, patient_id=self.selected_patient)
        layout = QVBoxLayout(dlg)
        layout.addWidget(view)
        dlg.exec()

    def edit_patient(self):
        if self.selected_patient is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Éditer Patient")
        dlg.resize(600,400)
        view = PatientsEditView(dlg, self.controller, patient_id=self.selected_patient)
        layout = QVBoxLayout(dlg)
        layout.addWidget(view)
        if dlg.exec():
            self.refresh()
