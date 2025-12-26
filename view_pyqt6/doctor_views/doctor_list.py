from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt


class DoctorsListView(QWidget):
    def __init__(self, parent=None, controller=None, on_edit=None):
        super().__init__(parent)
        self.controller = controller
        self.on_edit = on_edit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Liste des Médecins")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nom", "Spécialité"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.edit_btn = QPushButton("Éditer")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._edit)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        doctors = self.controller.get_doctors() if self.controller else []
        self.table.setRowCount(len(doctors))
        for row, doc in enumerate(doctors):
            self.table.setItem(row, 0, QTableWidgetItem(doc.full_name))
            self.table.setItem(row, 1, QTableWidgetItem(getattr(doc, 'specialty', '')))
        self.edit_btn.setEnabled(False)

    def _on_select(self):
        selected = self.table.selectionModel().selectedRows()
        has = bool(selected)
        self.edit_btn.setEnabled(has)
        if has:
            self.selected_doc = selected[0].row()
        else:
            self.selected_doc = None

    def _edit(self):
        if self.selected_doc is None:
            return
        # Récupère le médecin et appelle on_edit
        doctors = self.controller.get_doctors()
        doc = doctors[self.selected_doc]
        if callable(self.on_edit):
            self.on_edit(doc)
