import sys
from datetime import datetime
from typing import Optional, Callable, Dict, Any, cast

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QMessageBox, QFrame, QScrollArea, QFormLayout,
    QApplication, QSizePolicy, QDialog, QGroupBox, QGridLayout, QCheckBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QIcon

from view_pyqt6.controller_resolver import ControllerResolver
# Assurez-vous que l'import de MedicalRecordFormView est correct selon votre structure de projet
# from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView 

class PatientFormView(QWidget):
    # Style CSS pour uniformiser et moderniser l'interface
    STYLESHEET = """
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            font-size: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #333;
        }
        QLineEdit, QComboBox, QDateEdit {
            padding: 6px;
            border: 1px solid #aaa;
            border-radius: 4px;
            font-size: 13px;
            background-color: #fff;
        }
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
            border: 2px solid #3f51b5;
        }
        QCheckBox {
            font-size: 13px;
            spacing: 8px;
        }
    """

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
        
        # Checkboxes spécifiques
        self.chk_clinical = None
        self.chk_spiritual = None
        self.chk_toxico = None

        self.main_layout: QVBoxLayout  # type: ignore
        
        self.setStyleSheet(self.STYLESHEET)
        self._setup_ui()

        if not self.is_new:
            self._load()
        else:
            self._apply_role_defaults()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.main_layout = main_layout
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Titre
        title_text = "Nouveau Patient" if self.is_new else "Modifier Patient"
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title)

        # 2. Scroll Area (pour gérer les petits écrans)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll_area, 1)

        # Conteneur principal du formulaire
        form_container = QWidget()
        scroll_layout = QVBoxLayout(form_container)
        scroll_layout.setSpacing(20)
        scroll_area.setWidget(form_container)

        # --- SECTION A: TYPE DE PRISE EN CHARGE (CHECKBOXES) ---
        group_type = QGroupBox("Type de Prise en Charge")
        layout_type = QHBoxLayout(group_type)
        
        self.chk_clinical = QCheckBox("Clinique (Médical)")
        self.chk_spiritual = QCheckBox("Suivi Spirituel")
        self.chk_toxico = QCheckBox("Toxicologie")
        
        # Style des checkboxes pour les rendre plus visibles
        checkbox_style = "QCheckBox { font-weight: bold; padding: 5px; }"
        self.chk_clinical.setStyleSheet(checkbox_style)
        self.chk_spiritual.setStyleSheet(checkbox_style)
        self.chk_toxico.setStyleSheet(checkbox_style)

        layout_type.addWidget(self.chk_clinical)
        layout_type.addWidget(self.chk_spiritual)
        layout_type.addWidget(self.chk_toxico)
        layout_type.addStretch()
        
        scroll_layout.addWidget(group_type)

        # --- SECTION B: IDENTITÉ ---
        group_identity = QGroupBox("Identité du Patient")
        grid_identity = QGridLayout(group_identity)
        grid_identity.setColumnStretch(1, 1) # Étire les champs input
        grid_identity.setColumnStretch(3, 1)
        grid_identity.setHorizontalSpacing(20)
        grid_identity.setVerticalSpacing(15)

        # Helper pour ajouter des champs dans la grille
        def add_field(layout, label, key, widget_type, row, col):
            lbl = QLabel(label)
            widget = None
            if widget_type == "text":
                widget = QLineEdit()
            elif widget_type == "date":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDate(QDate.currentDate().addYears(-30))
                widget.setDisplayFormat("yyyy-MM-dd")
            elif widget_type == "combo":
                widget = QComboBox()
                widget.addItems(["Homme", "Femme", "Autre"])
            
            self.field_widgets[key] = widget
            layout.addWidget(lbl, row, col)
            layout.addWidget(widget, row, col + 1)

        # Ligne 0
        add_field(grid_identity, "Prénom *", "first_name", "text", 0, 0)
        add_field(grid_identity, "Nom *", "last_name", "text", 0, 2)
        
        # Ligne 1
        add_field(grid_identity, "Date Naissance *", "birth_date", "date", 1, 0)
        add_field(grid_identity, "Genre", "gender", "combo", 1, 2)

        # Ligne 2
        add_field(grid_identity, "N° National", "national_id", "text", 2, 0)

        scroll_layout.addWidget(group_identity)

        # --- SECTION C: COORDONNÉES ET STATUT ---
        group_contact = QGroupBox("Coordonnées & Statut")
        grid_contact = QGridLayout(group_contact)
        grid_contact.setColumnStretch(1, 1)
        grid_contact.setColumnStretch(3, 1)
        grid_contact.setHorizontalSpacing(20)
        grid_contact.setVerticalSpacing(15)

        add_field(grid_contact, "Téléphone", "contact_phone", "text", 0, 0)
        add_field(grid_contact, "Résidence", "residence", "text", 0, 2)
        add_field(grid_contact, "Assurance", "assurance", "text", 1, 0)

        scroll_layout.addWidget(group_contact)

        # --- SECTION D: FILIATION ---
        group_family = QGroupBox("Filiation")
        grid_family = QGridLayout(group_family)
        grid_family.setColumnStretch(1, 1)
        grid_family.setColumnStretch(3, 1)
        grid_family.setHorizontalSpacing(20)
        grid_family.setVerticalSpacing(15)

        add_field(grid_family, "Nom du Père", "father_name", "text", 0, 0)
        add_field(grid_family, "Nom de la Mère", "mother_name", "text", 0, 2)

        scroll_layout.addWidget(group_family)
        
        # Ajouter un stretch final pour pousser le formulaire vers le haut
        scroll_layout.addStretch()

        # --- SECTION BOUTONS ---
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._cancel)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336; color: white; font-weight: bold;
                padding: 10px 20px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)

        save_btn = QPushButton("Enregistrer")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32; color: white; font-weight: bold;
                padding: 10px 20px; border-radius: 4px; border: none;
            }
            QPushButton:hover { background-color: #1b5e20; }
        """)

        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        
        main_layout.addWidget(button_container)

    def _apply_role_defaults(self):
        """Coche les cases par défaut selon le rôle de l'utilisateur."""
        user_role = getattr(self.current_user, 'role_name', '').lower()
        
        # Réinitialiser tout
        self.chk_clinical.setChecked(False)
        self.chk_spiritual.setChecked(False)
        self.chk_toxico.setChecked(False)

        # Logique métier
        if 'secretaire' in user_role:
            self.chk_spiritual.setChecked(True)
        
        if any(r in user_role for r in ['medecin', 'nurse', 'assistant', 'docteur']):
            self.chk_clinical.setChecked(True)
            
        if 'admin' in user_role:
            # L'admin ne coche rien par défaut ou tout, au choix.
            # Ici on laisse vide pour forcer un choix conscient.
            pass

    def _show_error(self, message, invalid_fields=None):
        if self.error_label:
            self.error_label.deleteLater()

        self.error_label = QLabel(message)
        self.error_label.setStyleSheet("background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 4px; border: 1px solid #ef9a9a;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Insérer l'erreur en haut du layout principal (index 1, juste après le titre)
        try:
            self.main_layout.insertWidget(1, self.error_label)
        except Exception:
            self.main_layout.addWidget(self.error_label)

        # Reset styles
        for widget in self.field_widgets.values():
            if hasattr(widget, "setStyleSheet"):
                 # On remet le style par défaut défini dans le CSS global ou vide
                 widget.setStyleSheet("")

        # Highlight invalid fields
        if invalid_fields:
            for field in invalid_fields:
                widget = self.field_widgets.get(field)
                if widget:
                    widget.setStyleSheet("border: 2px solid #e53935; background-color: #fff8f8;")
                    widget.setFocus()

    def _load(self):
        try:
            patient_data = self.controller.get_patient(self.patient_id)

            if isinstance(patient_data, dict) and 'error' in patient_data:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger le patient: {patient_data.get('details', 'Erreur inconnue')}")
                return

            data = {}
            if isinstance(patient_data, dict):
                data = patient_data
            else:
                data = {key: getattr(patient_data, key, None) for key in self.field_widgets.keys()}
                # Récupérer aussi les drapeaux boolean de l'objet
                data['is_clinical'] = getattr(patient_data, 'is_clinical', False)
                data['is_spiritual'] = getattr(patient_data, 'is_spiritual', False)
                data['is_toxicology'] = getattr(patient_data, 'is_toxicology', False)

            # Remplissage des champs textes/dates
            for key, widget in self.field_widgets.items():
                value = data.get(key)
                if value is None: continue

                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0: widget.setCurrentIndex(index)
                elif isinstance(widget, QDateEdit) and value:
                    try:
                        if isinstance(value, str):
                            date = QDate.fromString(value, "yyyy-MM-dd")
                        else:
                            date = QDate(value.year, value.month, value.day)
                        widget.setDate(date)
                    except Exception:
                        pass
            
            # Remplissage des Checkboxes
            if self.chk_clinical: self.chk_clinical.setChecked(bool(data.get('is_clinical')))
            if self.chk_spiritual: self.chk_spiritual.setChecked(bool(data.get('is_spiritual')))
            if self.chk_toxico: self.chk_toxico.setChecked(bool(data.get('is_toxicology')))

        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")

    def _save(self):
        # 1. Collecte des données textuelles
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

        # 2. Collecte des Checkboxes (La nouveauté)
        data['is_clinical'] = self.chk_clinical.isChecked()
        data['is_spiritual'] = self.chk_spiritual.isChecked()
        data['is_toxicology'] = self.chk_toxico.isChecked()

        # 3. Validation
        required = ["first_name", "last_name", "birth_date"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            self._show_error("Veuillez remplir les champs obligatoires (*)", invalid_fields=missing)
            return

        try:
            if self.is_new:
                # Création
                result = self.controller.create_patient(data)

                if isinstance(result, dict) and 'error' in result:
                    self._show_error(f"Erreur: {result.get('details', 'Erreur inconnue')}")
                    return

                patient_id = None
                code_patient = None

                if isinstance(result, dict):
                    patient_id = result.get('patient_id')
                    code_patient = result.get('code_patient')
                else:
                    patient_id = getattr(result, 'patient_id', None)
                    code_patient = getattr(result, 'code_patient', None)

                if patient_id and code_patient:
                    self.patient_id = patient_id
                    self._clear_form()
                    # C'est ici qu'on appelle la nouvelle modal conditionnelle
                    self._open_code_then_medrec_dialog(code_patient)
                else:
                    self._show_error("Erreur: Réponse invalide du serveur")

            else:
                # Mise à jour
                result = self.controller.update_patient(self.patient_id, data)
                if isinstance(result, dict) and 'error' in result:
                    self._show_error(f"Erreur: {result.get('details', 'Erreur inconnue')}")
                    return

                QMessageBox.information(self, "Succès", "Patient mis à jour avec succès")
                self._close_form()

        except Exception as e:
            self._show_error(f"Erreur inattendue: {str(e)}")

    def _open_code_then_medrec_dialog(self, code_patient: str):
        """
        Affiche le code patient généré.
        Conditionne l'affichage du bouton 'Dossier Médical' selon le rôle.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Patient Enregistré")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        # Style du modal
        dialog.setStyleSheet("""
            QDialog { background-color: #fff; }
            QLabel { color: #333; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Icone de succès (simulée par texte ici ou image si dispo)
        lbl_icon = QLabel("✅")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 40px;")
        layout.addWidget(lbl_icon)

        # Message et Code
        lbl_info = QLabel("Le patient a été créé avec succès.")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl_info)

        lbl_code = QLabel(code_patient)
        lbl_code.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #1976D2; 
            padding: 15px; 
            background-color: #e3f2fd;
            border-radius: 8px;
            border: 1px dashed #1976D2;
        """)
        lbl_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(lbl_code)

        lbl_hint = QLabel("(Ce code a été copié dans le presse-papier)")
        lbl_hint.setStyleSheet("color: #757575; font-size: 11px; font-style: italic;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_hint)

        # Copie automatique
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(code_patient)

        # Boutons d'action conditionnels
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_close = QPushButton("Nouveau Patient / Fermer")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(dialog.accept)
        btn_close.setStyleSheet("padding: 8px; border: 1px solid #aaa; border-radius: 4px; background-color: #f5f5f5;")
        btn_layout.addWidget(btn_close)

        # --- LOGIQUE CONDITIONNELLE ---
        user_role = getattr(self.current_user, 'role_name', '').lower()
        is_medical_staff = any(r in user_role for r in ['medecin', 'nurse', 'assistant', 'docteur'])
        
        # Si c'est Admin, on peut aussi donner l'accès
        if 'admin' in user_role:
             is_medical_staff = True

        if is_medical_staff:
            btn_mr = QPushButton("Ouvrir Dossier Médical")
            btn_mr.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_mr.setStyleSheet("""
                QPushButton {
                    background-color: #0288d1; 
                    color: white; 
                    font-weight: bold;
                    padding: 8px 15px;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #01579b; }
            """)
            
            def open_mr():
                dialog.accept() # Ferme le modal
                self._go_to_medical_record(code_patient) # Ouvre le dossier
                
            btn_mr.clicked.connect(open_mr)
            btn_layout.addWidget(btn_mr)
        
        layout.addLayout(btn_layout)
        dialog.exec()

    def _go_to_medical_record(self, code_patient):
        """Redirige vers la vue dossier médical via le parent."""
        parent = self.window()
        
        # Essayer différentes méthodes potentielles sur le parent
        if hasattr(parent, "open_medical_record_by_code"):
            parent.open_medical_record_by_code(code_patient)
        elif hasattr(parent, "show_medical_dashboard"):
            # Si on ne peut pas ouvrir direct, on va au dashboard
            parent.show_medical_dashboard() 
        else:
            # Fallback simple
            QMessageBox.information(self, "Info", f"Veuillez ouvrir le dossier {code_patient} depuis le tableau de bord.")

    def _close_form(self):
        parent = self.parent()
        if parent is None:
            parent = self.window()
        if parent is not None and hasattr(parent, "close"):
            try:
                getattr(parent, "close")()
                return
            except Exception:
                pass
        try:
            self.close()
        except Exception:
            self.deleteLater()

    def _clear_form(self):
        for key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate().addYears(-30))

        # Reset Checkboxes par défaut
        self._apply_role_defaults()

        # Reset styles
        for widget in self.field_widgets.values():
            if hasattr(widget, "setStyleSheet"):
                 widget.setStyleSheet("")

        if self.error_label:
            self.error_label.deleteLater()
            self.error_label = None

    def _cancel(self):
        self._clear_form()

    def _redirect_to_dashboard(self):
        # Méthode utilitaire gardée pour compatibilité
        parent = self.parent()
        if parent is None:
            parent = self.window()
        if parent and hasattr(parent, 'show_doctors_dashboard'):
            try:
                getattr(parent, 'show_doctors_dashboard')()
            except Exception:
                pass
            if hasattr(parent, "close"):
                try:
                    getattr(parent, "close")()
                except Exception:
                    pass
        else:
            QMessageBox.information(self, "Info", "Opération terminée")