import sys
from datetime import datetime
from typing import Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QMessageBox, QScrollArea, QFormLayout,
    QApplication, QSizePolicy, QDialog, QCheckBox, QGroupBox # 🟢 Ajout QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont

from view_pyqt6.controller_resolver import ControllerResolver


class PatientsEditView(QWidget):
    def __init__(self, parent, controllers: Any, patient_id: int):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.patient_controller()
        self.patient_id = patient_id

        # Initialisation des widgets Checkbox
        self.chk_clinical = None
        self.chk_spiritual = None
        self.chk_toxico = None

        self._setup_ui()
        self._load_patient()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_text = "Éditer un patient" if self.patient_id else "Ajouter un patient"
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        main_layout.addWidget(scroll_area, 1)

        # Form container
        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(10)
        scroll_area.setWidget(form_container)

        # 🟢 AJOUT : Section Type de Patient (Checkboxes)
        type_group = QGroupBox("Type de Prise en charge")
        type_layout = QHBoxLayout(type_group)
        
        self.chk_clinical = QCheckBox("Clinique")
        self.chk_spiritual = QCheckBox("Spirituel")
        self.chk_toxico = QCheckBox("Toxicologie")
        
        # Style pour rendre plus visible
        chk_style = "font-weight: bold; font-size: 13px;"
        self.chk_clinical.setStyleSheet(chk_style)
        self.chk_spiritual.setStyleSheet(chk_style)
        self.chk_toxico.setStyleSheet(chk_style)

        type_layout.addWidget(self.chk_clinical)
        type_layout.addWidget(self.chk_spiritual)
        type_layout.addWidget(self.chk_toxico)
        type_layout.addStretch() # Pousser vers la gauche

        # On ajoute le groupe en haut du formulaire
        form_layout.addRow(type_group)
        # ----------------------------------------------------

        # Form fields
        self.fields = {}
        labels = [
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

        for label_text, key, field_type in labels:
            if field_type == "text":
                widget = QLineEdit()
                self.fields[key] = widget
                form_layout.addRow(QLabel(label_text), widget)
            elif field_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(QDate.currentDate().addYears(-30))
                widget.setDisplayFormat("yyyy-MM-dd")
                self.fields[key] = widget
                form_layout.addRow(QLabel(label_text), widget)
            elif field_type == "combo":
                widget = QComboBox()
                widget.addItems(["Homme", "Femme", "Autre"])
                self.fields[key] = widget
                form_layout.addRow(QLabel(label_text), widget)

        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
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
        
        if self.patient_id:
            delete_btn = QPushButton("Supprimer")
            delete_btn.clicked.connect(self._on_delete)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #b71c1c;
                }
            """)
            button_layout.addWidget(delete_btn)
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self._cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        
        main_layout.addLayout(button_layout)

    def _load_patient(self):
        if not self.patient_id:
            return
            
        try:
            patient_data = self.controller.get_patient(self.patient_id)
            
            if isinstance(patient_data, dict) and 'error' in patient_data:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger le patient: {patient_data.get('details', 'Erreur inconnue')}")
                return
                
            # Extract data
            data = {}
            if isinstance(patient_data, dict):
                data = patient_data
            else:
                # Si c'est un objet, on le convertit en dict ou on utilise getattr
                # On récupère d'abord les champs standards
                data = {key: getattr(patient_data, key, None) for key in self.fields.keys()}
                # 🟢 On récupère aussi les drapeaux booléens
                data['is_clinical'] = getattr(patient_data, 'is_clinical', False)
                data['is_spiritual'] = getattr(patient_data, 'is_spiritual', False)
                data['is_toxicology'] = getattr(patient_data, 'is_toxicology', False)
            
            # Populate form fields (Standard)
            for key, widget in self.fields.items():
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
                            date = QDate(value.year, value.month, value.day)
                        widget.setDate(date)
                    except Exception:
                        pass

            # 🟢 Populate Checkboxes (Types)
            if self.chk_clinical: self.chk_clinical.setChecked(bool(data.get('is_clinical')))
            if self.chk_spiritual: self.chk_spiritual.setChecked(bool(data.get('is_spiritual')))
            if self.chk_toxico: self.chk_toxico.setChecked(bool(data.get('is_toxicology')))
                        
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")

    def _collect_data(self):
        data = {}
        
        # 1. Collecte Champs Texte/Date
        for key, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                value = widget.text().strip()
                data[key] = value if value else None
            elif isinstance(widget, QComboBox):
                data[key] = widget.currentText()
            elif isinstance(widget, QDateEdit):
                qdate = widget.date()
                data[key] = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        
        # 🟢 2. Collecte Checkboxes
        data['is_clinical'] = self.chk_clinical.isChecked()
        data['is_spiritual'] = self.chk_spiritual.isChecked()
        data['is_toxicology'] = self.chk_toxico.isChecked()

        # Set empty strings to None
        optional_fields = ['national_id', 'contact_phone', 'assurance', 'residence', 'father_name', 'mother_name']
        for field in optional_fields:
            if data.get(field) == '':
                data[field] = None
        
        return data

    def _on_save(self):
        data = self._collect_data()
        
        # Validate required fields
        required = ["first_name", "last_name", "birth_date"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            QMessageBox.warning(self, "Erreur", "Champs obligatoires manquants: " + ", ".join(missing))
            return
        
        try:
            # Grâce au Gateway, on appelle les méthodes standards
            if self.patient_id:
                result = self.controller.update_patient(self.patient_id, data)
                
                if isinstance(result, dict) and 'error' in result:
                    QMessageBox.warning(self, "Erreur", f"Erreur lors de la mise à jour: {result.get('details', 'Erreur inconnue')}")
                    return
                
                QMessageBox.information(self, "Succès", "Patient mis à jour avec succès")
            else:
                result = self.controller.create_patient(data)
                
                if isinstance(result, dict) and 'error' in result:
                    QMessageBox.warning(self, "Erreur", f"Erreur lors de la création: {result.get('details', 'Erreur inconnue')}")
                    return
                
                QMessageBox.information(self, "Succès", "Patient créé avec succès")
            
            # Fermer la fenêtre
            self.parent().close()
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'enregistrement: {str(e)}")

    def _on_delete(self):
        reply = QMessageBox.question(
            self, 
            "Confirmation", 
            "Êtes-vous sûr de vouloir supprimer ce patient ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.controller.delete_patient(self.patient_id)
                
                if isinstance(result, dict) and 'error' in result:
                    QMessageBox.warning(self, "Erreur", f"Erreur lors de la suppression: {result.get('details', 'Erreur inconnue')}")
                    return
                
                QMessageBox.information(self, "Succès", "Patient supprimé avec succès")
                self.parent().close()
                
            except Exception as e:
                QMessageBox.warning(self, "Erreur", f"Erreur lors de la suppression: {str(e)}")

    def _cancel(self):
        self.parent().close()