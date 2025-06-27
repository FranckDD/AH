# view/secretaire/retrait_list_pyqt6.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, QDate, QDateTime

class RetraitListView(QWidget):
    def __init__(self, parent=None, retrait_ctrl=None, on_retraits_changed=None, locale:str="fr"):
        super().__init__(parent)
        self.retrait_ctrl = retrait_ctrl
        self.on_retraits_changed = on_retraits_changed
        self.locale = locale
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        # filters
        fl = QHBoxLayout()
        self.status_cb = QComboBox()
        statuses = {"fr":["Tous","Actif","Annulé"],"en":["All","Active","Cancelled"]}[self.locale]
        self.status_cb.addItems(statuses)
        self.status_cb.currentIndexChanged.connect(self.load_data)
        fl.addWidget(QLabel({"fr":"Statut :","en":"Status:"}[self.locale]))
        fl.addWidget(self.status_cb)
        self.from_de = QDateEdit(QDate.currentDate()); self.from_de.setCalendarPopup(True)
        fl.addWidget(QLabel({"fr":"Du :","en":"From:"}[self.locale]))
        fl.addWidget(self.from_de)
        self.to_de = QDateEdit(QDate.currentDate()); self.to_de.setCalendarPopup(True)
        fl.addWidget(QLabel({"fr":"Au :","en":"To:"}[self.locale]))
        fl.addWidget(self.to_de)
        btn = QPushButton({"fr":"Afficher totaux","en":"Show totals"}[self.locale])
        btn.clicked.connect(self.load_data)
        fl.addWidget(btn)
        layout.addLayout(fl)
        # table
        self.table = QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(["ID","Montant","Date","Auteur","Justification","Statut"])
        layout.addWidget(self.table)
        # cancel button
        btn_cancel = QPushButton({"fr":"Annuler Retrait","en":"Cancel Withdrawal"}[self.locale])
        btn_cancel.setStyleSheet("background:#D32F2F; color:white;")
        btn_cancel.clicked.connect(self._cancel_selected)
        layout.addWidget(btn_cancel)
        # total label
        hl = QHBoxLayout();
        hl.addWidget(QLabel({"fr":"Total Retraits :","en":"Total Withdrawals:"}[self.locale]))
        self.total_le = QLineEdit("0.00"); self.total_le.setReadOnly(True)
        hl.addWidget(self.total_le)
        layout.addLayout(hl)

    def load_data(self):
        # status filter
        st = self.status_cb.currentText()
        mapping_fr = {"Tous":None,"Actif":"active","Annulé":"cancelled"}
        mapping_en = {"All":None,"Active":"active","Cancelled":"cancelled"}
        filt = mapping_fr[st] if self.locale=='fr' else mapping_en[st]
        # dates
        d1 = self.from_de.date().toPyDate(); d2 = self.to_de.date().toPyDate()
        # fetch
        rets = self.retrait_ctrl.list_retraits(status=filt, date_from=d1, date_to=d2)
        # populate table
        self.table.setRowCount(len(rets))
        total = 0.0
        for i,r in enumerate(rets):
            total += float(r.amount)
            row = [str(r.retrait_id), f"{float(r.amount):.2f}",
                   r.retrait_at.strftime("%Y-%m-%d %H:%M"), getattr(r.user,'username',str(r.handled_by)),
                   r.cancel_justification or r.justification or "", r.status]
            for j,val in enumerate(row):
                self.table.setItem(i,j, QTableWidgetItem(val))
        self.total_le.setText(f"{total:.2f}")

    def _cancel_selected(self):
        sel = self.table.currentRow()
        if sel < 0:
            QMessageBox.critical(self, "Erreur", {"fr":"Aucun retrait sélectionné.","en":"No withdrawal selected."}[self.locale])
            return
        rid = int(self.table.item(sel,0).text())
        reason, ok = QMessageBox.getText(self, {"fr":"Justification","en":"Justification"}[self.locale],
                                         {"fr":"Motif d'annulation :","en":"Reason for cancellation:"}[self.locale])
        if not ok or not reason.strip():
            return
        try:
            self.retrait_ctrl.annuler_retrait(rid, reason)
            self.load_data()
            if callable(self.on_retraits_changed): self.on_retraits_changed()
            QMessageBox.information(self, {"fr":"Succès","en":"Success"}[self.locale],
                                    {"fr":"Retrait annulé.","en":"Withdrawal cancelled."}[self.locale])
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
