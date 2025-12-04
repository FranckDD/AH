from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTextEdit, QCheckBox, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from datetime import datetime
import logging
from view_pyqt6.api_controller import ApiGatewayError
from view_pyqt6.controller_resolver import ControllerResolver

logger = logging.getLogger(__name__)

class CSFormView(QDialog):
    def __init__(self, parent, controllers, consultation=None, on_save=None):
        super().__init__(parent)
        self.setWindowTitle("Consultation Spirituelle" + (" [Édition]" if consultation else " [Nouveau]"))
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.consultation_spirituel_controller()
        self.patient_ctrl = self.resolver.patient_controller()
        self.on_save = on_save
        self.patient_id = None
        self.consultation = consultation
        self.controllers = controllers  # Store for consistency

        self.texts = {
            "fr": {
                "code": "Code patient:",
                "load": "Charger",
                "type": "Type:",
                "notes": "Notes:",
                "save": "Enregistrer",
                "presc_gen": "Prescription générale:",
                "med_spir": "Méd. spirituel:",
                "prayer_book": "Prayer Book:",
                "psaume": "Psaume:",
                "fr_reg": "Date enreg. (YYYY-MM-DD):",
                "fr_app": "Date RDV (YYYY-MM-DD):",
                "fr_amt": "Montant payé:",
                "fr_obs": "Observation:",
                "error_no_patient": "Chargez d'abord un patient",
                "error_date": "Format date invalide",
                "error_amount": "Montant invalide",
                "error_network": "Erreur réseau : impossible de sauvegarder la consultation.",
                "error_unexpected": "Une erreur inattendue s'est produite. Veuillez réessayer.",
                "success_create": "Consultation créée",
                "success_update": "Consultation mise à jour",
                "error_patient_not_found": "Patient introuvable"
            },
            "en": {
                "code": "Patient code:",
                "load": "Load",
                "type": "Type:",
                "notes": "Notes:",
                "save": "Save",
                "presc_gen": "General Prescription:",
                "med_spir": "Spiritual Med.:",
                "prayer_book": "Prayer Book:",
                "psaume": "Psalm:",
                "fr_reg": "Registration Date (YYYY-MM-DD):",
                "fr_app": "Appointment Date (YYYY-MM-DD):",
                "fr_amt": "Amount Paid:",
                "fr_obs": "Observation:",
                "error_no_patient": "Please load a patient first",
                "error_date": "Invalid date format",
                "error_amount": "Invalid amount",
                "error_network": "Network error: Unable to save consultation.",
                "error_unexpected": "An unexpected error occurred. Please try again.",
                "success_create": "Consultation created",
                "success_update": "Consultation updated",
                "error_patient_not_found": "Patient not found"
            }
        }
        self.locale = "fr"

        try:
            self._setup_ui()
            if self.consultation:
                self._load_consultation_into_form()
        except Exception as e:
            logger.exception("Failed to initialize CSFormView: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _setup_ui(self):
        logger.debug("Setting up CSFormView UI")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Titre
        title = QLabel("Consultation Spirituelle")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Code patient
        frm_top = QFrame()
        top_layout = QHBoxLayout(frm_top)
        lbl_code = QLabel(self.texts[self.locale]["code"])
        self.entry_code = QLineEdit()
        btn_load = QPushButton(self.texts[self.locale]["load"])
        btn_load.setIcon(QIcon("assets/load.png"))
        btn_load.clicked.connect(self.load_patient)

        # ← AJOUT : Label pour afficher le nom du patient chargé
        self.lbl_patient_name = QLabel("")
        self.lbl_patient_name.setStyleSheet("color: #155724; font-weight: bold; padding-left: 10px;")

        top_layout.addWidget(lbl_code)
        top_layout.addWidget(self.entry_code)
        top_layout.addWidget(btn_load)
        top_layout.addWidget(self.lbl_patient_name)
        main_layout.addWidget(frm_top)

        # Type de consultation
        lbl_type = QLabel(self.texts[self.locale]["type"])
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Spiritual", "FamilyRestoration"])
        self.combo_type.currentIndexChanged.connect(self.render_fields)
        main_layout.addWidget(lbl_type)
        main_layout.addWidget(self.combo_type)

        # Frame dynamique
        self.dynamic_frame = QFrame()
        dynamic_layout = QVBoxLayout(self.dynamic_frame)
        dynamic_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.dynamic_frame)

        # Notes
        lbl_notes = QLabel(self.texts[self.locale]["notes"])
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(80)
        main_layout.addWidget(lbl_notes)
        main_layout.addWidget(self.txt_notes)

        # Bouton Enregistrer
        btn_save = QPushButton(self.texts[self.locale]["save"])
        btn_save.setIcon(QIcon("assets/save.png"))
        btn_save.clicked.connect(self.save)
        main_layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch()

        self.setStyleSheet("""
            QDialog { background: #F5F5F5; }
            QPushButton { background-color: #2e7d32; color: white; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #1b5e20; cursor: pointer; }
            QLineEdit, QComboBox, QTextEdit, QCheckBox { border: 1px solid #E0E0E0; border-radius: 5px; padding: 5px; }
            QLabel { color: #333333; }
        """)

        self.render_fields()

    def load_patient(self):
        logger.debug("Loading patient with code: %s", self.entry_code.text())
        code = self.entry_code.text().strip()
        if not code:
            QMessageBox.warning(self, "Attention", self.texts[self.locale]["error_no_patient"])
            return
        try:
            p = self.patient_ctrl.find_by_code(code)
            if not p:
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_patient_not_found"])
                return

            self.patient_id = p.get("patient_id") if isinstance(p, dict) else getattr(p, "patient_id", None)
            
            # === CONFIRMATION VISUELLE ===
            first_name = p.get("first_name") or getattr(p, "first_name", "")
            last_name = p.get("last_name") or getattr(p, "last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            
            if full_name:
                self.lbl_patient_name.setText(f"✓ {full_name}")
            else:
                self.lbl_patient_name.setText("✓ Patient chargé")
            
            # Fond vert clair pour confirmer
            self.entry_code.setStyleSheet("background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724;")
            
            logger.debug("Patient loaded, ID: %s, Name: %s", self.patient_id, full_name)
        except Exception as e:
            logger.exception("Erreur chargement patient")
            self.lbl_patient_name.setText("")
            self.entry_code.setStyleSheet("")  # reset style
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_network"])
        except Exception as e:
            logger.exception("Unexpected error loading patient: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def render_fields(self):
        logger.debug("Rendering fields for type: %s", self.combo_type.currentText())
        while self.dynamic_frame.layout().count():
            item = self.dynamic_frame.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Reset des références pour éviter les crashes
        self.chk_vars_generic = {}
        self.chk_vars_med = {}
        self.combo_prayer = None
        self.entry_psaume = None
        self.entry_reg = self.entry_app = self.entry_amt = self.entry_obs = None
        self.prayer_book_map = {}  # {type_code: label}

        if self.combo_type.currentText() == "Spiritual":
            self._render_spiritual_fields()
        else:
            self._render_family_fields()

    def _render_spiritual_fields(self):
        logger.debug("Rendering spiritual fields")
        layout = self.dynamic_frame.layout()

        # Prescription générale
        lbl_gen = QLabel(self.texts[self.locale]["presc_gen"])
        layout.addWidget(lbl_gen)
        h_gen = QHBoxLayout()
        self.chk_vars_generic = {
            'Hony': QCheckBox("Hony"),
            'Massage': QCheckBox("Massage"),
            'Prayer': QCheckBox("Prayer")
        }
        for chk in self.chk_vars_generic.values():
            h_gen.addWidget(chk)
        layout.addLayout(h_gen)

        # Médicaments spirituels
        lbl_med = QLabel(self.texts[self.locale]["med_spir"])
        layout.addWidget(lbl_med)
        h_med = QHBoxLayout()
        self.chk_vars_med = {
            'SE': QCheckBox("SE"),
            'TIS': QCheckBox("TIS"),
            'AE': QCheckBox("AE")
        }
        for chk in self.chk_vars_med.values():
            h_med.addWidget(chk)
        layout.addLayout(h_med)

        # Prayer Book → affiche le label, enregistre le type_code
        lbl_prayer = QLabel(self.texts[self.locale]["prayer_book"])
        layout.addWidget(lbl_prayer)
        self.combo_prayer = QComboBox()
        self.combo_prayer.addItem("", None)  # option vide

        try:
            books = self.controller.gateway.get_prayer_book_types()
            if isinstance(books, dict) and books.get("error"):
                raise Exception("API error")

            for book in books:
                code = book.get("type_code")
                label = book.get("label") or code or "Inconnu"
                if code:
                    self.prayer_book_map[code] = label
                    self.combo_prayer.addItem(label, code)  # affichage = label, data = code

            logger.debug("Loaded %d prayer book types", len(books))
        except Exception as e:
            logger.exception("Impossible de charger les Prayer Books: %s", e)
            self.combo_prayer.addItem("Erreur chargement", None)

        layout.addWidget(self.combo_prayer)

        # Psaume
        lbl_psaume = QLabel(self.texts[self.locale]["psaume"])
        layout.addWidget(lbl_psaume)
        self.entry_psaume = QLineEdit()
        layout.addWidget(self.entry_psaume)

        layout.addStretch()

    def _render_family_fields(self):
        logger.debug("Rendering family fields")
        layout = self.dynamic_frame.layout()

        # Date d'enregistrement
        lbl_reg = QLabel(self.texts[self.locale]["fr_reg"])
        layout.addWidget(lbl_reg)
        self.entry_reg = QLineEdit()
        layout.addWidget(self.entry_reg)

        # Date de rendez-vous
        lbl_app = QLabel(self.texts[self.locale]["fr_app"])
        layout.addWidget(lbl_app)
        self.entry_app = QLineEdit()
        layout.addWidget(self.entry_app)

        # Montant payé
        lbl_amt = QLabel(self.texts[self.locale]["fr_amt"])
        layout.addWidget(lbl_amt)
        self.entry_amt = QLineEdit()
        layout.addWidget(self.entry_amt)

        # Observation
        lbl_obs = QLabel(self.texts[self.locale]["fr_obs"])
        layout.addWidget(lbl_obs)
        self.entry_obs = QLineEdit()
        layout.addWidget(self.entry_obs)

        layout.addStretch()

    def _load_consultation_into_form(self):
        logger.debug("Loading consultation into form: %s", self.consultation)
        try:
            cs = self.consultation
            if isinstance(cs, dict):
                patient = cs.get('patient', {})
                code = patient.get('code_patient', '') if patient else ''
                self.entry_code.setText(code)
                self.patient_id = cs.get('patient_id')
                type_consultation = cs.get('type_consultation', '')
                if type_consultation:
                    index = self.combo_type.findText(type_consultation)
                    if index >= 0:
                        self.combo_type.setCurrentIndex(index)
                    # ← IMPORTANT : recréer les champs dynamiques avant de charger les données
                    self.render_fields()

                if cs.get('notes'):
                    self.txt_notes.setPlainText(cs.get('notes', ''))

                if type_consultation == "Spiritual":
                    for label in cs.get('presc_generic', []) or []:
                        if label in self.chk_vars_generic:
                            self.chk_vars_generic[label].setChecked(True)
                    for label in cs.get('presc_med_spirituel', []) or []:
                        if label in self.chk_vars_med:
                            self.chk_vars_med[label].setChecked(True)

                    # Prayer Book
                    mp_code = cs.get('mp_type')
                    if mp_code and self.combo_prayer:
                        idx = self.combo_prayer.findData(mp_code)
                        if idx >= 0:
                            self.combo_prayer.setCurrentIndex(idx)
                        else:
                            # Livre supprimé → affiché temporairement
                            label = self.prayer_book_map.get(mp_code, f"{mp_code} (supprimé)")
                            self.combo_prayer.addItem(label, mp_code)
                            self.combo_prayer.setCurrentIndex(self.combo_prayer.count() - 1)

                    if cs.get('psaume'):
                        self.entry_psaume.setText(cs.get('psaume', ''))

                else:  # FamilyRestoration
                    if cs.get('fr_registered_at'):
                        reg = cs.get('fr_registered_at')
                        if isinstance(reg, datetime):
                            reg = reg.strftime("%Y-%m-%d")
                        self.entry_reg.setText(reg)
                    if cs.get('fr_appointment_at'):
                        app = cs.get('fr_appointment_at')
                        if isinstance(app, datetime):
                            app = app.strftime("%Y-%m-%d")
                        self.entry_app.setText(app)
                    if cs.get('fr_amount_paid') is not None:
                        self.entry_amt.setText(str(cs.get('fr_amount_paid')))
                    if cs.get('fr_observation'):
                        self.entry_obs.setText(cs.get('fr_observation', ''))
            else:
                if hasattr(cs, 'patient') and cs.patient:
                    code = getattr(cs.patient, "code_patient", "")
                    self.entry_code.setText(code)
                    self.patient_id = getattr(cs, 'patient_id', None)
                if hasattr(cs, 'type_consultation') and cs.type_consultation:
                    index = self.combo_type.findText(cs.type_consultation)
                    if index >= 0:
                        self.combo_type.setCurrentIndex(index)
                    self.render_fields()
                if hasattr(cs, 'notes') and cs.notes:
                    self.txt_notes.setPlainText(cs.notes)
                if getattr(cs, 'type_consultation', '') == "Spiritual":
                    if hasattr(cs, 'presc_generic') and cs.presc_generic:
                        for label in cs.presc_generic:
                            if label in self.chk_vars_generic:
                                self.chk_vars_generic[label].setChecked(True)
                    if hasattr(cs, 'presc_med_spirituel') and cs.presc_med_spirituel:
                        for label in cs.presc_med_spirituel:
                            if label in self.chk_vars_med:
                                self.chk_vars_med[label].setChecked(True)
                    if hasattr(cs, 'mp_type') and cs.mp_type:
                        index = self.combo_prayer.findText(cs.mp_type)
                        if index >= 0:
                            self.combo_prayer.setCurrentIndex(index)
                    if hasattr(cs, 'psaume') and cs.psaume:
                        self.entry_psaume.setText(cs.psaume)
                else:
                    if hasattr(cs, 'fr_registered_at') and cs.fr_registered_at:
                        self.entry_reg.setText(cs.fr_registered_at.strftime("%Y-%m-%d"))
                    if hasattr(cs, 'fr_appointment_at') and cs.fr_appointment_at:
                        self.entry_app.setText(cs.fr_appointment_at.strftime("%Y-%m-%d"))
                    if hasattr(cs, 'fr_amount_paid') and cs.fr_amount_paid is not None:
                        self.entry_amt.setText(str(cs.fr_amount_paid))
                    if hasattr(cs, 'fr_observation') and cs.fr_observation:
                        self.entry_obs.setText(cs.fr_observation)
            logger.debug("Consultation loaded into form")
        except Exception as e:
            logger.exception("Error loading consultation into form: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def save(self):
        logger.debug("Saving consultation, patient_id=%s", self.patient_id)
        try:
            if not self.patient_id:
                logger.warning("No patient loaded")
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_no_patient"])
                return

            data = {
                'patient_id': self.patient_id,
                'type_consultation': self.combo_type.currentText(),
                'notes': self.txt_notes.toPlainText().strip() or None
            }

            if data['type_consultation'] == 'Spiritual':
                sel_generic = [k for k, v in self.chk_vars_generic.items() if v.isChecked()]
                data['presc_generic'] = sel_generic if sel_generic else None
                sel_med = [k for k, v in self.chk_vars_med.items() if v.isChecked()]
                data['presc_med_spirituel'] = sel_med if sel_med else None
                
                # Envoie le type_code réel (pas le label)
                data['mp_type'] = self.combo_prayer.currentData()
                
                data['psaume'] = self.entry_psaume.text().strip() or None
            else:
                reg_str = self.entry_reg.text().strip()
                app_str = self.entry_app.text().strip()
                try:
                    data['fr_registered_at'] = datetime.strptime(reg_str, "%Y-%m-%d") if reg_str else None
                    data['fr_appointment_at'] = datetime.strptime(app_str, "%Y-%m-%d") if app_str else None
                except ValueError as e:
                    logger.exception("Invalid date format: %s", e)
                    QMessageBox.warning(self, "Erreur", f"{self.texts[self.locale]['error_date']}: {e}")
                    return
                try:
                    amt = float(self.entry_amt.text()) if self.entry_amt.text().strip() else None
                except ValueError as e:
                    logger.exception("Invalid amount: %s", e)
                    QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_amount"])
                    return
                data['fr_amount_paid'] = amt
                data['fr_observation'] = self.entry_obs.text().strip() or None

            # === SAUVEGARDE ===
            try:
                if self.consultation:
                    # Mode édition
                    cid = (self.consultation.get("consultation_id") 
                           if isinstance(self.consultation, dict) 
                           else self.consultation.consultation_id)
                    self.controller.update_consultation(cid, data)
                    QMessageBox.information(self, "Succès", self.texts[self.locale]["success_update"])
                    
                    # Édition → on ferme la fenêtre
                    if self.on_save:
                        self.on_save()
                    self.accept()

                else:
                    # Mode création
                    self.controller.create_consultation(data)
                    QMessageBox.information(self, "Succès", self.texts[self.locale]["success_create"])

                    # Callback pour rafraîchir la liste
                    if self.on_save:
                        self.on_save()

                    # === Réinitialisation du formulaire pour une nouvelle consultation ===
                    current_type = self.combo_type.currentText()

                    self.entry_code.clear()
                    # ← AJOUT : reset style et label
                    self.entry_code.setStyleSheet("")
                    self.lbl_patient_name.setText("")
                    self.patient_id = None
                    self.txt_notes.clear()

                    # Vide les champs dynamiques
                    self.render_fields()

                    # Restaure le type de consultation
                    idx = self.combo_type.findText(current_type)
                    if idx >= 0:
                        self.combo_type.setCurrentIndex(idx)

                    # Focus direct sur le code patient → prêt pour le suivant !
                    self.entry_code.setFocus()

            except Exception as e:
                logger.exception("Erreur lors de la sauvegarde: %s", e)
                raise

        except ApiGatewayError as e:
            logger.exception("API error saving consultation: %s", e)
            QMessageBox.critical(self, "Erreur", self.text-fluor["error_network"])
        except Exception as e:
            logger.exception("Unexpected error saving consultation: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])