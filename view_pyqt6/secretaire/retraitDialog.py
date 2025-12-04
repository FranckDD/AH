from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt

class RetraitDialog(QDialog):
    def __init__(self, parent, on_confirm, locale: str = "fr"):
        """
        - parent     : fenêtre parente
        - on_confirm : callback(amount: float, justification: str)
        - locale     : "fr" ou "en"
        """
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.locale = locale
        
        self.texts = {
            "fr": {
                "title": "Effectuer un retrait",
                "amount": "Montant (CFA) :",
                "justif": "Justification :",
                "confirm": "Valider",
                "cancel": "Annuler",
                "err_title": "Erreur",
                "err_amount": "Montant invalide.",
                "err_neg": "Le montant doit être strictement positif."
            },
            "en": {
                "title": "Perform Withdrawal",
                "amount": "Amount (CFA):",
                "justif": "Justification:",
                "confirm": "Confirm",
                "cancel": "Cancel",
                "err_title": "Error",
                "err_amount": "Invalid amount.",
                "err_neg": "Amount must be strictly positive."
            }
        }
        
        self.setWindowTitle(self.texts[self.locale]["title"])
        self.setModal(True)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Montant
        lbl_amt = QLabel(self.texts[self.locale]["amount"])
        self.ent_amount = QLineEdit()
        self.ent_amount.setPlaceholderText("0.00")
        
        # 2. Justification
        lbl_justif = QLabel(self.texts[self.locale]["justif"])
        self.ent_justif = QLineEdit()
        
        layout.addWidget(lbl_amt)
        layout.addWidget(self.ent_amount)
        layout.addWidget(lbl_justif)
        layout.addWidget(self.ent_justif)
        
        # 3. Boutons
        btn_layout = QHBoxLayout()
        btn_confirm = QPushButton(self.texts[self.locale]["confirm"])
        btn_confirm.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 6px;")
        btn_confirm.clicked.connect(self._on_confirm)
        
        btn_cancel = QPushButton(self.texts[self.locale]["cancel"])
        btn_cancel.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 6px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_confirm)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
        
    def _on_confirm(self):
        try:
            amt_str = self.ent_amount.text().strip().replace(",", ".")
            if not amt_str:
                raise ValueError
            amount = float(amt_str)
        except ValueError:
            QMessageBox.warning(self, self.texts[self.locale]["err_title"], self.texts[self.locale]["err_amount"])
            return

        if amount <= 0:
            QMessageBox.warning(self, self.texts[self.locale]["err_title"], self.texts[self.locale]["err_neg"])
            return
            
        justification = self.ent_justif.text().strip()
        
        # Appel callback
        if self.on_confirm:
            self.on_confirm(amount, justification)
            
        self.accept()