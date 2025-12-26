import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer

class AppointmentBook(QDialog):
    def __init__(self, parent=None, controller=None, appointment=None, on_save=None):
        super().__init__(parent)
        self.controller = controller
        self.appointment = appointment
        self.on_save = on_save

        # Window setup
        title = "Prendre un RDV" if not appointment else "Éditer un RDV"
        self.setWindowTitle(title)
        self.setFixedSize(400, 500)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Form
        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Code Patient
        self.code_edit = QLineEdit()
        self.code_edit.returnPressed.connect(self.on_code_enter)
        self.form.addRow("Code Patient:", self.code_edit)

        # Name and Phone labels
        self.name_label = QLabel("–")
        self.phone_label = QLabel("–")
        self.form.addRow("Prénom Nom:", self.name_label)
        self.form.addRow("Téléphone:", self.phone_label)

        # Spécialité
        self.specialty_combo = QComboBox()
        specs = self.controller.get_all_specialties() if self.controller else []
        self.specialty_combo.addItems(specs)
        self.form.addRow("Spécialité:", self.specialty_combo)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat('yyyy-MM-dd')
        self.date_edit.setCalendarPopup(True)
        self.form.addRow("Date:", self.date_edit)

        # Heure
        self.time_combo = QComboBox()
        times = [f"{h:02d}:{m:02d}" for h in range(8,19) for m in (0,30)]
        self.time_combo.addItems(times)
        self.form.addRow("Heure:", self.time_combo)

        # Raison
        self.reason_edit = QLineEdit()
        self.form.addRow("Raison:", self.reason_edit)

        main_layout.addLayout(self.form)

        # Feedback
        self.feedback_label = QLabel("")
        main_layout.addWidget(self.feedback_label)

        # Save button
        self.save_btn = QPushButton("Enregistrer")
        self.save_btn.clicked.connect(self.save_appointment)
        main_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Prefill if editing
        if self.appointment:
            self._prefill_fields()

    def on_code_enter(self):
        raw = self.code_edit.text().strip()
        if not raw:
            return
        norm = raw.upper()
        code = norm if norm.startswith("AH2-") else f"AH2-{norm}"
        self.code_edit.setText(code)

        # Lookup patient
        patient = self.controller.patient_ctrl.find_by_code(code)
        if not patient:
            self.feedback_label.setText("Code inconnu !")
            self.feedback_label.setStyleSheet("color:red;")
            return

        # Display info
        name = f"{patient['first_name']} {patient['last_name']}"
        self.name_label.setText(name)
        self.phone_label.setText(patient['contact_phone'])
        self.patient_id = patient['patient_id']
        self.feedback_label.setText("")

    def _prefill_fields(self):
        appt = self.appointment
        # Fill fields
        self.code_edit.setText(appt.patient.code_patient)
        self.on_code_enter()
        if appt.specialty:
            idx = self.specialty_combo.findText(appt.specialty)
            if idx != -1:
                self.specialty_combo.setCurrentIndex(idx)
        self.date_edit.setDate(appt.appointment_date)
        time_str = appt.appointment_time.strftime("%H:%M")
        idx_time = self.time_combo.findText(time_str)
        if idx_time != -1:
            self.time_combo.setCurrentIndex(idx_time)
        self.reason_edit.setText(appt.reason or "")

    def save_appointment(self):
        if not hasattr(self, 'patient_id'):
            self.feedback_label.setText("Veuillez saisir un code patient valide.")
            self.feedback_label.setStyleSheet("color:red;")
            return
        data = {
            'patient_id': self.patient_id,
            'specialty': self.specialty_combo.currentText(),
            'appointment_date': self.date_edit.date().toPyDate(),
            'appointment_time': self.time_combo.currentText(),
            'reason': self.reason_edit.text().strip()
        }

        try:
            if self.appointment:
                self.controller.modify_appointment(self.appointment.id, **data)
                msg = f"RDV #{self.appointment.id} modifié avec succès"
            else:
                appt = self.controller.book_appointment(data)
                msg = f"RDV créé (ID {appt.id})"

            self.feedback_label.setText(msg)
            self.feedback_label.setStyleSheet("color:green;")
            if self.on_save:
                self.on_save()
            QTimer.singleShot(1500, self.accept)
        except Exception as e:
            self.feedback_label.setText(f"Erreur : {e}")
            self.feedback_label.setStyleSheet("color:red;")
