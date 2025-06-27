# view/secretaire/renew_stock_dialog_pyqt6.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QWidget, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt

class RenewStockDialog(QDialog):
    def __init__(self, parent=None, product_name:str="", on_confirm=None):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.setWindowTitle("Réapprovisionnement")
        self.setFixedSize(400, 200)
        
        # Main container
        container = QWidget(self)
        container.setStyleSheet("border-radius:10px;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20,20,20,20)

        # Title
        title = QLabel(f"Réapprovisionner : {product_name}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:16pt; font-weight:bold;")
        layout.addWidget(title)

        # Input
        self.add_edit = QLineEdit("0")
        self.add_edit.setPlaceholderText("Entrez un entier")
        self.add_edit.setFixedHeight(30)
        layout.addWidget(QLabel("Quantité à ajouter :"))
        layout.addWidget(self.add_edit)

        # Buttons
        btn_frame = QHBoxLayout()
        btn_frame.setSpacing(10)
        confirm_btn = QPushButton("Valider")
        confirm_btn.clicked.connect(self._on_confirm)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet("background:#D32F2F; color:white;")
        cancel_btn.clicked.connect(self.reject)
        btn_frame.addWidget(confirm_btn)
        btn_frame.addWidget(cancel_btn)
        layout.addLayout(btn_frame)

        self.setLayout(layout)
        self.add_edit.returnPressed.connect(self._on_confirm)

    def _on_confirm(self):
        text = self.add_edit.text().strip()
        try:
            added = int(text)
            if added <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.critical(self, "Erreur", "La quantité doit être un entier strictement positif.")
            return
        if callable(self.on_confirm):
            self.on_confirm(added)
        self.accept()