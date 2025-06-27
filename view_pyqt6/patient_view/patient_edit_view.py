import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit, QComboBox, QDateEdit, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QDateTime
from PyQt6.QtGui import QFont

class PatientsEditView(QWidget):
    def __init__(self, parent, controller, patient=None):
        super().__init__(parent)
        self.controller = controller
        self.patient = patient
        self._init_ui()
        if self.patient:
            self._load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.fields = {}
        # Reuse keys
        keys = [
            ('Prénom','first_name'), ('Nom','last_name'),
            ('Date Naiss.','birth_date'), ('Genre','gender'),
            ('N° national','national_id'), ('Téléphone','contact_phone'),
            ('Assurance','assurance'), ('Résidence','residence'),
            ('Nom Père','father_name'), ('Nom Mère','mother_name')
        ]
        for label, key in keys:
            if key == 'gender':
                cb = QComboBox()
                cb.addItems(["Homme","Femme","Autre"])
                self.fields[key] = cb
                form_layout.addRow(f"{label}:", cb)
            elif key == 'birth_date':
                de = QDateEdit()
                de.setCalendarPopup(True)
                de.setDisplayFormat("yyyy-MM-dd")
                de.setDate(QDate(2000,1,1))
                self.fields[key] = de
                form_layout.addRow(f"{label}:", de)
            else:
                le = QLineEdit()
                self.fields[key] = le
                form_layout.addRow(f"{label}:", le)

        main_layout.addLayout(form_layout)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def _load_data(self):
        data = self.controller.get_patient(self.patient.id)
        for key, widget in self.fields.items():
            val = getattr(data, key, None)
            if val is None:
                continue
            if key == 'birth_date':
                dt = QDateTime.strptime(val, "%Y-%m-%d").date()
                widget.setDate(QDate(dt.year, dt.month, dt.day))
            elif key == 'gender':
                idx = widget.findText(val)
                if idx>=0: widget.setCurrentIndex(idx)
            else:
                widget.setText(str(val))

    def _on_save(self):
        data = {}
        for key, widget in self.fields.items():
            if key == 'birth_date':
                data[key] = widget.date().toString("yyyy-MM-dd")
            elif key == 'gender':
                data[key] = widget.currentText()
            else:
                data[key] = widget.text().strip() or None
        try:
            if self.patient:
                self.controller.update_patient(self.patient.id, data)
                QMessageBox.information(self, 'Patient mis à jour', 'Modifications enregistrées.')
            else:
                new_id = self.controller.create_patient(data)
                QMessageBox.information(self, 'Patient créé', f'ID: {new_id}')
            # close or notify parent
            if hasattr(self.parent(), 'refresh'):
                self.parent().refresh()
        except Exception as e:
            QMessageBox.critical(self, 'Erreur', str(e))
