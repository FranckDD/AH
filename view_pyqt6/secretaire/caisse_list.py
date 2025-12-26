# view/secretaire/caisse_list_pyqt6.py
from datetime import date, datetime
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from view_pyqt6.secretaire.caisse_form import CaisseFormDialog
from view_pyqt6.secretaire.retraitList import RetraitListView
from view_pyqt6.secretaire.retraitDialog import RetraitDialog
from view_pyqt6.languagemanager import lang

class CaisseListView(QWidget):
    def __init__(self, parent, controller,
                 caisse_retrait_controller,
                 patient_ctrl, pharmacy_ctrl,
                 locale='fr'):
        super().__init__(parent)
        self.controller = controller
        self.retrait_ctrl = caisse_retrait_controller
        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.locale = locale
        self.filtered = None

        self.var_total_tx = "0.00"
        self.var_total_rt = "0.00"
        self.var_net      = "0.00"

        lang.set_language(locale)
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        # Header
        hl = QHBoxLayout()
        lbl = QLabel(lang.t('transaction_list'))
        lbl.setStyleSheet("font-size:20px; font-weight:bold;")
        hl.addWidget(lbl)
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(['fr','en'])
        self.lang_cb.setCurrentText(self.locale)
        self.lang_cb.currentTextChanged.connect(self._on_lang_change)
        hl.addStretch(); hl.addWidget(self.lang_cb)
        layout.addLayout(hl)

        # Filters
        fhl = QHBoxLayout()
        fhl.addWidget(QLabel(lang.t('search')))
        self.search_le = QLineEdit()
        self.search_le.setPlaceholderText(lang.t('search_ph'))
        self.search_le.returnPressed.connect(self.apply_filters)
        fhl.addWidget(self.search_le)

        fhl.addWidget(QLabel(lang.t('from')))
        self.dt_from = QLineEdit(date.today().strftime("%Y-%m-%d"))
        fhl.addWidget(self.dt_from)
        fhl.addWidget(QLabel(lang.t('to')))
        self.dt_to = QLineEdit(date.today().strftime("%Y-%m-%d"))
        fhl.addWidget(self.dt_to)

        btn_f = QPushButton(lang.t('filter')); btn_f.clicked.connect(self.apply_filters)
        btn_r = QPushButton(lang.t('reset'));  btn_r.clicked.connect(self.load_data)
        fhl.addWidget(btn_f); fhl.addWidget(btn_r)
        layout.addLayout(fhl)

        # Table
        self.table = QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(
            ["ID","Patient","Type","Paiement","Montant","Date","Statut"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table)

        # Totals
        thl = QHBoxLayout()
        thl.addWidget(QLabel("Total Tx :")); thl.addWidget(QLabel(self.var_total_tx))
        thl.addWidget(QLabel("Total Retraits :")); thl.addWidget(QLabel(self.var_total_rt))
        thl.addWidget(QLabel("Solde net :")); thl.addWidget(QLabel(self.var_net))
        layout.addLayout(thl)

        # Actions
        ahl = QHBoxLayout()
        for key, fn in [('new',self._new),
                        ('edit',self._edit),
                        ('cancel_tx',self._cancel),
                        ('delete_tx',self._delete),
                        ('make_withdrawal',self._withdraw),
                        ('refresh',self.load_data)]:
            b = QPushButton(lang.t(key)); b.clicked.connect(fn)
            ahl.addWidget(b)
        layout.addLayout(ahl)

        # RetraitList
        self.retrait_list = RetraitListView(self, self.retrait_ctrl,
                                            locale=self.locale,
                                            on_retraits_changed=self._refresh_totals)
        layout.addWidget(self.retrait_list)

    def _on_lang_change(self, new):
        self.locale = new
        lang.set_language(new)
        for w in self.children(): w.deleteLater()
        self._build_ui()
        self.load_data()

    def load_data(self):
        txs = self.controller.list_transactions()
        self._populate(txs)
        self._refresh_totals()
        self.retrait_list.load_data()

    def apply_filters(self):
        # parse dates
        try:
            d1 = datetime.fromisoformat(self.dt_from.text())
            d2 = datetime.fromisoformat(self.dt_to.text())
        except:
            QMessageBox.warning(self, lang.t('warning'), "Dates invalides")
            return
        txs = [tx for tx in self.controller.list_transactions()
               if d1.date() <= tx.paid_at.date() <= d2.date()]
        self._populate(txs)
        self._refresh_totals()

    def _populate(self, txs):
        self.table.setRowCount(len(txs))
        for i, tx in enumerate(txs):
            p = ""
            if tx.patient_id:
                pat = self.patient_ctrl.get_patient(tx.patient_id)
                p = getattr(pat,'code_patient','') if pat else ''
            vals = [
                str(tx.transaction_id), p, tx.transaction_type,
                tx.payment_method, f"{tx.amount:.2f}",
                tx.paid_at.strftime("%Y-%m-%d %H:%M"), tx.status
            ]
            for c, v in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(v))

    def _refresh_totals(self):
        """
        Calcule et met à jour :
         - total des transactions (float)
         - total des retraits (float)
         - net = total_tx - total_rt
        """
        # On force tx.amount en float pour éviter Decimal/float
        total_tx = sum(float(tx.amount) for tx in self.controller.list_transactions())
        # get_total_retraits() retourne déjà un float
        total_rt = self.retrait_ctrl.get_total_retraits(None, None, None)
        net      = total_tx - total_rt

        # Mise à jour des chaînes
        self.var_total_tx = f"{total_tx:.2f}"
        self.var_total_rt = f"{total_rt:.2f}"
        self.var_net      = f"{net:.2f}"


    def _new(self):       CaisseFormDialog(self, self.controller,
                                         self.patient_ctrl,
                                         self.pharmacy_ctrl,
                                         self.consultation_spirituel_ctrl,
                                         self.medical_record_ctrl,
                                         on_save=self.load_data,
                                         locale=self.locale).exec()

    def _edit(self):      pass  # idem que new, mais avec transaction chargée
    def _cancel(self):    pass
    def _delete(self):    pass
    def _withdraw(self):  pass
