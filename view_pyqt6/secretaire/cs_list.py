
# view/secretaire/cs_list_pyqt6.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox
)
from PyQt6.QtCore import Qt
from view_pyqt6.secretaire.cs_form import CSFormDialog
from view_pyqt6.secretaire.retraitList import RetraitListView
from view_pyqt6.secretaire.retraitDialog import RetraitDialog
from datetime import date, datetime
from view_pyqt6.languagemanager import lang

class CSListView(QWidget):
    def __init__(self, parent=None, controller=None, locale='fr'):
        super().__init__(parent)
        self.controller = controller
        self.locale = locale
        lang.set_language(locale)
        self.filtered = None
        self.page = 0
        self.page_size = 100
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        l = QVBoxLayout(self)
        # header
        hl = QHBoxLayout(); hl.addWidget(QLabel('Liste des Consultations Spirituelles'))
        lang_cb = QPushButton(lang.t('language'))  # skip full switch here
        hl.addStretch(); hl.addWidget(lang_cb)
        l.addLayout(hl)
        # search
        sh = QHBoxLayout();
        self.search_le = QLineEdit(); self.search_le.setPlaceholderText(lang.t('search_ph'))
        self.search_le.returnPressed.connect(self._apply_filters)
        sh.addWidget(self.search_le)
        btn = QPushButton('🔍'); btn.clicked.connect(self._apply_filters)
        sh.addWidget(btn)
        l.addLayout(sh)
        # table
        self.table = QTableWidget(0,9)
        headers = ['Patient','Type','Presc.Gen','Presc.Méd.SP','MP Type',
                   'Inscrit','Rdv','Montant','Obs']
        self.table.setHorizontalHeaderLabels(headers)
        l.addWidget(self.table)
        # export/edit
        ah = QHBoxLayout()
        btn_e = QPushButton(lang.t('edit')); btn_e.clicked.connect(self._edit)
        btn_p = QPushButton('Exporter PDF'); btn_p.clicked.connect(self._export)
        ah.addWidget(btn_e); ah.addWidget(btn_p); ah.addStretch()
        l.addLayout(ah)

    def load_data(self):
        self.filtered=None; self.page=0; self._populate()

    def _apply_filters(self):
        term = self.search_le.text().lower()
        all_cs = self.controller.list_consultations()
        if term:
            def m(c):
                if not c.patient: return False
                return term in (c.patient.code_patient or '').lower() \
                       or term in (c.patient.last_name or '').lower()
            self.filtered = [c for c in all_cs if m(c)]
        else:
            self.filtered=None
        self.page=0; self._populate()

    def _populate(self):
        data = self.filtered if self.filtered is not None else self.controller.list_consultations()
        page_data = data[self.page*self.page_size:(self.page+1)*self.page_size]
        self.table.setRowCount(len(page_data))
        for i, cs in enumerate(page_data):
            pat = cs.patient; txt = f"{pat.code_patient} – {pat.last_name} {pat.first_name}" if pat else ''
            vals = [
                txt,
                cs.type_consultation,
                ','.join(cs.presc_generic or []),
                ','.join(cs.presc_med_spirituel or []),
                cs.mp_type or '',
                cs.fr_registered_at.strftime('%Y-%m-%d') if cs.fr_registered_at else '',
                cs.fr_appointment_at.strftime('%Y-%m-%d') if cs.fr_appointment_at else '',
                f"{cs.fr_amount_paid:.2f}" if cs.fr_amount_paid is not None else '',
                (cs.fr_observation or '')[:30]
            ]
            for j,v in enumerate(vals):
                self.table.setItem(i,j,QTableWidgetItem(v))

    def _edit(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(self, lang.t('warning'), 'Sélectionnez une ligne')
            return
        idx = sel[0].row()
        data = self.filtered or self.controller.list_consultations()
        cs = data[self.page*self.page_size + idx]
        dlg = CSFormDialog(self, self.controller, self.controller.patient_ctrl,
                           consultation=cs, on_save=self.load_data,
                           locale=self.locale)
        dlg.exec()

    def _export(self):
        # implement export logic or call utility
        pass