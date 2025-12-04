import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QMessageBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView, QWidget, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator

logger = logging.getLogger(__name__)

class AddItemDialog(QDialog):
    def __init__(
        self, 
        parent, 
        on_confirm, 
        allowed_types: list, 
        patient_id=None, 
        initial_data: dict = None, 
        pharmacy_ctrl=None, 
        consultation_spirituel_ctrl=None, 
        medical_record_ctrl=None,
        lab_controller=None,
        locale: str = "fr"
    ):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.allowed_types = allowed_types
        self.patient_id = patient_id
        self.initial_data = initial_data
        self.pharmacy_ctrl = pharmacy_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl
        self.lab_controller = lab_controller
        self.locale = locale
        
        self.exams_list = [] 
        self._med_mapping = {} 

        self.texts = {
            "fr": {
                "title": "Ajouter une ligne",
                "type": "Type de ligne :",
                "cat": "Catégorie Méd. :",
                "prod": "Produit :",
                "ref": "Réf. ID :",
                "qty": "Quantité :",
                "price": "Prix unitaire :",
                "note": "Note :",
                "exams": "Examens disponibles :",
                "search_exam": "Rechercher un examen...",
                "confirm": "Valider",
                "cancel": "Annuler",
                "err_qty": "Quantité invalide (doit être > 0).",
                "err_price": "Prix invalide (doit être >= 0).",
                "err_ref": "Réf. ID invalide.",
                "err_exam_sel": "Sélectionnez au moins un examen.",
                "err_exam_price": "Prix invalide pour l'examen : ",
                "cat_nat": "Naturel",
                "cat_pharma": "Pharmaceutique",
                "loading": "Chargement...",
                "error": "Erreur",
                "col_exam": "Examen",
                "col_price": "Prix"
            },
            "en": {
                "title": "Add Line Item",
                "type": "Line Type:",
                "cat": "Med Category:",
                "prod": "Product:",
                "ref": "Ref. ID:",
                "qty": "Quantity:",
                "price": "Unit Price:",
                "note": "Note:",
                "exams": "Available Exams:",
                "search_exam": "Search exam...",
                "confirm": "Confirm",
                "cancel": "Cancel",
                "err_qty": "Invalid quantity (must be > 0).",
                "err_price": "Invalid price (must be >= 0).",
                "err_ref": "Invalid Ref. ID.",
                "err_exam_sel": "Select at least one exam.",
                "err_exam_price": "Invalid price for exam: ",
                "cat_nat": "Natural",
                "cat_pharma": "Pharmaceutical",
                "loading": "Loading...",
                "error": "Error",
                "col_exam": "Exam",
                "col_price": "Price"
            }
        }

        self.setWindowTitle(self.texts[self.locale]["title"])
        self.resize(600, 650)
        self._setup_ui()
        
        # Initialisation logique
        forced = self.allowed_types[0] if len(self.allowed_types) == 1 else None
        default_type = self.initial_data.get("item_type") if self.initial_data else (forced or self.allowed_types[0])
        
        idx = self.combo_type.findText(default_type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        if forced:
            self.combo_type.setEnabled(False)
            
        # Pré-remplissage
        if self.initial_data:
            self.entry_qty.setText(str(self.initial_data.get("quantity", 1)))
            self.entry_price.setText(f"{self.initial_data.get('unit_price', 0):.2f}")
            self.entry_note.setText(self.initial_data.get("note", ""))
            self.entry_ref.setText(str(self.initial_data.get("item_ref_id", 0)))
        else:
            self.entry_ref.setText(str(self.patient_id) if self.patient_id else "0")

        # Forcer la mise à jour de l'interface selon le type initial
        self._update_visibility()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Formulaire Grid (Champs standards) ---
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # Type
        grid.addWidget(QLabel(self.texts[self.locale]["type"]), 0, 0)
        self.combo_type = QComboBox()
        self.combo_type.addItems(self.allowed_types)
        self.combo_type.currentTextChanged.connect(self._update_visibility)
        grid.addWidget(self.combo_type, 0, 1)
        
        # Catégorie (Médicament)
        self.lbl_cat = QLabel(self.texts[self.locale]["cat"])
        grid.addWidget(self.lbl_cat, 1, 0)
        self.combo_cat = QComboBox()
        self.combo_cat.addItems([self.texts[self.locale]["cat_nat"], self.texts[self.locale]["cat_pharma"]])
        self.combo_cat.currentTextChanged.connect(self._on_med_category_change)
        grid.addWidget(self.combo_cat, 1, 1)
        
        # Produit
        self.lbl_prod = QLabel(self.texts[self.locale]["prod"])
        grid.addWidget(self.lbl_prod, 2, 0)
        self.combo_prod = QComboBox()
        self.combo_prod.setEditable(True) 
        self.combo_prod.currentIndexChanged.connect(self._on_med_sel_change)
        grid.addWidget(self.combo_prod, 2, 1)
        
        # Réf ID
        self.lbl_ref = QLabel(self.texts[self.locale]["ref"])
        grid.addWidget(self.lbl_ref, 3, 0)
        self.entry_ref = QLineEdit()
        self.entry_ref.setValidator(QIntValidator())
        grid.addWidget(self.entry_ref, 3, 1)
        
        # Quantité
        self.lbl_qty = QLabel(self.texts[self.locale]["qty"])
        grid.addWidget(self.lbl_qty, 4, 0)
        self.entry_qty = QLineEdit("1")
        self.entry_qty.setValidator(QIntValidator())
        grid.addWidget(self.entry_qty, 4, 1)
        
        # Prix
        self.lbl_price = QLabel(self.texts[self.locale]["price"])
        grid.addWidget(self.lbl_price, 5, 0)
        self.entry_price = QLineEdit("0.00")
        self.entry_price.setValidator(QDoubleValidator(0.0, 999999999.0, 2))
        grid.addWidget(self.entry_price, 5, 1)
        
        # Note
        self.lbl_note = QLabel(self.texts[self.locale]["note"])
        grid.addWidget(self.lbl_note, 6, 0)
        self.entry_note = QLineEdit()
        grid.addWidget(self.entry_note, 6, 1)
        
        layout.addLayout(grid)
        
        # --- Zone Examens (Tableau + Recherche) ---
        self.group_exams = QWidget()
        vbox_exam = QVBoxLayout(self.group_exams)
        vbox_exam.setContentsMargins(0, 10, 0, 0)
        
        # Barre de recherche Examen (Filtre Frontend)
        self.entry_search_exam = QLineEdit()
        self.entry_search_exam.setPlaceholderText(self.texts[self.locale]["search_exam"])
        self.entry_search_exam.textChanged.connect(self._filter_exams_table)
        vbox_exam.addWidget(self.entry_search_exam)
        
        self.table_exams = QTableWidget()
        self.table_exams.setColumnCount(3)
        self.table_exams.setHorizontalHeaderLabels(["", self.texts[self.locale]["col_exam"], self.texts[self.locale]["col_price"]])
        self.table_exams.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_exams.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_exams.verticalHeader().setVisible(False)
        self.table_exams.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        vbox_exam.addWidget(self.table_exams)
        
        layout.addWidget(self.group_exams)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_confirm = QPushButton(self.texts[self.locale]["confirm"])
        btn_confirm.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        btn_confirm.clicked.connect(self._on_confirm)
        
        btn_cancel = QPushButton(self.texts[self.locale]["cancel"])
        btn_cancel.setStyleSheet("background-color: #dc3545; color: white; padding: 8px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_confirm)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)

    def _update_visibility(self):
        itype = self.combo_type.currentText()
        
        # Masquer tout par défaut
        widgets_med = [self.lbl_cat, self.combo_cat, self.lbl_prod, self.combo_prod]
        widgets_std = [self.lbl_ref, self.entry_ref, self.lbl_qty, self.entry_qty, self.lbl_price, self.entry_price, self.lbl_note, self.entry_note]
        
        for w in widgets_med: w.setVisible(False)
        for w in widgets_std: w.setVisible(True)
        self.group_exams.setVisible(False)
        self.entry_ref.setEnabled(True)
        self.entry_price.setEnabled(True)

        # Logique par type
        if itype in ("Médicament", "Medication", "Vente Médicament", "Sale Medication"):
            for w in widgets_med: w.setVisible(True)
            self.entry_ref.setEnabled(False) 
            self.entry_price.setEnabled(False) # Prix auto
            self._on_med_category_change() # Charge les produits
            
        elif itype in ("Carnet", "Booklet", "Vente Carnet", "Sale Booklet"):
            self.lbl_prod.setVisible(True)
            self.combo_prod.setVisible(True)
            self.entry_ref.setEnabled(False)
            self.entry_price.setText("500.00") 
            self._load_carnets()
            
        elif "Consultation" in itype:
            if "Spirituel" in itype:
                self._prefill_last_consultation_spirituel()
            elif "Médical" in itype or "Medical" in itype:
                self._prefill_last_consultation_medical()
            
        elif "Examen" in itype:
            self.group_exams.setVisible(True)
            self.lbl_qty.setVisible(False)
            self.entry_qty.setVisible(False)
            self.lbl_price.setVisible(False)
            self.entry_price.setVisible(False)
            self.entry_ref.setText(str(self.patient_id) if self.patient_id else "0")
            
            # Charger la liste des examens si vide
            if not self.exams_list:
                self._load_exams_from_api()

    def _load_exams_from_api(self):
        """Charge la liste complète des examens"""
        if not self.lab_controller: return

        try:
            if hasattr(self.lab_controller, "list_examens"):
                raw_exams = self.lab_controller.list_examens()
            elif hasattr(self.lab_controller, "request"): # Si c'est le gateway direct
                 raw_exams = self.lab_controller.request("GET", "/labo/")
            else:
                raw_exams = []

            self.exams_list = raw_exams
            self._populate_exams_table()
            
        except Exception as e:
            logger.error(f"Erreur chargement examens: {e}")
            QMessageBox.warning(self, self.texts[self.locale]["error"], f"Impossible de charger les examens: {e}")

    def _populate_exams_table(self):
        """Remplit le tableau avec self.exams_list"""
        self.table_exams.setRowCount(0) # Clear
        self.table_exams.setRowCount(len(self.exams_list))
        
        for row, exam in enumerate(self.exams_list):
            # Checkbox
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0,0,0,0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setProperty("exam_data", exam)
            chk_layout.addWidget(chk)
            self.table_exams.setCellWidget(row, 0, chk_widget)
            
            # Nom
            label = exam.get("label") or exam.get("nom")
            item_name = QTableWidgetItem(str(label))
            self.table_exams.setItem(row, 1, item_name)
            
            # Prix (Edit)
            price_edit = QLineEdit("0.00")
            price_edit.setValidator(QDoubleValidator(0.0, 99999999.0, 2))
            price_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.table_exams.setCellWidget(row, 2, price_edit)

    def _filter_exams_table(self, text):
        """Filtre les lignes du tableau en temps réel"""
        search_term = text.lower()
        for row in range(self.table_exams.rowCount()):
            item = self.table_exams.item(row, 1) # Colonne Nom
            if item:
                visible = search_term in item.text().lower()
                self.table_exams.setRowHidden(row, not visible)

    def _load_carnets(self):
        term = "carnet" if self.locale == "fr" else "book"
        self._search_products(term=term, cat_filter=None)

    def _on_med_category_change(self):
        cat_txt = self.combo_cat.currentText()
        # Mapping UI -> API value
        cat_val = "Naturel" if "Naturel" in cat_txt or "Natural" in cat_txt else "Pharmaceutique"
        self._search_products(term=None, cat_filter=cat_val)

    def _search_products(self, term, cat_filter):
        if not self.pharmacy_ctrl: return
        try:
            # Appel API search sur la pharmacie
            # Note: self.pharmacy_ctrl doit avoir une methode 'search_products'
            # Si c'est le RemoteGateway, la méthode s'appelle list_products
            if hasattr(self.pharmacy_ctrl, "search_products"):
                products = self.pharmacy_ctrl.search_products(term=term, type_filter=cat_filter)
            elif hasattr(self.pharmacy_ctrl, "list_products"):
                 # Utilisation du Gateway ou Controller
                 res = self.pharmacy_ctrl.list_products(term=term, type_filter=cat_filter, per_page=100)
                 products = res.get("data", []) if isinstance(res, dict) else res
            else:
                products = []
        except Exception:
            products = []
            
        self._med_mapping = {}
        display_list = []
        
        for p in products:
            # Gestion Objet vs Dict
            if isinstance(p, dict):
                pid = p.get("medication_id")
                name = p.get("drug_name")
                price = p.get("price", 0.0)
            else:
                pid = getattr(p, "medication_id", None)
                name = getattr(p, "drug_name", "")
                price = getattr(p, "price", 0.0)
            
            label = f"{name} (ID {pid})"
            self._med_mapping[label] = {"id": pid, "price": price}
            display_list.append(label)
            
        self.combo_prod.clear()
        self.combo_prod.addItems(display_list)
        if display_list:
            self.combo_prod.setCurrentIndex(0)
            self._on_med_sel_change()

    def _on_med_sel_change(self):
        sel = self.combo_prod.currentText()
        data = self._med_mapping.get(sel)
        if data:
            self.entry_ref.setText(str(data["id"]))
            self.entry_price.setText(f"{float(data['price']):.2f}")

    def _prefill_last_consultation_spirituel(self):
        if self.consultation_spirituel_ctrl and self.patient_id:
            try:
                cs = self.consultation_spirituel_ctrl.get_last_for_patient(self.patient_id)
                if cs:
                    cid = cs.get("consultation_id") if isinstance(cs, dict) else cs.consultation_id
                    self.entry_ref.setText(str(cid))
            except:
                self.entry_ref.setText("0")

    def _prefill_last_consultation_medical(self):
        if self.medical_record_ctrl and self.patient_id:
            try:
                mr = self.medical_record_ctrl.get_last_for_patient(self.patient_id)
                if mr:
                    cid = mr.get("consultation_id") if isinstance(mr, dict) else mr.consultation_id
                    self.entry_ref.setText(str(cid))
            except:
                self.entry_ref.setText("0")

    def _on_confirm(self):
        itype = self.combo_type.currentText()
        
        # --- Cas Examens (Multi-lignes) ---
        if "Examen" in itype:
            try:
                ref_id = int(self.entry_ref.text().strip())
            except ValueError:
                QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_ref"])
                return

            selected_exams = []
            for r in range(self.table_exams.rowCount()):
                # Si la ligne est cachée par le filtre, on l'ignore ou pas ?
                # En général on prend tout ce qui est coché, même si masqué.
                
                chk_widget = self.table_exams.cellWidget(r, 0)
                chk = chk_widget.findChild(QCheckBox)
                
                if chk and chk.isChecked():
                    exam_data = chk.property("exam_data")
                    price_widget = self.table_exams.cellWidget(r, 2)
                    try:
                        price = float(price_widget.text().replace(",", "."))
                    except ValueError:
                        name = exam_data.get('nom', '') if isinstance(exam_data, dict) else exam_data
                        QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_exam_price"] + str(name))
                        return
                    
                    line = {
                        "item_type": itype,
                        "item_ref_id": exam_data.get("id") if isinstance(exam_data, dict) else 0,
                        "quantity": 1,
                        "unit_price": price,
                        "line_total": price,
                        "note": exam_data.get("nom") if isinstance(exam_data, dict) else str(exam_data)
                    }
                    selected_exams.append(line)
            
            if not selected_exams:
                QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_exam_sel"])
                return

            for line in selected_exams:
                self.on_confirm(line)
            self.accept()
            return

        # --- Cas Standard (1 ligne) ---
        try:
            ref_id = int(self.entry_ref.text().strip())
        except ValueError:
            QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_ref"])
            return

        try:
            qty = int(self.entry_qty.text().strip())
            if qty <= 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_qty"])
            return

        try:
            price = float(self.entry_price.text().replace(",", "."))
            if price < 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_price"])
            return

        line = {
            "item_type": itype,
            "item_ref_id": ref_id,
            "quantity": qty,
            "unit_price": price,
            "line_total": qty * price,
            "note": self.entry_note.text().strip()
        }
        self.on_confirm(line)
        self.accept()