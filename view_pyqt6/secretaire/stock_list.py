# view/secretaire/stock_list_pyqt6.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from view_pyqt6.secretaire.stock_form import StockFormDialog

class StockListView(QWidget):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.filtered = None
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Liste des Produits / Product List")
        title.setStyleSheet("font-size:20px; font-weight:bold;")
        layout.addWidget(title)
        # Filters
        fl = QHBoxLayout()
        self.search_le = QLineEdit()
        self.search_le.setPlaceholderText("Nom, type ou forme… / Name, type or form…")
        fl.addWidget(self.search_le)
        btn = QPushButton("🔍")
        btn.clicked.connect(self.apply_filters)
        fl.addWidget(btn)
        self.type_cb = QComboBox()
        self.type_cb.addItems(["Tous / All","Naturel / Natural","Pharmaceutique / Pharmaceutical"])
        fl.addWidget(self.type_cb)
        self.status_cb = QComboBox()
        self.status_cb.addItems(["Tous / All","normal","critique","épuisé"])
        fl.addWidget(self.status_cb)
        layout.addLayout(fl)
        # Table
        self.table = QTableWidget(0,8)
        headers = ["Nom","Type","Forme","Quantité","Seuil","Statut","Dosage","Expiration"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        # Actions
        ah = QHBoxLayout()
        new_btn = QPushButton("Nouveau / New")
        new_btn.clicked.connect(self._on_create)
        edit_btn = QPushButton("Éditer / Edit")
        edit_btn.clicked.connect(self._on_edit)
        refresh_btn = QPushButton("Rafraîchir / Refresh")
        refresh_btn.clicked.connect(self.load_data)
        ah.addWidget(new_btn); ah.addWidget(edit_btn); ah.addWidget(refresh_btn)
        layout.addLayout(ah)

    def load_data(self):
        self.filtered = None
        self._populate()

    def apply_filters(self):
        all_p = self.controller.list_products()
        term = self.search_le.text().lower()
        t = self.type_cb.currentText().split(" /")[0]
        s = self.status_cb.currentText().split(" /")[0]
        f = [p for p in all_p if (not term or term in p.drug_name.lower() or term in p.medication_type.lower() or term in p.forme.lower())]
        if t!="Tous": f = [p for p in f if p.medication_type==t]
        if s!="Tous": f = [p for p in f if p.stock_status==s]
        self.filtered = f
        self._populate()

    def _populate(self):
        data = self.filtered if self.filtered is not None else self.controller.list_products()
        self.table.setRowCount(len(data))
        for i,p in enumerate(data):
            vals = [
                p.drug_name, p.medication_type, p.forme or "",
                str(p.quantity), str(p.threshold), p.stock_status,
                str(p.dosage_mg or ""),
                p.expiry_date.strftime("%Y-%m-%d") if p.expiry_date else ""
            ]
            for j,v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))

    def _on_create(self):
        dlg = StockFormDialog(self, self.controller, on_save=self.load_data)
        dlg.exec()

    def _on_edit(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.critical(self, "Erreur / Error", "Aucun produit sélectionné / No product selected.")
            return
        idx = sel[0].row()
        data = self.filtered if self.filtered is not None else self.controller.list_products()
        prod = data[idx]
        dlg = StockFormDialog(self, self.controller, on_save=self.load_data, product=prod)
        dlg.exec()
