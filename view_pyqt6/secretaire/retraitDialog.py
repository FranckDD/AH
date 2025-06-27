# view/secretaire/retrait_dialog_pyqt6.py
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QVBoxLayout
)
from PyQt6.QtCore import Qt

class RetraitDialog(QDialog):
    def __init__(self, parent=None, on_confirm=None, locale:str="fr"):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.locale = locale
        title = {"fr":"Effectuer un retrait","en":"Perform Withdrawal"}[locale]
        self.setWindowTitle(title)
        self.setFixedSize(400, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.amount_edit = QLineEdit("0.00")
        form.addRow({"fr":"Montant (CFA) :","en":"Amount (CFA):"}[locale], self.amount_edit)
        self.justif_edit = QLineEdit("")
        form.addRow({"fr":"Justification :","en":"Justification:"}[locale], self.justif_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        confirm = QPushButton({"fr":"Valider","en":"Confirm"}[locale])
        confirm.clicked.connect(self._on_confirm)
        cancel = QPushButton({"fr":"Annuler","en":"Cancel"}[locale])
        cancel.setStyleSheet("background:#D32F2F; color:white;")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(confirm)
        btn_layout.addWidget(cancel)
        layout.addLayout(btn_layout)

    def _on_confirm(self):
        raw = self.amount_edit.text().strip().replace(',', '.')
        try:
            amount = float(raw)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.critical(self, "Erreur", {"fr":"Montant invalide.","en":"Invalid amount."}[self.locale])
            return
        justification = self.justif_edit.text().strip()
        if callable(self.on_confirm):
            self.on_confirm(amount, justification)
        self.accept()
