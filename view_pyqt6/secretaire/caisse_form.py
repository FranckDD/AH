# view/secretaire/caisse_form_pyqt6.py
import traceback
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QComboBox, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QDateTimeEdit, QSizePolicy
)
from PyQt6.QtCore import Qt
from view_pyqt6.secretaire.transaction_viewpyqt6 import AddItemDialog
from view_pyqt6.languagemanager import lang

class CaisseFormDialog(QDialog):
    def __init__(self, parent=None, controller=None,
                 patient_ctrl=None, pharmacy_ctrl=None,
                 consultation_spirituel_ctrl=None,
                 medical_record_ctrl=None,
                 on_save=None, transaction=None,
                 locale='fr'):
        super().__init__(parent)
        self.controller = controller
        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl
        self.on_save = on_save
        self.transaction = transaction
        self.locale = locale
        self.patient_id = None
        self.items = []

        lang.set_language(locale)
        self._init_ui()
        if self.transaction:
            self._load_transaction()

    def _init_ui(self):
        self.setWindowTitle(
            lang.t('transaction_list') +
            (lang.t('edit') if self.transaction else lang.t('new'))
        )
        self.resize(700, 600)
        layout = QVBoxLayout(self)

        # Top form
        form = QFormLayout()
        # Langue selector
        hl = QHBoxLayout()
        hl.addWidget(QLabel(lang.t('language')))
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(['fr','en'])
        self.lang_cb.setCurrentText(self.locale)
        self.lang_cb.currentTextChanged.connect(self._on_lang_change)
        hl.addWidget(self.lang_cb)
        form.addRow('', hl)

        self.code_edit = QLineEdit()
        load_btn = QPushButton(lang.t('load'))
        load_btn.clicked.connect(self._load_patient)
        h1 = QHBoxLayout()
        h1.addWidget(self.code_edit); h1.addWidget(load_btn)
        form.addRow(lang.t('patient_code'), h1)

        self.info_label = QLabel('')
        form.addRow('', self.info_label)

        self.dt_edit = QDateTimeEdit(datetime.utcnow())
        self.dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_edit.setCalendarPopup(True)
        self.dt_edit.setReadOnly(True)
        form.addRow(lang.t('date_time'), self.dt_edit)

        self.advance_edit = QLineEdit("0.00")
        form.addRow(lang.t('advance_amount'), self.advance_edit)

        box = QHBoxLayout()
        self.chk_consult = QCheckBox(lang.t('consultation'))
        self.chk_med     = QCheckBox(lang.t('sale_medication'))
        self.chk_book    = QCheckBox(lang.t('sale_booklet'))
        for w in (self.chk_consult, self.chk_med, self.chk_book):
            box.addWidget(w)
        form.addRow(lang.t('trans_types'), box)

        self.payment_cb = QComboBox()
        self.payment_cb.addItems([lang.t('payment_method')])
        form.addRow(lang.t('payment_method'), self.payment_cb)

        layout.addLayout(form)

        # Note
        layout.addWidget(QLabel(lang.t('note')))
        self.note_edit = QTextEdit()
        self.note_edit.setFixedHeight(60)
        layout.addWidget(self.note_edit)

        # Items tree
        layout.addWidget(QLabel(lang.t('lines')))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ['Type','Ref ID','Qty','Unit Price','Total','Note']
        )
        self.tree.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tree)

        # Add/Remove buttons
        hl2 = QHBoxLayout()
        add_btn = QPushButton(lang.t('add_line'))
        add_btn.clicked.connect(self._add_line)
        rem_btn = QPushButton(lang.t('remove_line'))
        rem_btn.clicked.connect(self._remove_line)
        hl2.addWidget(add_btn); hl2.addWidget(rem_btn); hl2.addStretch()
        layout.addLayout(hl2)

        # Total
        hl3 = QHBoxLayout()
        hl3.addWidget(QLabel(lang.t('total_amount')))
        self.total_lbl = QLabel("0.00")
        hl3.addWidget(self.total_lbl)
        hl3.addStretch()
        layout.addLayout(hl3)

        # Save/Cancel
        hl4 = QHBoxLayout()
        save_btn = QPushButton(lang.t('save'))
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton(lang.t('cancel'))
        cancel_btn.clicked.connect(self.reject)
        hl4.addWidget(save_btn); hl4.addWidget(cancel_btn)
        layout.addLayout(hl4)

    def _on_lang_change(self, new_lang):
        self.locale = new_lang
        lang.set_language(new_lang)
        # Rebuild UI
        for w in self.children():
            w.deleteLater()
        self._init_ui()

    def _load_patient(self):
        code = self.code_edit.text().strip()
        try:
            patient = (self.patient_ctrl.find_by_code(code)
                       if hasattr(self.patient_ctrl,'find_by_code')
                       else self.patient_ctrl.find_patient_by_code(code))
        except:
            patient = None
        if not patient:
            QMessageBox.critical(self, lang.t('warning'),
                                 lang.t('patient_not_found'))
            return
        pid = (patient['patient_id'] if isinstance(patient,dict)
               else patient.patient_id)
        self.patient_id = pid
        # name + last consult...
        name = patient.get('first_name','')+' '+patient.get('last_name','') \
               if isinstance(patient,dict) \
               else f"{patient.first_name} {patient.last_name}"
        last_id, last_date = "0", None
        for ctrl in (self.consultation_spirituel_ctrl,
                     self.medical_record_ctrl):
            if ctrl:
                try:
                    last = ctrl.get_last_for_patient(pid)
                    if last and (not last_date or last.date>last_date):
                        last_id, last_date = last.consultation_id, last.date
                except: pass
        self.info_label.setText(
            f"{lang.t('patient_code')} {name}    |    {last_id}"
        )

    def _add_line(self):
        allowed = []
        if self.chk_consult.isChecked():
            allowed += ['Consultation Spirituel','Consultation Médical']
        if self.chk_med.isChecked(): allowed.append('Médicament')
        if self.chk_book.isChecked(): allowed.append('Carnet')
        if not allowed:
            QMessageBox.warning(self, lang.t('warning'),
                                lang.t('add_line'))
            return
        dlg = AddItemDialog(self, self.pharmacy_ctrl,
                            self.patient_ctrl,
                            self.consultation_spirituel_ctrl,
                            self.medical_record_ctrl,
                            allowed, self.patient_id,
                            self.locale)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            item = dlg.get_item()
            self.items.append(item)
            self._refresh_items()

    def _remove_line(self):
        it = self.tree.currentItem()
        if not it: return
        idx = self.tree.indexOfTopLevelItem(it)
        del self.items[idx]
        self._refresh_items()

    def _refresh_items(self):
        self.tree.clear()
        total = 0
        for it in self.items:
            row = QTreeWidgetItem([
                it['item_type'], str(it['item_ref_id']),
                str(it['quantity']),
                f"{it['unit_price']:.2f}",
                f"{it['line_total']:.2f}",
                it.get('note','')
            ])
            self.tree.addTopLevelItem(row)
            total += it['line_total']
        self.total_lbl.setText(f"{total:.2f}")

    def _on_save(self):
        data = {}
        types = []
        if self.chk_consult.isChecked(): types.append('Consultation')
        if self.chk_med.isChecked():    types.append('Vente Médicament')
        if self.chk_book.isChecked():   types.append('Vente Carnet')
        if not types:
            QMessageBox.critical(self, lang.t('warning'),
                                 lang.t('trans_types'))
            return
        data['transaction_type'] = ", ".join(types)
        try:
            adv = float(self.advance_edit.text())
        except ValueError:
            QMessageBox.critical(self, lang.t('warning'),
                                 lang.t('advance_amount'))
            return
        if adv>0 and not self.patient_id:
            QMessageBox.critical(self, lang.t('warning'),
                                 lang.t('patient_not_found'))
            return
        data.update({
            'advance_amount': adv,
            'patient_id': self.patient_id,
            'payment_method': self.payment_cb.currentText(),
            'note': self.note_edit.toPlainText() or None,
            'paid_at': self.dt_edit.dateTime().toPyDateTime(),
            'amount': float(self.total_lbl.text()),
            'items': self.items.copy()
        })
        try:
            if self.transaction:
                self.controller.update_transaction(
                    self.transaction.transaction_id, data)
            else:
                self.controller.create_transaction(data)
            QMessageBox.information(self, lang.t('save'),
                                    lang.t('save'))
            if self.on_save: self.on_save()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, lang.t('warning'), str(e))
