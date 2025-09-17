import sys
import winsound
from datetime import datetime, date
from typing import Any, Dict, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QDateEdit, QScrollArea, QFrame, QMessageBox,
    QFormLayout, QSizePolicy, QApplication, QDialog, QGridLayout, QGroupBox, QMainWindow
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QDoubleValidator, QIntValidator
from PyQt6.QtCore import QTimer

from view_pyqt6.controller_resolver import ControllerResolver


class MedicalRecordFormView(QWidget):
    def __init__(self, parent, controllers: Any, current_user: Any, 
                 record_id: Optional[int] = None, on_save: Optional[Callable] = None, patient_code: Optional[str] = None):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.medical_record_controller()
        self.current_user = current_user
        self.record_id = record_id
        self.on_save = on_save
        self.is_new = record_id is None
        self.patient_code = patient_code
        
        # Données pour les combobox
        self.marital_options = [
            ("Célibataire", "Single"),
            ("Marié(e)", "Married"),
            ("Divorcé(e)", "Divorced"),
            ("Veuf(ve)", "Widowed")
        ]
        
        self.severity_options = [
            ("Faible", "low"),
            ("Moyen", "medium"),
            ("Élevé", "high")
        ]
        
        self.field_widgets = {}
        self.error_label = None
        self.motif_options = []
        self.patient_id = None
        
        self._setup_ui()
        self._load_motifs()
        
        if self.patient_code:
            self.search_entry.setText(self.patient_code)
            self._on_search()
        
        if not self.is_new:
            self._load_record()

    def _load_motifs(self):
        """Charge les motifs depuis l'API"""
        try:
            motifs = self.controller.list_motifs()
            
            if isinstance(motifs, dict) and 'error' in motifs:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger les motifs: {motifs.get('details', 'Erreur inconnue')}")
                self.motif_options = [("Aucun motif disponible", "")]
                return
                
            # Formater les options de motif
            self.motif_options = [("Sélectionner un motif", "")]  # Option par défaut
            
            if isinstance(motifs, list):
                for motif in motifs:
                    if isinstance(motif, dict):
                        label = motif.get('label_fr', motif.get('code', 'Inconnu'))
                        code = motif.get('code', '')
                        self.motif_options.append((label, code))
                    else:
                        label = getattr(motif, 'label_fr', getattr(motif, 'code', 'Inconnu'))
                        code = getattr(motif, 'code', '')
                        self.motif_options.append((label, code))
            
            # Mettre à jour le combobox des motifs
            if hasattr(self, 'motif_combo'):
                self.motif_combo.clear()
                for label, code in self.motif_options:
                    self.motif_combo.addItem(label, code)
                    
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement des motifs: {str(e)}")
            self.motif_options = [("Erreur de chargement", "")]

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("Formulaire Dossier Médical")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        main_layout.addWidget(title)
        
        # Scroll area for form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll_area, 1)
        
        # Form container
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(15)
        scroll_area.setWidget(form_container)
        
        # Section Recherche Patient
        patient_group = QGroupBox("Informations Patient")
        patient_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        patient_layout = QVBoxLayout(patient_group)
        
        search_layout = QHBoxLayout()
        search_label = QLabel("Rechercher par ID ou code:")
        search_label.setStyleSheet("font-weight: bold;")
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("ID patient ou code")
        self.search_entry.returnPressed.connect(self._on_search)  # Enter key support
        search_btn = QPushButton("🔍 Rechercher")
        search_btn.clicked.connect(self._on_search)
        search_btn.setStyleSheet("padding: 5px; background-color: #3498db; color: white;")
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_entry, 1)
        search_layout.addWidget(search_btn)
        patient_layout.addLayout(search_layout)
        
        # Patient info display
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #f8f9fa; padding: 10px; border-radius: 5px;")
        info_layout = QGridLayout(info_frame)
        
        self.patient_id_label = QLabel("ID: -")
        self.patient_code_label = QLabel("Code: -")
        self.patient_name_label = QLabel("Nom: -")
        self.patient_dob_label = QLabel("Naissance: -")
        
        info_layout.addWidget(QLabel("ID:"), 0, 0)
        info_layout.addWidget(self.patient_id_label, 0, 1)
        info_layout.addWidget(QLabel("Code:"), 0, 2)
        info_layout.addWidget(self.patient_code_label, 0, 3)
        info_layout.addWidget(QLabel("Nom:"), 1, 0)
        info_layout.addWidget(self.patient_name_label, 1, 1, 1, 3)
        info_layout.addWidget(QLabel("Naissance:"), 2, 0)
        info_layout.addWidget(self.patient_dob_label, 2, 1, 1, 3)
        
        patient_layout.addWidget(info_frame)
        form_layout.addWidget(patient_group)
        
        # Section Informations Consultation
        consult_group = QGroupBox("Informations Consultation")
        consult_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        consult_layout = QGridLayout(consult_group)
        
        # Row 0
        consult_layout.addWidget(QLabel("Date Consultation:"), 0, 0)
        self.consultation_date = QDateEdit()
        self.consultation_date.setCalendarPopup(True)
        self.consultation_date.setDate(QDate.currentDate())
        self.consultation_date.setDisplayFormat("yyyy-MM-dd")
        consult_layout.addWidget(self.consultation_date, 0, 1)
        
        consult_layout.addWidget(QLabel("Motif:"), 0, 2)
        self.motif_combo = QComboBox()
        for label, code in self.motif_options:
            self.motif_combo.addItem(label, code)
        consult_layout.addWidget(self.motif_combo, 0, 3)
        
        # Row 1
        consult_layout.addWidget(QLabel("Statut matrimonial:"), 1, 0)
        self.marital_combo = QComboBox()
        for display, value in self.marital_options:
            self.marital_combo.addItem(display, value)
        consult_layout.addWidget(self.marital_combo, 1, 1)
        
        consult_layout.addWidget(QLabel("Gravité:"), 1, 2)
        self.severity_combo = QComboBox()
        for display, value in self.severity_options:
            self.severity_combo.addItem(display, value)
        consult_layout.addWidget(self.severity_combo, 1, 3)
        
        form_layout.addWidget(consult_group)
        
        # Section Signes Vitaux
        vital_group = QGroupBox("Signes Vitaux")
        vital_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        vital_layout = QGridLayout(vital_group)
        
        vital_layout.addWidget(QLabel("Tension artérielle:"), 0, 0)
        self.bp_entry = QLineEdit()
        self.bp_entry.setPlaceholderText("Ex: 120/80")
        vital_layout.addWidget(self.bp_entry, 0, 1)
        
        vital_layout.addWidget(QLabel("Température (°C):"), 0, 2)
        self.temp_entry = QLineEdit()
        self.temp_entry.setValidator(QDoubleValidator(30, 45, 1))
        self.temp_entry.setPlaceholderText("Ex: 36.6")
        vital_layout.addWidget(self.temp_entry, 0, 3)
        
        vital_layout.addWidget(QLabel("Poids (kg):"), 1, 0)
        self.weight_entry = QLineEdit()
        self.weight_entry.setValidator(QDoubleValidator(0, 300, 1))
        self.weight_entry.setPlaceholderText("Ex: 70.5")
        vital_layout.addWidget(self.weight_entry, 1, 1)
        
        vital_layout.addWidget(QLabel("Taille (cm):"), 1, 2)
        self.height_entry = QLineEdit()
        self.height_entry.setValidator(QDoubleValidator(0, 250, 1))
        self.height_entry.setPlaceholderText("Ex: 175")
        vital_layout.addWidget(self.height_entry, 1, 3)
        
        form_layout.addWidget(vital_group)
        
        # Section Antécédents (OPTIONNEL)
        history_group = QGroupBox("Antécédents et Allergies (Optionnel)")
        history_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        history_layout = QVBoxLayout(history_group)
        
        self.history_text = QTextEdit()
        self.history_text.setPlaceholderText("Antécédents médicaux...")
        self.history_text.setMaximumHeight(80)
        history_layout.addWidget(self.history_text)
        
        self.allergy_text = QTextEdit()
        self.allergy_text.setPlaceholderText("Allergies connues...")
        self.allergy_text.setMaximumHeight(80)
        history_layout.addWidget(self.allergy_text)
        
        form_layout.addWidget(history_group)
        
        # Section Diagnostic (OPTIONNEL)
        diag_group = QGroupBox("Diagnostic et Traitement (Optionnel)")
        diag_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        diag_layout = QVBoxLayout(diag_group)
        
        self.symptoms_text = QTextEdit()
        self.symptoms_text.setPlaceholderText("Symptômes rapportés...")
        self.symptoms_text.setMaximumHeight(80)
        diag_layout.addWidget(self.symptoms_text)
        
        self.diagnosis_text = QTextEdit()
        self.diagnosis_text.setPlaceholderText("Diagnostic posé...")
        self.diagnosis_text.setMaximumHeight(80)
        diag_layout.addWidget(self.diagnosis_text)
        
        self.treatment_text = QTextEdit()
        self.treatment_text.setPlaceholderText("Traitement prescrit...")
        self.treatment_text.setMaximumHeight(80)
        diag_layout.addWidget(self.treatment_text)
        
        form_layout.addWidget(diag_group)
        
        # Section Notes (OPTIONNEL)
        notes_group = QGroupBox("Notes supplémentaires (Optionnel)")
        notes_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("Notes additionnelles...")
        self.notes_text.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_text)
        
        form_layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self._cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        button_layout.addWidget(save_btn)
        
        if not self.is_new:
            delete_btn = QPushButton("Supprimer")
            delete_btn.clicked.connect(self._on_delete)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            button_layout.addWidget(delete_btn)
        
        form_layout.addLayout(button_layout)

    def _show_error(self, message, invalid_fields=None):
        if self.error_label:
            self.error_label.deleteLater()
            
        self.error_label = QLabel(message)
        self.error_label.setStyleSheet("color: red; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().insertWidget(1, self.error_label)
        
        if invalid_fields:
            for field in invalid_fields:
                if field == "search":
                    self.search_entry.setStyleSheet("border: 2px solid red;")
                    self.search_entry.setFocus()
                elif hasattr(self, field + "_entry"):
                    getattr(self, field + "_entry").setStyleSheet("border: 2px solid red;")
                    getattr(self, field + "_entry").setFocus()
                elif hasattr(self, field + "_combo"):
                    getattr(self, field + "_combo").setStyleSheet("border: 2px solid red;")
                    getattr(self, field + "_combo").setFocus()
                elif hasattr(self, field + "_text"):
                    getattr(self, field + "_text").setStyleSheet("border: 2px solid red;")
                    getattr(self, field + "_text").setFocus()

    def _on_search(self):
        search_term = self.search_entry.text().strip()
        if not search_term:
            self._show_error("Veuillez entrer un ID ou code patient", ["search"])
            return
            
        try:
            patient_controller = self.resolver.patient_controller()
            
            if search_term.isdigit():
                patient_data = patient_controller.get_patient(int(search_term))
            else:
                patients = patient_controller.list_patients(search=search_term)
                if patients and isinstance(patients, list) and len(patients) > 0:
                    patient_data = patients[0]
                elif patients and isinstance(patients, dict) and 'data' in patients and len(patients['data']) > 0:
                    patient_data = patients['data'][0]
                else:
                    patient_data = None
            
            if not patient_data or (isinstance(patient_data, dict) and 'error' in patient_data):
                self._show_error("Patient non trouvé", ["search"])
                return
                
            if isinstance(patient_data, dict):
                patient_id = patient_data.get('patient_id')
                code = patient_data.get('code_patient', '')
                first_name = patient_data.get('first_name', '')
                last_name = patient_data.get('last_name', '')
                birth_date = patient_data.get('birth_date', '')
            else:
                patient_id = getattr(patient_data, 'patient_id', None)
                code = getattr(patient_data, 'code_patient', '')
                first_name = getattr(patient_data, 'first_name', '')
                last_name = getattr(patient_data, 'last_name', '')
                birth_date = getattr(patient_data, 'birth_date', '')
            
            self.patient_id_label.setText(f"ID: {patient_id}")
            self.patient_code_label.setText(f"Code: {code}")
            self.patient_name_label.setText(f"Nom: {last_name} {first_name}")
            self.patient_dob_label.setText(f"Naissance: {birth_date}")
            
            self.patient_id = patient_id
            
            if self.error_label:
                self.error_label.deleteLater()
                self.error_label = None
            self.search_entry.setStyleSheet("")
                
        except Exception as e:
            self._show_error(f"Erreur lors de la recherche: {str(e)}", ["search"])

    def _on_save(self) -> None:
        # Clear UI feedback
        """try:
            self._clear_feedback()
            self._clear_highlights()
        except Exception:
            pass"""

        # --- Basic presence checks ---
        if not getattr(self, "patient_id", None):
            self._show_error("Veuillez d'abord sélectionner un patient", ["search"])
            return

        # motif: index 0 is placeholder -> must be > 0 and have data
        if not hasattr(self, "motif_combo") or self.motif_combo.currentIndex() <= 0 or not self.motif_combo.currentData():
            self._show_error("Veuillez sélectionner un motif valide", ["motif_combo"])
            return

        # marital & severity must have data (index 0 can be a valid value)
        if not hasattr(self, "marital_combo") or not self.marital_combo.currentData():
            self._show_error("Veuillez sélectionner un statut matrimonial", ["marital_combo"])
            return
        if not hasattr(self, "severity_combo") or not self.severity_combo.currentData():
            self._show_error("Veuillez sélectionner la gravité", ["severity_combo"])
            return

        # consultation_date validity
        try:
            if not hasattr(self, "consultation_date") or not self.consultation_date.date().isValid():
                self._show_error("Date de consultation invalide", ["consultation_date"])
                return
        except Exception:
            self._show_error("Date de consultation invalide", ["consultation_date"])
            return

        # --- Numeric validations (if provided) ---
        def _parse_float(s):
            try:
                ss = s.strip()
                if ss == "":
                    return None
                return float(ss)
            except Exception:
                return None

        # temperature / weight / height checks (range)
        # Only validate when user provided a value
        numeric_specs = {
            "temperature": ("Température", 30, 45, getattr(self, "temp_entry", None)),
            "weight": ("Poids (kg)", 0, 1000, getattr(self, "weight_entry", None)),
            "height": ("Taille (cm)", 30, 250, getattr(self, "height_entry", None)),
        }
        for key, (label, mn, mx, widget) in numeric_specs.items():
            if widget is None:
                continue
            try:
                txt = widget.text().strip()
            except Exception:
                txt = ""
            if txt:
                val = _parse_float(txt)
                if val is None:
                    self._show_error(f"{label} doit être un nombre", [widget.objectName() if hasattr(widget, "objectName") else None])
                    return
                if not (mn <= val < mx):
                    self._show_error(f"{label} doit être entre {mn} et {mx}", [widget.objectName() if hasattr(widget, "objectName") else None])
                    return

        # --- Build payload ---
        # Date -> ISO datetime (safe)
        try:
            qdate = self.consultation_date.date()
            date_str = qdate.toString("yyyy-MM-dd")
            try:
                # create full ISO datetime (00:00:00) which Pydantic/DB accepts
                from datetime import datetime as _dt
                date_obj = _dt.strptime(date_str, "%Y-%m-%d")
                consultation_iso = date_obj.isoformat()
            except Exception:
                consultation_iso = date_str
        except Exception:
            consultation_iso = None

        data: Dict[str, Any] = {
            "patient_id": int(self.patient_id),
            "consultation_date": consultation_iso,
            "marital_status": self.marital_combo.currentData(),
            "severity": self.severity_combo.currentData(),
            "motif_code": self.motif_combo.currentData(),
        }

        # bp (string)
        try:
            if hasattr(self, "bp_entry"):
                bpv = self.bp_entry.text().strip()
                data["bp"] = bpv if bpv else None
        except Exception:
            pass

        # numeric fields
        try:
            if hasattr(self, "temp_entry"):
                t = _parse_float(self.temp_entry.text())
                data["temperature"] = t
        except Exception:
            data["temperature"] = None
        try:
            if hasattr(self, "weight_entry"):
                w = _parse_float(self.weight_entry.text())
                data["weight"] = w
        except Exception:
            data["weight"] = None
        try:
            if hasattr(self, "height_entry"):
                h = _parse_float(self.height_entry.text())
                data["height"] = h
        except Exception:
            data["height"] = None

        # textareas (may be empty)
        try:
            data["medical_history"] = self.history_text.toPlainText().strip() if hasattr(self, "history_text") else None
        except Exception:
            data["medical_history"] = None
        try:
            data["allergies"] = self.allergy_text.toPlainText().strip() if hasattr(self, "allergy_text") else None
        except Exception:
            data["allergies"] = None
        try:
            data["symptoms"] = self.symptoms_text.toPlainText().strip() if hasattr(self, "symptoms_text") else None
        except Exception:
            data["symptoms"] = None
        try:
            data["diagnosis"] = self.diagnosis_text.toPlainText().strip() if hasattr(self, "diagnosis_text") else None
        except Exception:
            data["diagnosis"] = None
        try:
            data["treatment"] = self.treatment_text.toPlainText().strip() if hasattr(self, "treatment_text") else None
        except Exception:
            data["treatment"] = None
        try:
            data["notes"] = self.notes_text.toPlainText().strip() if hasattr(self, "notes_text") else None
        except Exception:
            data["notes"] = None

        # Audit fields if available
        try:
            if getattr(self, "current_user", None):
                user_id = getattr(self.current_user, "user_id", None)
                username = getattr(self.current_user, "username", None)
                if user_id:
                    data["created_by"] = user_id
                    data["last_updated_by"] = user_id
                if username:
                    data["created_by_name"] = username
                    data["last_updated_by_name"] = username
        except Exception:
            pass

        # --- Ensure all keys expected by backend update procedure are present ---
        # This prevents SQLAlchemy binding errors when payload is partial.
        expected_update_keys = [
            "marital_status", "bp", "temperature", "weight", "height",
            "medical_history", "allergies", "symptoms", "diagnosis", "treatment",
            "severity", "notes", "motif_code", "consultation_date"
        ]
        for k in expected_update_keys:
            data.setdefault(k, None)

        # --- Debug print of payload ---
        try:
            import json
            print("DEBUG CLIENT PAYLOAD:", json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print("DEBUG CLIENT PAYLOAD:", data)
        try:
            print("DEBUG controller object:", type(self.controller), getattr(self.controller, "__dict__", "{}"))
        except Exception:
            pass

        # --- Send to controller / gateway ---
        try:
            if self.is_new:
                result = self.controller.create_medical_record(data)
                if isinstance(result, dict) and result.get("error"):
                    self._show_error(f"Erreur création: {result.get('details', 'Erreur inconnue')}")
                    return
                
                # SUCCÈS - Message auto-fermant et rafraîchissement
                self._show_auto_close_message("Succès", "Dossier médical créé avec succès", 1500)
                
                # Rafraîchir le formulaire pour une nouvelle saisie
                self._reset_form()
                
            else:
                result = self.controller.update_medical_record(self.record_id, data)
                if isinstance(result, dict) and result.get("error"):
                    self._show_error(f"Erreur mise à jour: {result.get('details', 'Erreur inconnue')}")
                    return
                
                # SUCCÈS - Message auto-fermant et fermeture
                self._show_auto_close_message("Succès", "Dossier médical mis à jour avec succès", 1500)
                
                # Fermer le formulaire et retourner à la liste
                self._close_and_show_list()
                
        except Exception as e:
            # Show server-side or network exception
            self._show_error(f"Erreur lors de l'enregistrement : {e}")



    def _show_auto_close_message(self, title: str, message: str, timeout: int = 2000):
        """Affiche un message qui se ferme automatiquement"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.button(QMessageBox.StandardButton.Ok).setVisible(False)  # Cacher le bouton OK
        
        # Fermer automatiquement après timeout
        QTimer.singleShot(timeout, msg_box.accept)
        msg_box.exec()



    def _on_delete(self):
        if not self.record_id:
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirmation", 
            "Êtes-vous sûr de vouloir supprimer ce dossier médical ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.controller.delete_medical_record(self.record_id)
                
                if isinstance(result, dict) and 'error' in result:
                    QMessageBox.warning(self, "Erreur", f"Impossible de supprimer: {result.get('details', 'Erreur inconnue')}")
                    return
                
                QMessageBox.information(self, "Succès", "Dossier médical supprimé avec succès")
                self._close_form()
                
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Erreur lors de la suppression: {str(e)}")

    def _load_record(self):
        try:
            record_data = self.controller.get_medical_record(self.record_id)
            
            if isinstance(record_data, dict) and 'error' in record_data:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger le dossier: {record_data.get('details', 'Erreur inconnue')}")
                return
                
            # Extract data
            data = {}
            if isinstance(record_data, dict):
                data = record_data
            else:
                data = {key: getattr(record_data, key, None) for key in [
                    'patient_id', 'consultation_date', 'marital_status', 'severity',
                    'motif_code', 'bp', 'temperature', 'weight', 'height',
                    'medical_history', 'allergies', 'symptoms', 'diagnosis',
                    'treatment', 'notes'
                ]}
            
            # Load patient info
            patient_id = data.get('patient_id')
            if patient_id:
                try:
                    patient_controller = self.resolver.patient_controller()
                    patient_data = patient_controller.get_patient(patient_id)
                    
                    if patient_data and not (isinstance(patient_data, dict) and 'error' in patient_data):
                        if isinstance(patient_data, dict):
                            code = patient_data.get('code_patient', '')
                            first_name = patient_data.get('first_name', '')
                            last_name = patient_data.get('last_name', '')
                            birth_date = patient_data.get('birth_date', '')
                        else:
                            code = getattr(patient_data, 'code_patient', '')
                            first_name = getattr(patient_data, 'first_name', '')
                            last_name = getattr(patient_data, 'last_name', '')
                            birth_date = getattr(patient_data, 'birth_date', '')
                        
                        self.patient_id_label.setText(f"ID: {patient_id}")
                        self.patient_code_label.setText(f"Code: {code}")
                        self.patient_name_label.setText(f"Nom: {last_name} {first_name}")
                        self.patient_dob_label.setText(f"Naissance: {birth_date}")
                        self.patient_id = patient_id
                except Exception:
                    pass
            
            # Populate form fields
            # Date
            consult_date = data.get('consultation_date')
            if consult_date:
                try:
                    if isinstance(consult_date, str):
                        qdate = QDate.fromString(consult_date, "yyyy-MM-dd")
                    else:
                        qdate = QDate(consult_date.year, consult_date.month, consult_date.day)
                    self.consultation_date.setDate(qdate)
                except Exception:
                    pass
            
            # Combo boxes
            marital_status = data.get('marital_status')
            if marital_status:
                for i in range(self.marital_combo.count()):
                    if self.marital_combo.itemData(i) == marital_status:
                        self.marital_combo.setCurrentIndex(i)
                        break
            
            severity = data.get('severity')
            if severity:
                for i in range(self.severity_combo.count()):
                    if self.severity_combo.itemData(i) == severity:
                        self.severity_combo.setCurrentIndex(i)
                        break
            
            motif_code = data.get('motif_code')
            if motif_code:
                for i in range(self.motif_combo.count()):
                    if self.motif_combo.itemData(i) == motif_code:
                        self.motif_combo.setCurrentIndex(i)
                        break
            
            # Text fields
            text_fields = {
                'bp': self.bp_entry,
                'temperature': self.temp_entry,
                'weight': self.weight_entry,
                'height': self.height_entry
            }
            
            for field, widget in text_fields.items():
                value = data.get(field)
                if value:
                    widget.setText(str(value))
            
            # Text areas
            text_areas = {
                'medical_history': self.history_text,
                'allergies': self.allergy_text,
                'symptoms': self.symptoms_text,
                'diagnosis': self.diagnosis_text,
                'treatment': self.treatment_text,
                'notes': self.notes_text
            }
            
            for field, widget in text_areas.items():
                value = data.get(field)
                if value:
                    widget.setPlainText(str(value))
                        
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")

    def _reset_form(self):
        """Réinitialise le formulaire pour une nouvelle saisie"""
        try:
            # Réinitialiser tous les champs
            self.search_entry.clear()
            self.patient_id_label.setText("ID: -")
            self.patient_code_label.setText("Code: -")
            self.patient_name_label.setText("Nom: -")
            self.patient_dob_label.setText("Naissance: -")
            self.patient_id = None
            
            # Réinitialiser la date à aujourd'hui
            self.consultation_date.setDate(QDate.currentDate())
            
            # Réinitialiser les combobox
            self.marital_combo.setCurrentIndex(0)
            self.severity_combo.setCurrentIndex(0)
            self.motif_combo.setCurrentIndex(0)
            
            # Réinitialiser les champs texte
            self.bp_entry.clear()
            self.temp_entry.clear()
            self.weight_entry.clear()
            self.height_entry.clear()
            self.history_text.clear()
            self.allergy_text.clear()
            self.symptoms_text.clear()
            self.diagnosis_text.clear()
            self.treatment_text.clear()
            self.notes_text.clear()
            
            # Supprimer les messages d'erreur
            if self.error_label:
                self.error_label.deleteLater()
                self.error_label = None
                
            # Remettre le focus sur la recherche
            self.search_entry.setFocus()
            
        except Exception as e:
            print(f"Erreur lors de la réinitialisation du formulaire: {e}")

    def _close_and_show_list(self):
        """Ferme le formulaire et affiche la liste des dossiers médicaux"""
        try:
            # Appeler le callback parent pour afficher la liste
            if callable(self.on_save):
                self.on_save()
            
            # Fermer le formulaire
            self._close_form()
            
        except Exception as e:
            print(f"Erreur lors de la fermeture: {e}")
            self._close_form()

    def _close_form(self):
        parent = self.parent()
        while parent and not isinstance(parent, (QDialog, QMainWindow)):
            parent = parent.parent()
        
        if parent:
            parent.close()
        else:
            self.deleteLater()

    def _cancel(self):
        self._close_form()