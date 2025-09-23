import sys
from datetime import datetime
from typing import Optional, Callable, Dict, Any, cast
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QMessageBox, QFrame, QScrollArea, QFormLayout,
    QApplication, QSizePolicy, QDialog, QMainWindow
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from view_pyqt6.controller_resolver import ControllerResolver
from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView


class PatientFormView(QWidget):
    def __init__(self, parent, controllers: Any, current_user, patient_id=None, on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.patient_controller()
        self.current_user = current_user
        self.on_save = on_save
        self.patient_id = patient_id
        self.is_new = patient_id is None

        self.field_widgets = {}
        self.error_label = None

        # store main layout as attribute -> fixes Pylance warning for insertWidget
        self.main_layout: QVBoxLayout  # type: ignore
        self._setup_ui()

        if not self.is_new:
            self._load()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.main_layout = main_layout  # keep reference for insertWidget (static type recognized)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title = QLabel("Formulaire Patient")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Scroll area for form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll_area, 1)

        # Form container
        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(10)
        scroll_area.setWidget(form_container)

        # Form fields
        fields = [
            ("Prénom", "first_name", "text"),
            ("Nom", "last_name", "text"),
            ("Date Naiss.", "birth_date", "date"),
            ("Genre", "gender", "combo"),
            ("N° national", "national_id", "text"),
            ("Téléphone", "contact_phone", "text"),
            ("Assurance", "assurance", "text"),
            ("Résidence", "residence", "text"),
            ("Nom Père", "father_name", "text"),
            ("Nom Mère", "mother_name", "text"),
        ]

        for label_text, key, field_type in fields:
            if field_type == "text":
                widget = QLineEdit()
                self.field_widgets[key] = widget
                form_layout.addRow(QLabel(label_text), widget)

            elif field_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(QDate.currentDate().addYears(-30))
                widget.setDisplayFormat("yyyy-MM-dd")
                self.field_widgets[key] = widget
                form_layout.addRow(QLabel(label_text), widget)

            elif field_type == "combo":
                widget = QComboBox()
                widget.addItems(["Homme", "Femme", "Autre"])
                self.field_widgets[key] = widget
                form_layout.addRow(QLabel(label_text), widget)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self._cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)

        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        main_layout.addLayout(button_layout)

    def _show_error(self, message, invalid_fields=None):
        # use stored layout to avoid Pylance error
        if self.error_label:
            self.error_label.deleteLater()

        self.error_label = QLabel(message)
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # insert in the main_layout at position 1
        try:
            self.main_layout.insertWidget(1, self.error_label)
        except Exception:
            # fallback if something unexpected happens
            self.main_layout.addWidget(self.error_label)

        # Reset all field styles
        for widget in self.field_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet("")
            elif isinstance(widget, QComboBox):
                widget.setStyleSheet("")
            elif isinstance(widget, QDateEdit):
                widget.setStyleSheet("")

        # Highlight invalid fields
        if invalid_fields:
            for field in invalid_fields:
                widget = self.field_widgets.get(field)
                if widget:
                    widget.setStyleSheet("border: 2px solid red;")
                    widget.setFocus()

    def _load(self):
        try:
            patient_data = self.controller.get_patient(self.patient_id)

            # Handle different response formats
            if isinstance(patient_data, dict) and 'error' in patient_data:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger le patient: {patient_data.get('details', 'Erreur inconnue')}")
                return

            # Extract data based on format (dict or object)
            data = {}
            if isinstance(patient_data, dict):
                data = patient_data
            else:
                # Assume it's an object with attributes
                data = {key: getattr(patient_data, key, None) for key in self.field_widgets.keys()}

            # Populate form fields
            for key, widget in self.field_widgets.items():
                value = data.get(key)
                if value is None:
                    continue

                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QDateEdit) and value:
                    try:
                        if isinstance(value, str):
                            date = QDate.fromString(value, "yyyy-MM-dd")
                        else:
                            # Assume it's a date object
                            date = QDate(value.year, value.month, value.day)
                        widget.setDate(date)
                    except Exception:
                        pass

        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")

    def _save(self):
        # Collect data from form
        data = {}
        for key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                data[key] = value if value else None
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText()
            elif isinstance(widget, QDateEdit):
                qdate = widget.date()
                data[key] = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"

        # Validate required fields
        required = ["first_name", "last_name", "birth_date"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            self._show_error("Champs obligatoires manquants", invalid_fields=missing)
            return

        try:
            if self.is_new:
                # Create new patient via controller
                result = self.controller.create_patient(data)

                # Handle different response formats
                if isinstance(result, dict) and 'error' in result:
                    self._show_error(f"Erreur: {result.get('details', 'Erreur inconnue')}")
                    return

                # Extract patient ID and code from response
                patient_id = None
                code_patient = None

                if isinstance(result, dict):
                    patient_id = result.get('patient_id')
                    code_patient = result.get('code_patient')
                else:
                    # Assume it's an object
                    patient_id = getattr(result, 'patient_id', None)
                    code_patient = getattr(result, 'code_patient', None)

                if patient_id and code_patient:
                    # store patient id for possible later refresh
                    self.patient_id = patient_id

                    # clear the form visually (you previously requested this)
                    self._clear_form()

                    # Open a single modal that first shows the code, then allows continuing to MR form.
                    # When MR form saves, we will call _on_medrec_saved to refresh / notify parent.
                    self._open_code_then_medrec_dialog(code_patient)

                else:
                    self._show_error("Erreur: Réponse invalide du serveur")

            else:
                # Update existing patient
                result = self.controller.update_patient(self.patient_id, data)

                if isinstance(result, dict) and 'error' in result:
                    self._show_error(f"Erreur: {result.get('details', 'Erreur inconnue')}")
                    return

                QMessageBox.information(self, "Succès", "Patient mis à jour avec succès")
                # Fermer le formulaire après mise à jour réussie
                self._close_form()

        except Exception as e:
            self._show_error(f"Erreur: {str(e)}")

    def _close_form(self):
        """Ferme le formulaire proprement (utilise window()/parent avec fallback)."""
        parent = self.parent()
        if parent is None:
            parent = self.window()
        # safe call: vérifie la présence de close
        if parent is not None and hasattr(parent, "close"):
            try:
                getattr(parent, "close")()
                return
            except Exception:
                pass
        # fallback
        try:
            self.close()
        except Exception:
            self.deleteLater()

    def _clear_form(self):
        """Vide tous les champs du formulaire et réinitialise les styles"""
        for key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate().addYears(-30))

        # Reset styles
        for widget in self.field_widgets.values():
            widget.setStyleSheet("")

        # Remove error label if present
        if self.error_label:
            self.error_label.deleteLater()
            self.error_label = None

    def _cancel(self):
        # safe close
        self._close_form()

    def _redirect_to_dashboard(self):
        parent = self.parent()
        if parent is None:
            parent = self.window()
        # attempt to call dashboard method, else close
        if parent and hasattr(parent, 'show_doctors_dashboard'):
            try:
                getattr(parent, 'show_doctors_dashboard')()
            except Exception:
                pass
            # close window if possible
            if hasattr(parent, "close"):
                try:
                    getattr(parent, "close")()
                except Exception:
                    pass
        else:
            QMessageBox.information(self, "Info", "Opération terminée avec succès")
            self._close_form()

    def _redirect_to_medical_record(self, code_patient):
        parent = self.parent()
        if parent is None:
            parent = self.window()
        if parent and hasattr(parent, 'show_medical_record_form'):
            try:
                getattr(parent, 'show_medical_record_form')(code_patient=code_patient)
            except Exception:
                # fallback to internal dialog
                self._open_medrec_fallback_dialog(code_patient)
            else:
                # if we successfully asked parent to show medrec, close our form
                self._close_form()
        else:
            # fallback: open a new dialog with medical record form preloaded
            self._open_medrec_fallback_dialog(code_patient)

    def _open_medrec_fallback_dialog(self, code_patient: str):
        dialog = QDialog(self)
        dialog.setModal(True)
        form = MedicalRecordFormView(dialog, self.controllers, self.current_user, patient_code=code_patient)
        # If MR form exposes on_save, we attach a handler to notify parent and possibly refresh.
        if hasattr(form, "on_save"):
            try:
                form.on_save = lambda res=None: self._on_medrec_saved(res, dialog)
            except Exception:
                pass
        layout = QVBoxLayout(dialog)
        layout.addWidget(form)
        dialog.setWindowTitle("Nouveau Dossier Médical")
        dialog.resize(800, 600)
        dialog.exec()

    def _on_medrec_saved(self, result=None, dialog: Optional[QDialog] = None):
        """Callback quand le MedicalRecordFormView a sauvegardé son contenu."""
        # fermer la dialog si fournie
        if dialog is not None:
            try:
                dialog.accept()
            except Exception:
                try:
                    dialog.close()
                except Exception:
                    pass

        # notifier le parent extérieur si nécessaire (rafraîchir liste patients, etc.)
        if callable(self.on_save):
            try:
                self.on_save(result)
            except Exception:
                pass

        # rafraîchir ce formulaire si on a un patient_id (charge les données si besoin)
        try:
            if getattr(self, "patient_id", None):
                self._load()
        except Exception:
            pass

    def _open_code_then_medrec_dialog(self, code_patient: str):
        """
        Ouvre une seule QDialog modal qui :
        1) affiche le code patient et 2 boutons (Continuer / Fermer)
        2) si Continuer -> remplace le contenu par MedicalRecordFormView (préchargé avec code_patient)
        """
        dialog = QDialog(self)
        dialog.setModal(True)
        dialog.setWindowTitle("Patient créé")
        dialog.resize(900, 700)

        main_layout = QVBoxLayout(dialog)
        dialog.setLayout(main_layout)

        # View initiale : message avec code + boutons
        msg_label = QLabel(f"Patient créé avec succès.\n\nCode patient : {code_patient}")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        btn_continue = QPushButton("Continuer vers le dossier médical")
        btn_close = QPushButton("Fermer")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_continue)

        # conteneur pour remplacement
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.addStretch()
        content_layout.addWidget(msg_label)
        content_layout.addStretch()
        content_layout.addLayout(btn_layout)

        main_layout.addWidget(content_container)

        # handlers
        def on_close():
            dialog.close()

        def on_continue():
            # clear content_layout safely
            for i in reversed(range(content_layout.count())):
                item = content_layout.takeAt(i)
                w = item.widget()
                if w:
                    w.setParent(None)

            # create MR form inside the same dialog
            try:
                mr_form = MedicalRecordFormView(dialog, self.controllers, self.current_user, patient_code=code_patient)
            except TypeError:
                mr_form = MedicalRecordFormView(dialog, self.controllers, self.current_user, patient_code=code_patient)

            # attach on_save of MR form to close dialog and notify us
            if hasattr(mr_form, "on_save"):
                try:
                    # override/assign the callback to ensure we run our logic
                    mr_form.on_save = lambda res=None: self._on_medrec_saved(res, dialog)
                except Exception:
                    pass

            close_after_layout = QHBoxLayout()
            close_btn = QPushButton("Fermer")
            close_btn.clicked.connect(dialog.close)
            close_after_layout.addStretch()
            close_after_layout.addWidget(close_btn)

            content_layout.addWidget(mr_form)
            content_layout.addLayout(close_after_layout)
            content_container.setLayout(content_layout)
            dialog.setWindowTitle("Dossier Médical — " + code_patient)

        btn_continue.clicked.connect(on_continue)
        btn_close.clicked.connect(on_close)

        dialog.exec()
