from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt

class PrescriptionListView(QWidget):
    def __init__(self, parent=None, controller=None, per_page=20):
        super().__init__(parent)
        self.controller = controller
        self.page = 1
        self.per_page = per_page
        self.selected_id = None

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # Filtres (from/to)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        filter_layout.addWidget(QLabel("Date from:"))
        self.from_date = QDateEdit()
        self.from_date.setDisplayFormat('yyyy-MM-dd')
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(date.today())
        filter_layout.addWidget(self.from_date)

        filter_layout.addWidget(QLabel("to:"))
        self.to_date = QDateEdit()
        self.to_date.setDisplayFormat('yyyy-MM-dd')
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(date.today())
        filter_layout.addWidget(self.to_date)

        self.filter_btn = QPushButton("Filtrer")
        self.filter_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # Tableau
        cols = ["ID","Patient","Médoc","Dosage","Freq","Début","Fin"]
        self.table = QTableWidget()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_select)
        main_layout.addWidget(self.table)

        # Actions
        action_layout = QHBoxLayout()
        self.edit_btn = QPushButton("Aff/Edit")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.edit_record)
        action_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_record)
        action_layout.addWidget(self.delete_btn)

        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        # Initial load
        self.refresh()

    def refresh(self):
        # Récupère prescriptions
        recs = self.controller.list_prescriptions(page=self.page, per_page=self.per_page)
        # Filtre dates
        fd = self.from_date.date().toPyDate()
        td = self.to_date.date().toPyDate()
        recs = [r for r in recs if fd <= r.start_date <= td]

        # Remplit table
        self.table.setRowCount(len(recs))
        for row, r in enumerate(recs):
            values = [
                str(r.prescription_id),
                getattr(r.patient, 'code_patient', ''),
                r.medication,
                r.dosage,
                r.frequency,
                r.start_date.strftime("%Y-%m-%d"),
                r.end_date.strftime("%Y-%m-%d") if r.end_date else ''
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                self.table.setItem(row, col, item)
        self.selected_id = None
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def on_select(self):
        selected = self.table.selectionModel().selectedRows()
        has = bool(selected)
        if has:
            self.selected_id = int(self.table.item(selected[0].row(), 0).text())
        else:
            self.selected_id = None
        self.edit_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)

    def edit_record(self):
        if self.selected_id is None:
            return
        # Ouvre un dialog ou une vue pour édition
        dialog = self.controller.open_prescription_form(
            parent=self, prescription_id=self.selected_id
        )
        dialog.exec()
        self.refresh()

    def delete_record(self):
        if self.selected_id is None:
            return
        confirm = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer la prescription #{self.selected_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.controller.delete_prescription(self.selected_id)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))
