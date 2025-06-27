import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

class PatientProfileView(QWidget):
    def __init__(self, parent, controller, patient_id=None):
        super().__init__(parent)
        self.controller = controller
        self.patient_id = patient_id or getattr(controller, 'selected_patient', None)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title = QLabel(f"Profil Patient #{self.patient_id}")
        title.setFont(QFont(None, 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)

        # Create tabs
        self._create_info_tab()
        self._create_table_tab("Rendez-vous", ["Date", "Médecin", "Motif"], self._fetch_appointments)
        self._create_table_tab("Prescriptions", ["Médicament", "Posologie", "Début", "Fin"], self._fetch_prescriptions)
        self._create_table_tab("Examens labo", ["Type", "Date", "Statut"], self._fetch_lab_results)
        self._create_table_tab("Consult. spirituelles", ["Notes", "Date"], self._fetch_spiritual)

        # Load
        if self.patient_id:
            self.load_patient()
        else:
            placeholder = QLabel("Aucun patient sélectionné.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)

    def _create_info_tab(self):
        info_widget = QWidget()
        form_layout = QVBoxLayout(info_widget)
        self.info_labels = {}
        for label, attr in [
            ("Code patient", "code_patient"), ("Prénom", "first_name"), ("Nom", "last_name"),
            ("Date Naiss.", "birth_date"), ("Genre", "gender"), ("Téléphone", "contact_phone"),
            ("Assurance", "assurance"), ("Résidence", "residence"), ("Nom Père", "father_name"),
            ("Nom Mère", "mother_name"), ("Créé le", "created_at"), ("Par", "created_by_name")
        ]:
            lbl = QLabel(f"{label}: ")
            lbl.setFont(QFont(None, 12))
            self.info_labels[attr] = lbl
            form_layout.addWidget(lbl)
        self.tabs.addTab(info_widget, "Informations")

    def _create_table_tab(self, name, columns, fetcher_name):
        table_widget = QTableWidget()
        table_widget.setColumnCount(len(columns))
        table_widget.setHorizontalHeaderLabels(columns)
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        setattr(self, f"_{name.lower().replace(' ', '_')}_table", table_widget)
        setattr(self, f"_fetch_{name.lower().replace(' ', '_')}", getattr(self, fetcher_name))
        self.tabs.addTab(table_widget, name)

    # Fetch helpers
    def _fetch_appointments(self, patient_id):
        return getattr(self.controller, 'get_appointments', lambda x: [])(patient_id)
    def _fetch_prescriptions(self, patient_id):
        return getattr(self.controller, 'get_prescriptions', lambda x: [])(patient_id)
    def _fetch_lab_results(self, patient_id):
        return getattr(self.controller, 'get_lab_results', lambda x: [])(patient_id)
    def _fetch_spiritual(self, patient_id):
        return getattr(self.controller, 'get_spiritual_consultations', lambda x: [])(patient_id)

    def load_patient(self):
        data = self.controller.get_patient(self.patient_id)
        if not data:
            return
        # Info
        for attr, lbl in self.info_labels.items():
            val = data.get(attr) if isinstance(data, dict) else getattr(data, attr, "")
            if hasattr(val, 'strftime'):
                val = val.strftime("%Y-%m-%d")
            lbl.setText(f"{lbl.text().split(':')[0]}: {val}")
        # Tables
        for idx in range(self.tabs.count()):
            name = self.tabs.tabText(idx)
            if name == "Informations": continue
            table = getattr(self, f"_{name.lower().replace(' ', '_')}_table")
            fetch = getattr(self, f"_fetch_{name.lower().replace(' ', '_')}")
            table.setRowCount(0)
            for row_data in fetch(self.patient_id):
                row = table.rowCount()
                table.insertRow(row)
                for col, key in enumerate(table.horizontalHeaderItem(i).text().lower().replace(' ', '_') for i in range(table.columnCount())):
                    val = row_data.get(key) if isinstance(row_data, dict) else getattr(row_data, key, "")
                    if hasattr(val, 'strftime'):
                        val = val.strftime("%Y-%m-%d")
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(row, col, item)
