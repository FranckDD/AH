import logging
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QFrame, QComboBox, QMessageBox, QHeaderView
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QDate
from view_pyqt6.secretaire.stock_form import StockFormView
from view_pyqt6.api_controller import ApiGatewayError
from view_pyqt6.controller_resolver import ControllerResolver
from datetime import datetime

logger = logging.getLogger(__name__)

class StockListView(QWidget):
    def __init__(self, parent, controllers):
        super().__init__(parent)
        self.resolver = ControllerResolver(controllers)
        self.controllers = controllers

        self.texts = {
            "fr": {
                "title": "Liste des Produits",
                "new": "Nouveau",
                "edit": "Éditer",
                "refresh": "Rafraîchir",
                "search": "Rechercher:",
                "type": "Type:",
                "status": "Statut:",
                "error_no_selection": "Aucun produit sélectionné.",
                "error_invalid_id": "ID invalide.",
                "error_network": "Erreur réseau : impossible de charger les données.",
                "error_unexpected": "Une erreur inattendue s'est produite.",
                "no_data": "Aucun produit trouvé.",
                "controller_error": "Contrôleur de stock non initialisé."
            },
            "en": {
                "title": "Product List",
                "new": "New",
                "edit": "Edit",
                "refresh": "Refresh",
                "search": "Search:",
                "type": "Type:",
                "status": "Status:",
                "error_no_selection": "No product selected.",
                "error_invalid_id": "Invalid ID.",
                "error_network": "Network error: unable to load data.",
                "error_unexpected": "An unexpected error occurred.",
                "no_data": "No products found.",
                "controller_error": "Stock controller not initialized."
            }
        }
        self.locale = "fr"

        # === INITIALISATION DU CONTROLLER ===
        try:
            self.controller = self.resolver.stock_controller()
        except Exception as e:
            logger.exception("Impossible d'initialiser le contrôleur de stock: %s", e)
            self.controller = None  # ← OK ici, mais seulement si vraiment échoué

        # === PAGINATION ===
        self.current_page = 1
        self.per_page = 25
        self.total_items = 0
        self.total_pages = 1

        # === UI + CHARGEMENT ===
        try:
            self._setup_ui()
            self._load_page()  # ← maintenant self.texts existe, tout est bon
        except Exception as e:
            logger.exception("Erreur lors de l'initialisation de l'interface: %s", e)
            QMessageBox.critical(self, "Erreur", "Impossible d'initialiser l'interface.")

    def _setup_ui(self):
        logger.debug("Setting up StockListView UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title
        title = QLabel(self.texts[self.locale]["title"])
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        # Filter Frame
        filter_group = QFrame()
        filter_group.setStyleSheet("QFrame { border: 1px solid #E0E0E0; border-radius: 5px; }")
        filter_layout = QHBoxLayout(filter_group)
        
        # Search
        lbl_search = QLabel(self.texts[self.locale]["search"])
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Nom, type ou forme…")
        self.search_entry.textChanged.connect(self._apply_filters)
        search_btn = QPushButton("🔍")
        search_btn.setFixedWidth(40)
        search_btn.clicked.connect(self._apply_filters)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                cursor: pointer;
            }
        """)
        
        # Type Filter
        lbl_type = QLabel(self.texts[self.locale]["type"])
        self.combo_type = QComboBox()
        types = ["Tous", "Naturel", "Pharmaceutique"]
        if self.controller:
            try:
                products = self.controller.list_products()
                types = ["Tous"] + sorted({p.get('medication_type', '') for p in products if p.get('medication_type')})
            except Exception as e:
                logger.exception("Error loading product types: %s", e)
        self.combo_type.addItems(types)
        self.combo_type.currentTextChanged.connect(self._apply_filters)
        
        # Status Filter
        lbl_status = QLabel(self.texts[self.locale]["status"])
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Tous", "normal", "critique", "épuisé"])
        self.combo_status.currentTextChanged.connect(self._apply_filters)

        filter_layout.addWidget(lbl_search)
        filter_layout.addWidget(self.search_entry, 1)
        filter_layout.addWidget(search_btn)
        filter_layout.addWidget(lbl_type)
        filter_layout.addWidget(self.combo_type)
        filter_layout.addWidget(lbl_status)
        filter_layout.addWidget(self.combo_status)
        layout.addWidget(filter_group)

        # Table
        self.table = QTableWidget()
        cols = (
            "name", "type", "form", "price", "quantity", "threshold", "status", "dosage", "expiry"
        )
        headings = {
            "name": "Nom",
            "type": "Type",
            "form": "Forme",
            "price": "Prix (CFA)",
            "quantity": "Quantité",
            "threshold": "Seuil",
            "status": "Statut",
            "dosage": "Dosage (mg)",
            "expiry": "Expiration"
        }
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([headings[col] for col in cols])
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget::item:selected { background-color: #b8e6f3; }
            QTableWidget::item[status="normal"] { background-color: white; }
            QTableWidget::item[status="critique"] { background-color: #FFF3CD; }
            QTableWidget::item[status="épuisé"] { background-color: #F8D7DA; }
        """)
        layout.addWidget(self.table, 1)

                # === BOUTONS D'ACTION – HARMONISÉS ET ERGONOMIQUES ===
        action_layout = QHBoxLayout()

        # Bouton Nouveau – Vert principal (action créative)
        btn_new = QPushButton(self.tr("new"))
        btn_new.setIcon(QIcon("assets/add.png"))
        btn_new.clicked.connect(self._on_create)
        btn_new.setStyleSheet("""
            QPushButton {
                background-color: #10b981;   /* vert émeraude moderne */
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)

        # Bouton Éditer – Bleu principal (action principale)
        btn_edit = QPushButton(self.tr("edit"))
        btn_edit.setIcon(QIcon("assets/edit.png"))
        btn_edit.clicked.connect(self._on_edit)
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;   /* bleu moderne */
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)

        # Bouton Rafraîchir – Gris neutre (action secondaire)
        btn_refresh = QPushButton(self.tr("refresh"))
        btn_refresh.setIcon(QIcon("assets/refresh.png"))
        btn_refresh.clicked.connect(self._load_page)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #6b7280;   /* gris moyen */
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
        """)

        action_layout.addWidget(btn_new)
        action_layout.addWidget(btn_edit)
        action_layout.addWidget(btn_refresh)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        self.btn_prev = QPushButton("◀ Précédent")
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setFixedWidth(120)

        self.lbl_page = QLabel("Page 1 / 1 (0 produits)")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page.setMinimumWidth(200)

        self.btn_next = QPushButton("Suivant ▶")
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setFixedWidth(120)

        action_layout.addWidget(btn_new)
        action_layout.addWidget(btn_edit)
        action_layout.addWidget(btn_refresh)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_prev)
        action_layout.addWidget(self.lbl_page)
        action_layout.addWidget(self.btn_next)
        layout.addLayout(action_layout)
                # === LÉGENDE DES COULEURS (ajoutée en bas) ===
        legend_frame = QFrame()
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setSpacing(20)
        legend_layout.setContentsMargins(10, 10, 10, 10)
        legend_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;")

        # Statut stock
        stock_legend = QHBoxLayout()
        stock_legend.addWidget(QLabel("Stock :"))
        normal_box = QLabel(" Normal ")
        normal_box.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 4px; padding: 2px 8px;")
        warning_box = QLabel(" Proche seuil ")
        warning_box.setStyleSheet("background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; border-radius: 4px; padding: 2px 8px;")
        critical_box = QLabel(" Épuisé / Critique ")
        critical_box.setStyleSheet("background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px; padding: 2px 8px;")
        stock_legend.addWidget(normal_box)
        stock_legend.addWidget(warning_box)
        stock_legend.addWidget(critical_box)
        stock_legend.addStretch()

        # Expiration
        exp_legend = QHBoxLayout()
        exp_legend.addWidget(QLabel("Expiration :"))
        exp_ok = QLabel(" OK ")
        exp_ok.setStyleSheet("background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; border-radius: 4px; padding: 2px 8px;")
        exp_soon = QLabel(" < 30 jours ")
        exp_soon.setStyleSheet("background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; border-radius: 4px; padding: 2px 8px;")
        exp_expired = QLabel(" Expiré ")
        exp_expired.setStyleSheet("background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; border-radius: 4px; padding: 2px 8px;")
        exp_legend.addWidget(exp_ok)
        exp_legend.addWidget(exp_soon)
        exp_legend.addWidget(exp_expired)
        exp_legend.addStretch()

        legend_layout.addLayout(stock_legend)
        legend_layout.addLayout(exp_legend)
        layout.addWidget(legend_frame)

    

    def _load_page(self):
        logger.debug("Chargement page %d", self.current_page)
        if not self.controller:
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["controller_error"])
            return

        try:
            # Appel API avec tous les filtres + pagination
            response = self.controller.list_products(
                page=self.current_page,
                per_page=self.per_page,
                term=self.search_entry.text().strip() or None,
                type_filter=self.combo_type.currentText() if self.combo_type.currentText() != "Tous" else None,
                status_filter=self.combo_status.currentText() if self.combo_status.currentText() != "Tous" else None
            )

            # Gestion de la réponse paginée
            if isinstance(response, dict) and "data" in response:
                data = response["data"]
                self.total_items = response.get("total", 0)
                self.total_pages = response.get("total_pages", 1)
                self.current_page = response.get("page", 1)
            else:
                data = response if isinstance(response, list) else []
                self.total_items = len(data)
                self.total_pages = 1

            self._populate_table(data)
            self._update_pagination_buttons()

        except ApiGatewayError as e:
            logger.exception("Erreur réseau lors du chargement: %s", e)
            QMessageBox.critical(self, "Erreur réseau", "Impossible de charger les produits.")
        except Exception as e:
            logger.exception("Erreur inattendue lors du chargement: %s", e)
            QMessageBox.critical(self, "Erreur", "Une erreur inconnue s'est produite.")

    def _apply_filters(self):
        logger.debug("Application des filtres (recherche/type/statut)")
        self.current_page = 1  # Reset page quand on change de filtre
        self._load_page()        

    def load_data(self):
        self.current_page = 1
        self.search_entry.clear()
        self.combo_type.setCurrentText("Tous")
        self.combo_status.setCurrentText("Tous")
        self._load_page()  # ← remplace self._apply_filters()

    def _populate_table(self, data=None):
        logger.debug("Remplissage table avec %d produits", len(data) if data else 0)
        self.table.clearContents()
        self.table.setRowCount(0)

        if not data or len(data) == 0:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("Aucun produit trouvé"))
            return

        self.table.setRowCount(len(data))
        today = QDate.currentDate()
        warning_date = today.addDays(30)

        for row, p in enumerate(data):
            drug_name = str(p.get('drug_name') or '')
            med_type = str(p.get('medication_type') or '')
            forme = str(p.get('forme') or 'Autre')
            quantity = int(p.get('quantity') or 0)
            threshold = int(p.get('threshold') or 0)
            status = str(p.get('stock_status') or 'normal').lower()
            dosage = p.get('dosage_mg')
            dosage_str = f"{float(dosage):.1f}" if dosage and str(dosage).replace('.', '').replace('-', '').isdigit() else ""

            # --- AJOUT PRIX ---
            price_val = float(p.get('price') or 0.0)
            price_str = f"{price_val:,.0f}" # Format millier sans décimale pour CFA, ou :,.2f
            # ------------------

            expiry_raw = p.get('expiry_date')
            expiry_str = ""
            expiry_qdate = None
            if expiry_raw:
                if isinstance(expiry_raw, str):
                    expiry_qdate = QDate.fromString(expiry_raw[:10], "yyyy-MM-dd")
                elif hasattr(expiry_raw, 'year'):
                    expiry_qdate = QDate(expiry_raw.year, expiry_raw.month, expiry_raw.day)
                if expiry_qdate and expiry_qdate.isValid():
                    expiry_str = expiry_qdate.toString("dd/MM/yyyy")

            items = [
                QTableWidgetItem(drug_name),
                QTableWidgetItem(med_type),
                QTableWidgetItem(forme),
                QTableWidgetItem(price_str),
                QTableWidgetItem(str(quantity)),
                QTableWidgetItem(str(threshold)),
                QTableWidgetItem(status.capitalize()),
                QTableWidgetItem(dosage_str),
                QTableWidgetItem(expiry_str)
            ]

            items[0].setData(Qt.ItemDataRole.UserRole, p.get('medication_id'))

            # Couleurs stock
            if quantity <= 0 or "épuis" in status:
                stock_color = QColor("#f8d7da")
            elif quantity <= threshold:
                stock_color = QColor("#fff3cd")
            else:
                stock_color = QColor("#ffffff")

            # Couleurs expiration
            if expiry_qdate and expiry_qdate.isValid():
                if expiry_qdate < today:
                    exp_color = QColor("#f8d7da")
                elif expiry_qdate <= warning_date:
                    exp_color = QColor("#fff3cd")
                else:
                    exp_color = QColor("#d4edda")
            else:
                exp_color = QColor("#ffffff")

            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
                if col == 5:  # statut
                    item.setBackground(stock_color)
                if col == 7:  # expiration
                    item.setBackground(exp_color)

    def _on_create(self):
        logger.debug("Creating new product")
        if not self.controller:
            logger.error("StockController not initialized")
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["controller_error"])
            return

        try:
            form = StockFormView(
                parent=self,
                controllers=self.controllers,
                product=None,
                on_save=lambda: (self.load_data(), form.close())
            )
            form.show()
        except Exception as e:
            logger.exception("Error creating new product: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _on_edit(self):
        logger.debug("Édition d'un produit")
        if not self.controller:
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["controller_error"])
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Info", self.texts[self.locale]["error_no_selection"])
            return

        item = self.table.item(row, 0)
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            QMessageBox.warning(self, "Attention", "Produit non valide ou ID manquant.")
            return

        product_id = item.data(Qt.ItemDataRole.UserRole)

        # On charge le produit SANS afficher d'erreur parasite
        try:
            product = self.controller.get_product(int(product_id))
        except Exception as e:
            logger.exception("Erreur lors du chargement du produit ID=%s : %s", product_id, e)
            QMessageBox.critical(self, "Erreur", "Impossible de charger le produit.\nVérifiez votre connexion ou contactez l'administrateur.")
            return

        # Si le produit est vide ou None
        if not product or (isinstance(product, dict) and len(product) == 0):
            QMessageBox.warning(self, "Attention", f"Produit ID {product_id} introuvable ou supprimé.")
            return

        # === OUVERTURE DU FORMULAIRE – TOUJOURS ICI, SANS EXCEPTION ===
        try:
            form = StockFormView(
                parent=self,
                controllers=self.controllers,
                product=product,
                on_save=self.load_data
            )
            form.exec()
        except Exception as e:
            logger.exception("Erreur lors de l'ouverture du formulaire d'édition : %s", e)
            QMessageBox.critical(self, "Erreur", "Impossible d'ouvrir le formulaire d'édition.")

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._load_page()

    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_page()

    def _update_pagination_buttons(self):
        self.lbl_page.setText(f"Page {self.current_page} / {self.total_pages} ({self.total_items} produits)")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)        