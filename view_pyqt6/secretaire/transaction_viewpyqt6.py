# view/secretaire/add_item_dialog_pyqt6.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt

class AddItemDialog(QDialog):
    def __init__(self, master, on_confirm, pharmacy_ctrl,
                 patient_ctrl, consultation_spirituel_ctrl,
                 medical_record_ctrl, allowed_types, patient_id=None,
                 locale='fr'):
        super().__init__(master)
        self.on_confirm = on_confirm
        self.pharmacy_ctrl = pharmacy_ctrl
        self.patient_ctrl = patient_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl
        self.allowed_types = allowed_types
        self.patient_id = patient_id
        self.locale = locale

        self.setWindowTitle("Add/Edit Line")
        self.resize(350, 300)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_cb = QComboBox(); self.type_cb.addItems(allowed_types)
        form.addRow("Line type:", self.type_cb)
        self.cat_cb = QComboBox(); self.cat_cb.addItems(["Naturel","Pharmaceutique"])
        form.addRow("Med Category:", self.cat_cb)
        self.prod_cb = QComboBox()
        form.addRow("Product:", self.prod_cb)
        self.ref_edit = QLineEdit()
        form.addRow("Ref. ID:", self.ref_edit)
        self.qty_edit = QLineEdit("1")
        form.addRow("Quantity:", self.qty_edit)
        self.unit_edit = QLineEdit("0.00")
        form.addRow("Unit price:", self.unit_edit)
        self.note_edit = QLineEdit()
        form.addRow("Note:", self.note_edit)

        layout.addLayout(form)
        btn = QPushButton("Confirm")
        btn.clicked.connect(self._confirm)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.type_cb.currentTextChanged.connect(self._update)
        self.cat_cb.currentTextChanged.connect(self._load_products)
        self.prod_cb.currentTextChanged.connect(self._prefill)
        self._update()

    def _update(self):
        t = self.type_cb.currentText()
        is_med = t in ("Médicament","Medication")
        is_book = t in ("Carnet","Booklet")
        if is_med:
            self.cat_cb.setEnabled(True)
            self.prod_cb.setEnabled(True)
            self.ref_edit.setEnabled(False)
            self.unit_edit.setEnabled(True)
        elif is_book:
            self.cat_cb.setEnabled(False)
            self.prod_cb.setEnabled(True)
            self.ref_edit.setEnabled(False)
            self.unit_edit.setEnabled(False)
            self._load_carnets()
        else:
            # consultations
            self.cat_cb.setEnabled(False)
            self.prod_cb.setEnabled(False)
            self.ref_edit.setEnabled(True)
            self.unit_edit.setEnabled(True)
            if "Spirituel" in t: self._prefill_last_spirituel()
            else: self._prefill_last_medical()

    def _load_products(self):
        cat = self.cat_cb.currentText()
        # example call
        meds = self.pharmacy_ctrl.search_products(None, cat, None)
        self.prod_cb.clear()
        for m in meds:
            label = f"{m.drug_name} (ID {m.medication_id})"
            self.prod_cb.addItem(label, m)

    def _load_carnets(self):
        carnets = self.pharmacy_ctrl.search_products("carnet", None, None)
        self.prod_cb.clear()
        for m in carnets:
            if "carnet" in m.drug_name.lower():
                label = f"{m.drug_name} (ID {m.medication_id})"
                self.prod_cb.addItem(label, m)

    def _prefill(self):
        m = self.prod_cb.currentData()
        if m:
            self.ref_edit.setText(str(m.medication_id))
            if "carnet" in m.drug_name.lower():
                self.unit_edit.setText("500.00")

    def _prefill_last_spirituel(self):
        if not self.patient_id: self.ref_edit.setText("0"); return
        try:
            cs = self.consultation_spirituel_ctrl.get_last_for_patient(self.patient_id)
            self.ref_edit.setText(str(cs.consultation_id) if cs else "0")
        except: self.ref_edit.setText("0")

    def _prefill_last_medical(self):
        if not self.patient_id: self.ref_edit.setText("0"); return
        try:
            mr = self.medical_record_ctrl.get_last_for_patient(self.patient_id)
            self.ref_edit.setText(str(mr.consultation_id) if mr else "0")
        except: self.ref_edit.setText("0")

    def _confirm(self):
        try:
            ref = int(self.ref_edit.text())
            qty = int(self.qty_edit.text())
            unit = float(self.unit_edit.text())
        except ValueError as ve:
            QMessageBox.critical(self, "Error", str(ve))
            return
        total = round(qty * unit, 2)
        item = {
            'item_type': self.type_cb.currentText(),
            'item_ref_id': ref,
            'quantity': qty,
            'unit_price': unit,
            'line_total': total,
            'note': self.note_edit.text().strip()
        }
        self.on_confirm(item)
        self.accept()
