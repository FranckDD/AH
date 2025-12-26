import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime

class PatientFormView(QWidget):
    def __init__(self, parent, controller, current_user, patient_id=None, on_save=None):
        super().__init__(parent)
        self.controller = controller
        self.current_user = current_user
        self.on_save = on_save
        self.patient_id = patient_id

        # Theme
        self.setStyleSheet("""
            QWidget { background: #ffffff; }
            QLineEdit, QComboBox, QDateEdit {
                padding: 8px; border:1px solid #c8e6c9;
                border-radius:6px; font-size:14px; }
            QPushButton {
                padding:10px; border-radius:6px;
                background:#4caf50; color:white;
                font-weight:bold; font-size:14px; }
            QPushButton:hover { background:#388e3c; }
            QLabel#error { color:#b71c1c; font-size:12px; }
        """)

        self._build_ui()
        if self.patient_id:
            self._load()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Fields
        self.fields = {}
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.hide()
        main_layout.addWidget(self.error_label)

        # First name
        self.fields['first_name'] = QLineEdit()
        form_layout.addRow("Prénom:", self.fields['first_name'])
        # Last name
        self.fields['last_name'] = QLineEdit()
        form_layout.addRow("Nom:", self.fields['last_name'])
        # Birth date
        self.fields['birth_date'] = QDateEdit()
        self.fields['birth_date'].setCalendarPopup(True)
        self.fields['birth_date'].setDisplayFormat("yyyy-MM-dd")
        self.fields['birth_date'].setDate(QDate(2000,1,1))
        form_layout.addRow("Date Naiss.:", self.fields['birth_date'])
        # Gender
        self.fields['gender'] = QComboBox()
        self.fields['gender'].addItems(["Homme","Femme","Autre"])
        form_layout.addRow("Genre:", self.fields['gender'])
        # Other fields
        for label, key in [
            ("N° national","national_id"),("Téléphone","contact_phone"),
            ("Assurance","assurance"),("Résidence","residence"),
            ("Nom Père","father_name"),("Nom Mère","mother_name")
        ]:
            self.fields[key] = QLineEdit()
            form_layout.addRow(label+":", self.fields[key])

        main_layout.addLayout(form_layout)

        # Save button
        btn = QPushButton("Enregistrer")
        btn.clicked.connect(self._save)
        main_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _load(self):
        p = self.controller.get_patient(self.patient_id)
        if not p:
            return
        for key, widget in self.fields.items():
            val = getattr(p, key, None) if not isinstance(p, dict) else p.get(key)
            if val is None:
                continue
            if key == 'birth_date':
                try:
                    dt = datetime.strptime(val, "%Y-%m-%d").date()
                    widget.setDate(QDate(dt.year, dt.month, dt.day))
                except:
                    pass
            elif key == 'gender':
                idx = widget.findText(val)
                if idx>=0: widget.setCurrentIndex(idx)
            else:
                widget.setText(str(val))

    def _show_error(self, message, fields=None):
        self.error_label.setText(message)
        self.error_label.show()
        if fields:
            for key in fields:
                w = self.fields.get(key)
                if w:
                    w.setStyleSheet("border:2px solid #b71c1c;")

    def _save(self):
        # Collect data
        data={}        
        for key, widget in self.fields.items():
            if key=='birth_date':
                data[key] = widget.date().toString("yyyy-MM-dd")
            elif key=='gender':
                data[key] = widget.currentText()
            else:
                data[key] = widget.text().strip() or None

        # Validate required
        missing=[k for k in ['first_name','last_name','birth_date'] if not data.get(k)]
        if missing:
            return self._show_error("Champs obligatoires manquants", missing)

        try:
            if self.patient_id:
                self.controller.update_patient(self.patient_id, data)
                QMessageBox.information(self, "Patient mis à jour", "Modifications enregistrées.")
            else:
                new_id, code = self.controller.create_patient(data)
                QMessageBox.information(self, "Patient créé", f"Code : {code}")
                if self.on_save:
                    self.on_save(code)
                    return

            # redirection
            if hasattr(self.parent(), 'show_doctors_dashboard'):
                self.parent().show_doctors_dashboard()
        except Exception as e:
            self._show_error(f"Erreur: {e}")
