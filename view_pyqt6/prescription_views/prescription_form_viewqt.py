from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QLabel, QDateEdit, QTextEdit,
    QPushButton, QMessageBox, QVBoxLayout
)
from PyQt6.QtCore import Qt

class PrescriptionFormView(QWidget):
    def __init__(self, parent=None, controller=None,
                 prescription_id=None, patient_id=None, medical_record_id=None):
        super().__init__(parent)
        self.controller = controller
        self.prescription_id = prescription_id
        self.patient_id = patient_id
        self.medical_record_id = medical_record_id

        # Layout principal
        main_layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # Champs
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Ex : AH2-00123")
        self.code_edit.editingFinished.connect(self.on_code_focus_out)
        form.addRow("Code Patient*:", self.code_edit)

        self.name_label = QLabel("–")
        self.name_label.setStyleSheet("color:gray;")
        form.addRow("Nom Patient:", self.name_label)

        self.record_edit = QLineEdit()
        if self.medical_record_id:
            self.record_edit.setText(str(self.medical_record_id))
            self.record_edit.setEnabled(False)
        form.addRow("ID Dossier Médical:", self.record_edit)

        self.medication_edit = QLineEdit()
        self.medication_edit.setPlaceholderText("Ex : Paracétamol")
        form.addRow("Médicament*:", self.medication_edit)

        self.dosage_edit = QLineEdit()
        self.dosage_edit.setPlaceholderText("Ex : 500mg")
        form.addRow("Dosage*:", self.dosage_edit)

        self.freq_edit = QLineEdit()
        self.freq_edit.setPlaceholderText("Ex : 2 fois/jour")
        form.addRow("Fréquence*:", self.freq_edit)

        self.duration_edit = QLineEdit()
        self.duration_edit.setPlaceholderText("Ex : 5 jours")
        form.addRow("Durée:", self.duration_edit)

        self.start_date = QDateEdit()
        self.start_date.setDisplayFormat('yyyy-MM-dd')
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(datetime.today())
        form.addRow("Date début*:", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setDisplayFormat('yyyy-MM-dd')
        self.end_date.setCalendarPopup(True)
        form.addRow("Date fin:", self.end_date)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(80)
        form.addRow("Notes:", self.notes_edit)

        main_layout.addLayout(form)
        self.save_btn = QPushButton("Modifier" if prescription_id else "Enregistrer")
        self.save_btn.clicked.connect(self.on_save)
        main_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        if prescription_id:
            self.load_prescription()

    def on_code_focus_out(self):
        code = self.code_edit.text().strip()
        if not code:
            self.patient_id = None
            self.name_label.setText("–")
            return
        # lookup
        rec = None
        try:
            rec = self.controller.find_patient(code)
        except Exception:
            rec = None
        if not rec:
            self.name_label.setText("❌ Code introuvable")
            self.patient_id = None
        else:
            if isinstance(rec, dict):
                fname = rec.get('first_name', '')
                lname = rec.get('last_name', '')
                pid = rec.get('patient_id')
            else:
                fname = getattr(rec, 'first_name', '')
                lname = getattr(rec, 'last_name', '')
                pid = getattr(rec, 'patient_id', None)
            self.name_label.setText(f"{lname} {fname}")
            self.patient_id = pid

    def validate(self):
        # vérifie les champs obligatoires
        errors = []
        if not getattr(self, 'patient_id', None):
            errors.append('Code Patient')
        if not self.medication_edit.text().strip():
            errors.append('Médicament')
        if not self.dosage_edit.text().strip():
            errors.append('Dosage')
        if not self.freq_edit.text().strip():
            errors.append('Fréquence')
        if not self.start_date.date():
            errors.append('Date début')
        if self.end_date.date() < self.start_date.date():
            errors.append('Date fin')
        return errors

    def on_save(self):
        errs = self.validate()
        if errs:
            QMessageBox.critical(
                self, "Erreur",
                "Veuillez corriger les champs : " + ", ".join(errs)
            )
            return
        data = {
            'patient_id': self.patient_id,
            'medical_record_id': self.medical_record_id,
            'medication': self.medication_edit.text().strip(),
            'dosage': self.dosage_edit.text().strip(),
            'frequency': self.freq_edit.text().strip(),
            'duration': self.duration_edit.text().strip() or None,
            'start_date': self.start_date.date().toPyDate(),
            'end_date': self.end_date.date().toPyDate(),
            'notes': self.notes_edit.toPlainText().strip() or None
        }
        try:
            if self.prescription_id:
                self.controller.update_prescription(self.prescription_id, data)
                QMessageBox.information(self, "Succès", "Prescription modifiée !")
            else:
                self.controller.create_prescription(data)
                QMessageBox.information(self, "Succès", "Prescription enregistrée !")
            # reset form si création
            if not self.prescription_id:
                self.reset_form()
        except Exception as e:
            QMessageBox.critical(self, "Erreur",
                                  "Une erreur est survenue. Veuillez réessayer.")

    def reset_form(self):
        self.patient_id = None
        self.code_edit.clear()
        self.name_label.setText("–")
        self.record_edit.clear()
        self.medication_edit.clear()
        self.dosage_edit.clear()
        self.freq_edit.clear()
        self.duration_edit.clear()
        self.start_date.setDate(datetime.today())
        self.end_date.setDate(datetime.today())
        self.notes_edit.clear()

    def load_prescription(self):
        rec = self.controller.get_prescription(self.prescription_id)
        # Pré-remplissage
        self.code_edit.setText(rec.patient.code_patient)
        self.on_code_focus_out()
        self.record_edit.setText(str(rec.medical_record_id))
        self.medication_edit.setText(rec.medication)
        self.dosage_edit.setText(rec.dosage)
        self.freq_edit.setText(rec.frequency)
        if rec.duration:
            self.duration_edit.setText(rec.duration)
        if rec.start_date:
            self.start_date.setDate(rec.start_date)
        if rec.end_date:
            self.end_date.setDate(rec.end_date)
        if rec.notes:
            self.notes_edit.setPlainText(rec.notes)
