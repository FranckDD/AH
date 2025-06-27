# view/secretaire/stock_form_pyqt6.py
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDateEdit

class StockFormDialog(QDialog):
    def __init__(self, parent=None, controller=None, on_save=None, product=None):
        super().__init__(parent)
        self.controller = controller
        self.on_save = on_save
        self.product = product
        self.setWindowTitle(
            f"Enregistrer Produit / Register Product"
            f"{ ' [Éditer / Edit]' if product else ' [Nouveau / New]' }"
        )
        self.resize(400, 300)

        # layout
        main_layout = QVBoxLayout(self)
        form = QFormLayout()

        # Product Name
        self.name_edit = QLineEdit(product.drug_name if product else "")
        form.addRow("Nom du produit / Product Name:", self.name_edit)

        # Quantity
        self.qty_edit = QLineEdit(str(product.quantity) if product else "0")
        form.addRow("Quantité / Quantity:", self.qty_edit)

        # Threshold
        self.threshold_edit = QLineEdit(str(product.threshold) if product else "0")
        form.addRow("Seuil critique / Threshold:", self.threshold_edit)

        # Type
        self.type_cb = QComboBox()
        self.type_cb.addItems([
            "Naturel / Natural",
            "Pharmaceutique / Pharmaceutical"
        ])
        if product:
            # match French part
            french = product.medication_type
            idx = 0 if french == "Naturel" else 1
            self.type_cb.setCurrentIndex(idx)
        form.addRow("Type du produit / Product Type:", self.type_cb)

        main_layout.addLayout(form)

        # Dynamic fields container
        self.dynamic = QWidget()
        self.dynamic.setLayout(QFormLayout())
        main_layout.addWidget(self.dynamic)
        self.type_cb.currentIndexChanged.connect(self._render_dynamic)
        self._render_dynamic()

        # Save button
        btn = QPushButton("Enregistrer / Save")
        btn.clicked.connect(self._save)
        main_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _render_dynamic(self):
        layout = self.dynamic.layout()
        # clear
        while layout.rowCount() > 0:
            layout.removeRow(0)

        french = self.type_cb.currentText().split(" /")[0]
        if french == "Pharmaceutique":
            # Form
            self.forme_edit = QLineEdit(self.product.forme if self.product else "")
            layout.addRow("Forme / Form:", self.forme_edit)
            # Dosage
            val = str(self.product.dosage_mg) if self.product and self.product.dosage_mg else "0.0"
            self.dosage_edit = QLineEdit(val)
            layout.addRow("Dosage (mg):", self.dosage_edit)
            # Expiry date
            self.expiry_edit = QDateEdit()
            self.expiry_edit.setCalendarPopup(True)
            date = self.product.expiry_date if self.product and self.product.expiry_date else datetime.utcnow()
            self.expiry_edit.setDate(date)
            self.expiry_edit.setDisplayFormat("yyyy-MM-dd")
            layout.addRow("Date d'expiration / Expiry Date:", self.expiry_edit)
        else:
            lbl = QLabel("(Pas de forme à saisir pour un produit Naturel / No form needed for Natural)")
            layout.addRow(lbl)

    def _save(self):
        # validation
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.critical(self, "Erreur / Error", "Le nom du produit est requis / Product name is required.")
            return
        try:
            qty = int(self.qty_edit.text().strip())
            thresh = int(self.threshold_edit.text().strip())
        except ValueError:
            QMessageBox.critical(self, "Erreur / Error", "Quantité et seuil doivent être des entiers / Quantity and threshold must be integers.")
            return
        med_type = self.type_cb.currentText().split(" /")[0]
        data = {
            'drug_name': name,
            'quantity': qty,
            'threshold': thresh,
            'medication_type': med_type,
        }
        if med_type == "Pharmaceutique":
            forme = self.forme_edit.text().strip()
            if not forme:
                QMessageBox.critical(self, "Erreur / Error", "La forme est requise / Form is required.")
                return
            try:
                dosage = float(self.dosage_edit.text().strip())
            except ValueError:
                QMessageBox.critical(self, "Erreur / Error", "Le dosage doit être un nombre / Dosage must be a number.")
                return
            expiry = self.expiry_edit.date().toPython()
            data.update({'forme': forme, 'dosage_mg': dosage, 'expiry_date': expiry})
        else:
            data.update({'forme': 'Autre', 'dosage_mg': None, 'expiry_date': None})
        try:
            if self.product:
                self.controller.update_product(self.product.medication_id, data)
            else:
                self.controller.create_product(data)
            if self.on_save:
                self.on_save()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur SQL / SQL Error", str(e))

