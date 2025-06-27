# view/secretaire/cs_form_pyqt6.py
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QCheckBox, QWidget, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
import traceback
from view_pyqt6.languagemanager import lang

class CSFormDialog(QDialog):
    def __init__(self, parent=None, controller=None, patient_ctrl=None,
                 consultation=None, on_save=None, locale='fr'):
        super().__init__(parent)
        self.controller = controller
        self.patient_ctrl = patient_ctrl
        self.consultation = consultation
        self.on_save = on_save
        self.locale = locale
        self.patient_id = None

        lang.set_language(locale)
        self._init_ui()
        if consultation:
            self._load_consultation()

    def _init_ui(self):
        self.setWindowTitle(
            lang.t('transaction_list').replace('Transaction','Consultation Spirituelle') +
            (lang.t('edit') if self.consultation else lang.t('new'))
        )
        layout = QVBoxLayout(self)

        # top form
        form = QFormLayout()
        # patient code
        self.code_edit = QLineEdit()
        load_btn = QPushButton(lang.t('load'))
        load_btn.clicked.connect(self._load_patient)
        h1 = QHBoxLayout()
        h1.addWidget(self.code_edit); h1.addWidget(load_btn)
        form.addRow(lang.t('patient_code'), h1)

        # type
        self.type_cb = QComboBox()
        self.type_cb.addItems(['Spiritual','FamilyRestoration'])
        self.type_cb.currentTextChanged.connect(self._render_fields)
        form.addRow('Type:', self.type_cb)

        layout.addLayout(form)

        # dynamic fields container
        self.dynamic = QWidget()
        self.dynamic.setLayout(QVBoxLayout())
        layout.addWidget(self.dynamic)

        # notes
        layout.addWidget(QLabel(lang.t('note')))
        self.notes_edit = QTextEdit()
        layout.addWidget(self.notes_edit)

        # save
        save_btn = QPushButton(lang.t('save'))
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._render_fields()

    def _load_patient(self):
        code = self.code_edit.text().strip()
        try:
            p = self.patient_ctrl.find_by_code(code)
        except:
            p = None
        if not p:
            QMessageBox.critical(self, lang.t('warning'), lang.t('patient_not_found'))
            return
        self.patient_id = p['patient_id'] if isinstance(p, dict) else p.patient_id

    def _render_fields(self):
        # clear
        lay = self.dynamic.layout()
        while lay.count(): lay.takeAt(0)
        t = self.type_cb.currentText()
        if t == 'Spiritual':
            self._render_spiritual()
        else:
            self._render_family()

    def _render_spiritual(self):
        layout = self.dynamic.layout()
        # generic prescription
        h = QHBoxLayout(); h.addWidget(QLabel('Prescription générale:'))
        self.chk_gen = {k: QCheckBox(k) for k in ['Hony','Massage','Prayer']}
        for cb in self.chk_gen.values(): h.addWidget(cb)
        layout.addLayout(h)
        # spirit meds
        h2 = QHBoxLayout(); h2.addWidget(QLabel('Méd. spirituel:'))
        self.chk_med = {k: QCheckBox(k) for k in ['SE','TIS','AE']}
        for cb in self.chk_med.values(): h2.addWidget(cb)
        layout.addLayout(h2)
        # prayer book
        h3 = QHBoxLayout(); h3.addWidget(QLabel('Prayer Book:'))
        self.pb_cb = QComboBox(); self.pb_cb.addItem('')
        # assume controller provides types
        for code in self.controller.get_prayer_book_types(): self.pb_cb.addItem(code)
        h3.addWidget(self.pb_cb)
        layout.addLayout(h3)
        # psaume
        h4 = QHBoxLayout(); h4.addWidget(QLabel('Psaume:'))
        self.ps_edit = QLineEdit()
        h4.addWidget(self.ps_edit)
        layout.addLayout(h4)

    def _render_family(self):
        layout = self.dynamic.layout()
        # registration date
        self.reg_edit = QLineEdit()
        layout.addWidget(QLabel('Date enreg. (YYYY-MM-DD):'))
        layout.addWidget(self.reg_edit)
        # appointment date
        self.app_edit = QLineEdit()
        layout.addWidget(QLabel('Date RDV (YYYY-MM-DD):'))
        layout.addWidget(self.app_edit)
        # amount paid
        self.amt_edit = QLineEdit()
        layout.addWidget(QLabel('Montant payé:'))
        layout.addWidget(self.amt_edit)
        # observation
        self.obs_edit = QLineEdit()
        layout.addWidget(QLabel('Observation:'))
        layout.addWidget(self.obs_edit)

    def _load_consultation(self):
        cs = self.consultation
        # patient
        if cs.patient:
            self.code_edit.setText(cs.patient.code_patient)
            self.patient_id = cs.patient.patient_id
        # type
        self.type_cb.setCurrentText(cs.type_consultation)
        self._render_fields()
        # notes
        if cs.notes: self.notes_edit.setPlainText(cs.notes)
        # spiritual fields
        if cs.type_consultation=='Spiritual':
            for k,v in self.chk_gen.items(): v.setChecked(k in cs.presc_generic or [])
            for k,v in self.chk_med.items(): v.setChecked(k in cs.presc_med_spirituel or [])
            if cs.mp_type: self.pb_cb.setCurrentText(cs.mp_type)
            if cs.psaume: self.ps_edit.setText(cs.psaume)
        else:
            if cs.fr_registered_at: self.reg_edit.setText(cs.fr_registered_at.strftime('%Y-%m-%d'))
            if cs.fr_appointment_at: self.app_edit.setText(cs.fr_appointment_at.strftime('%Y-%m-%d'))
            if cs.fr_amount_paid is not None: self.amt_edit.setText(str(cs.fr_amount_paid))
            if cs.fr_observation: self.obs_edit.setText(cs.fr_observation)

    def _save(self):
        if not self.patient_id:
            QMessageBox.critical(self, lang.t('warning'), lang.t('patient_not_found'))
            return
        data = {'patient_id': self.patient_id,
                'type_consultation': self.type_cb.currentText(),
                'notes': self.notes_edit.toPlainText() or None}
        if self.type_cb.currentText()=='Spiritual':
            data['presc_generic'] = [k for k,v in self.chk_gen.items() if v.isChecked()] or None
            data['presc_med_spirituel'] = [k for k,v in self.chk_med.items() if v.isChecked()] or None
            data['mp_type'] = self.pb_cb.currentText() or None
            data['psaume'] = self.ps_edit.text() or None
        else:
            try:
                data['fr_registered_at']=datetime.strptime(self.reg_edit.text(), '%Y-%m-%d')
                data['fr_appointment_at']=datetime.strptime(self.app_edit.text(), '%Y-%m-%d')
            except Exception as e:
                QMessageBox.critical(self, lang.t('warning'), f'Date format error: {e}')
                return
            data['fr_amount_paid']=float(self.amt_edit.text()) if self.amt_edit.text() else None
            data['fr_observation']=self.obs_edit.text() or None
        try:
            if self.consultation:
                self.controller.update_consultation(self.consultation.consultation_id, data)
            else:
                self.controller.create_consultation(data)
            if self.on_save: self.on_save()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, lang.t('warning'), str(e))