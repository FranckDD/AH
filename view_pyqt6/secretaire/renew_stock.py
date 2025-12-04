from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt

class RenewStockDialog(QDialog):
    def __init__(self, parent, product_name, on_confirm):
        """
        Dialog pour réapprovisionner un produit.
        - on_confirm: callback(added_qty: int)
        """
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.setWindowTitle("Réapprovisionnement")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Titre
        lbl_title = QLabel(f"Réapprovisionner : {product_name}")
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        # Input
        self.ent_qty = QLineEdit()
        self.ent_qty.setPlaceholderText("Quantité à ajouter (entier)")
        layout.addWidget(self.ent_qty)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        btn_ok = QPushButton("Valider")
        btn_ok.setStyleSheet("background-color: #28a745; color: white;")
        btn_ok.clicked.connect(self._on_confirm)
        
        btn_cancel = QPushButton("Annuler")
        btn_cancel.setStyleSheet("background-color: #dc3545; color: white;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
    def _on_confirm(self):
        try:
            qty_str = self.ent_qty.text().strip()
            if not qty_str: raise ValueError
            added = int(qty_str)
            if added <= 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un entier strictement positif.")
            return
            
        if self.on_confirm:
            self.on_confirm(added)
        self.accept()