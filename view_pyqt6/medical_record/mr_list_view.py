# view_pyqt6/medical_record/medical_record_list_view.py

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime, timedelta

from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView
from utils.export_utils import export_medical_records_to_pdf, export_medical_records_to_excel

class MedicalRecordListView(QWidget):
    def __init__(self, parent, controller, on_prescribe):
        super().__init__(parent)
        self.ctrl = controller
        self.on_prescribe = on_prescribe
        self.page = 1
        self.per_page = 20
        self.selected_record = None

        # Récupère les motifs
        motifs = self.ctrl.list_motifs()
        self.code_to_label = {m['code']: m['label_fr'] for m in motifs}
        self.label_to_code = {v:k for k,v in self.code_to_label.items()}

        # --- Layout principal ---
        main = QVBoxLayout(self)
        main.setContentsMargins(10,10,10,10)
        main.setSpacing(8)

        # --- Barre de filtres & actions ---
        filt_layout = QHBoxLayout()
        # Date from
        self.from_date = QDateEdit(self)
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addDays(-365))
        filt_layout.addWidget(self.from_date)
        # Date to
        self.to_date = QDateEdit(self)
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        filt_layout.addWidget(self.to_date)
        # Motif
        self.cbo_motif = QComboBox(self)
        self.cbo_motif.addItem("Tous")
        self.cbo_motif.addItems(list(self.label_to_code.keys()))
        filt_layout.addWidget(self.cbo_motif)
        # Gravité
        self.cbo_sev = QComboBox(self)
        self.cbo_sev.addItems(["Toutes", "low", "medium", "high"])
        filt_layout.addWidget(self.cbo_sev)
        # Recherche
        self.le_search = QLineEdit(self)
        self.le_search.setPlaceholderText("Rechercher code/nom")
        filt_layout.addWidget(self.le_search)
        # Boutons
        btn_refresh = QPushButton("Filtrer", self)
        btn_refresh.clicked.connect(self.refresh)
        filt_layout.addWidget(btn_refresh)
        btn_pdf = QPushButton("Export PDF", self)
        btn_pdf.clicked.connect(self.export_pdf)
        filt_layout.addWidget(btn_pdf)
        btn_xlsx = QPushButton("Export Excel", self)
        btn_xlsx.clicked.connect(self.export_excel)
        filt_layout.addWidget(btn_xlsx)

        main.addLayout(filt_layout)

        # --- Table de résultats ---
        self.table = QTableWidget(self)
        cols = [
            "ID","Code Patient","Pat. ID","Date","Statut","Tension",
            "Temp.","Poids","Taille","Diagnostic","Traitement","Gravité","Motif"
        ]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellClicked.connect(self.on_select)
        main.addWidget(self.table)

        # --- Actions sur la sélection ---
        act_layout = QHBoxLayout()
        self.btn_view = QPushButton("Voir/Éditer", self)
        self.btn_view.setEnabled(False)
        self.btn_view.clicked.connect(self.view_record)
        act_layout.addWidget(self.btn_view)
        self.btn_email = QPushButton("Envoyer Email", self)
        self.btn_email.setEnabled(False)
        # self.btn_email.clicked.connect(self.send_email)
        act_layout.addWidget(self.btn_email)
        self.btn_presc = QPushButton("Prescription", self)
        self.btn_presc.setEnabled(False)
        self.btn_presc.clicked.connect(self.prescribe_record)
        act_layout.addWidget(self.btn_presc)
        main.addLayout(act_layout)

        # --- Pagination ---
        nav = QHBoxLayout()
        btn_prev = QPushButton("← Page précédente", self)
        btn_prev.clicked.connect(self.prev_page)
        nav.addWidget(btn_prev)
        btn_next = QPushButton("Page suivante →", self)
        btn_next.clicked.connect(self.next_page)
        nav.addWidget(btn_next)
        main.addLayout(nav)

        # Chargement initial
        self.refresh()

    def _get_filtered_records(self, for_export=False):
        if for_export:
            recs = self.ctrl.list_records(page=1, per_page=10000)
        else:
            recs = self.ctrl.list_records(page=self.page, per_page=self.per_page)
        # Filtre dates
        from_d = self.from_date.date().toPyDate()
        to_d   = self.to_date.date().toPyDate()
        recs = [r for r in recs if from_d <= r.consultation_date.date() <= to_d]
        # Filtre motif
        m = self.cbo_motif.currentText()
        if m != "Tous":
            code = self.label_to_code[m]
            recs = [r for r in recs if r.motif_code == code]
        # Filtre gravité
        s = self.cbo_sev.currentText()
        if s != "Toutes":
            recs = [r for r in recs if r.severity == s]
        # Filtre recherche
        q = self.le_search.text().strip().lower()
        if q:
            recs = [
                r for r in recs
                if r.patient and (
                    q in r.patient.code_patient.lower()
                    or q in f"{r.patient.last_name} {r.patient.first_name}".lower()
                )
            ]
        # Tri décroissant
        return sorted(recs, key=lambda r: r.consultation_date, reverse=True)

    def refresh(self):
        self.selected_record = None
        self.btn_view.setEnabled(False)
        self.btn_email.setEnabled(False)
        self.btn_presc.setEnabled(False)
        recs = self._get_filtered_records()
        self.table.setRowCount(0)
        for r in recs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = [
                r.record_id,
                r.patient.code_patient if r.patient else "",
                r.patient_id,
                r.consultation_date.strftime("%Y-%m-%d"),
                r.marital_status,
                r.bp, r.temperature, r.weight, r.height,
                r.diagnosis or "", r.treatment or "",
                r.severity, r.motif_code
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, c, item)

    def on_select(self, row, _):
        item = self.table.item(row, 0)
        if item:
            self.selected_record = int(item.text())
            self.btn_view.setEnabled(True)
            self.btn_email.setEnabled(True)
            self.btn_presc.setEnabled(True)

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        self.page += 1
        self.refresh()

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        recs = self._get_filtered_records(for_export=True)
        data = [{
            'record_id': r.record_id,
            'consultation_date': r.consultation_date,
            'patient_name': f"{r.patient.last_name} {r.patient.first_name}" if r.patient else "",
            'motif_code': r.motif_code,
            'severity': r.severity,
            'bp': r.bp,
            'temperature': r.temperature,
            'weight': r.weight,
            'height': r.height,
            'diagnosis': r.diagnosis,
            'treatment': r.treatment
        } for r in recs]
        export_medical_records_to_pdf(data, path)
        QMessageBox.information(self, "Export PDF", f"Fichier enregistré :\n{path}")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Excel", "", "Excel Files (*.xlsx)")
        if not path:
            return
        recs = self._get_filtered_records(for_export=True)
        data = [{
            'record_id': r.record_id,
            'consultation_date': r.consultation_date,
            'patient_name': f"{r.patient.last_name} {r.patient.first_name}" if r.patient else "",
            'motif_code': r.motif_code,
            'severity': r.severity,
            'bp': r.bp,
            'temperature': r.temperature,
            'weight': r.weight,
            'height': r.height,
            'diagnosis': r.diagnosis,
            'treatment': r.treatment
        } for r in recs]
        export_medical_records_to_excel(data, path)
        QMessageBox.information(self, "Export Excel", f"Fichier enregistré :\n{path}")

    def view_record(self):
        if not self.selected_record:
            return
        dlg = QWidget(self, flags=Qt.WindowType.Dialog)
        dlg.setWindowTitle("Éditer Dossier Médical")
        dlg.resize(700, 500)
        layout = QVBoxLayout(dlg)
        frm = MedicalRecordFormView(dlg, self.ctrl, record_id=self.selected_record)
        layout.addWidget(frm)
        dlg.show()
        dlg.destroyed.connect(self.refresh)

    def prescribe_record(self):
        if not self.selected_record:
            return
        recs = self._get_filtered_records()
        rec = next((r for r in recs if r.record_id == self.selected_record), None)
        if rec and rec.patient_id:
            self.on_prescribe(patient_id=rec.patient_id,
                              medical_record_id=rec.record_id)
