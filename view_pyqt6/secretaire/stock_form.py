import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QFrame, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QIcon, QDoubleValidator
from datetime import datetime
from view_pyqt6.api_controller import ApiGatewayError
from view_pyqt6.controller_resolver import ControllerResolver

logger = logging.getLogger(__name__)

class StockFormView(QDialog):
    def __init__(self, parent, controllers, product=None, on_save=None):
        super().__init__(parent)
        self.setWindowTitle(
            "Enregistrer Produit" + (" [Édition]" if product else " [Nouveau]")
        )
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.stock_controller()
        self.on_save = on_save
        self.product = product
        self.controllers = controllers

        self.texts = {
            "fr": {
                "title": "Enregistrer Produit",
                "name": "Nom du produit:",
                "quantity": "Quantité:",
                "threshold": "Seuil critique:",
                "type": "Type du produit:",
                "form": "Forme:",
                "dosage": "Dosage (mg):",
                "expiry": "Date d'expiration:",
                "save": "Enregistrer",
                "error_name": "Le nom du produit est requis.",
                "error_quantity": "La quantité doit être un entier positif.",
                "error_threshold": "Le seuil doit être un entier positif.",
                "error_form": "La forme est requise pour un produit pharmaceutique.",
                "error_dosage": "Le dosage doit être un nombre positif.",
                "error_date": "Format de date invalide.",
                "error_network": "Erreur réseau : impossible de sauvegarder le produit.",
                "error_unexpected": "Une erreur inattendue s'est produite.",
                "success_create": "Produit créé.",
                "success_update": "Produit mis à jour.",
                "no_form_natural": "(Pas de forme à saisir pour un produit Naturel)"
            },
            "en": {
                "title": "Register Product",
                "name": "Product Name:",
                "quantity": "Quantity:",
                "threshold": "Threshold:",
                "type": "Product Type:",
                "form": "Form:",
                "dosage": "Dosage (mg):",
                "expiry": "Expiry Date:",
                "save": "Save",
                "error_name": "Product name is required.",
                "error_quantity": "Quantity must be a positive integer.",
                "error_threshold": "Threshold must be a positive integer.",
                "error_form": "Form is required for pharmaceutical product.",
                "error_dosage": "Dosage must be a positive number.",
                "error_date": "Invalid date format.",
                "error_network": "Network error: unable to save product.",
                "error_unexpected": "An unexpected error occurred.",
                "success_create": "Product created.",
                "success_update": "Product updated.",
                "no_form_natural": "(No form needed for a Natural product)"
            }
        }
        self.locale = "fr"

        try:
            self._setup_ui()
            if self.product:
                self._load_product_into_form()
        except Exception as e:
            logger.exception("Failed to initialize StockFormView: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _setup_ui(self):
        logger.debug("Setting up StockFormView UI")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Title
        title = QLabel(self.texts[self.locale]["title"])
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Product Name
        frm_name = QFrame()
        name_layout = QHBoxLayout(frm_name)
        lbl_name = QLabel(self.texts[self.locale]["name"])
        self.entry_name = QLineEdit()
        name_layout.addWidget(lbl_name)
        name_layout.addWidget(self.entry_name)
        main_layout.addWidget(frm_name)

        # Quantity
        frm_qty = QFrame()
        qty_layout = QHBoxLayout(frm_qty)
        lbl_qty = QLabel(self.texts[self.locale]["quantity"])
        self.entry_qty = QLineEdit()
        self.entry_qty.setText("0")
        qty_layout.addWidget(lbl_qty)
        qty_layout.addWidget(self.entry_qty)
        main_layout.addWidget(frm_qty)

        # PRIX
        frm_price = QFrame()
        price_layout = QHBoxLayout(frm_price)
        lbl_price = QLabel("Prix unitaire (CFA):") # Tu peux ajouter ça dans self.texts si tu veux traduire
        self.entry_price = QLineEdit()
        self.entry_price.setText("0.00")
        # Validateur pour forcer des chiffres
        self.entry_price.setValidator(QDoubleValidator(0.0, 999999999.0, 2))
        price_layout.addWidget(lbl_price)
        price_layout.addWidget(self.entry_price)
        main_layout.addWidget(frm_price)
        # -----------------------------

        # Threshold
        frm_threshold = QFrame()
        threshold_layout = QHBoxLayout(frm_threshold)
        lbl_threshold = QLabel(self.texts[self.locale]["threshold"])
        self.entry_threshold = QLineEdit()
        self.entry_threshold.setText("0")
        threshold_layout.addWidget(lbl_threshold)
        threshold_layout.addWidget(self.entry_threshold)
        main_layout.addWidget(frm_threshold)

        # Product Type
        frm_type = QFrame()
        type_layout = QHBoxLayout(frm_type)
        lbl_type = QLabel(self.texts[self.locale]["type"])
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Naturel", "Pharmaceutique"])
        self.combo_type.currentTextChanged.connect(self._render_dynamic_fields)
        type_layout.addWidget(lbl_type)
        type_layout.addWidget(self.combo_type)
        main_layout.addWidget(frm_type)

        # Dynamic Frame
        self.dynamic_frame = QFrame()
        dynamic_layout = QVBoxLayout(self.dynamic_frame)
        dynamic_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.dynamic_frame)

        # Save Button
        btn_save = QPushButton(self.texts[self.locale]["save"])
        btn_save.setIcon(QIcon("assets/save.png"))
        btn_save.clicked.connect(self._save)
        main_layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch()

        self.setStyleSheet("""
            QDialog { background: #F5F5F5; }
            QPushButton { background-color: #2e7d32; color: white; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #1b5e20; cursor: pointer; }
            QLineEdit, QComboBox, QDateEdit { border: 1px solid #E0E0E0; border-radius: 5px; padding: 5px; }
            QLabel { color: #333333; }
        """)

        self._render_dynamic_fields()

    def _render_dynamic_fields(self):
        logger.debug("Rendering dynamic fields for type: %s", self.combo_type.currentText())
        while self.dynamic_frame.layout().count():
            item = self.dynamic_frame.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        layout = self.dynamic_frame.layout()
        chosen_type = self.combo_type.currentText()

        if chosen_type == "Naturel":
            lbl_no_form = QLabel(self.texts[self.locale]["no_form_natural"])
            layout.addWidget(lbl_no_form)
            self.entry_form = QLineEdit()
            self.entry_form.setText("Autre")
            self.entry_form.setVisible(False)
            layout.addWidget(self.entry_form)
        else:
            # Form
            lbl_form = QLabel(self.texts[self.locale]["form"])
            self.entry_form = QLineEdit()
            layout.addWidget(lbl_form)
            layout.addWidget(self.entry_form)

            # Dosage
            lbl_dosage = QLabel(self.texts[self.locale]["dosage"])
            self.entry_dosage = QLineEdit()
            self.entry_dosage.setText("0.0")
            layout.addWidget(lbl_dosage)
            layout.addWidget(self.entry_dosage)

            # Expiry Date
            lbl_expiry = QLabel(self.texts[self.locale]["expiry"])
            self.date_expiry = QDateEdit()
            self.date_expiry.setDisplayFormat("yyyy-MM-dd")
            self.date_expiry.setDate(QDate.currentDate())
            layout.addWidget(lbl_expiry)
            layout.addWidget(self.date_expiry)

        layout.addStretch()

    def _load_product_into_form(self):
        logger.debug("Chargement du produit dans le formulaire")
        if not self.product:
            return

        try:
            if isinstance(self.product, dict):
                p = self.product
            else:
                # ORM → on convertit en dict pour simplifier
                p = {
                    'drug_name': getattr(self.product, 'drug_name', ''),
                    'quantity': getattr(self.product, 'quantity', 0),
                    'threshold': getattr(self.product, 'threshold', 0),
                    'medication_type': getattr(self.product, 'medication_type', 'Naturel'),
                    'forme': getattr(self.product, 'forme', 'Autre'),
                    'dosage_mg': getattr(self.product, 'dosage_mg', None),
                    'expiry_date': getattr(self.product, 'expiry_date', None),
                    'price': getattr(self.product, 'price', 0.0),
                }

            self.entry_name.setText(str(p.get('drug_name', '')))
            self.entry_qty.setText(str(p.get('quantity', 0)))
            self.entry_threshold.setText(str(p.get('threshold', 0)))

            # --- AJOUT CHARGEMENT PRIX ---
            price_val = p.get('price', 0.0)
            self.entry_price.setText(f"{float(price_val):.2f}")
            # -----------------------------

            med_type = p.get('medication_type', 'Naturel')
            idx = self.combo_type.findText(med_type)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)

            self._render_dynamic_fields()  # recrée les champs

            if med_type == "Pharmaceutique":
                self.entry_form.setText(str(p.get('forme', '')))
                dosage = p.get('dosage_mg')
                self.entry_dosage.setText(str(dosage) if dosage not in (None, '', 'None') else "0.0")

                expiry = p.get('expiry_date')
                if expiry:
                    if isinstance(expiry, str):
                        try:
                            date_obj = QDate.fromString(expiry[:10], "yyyy-MM-dd")
                            self.date_expiry.setDate(date_obj)
                        except:
                            pass
                    elif hasattr(expiry, 'date'):
                        self.date_expiry.setDate(QDate(expiry.year, expiry.month, expiry.day))

        except Exception as e:
            logger.exception("Erreur lors du chargement du produit dans le formulaire : %s", e)
            # → On n'affiche RIEN à l'utilisateur → le formulaire reste vide mais ouvert
            pass

    def _save(self):
        logger.debug("Saving product")
        try:
            # === Validation champs ===
            name = self.entry_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_name"])
                return

            try:
                qty = int(self.entry_qty.text().strip() or 0)
                if qty < 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_quantity"])
                return

            try:
                threshold = int(self.entry_threshold.text().strip() or 0)
                if threshold < 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_threshold"])
                return
            
            # --- VALIDATION PRIX ---
            try:
                price_txt = self.entry_price.text().replace(",", ".").strip()
                price = float(price_txt) if price_txt else 0.0
                if price < 0: raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Erreur", "Le prix doit être un nombre positif.")
                return
            # -----------------------------

            med_type = self.combo_type.currentText()

            data = {
                'drug_name': name,
                'quantity': qty,
                'threshold': threshold,
                'price': price,
                'medication_type': med_type
            }

            if med_type == "Pharmaceutique":
                forme = self.entry_form.text().strip()
                if not forme:
                    QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_form"])
                    return
                data['forme'] = forme

                try:
                    dosage = float(self.entry_dosage.text().strip() or 0.0)
                    if dosage <= 0:
                        raise ValueError
                except ValueError:
                    QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_dosage"])
                    return
                data['dosage_mg'] = dosage

                expiry = self.date_expiry.date().toPyDate()
                data['expiry_date'] = expiry.isoformat() if expiry else None
            else:
                data['forme'] = "Autre"
                data['dosage_mg'] = None
                data['expiry_date'] = None

            # === SAUVEGARDE SECURISEE ===
            try:
                if self.product is not None and not callable(self.product) and not isinstance(self.product, (str, int, float, list, tuple)):
                    # C'est un vrai objet produit (dict ou ORM)
                    if isinstance(self.product, dict):
                        product_id = self.product.get('medication_id')
                    else:
                        product_id = getattr(self.product, 'medication_id', None)

                    if not product_id:
                        raise ValueError("ID produit manquant")

                    self.controller.update_product(int(product_id), data)
                    QMessageBox.information(self, "Succès", self.texts[self.locale]["success_update"])
                    if self.on_save:
                        self.on_save()
                    self.accept()

                else:
                    # Création
                    self.controller.create_product(data)
                    QMessageBox.information(self, "Succès", self.texts[self.locale]["success_create"])
                    if self.on_save:
                        self.on_save()

                    # Reset pour nouvelle saisie
                    self.entry_name.clear()
                    self.entry_qty.setText("0")
                    self.entry_threshold.setText("0")
                    self.combo_type.setCurrentIndex(0)
                    self._render_dynamic_fields()
                    self.entry_name.setFocus()

            except ApiGatewayError as e:
                logger.exception("API error: %s", e)
                QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_network"])
            except Exception as e:
                logger.exception("Erreur sauvegarde produit: %s", e)
                QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

        except Exception as e:
            logger.exception("Erreur validation: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])