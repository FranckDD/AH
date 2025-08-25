import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime

class MedicalRecordFormView(QWidget):
    def __init__(self, parent, controller, record_id=None):
        super().__init__(parent)
        # Unwrap controller
        self.ctrl = getattr(controller, 'medical_record_controller', controller)
        self.record_id = record_id
        self.current_user = getattr(controller, 'current_user', None)

        self._setup_ui()
        if record_id:
            self._load_record()

    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget { background: #ffffff; }
            QLineEdit, QComboBox, QDateEdit { padding:6px; border:1px solid #c8e6c9; border-radius:5px; }
            QPushButton { padding:8px; border-radius:5px; background:#4caf50; color:white; font-weight:bold; }
            QPushButton:hover { background:#388e3c; }
            QLabel.error { color:#b71c1c; }
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10,10,10,10)
        main_layout.setSpacing(10)

        # Search section
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("ID ou Code patient")
        btn_search = QPushButton("🔍")
        btn_search.clicked.connect(self._on_search)
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(btn_search)
        main_layout.addLayout(search_layout)

        info_layout = QHBoxLayout()
        self.lbl_id = QLabel("ID:")
        self.lbl_code = QLabel("Code:")
        self.lbl_name = QLabel("Nom:")
        for lbl in (self.lbl_id, self.lbl_code, self.lbl_name):
            info_layout.addWidget(lbl)
        main_layout.addLayout(info_layout)

        # Form fields
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date Consultation:", self.date_edit)

        self.cbo_marital = QComboBox()
        self.marital_map = {d: v for d,v in [
            ("Single / Célibataire","Single"),("Married / Marié(e)","Married"),
            ("Divorced / Divorcé(e)","Divorced"),("Widowed / Veuf(ve)","Widowed")
        ]}
        self.cbo_marital.addItems(self.marital_map.keys())
        form.addRow("Statut matrimonial:", self.cbo_marital)

        self.txt_bp = QLineEdit()
        form.addRow("Tension artérielle:", self.txt_bp)

        self.txt_temp = QLineEdit()
        form.addRow("Température:", self.txt_temp)

        self.txt_weight = QLineEdit()
        form.addRow("Poids (kg):", self.txt_weight)

        self.txt_height = QLineEdit()
        form.addRow("Taille (cm):", self.txt_height)

        # History fields
        for label, key in [("Antécédents","medical_history"),("Allergies","allergies"),
                           ("Symptômes","symptoms"),("Diagnostic","diagnosis"),("Traitement","treatment")]:
            widget = QLineEdit()
            setattr(self, key, widget)
            form.addRow(f"{label}:", widget)

        # Severity
        self.cbo_severity = QComboBox()
        self.severity_map = {d: v for d,v in [
            ("Low / Faible","low"),("Medium / Moyen","medium"),("High / Élevé","high")
        ]}
        self.cbo_severity.addItems(self.severity_map.keys())
        form.addRow("Gravité:", self.cbo_severity)

        # Motif dropdown
        motifs = self.ctrl.list_motifs()
        self.motif_map = {m['label_fr']: m['code'] for m in motifs}
        self.cbo_motif = QComboBox()
        self.cbo_motif.addItems(self.motif_map.keys())
        form.addRow("Motif:", self.cbo_motif)

        main_layout.addLayout(form)

        # Feedback
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("error")
        self.lbl_error.hide()
        main_layout.addWidget(self.lbl_error)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)
        if self.record_id:
            self.btn_del = QPushButton("Supprimer")
            self.btn_del.setStyleSheet("background:#d32f2f;")
            self.btn_del.clicked.connect(self._on_delete)
            btn_layout.addWidget(self.btn_del)
        main_layout.addLayout(btn_layout)

    def _on_search(self):
        key = self.search_entry.text().strip()
        rec = self.ctrl.find_patient(key)
        if rec:
            pid = rec.get('patient_id', rec.patient_id)
            code = rec.get('code_patient', rec.code_patient)
            name = f"{rec.get('last_name', rec.last_name)} {rec.get('first_name', rec.first_name)}"
            self.lbl_id.setText(f"ID: {pid}")
            self.lbl_code.setText(f"Code: {code}")
            self.lbl_name.setText(f"Nom: {name}")
        else:
            self.lbl_id.setText("ID:")
            self.lbl_code.setText("Code:")
            self.lbl_name.setText("Nom:")

    def _on_save(self):
        self.lbl_error.hide()
        pid_text = self.lbl_id.text().split(':')[-1].strip()
        if not pid_text.isdigit():
            return self._show_error("Veuillez sélectionner un patient valide.")
        pid = int(pid_text)
        try:
            date = datetime.strptime(self.date_edit.text(), "%Y-%m-%d")
        except:
            return self._show_error("Date invalide.")
        data = {
            'patient_id': pid,
            'consultation_date': date,
            'marital_status': self.marital_map[self.cbo_marital.currentText()],
            'bp': self.txt_bp.text().strip() or None,
            'temperature': float(self.txt_temp.text()) if self.txt_temp.text() else None,
            'weight': float(self.txt_weight.text()) if self.txt_weight.text() else None,
            'height': float(self.txt_height.text()) if self.txt_height.text() else None,
            'medical_history': self.medical_history.text().strip() or None,
            'allergies': self.allergies.text().strip() or None,
            'symptoms': self.symptoms.text().strip() or None,
            'diagnosis': self.diagnosis.text().strip() or None,
            'treatment': self.treatment.text().strip() or None,
            'severity': self.severity_map[self.cbo_severity.currentText()],
            'motif_code': self.motif_map[self.cbo_motif.currentText()]
        }
        if self.current_user:
            uid = self.current_user.user_id
            uname = self.current_user.username
            data.update({'created_by': uid, 'last_updated_by': uid,
                         'created_by_name': uname, 'last_updated_by_name': uname})
        try:
            if self.record_id:
                self.ctrl.update_record(self.record_id, data)
            else:
                self.ctrl.create_record(data)
        except Exception as e:
            return self._show_error(f"Erreur : {e}")
        QMessageBox.information(self, "Succès", "Enregistrement réussi.")
        self.parent().close()

    def _on_delete(self):
        if self.record_id:
            self.ctrl.delete_record(self.record_id)
            QMessageBox.information(self, "Supprimé", "Le dossier a été supprimé.")
            self.parent().close()

    def _show_error(self, msg):
        self.lbl_error.setText(msg)
        self.lbl_error.show()
