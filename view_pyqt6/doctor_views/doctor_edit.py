from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt

class DoctorsEditView(QWidget):
    def __init__(self, parent=None, controller=None, doctor=None, on_save=None):
        super().__init__(parent)
        self.controller = controller
        self.doctor = doctor
        self.on_save = on_save

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        title = QLabel("Ajouter / Éditer Médecin")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.spec_edit = QLineEdit()
        form.addRow("Nom complet:", self.name_edit)
        form.addRow("Spécialité:", self.spec_edit)
        main_layout.addLayout(form)

        self.save_btn = QPushButton("Modifier" if doctor else "Enregistrer")
        self.save_btn.clicked.connect(self._on_save)
        main_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        if doctor:
            self.name_edit.setText(doctor.full_name)
            self.spec_edit.setText(getattr(doctor, 'specialty', ''))

    def _on_save(self):
        name = self.name_edit.text().strip()
        spec = self.spec_edit.text().strip()
        if not name or not spec:
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs.")
            return
        try:
            if self.doctor:
                self.controller.update_doctor(self.doctor.id, name, spec)
                QMessageBox.information(self, "Succès", "Médecin mis à jour !")
            else:
                self.controller.create_doctor(name, spec)
                QMessageBox.information(self, "Succès", "Médecin ajouté !")
            if callable(self.on_save):
                self.on_save()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))