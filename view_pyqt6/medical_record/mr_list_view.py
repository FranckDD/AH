import os
from datetime import datetime
from typing import Any, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QComboBox, QDateEdit, QGroupBox, QGridLayout, QDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor

from view_pyqt6.controller_resolver import ControllerResolver
from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView
from utils.export_utils import export_medical_records_to_excel, export_medical_records_to_pdf


class MedicalRecordListView(QWidget):
    def __init__(self, parent, controllers: Any, on_prescribe: Optional[Callable] = None):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.medical_record_controller()
        self.patient_controller = self.resolver.patient_controller()  # Ajout
        self.on_prescribe = on_prescribe
        self.selected_record = None
        self.page = 1
        self.per_page = 20
        self.total_pages = 1
        self.motif_options = []
        
        self._setup_ui()
        self._load_motifs()
        self.refresh()

    def _load_motifs(self):
        """Charge les motifs depuis l'API"""
        try:
            motifs = self.controller.list_motifs()
            if isinstance(motifs, dict) and 'error' in motifs:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger les motifs: {motifs.get('details', 'Erreur inconnue')}")
                self.motif_options = [("Tous", "")]
                return
            self.motif_options = [("Tous", "")]
            if isinstance(motifs, list):
                for motif in motifs:
                    if isinstance(motif, dict):
                        label = motif.get('label_fr', motif.get('code', 'Inconnu'))
                        code = motif.get('code', '')
                        self.motif_options.append((label, code))
                    else:
                        label = getattr(motif, 'label_fr', getattr(motif, 'code', 'Inconnu'))
                        code = getattr(motif, 'code', '')
                        self.motif_options.append((label, code))
            if hasattr(self, 'motif_filter'):
                self.motif_filter.clear()
                for label, code in self.motif_options:
                    self.motif_filter.addItem(label, code)
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement des motifs: {str(e)}")
            self.motif_options = [("Erreur de chargement", "")]

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title and actions
        header_layout = QHBoxLayout()
        title = QLabel("Dossiers Médicaux")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        new_btn = QPushButton("Nouveau Dossier")
        new_btn.clicked.connect(self._create_new)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; font-weight: bold;
                padding: 8px 16px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        header_layout.addWidget(new_btn)
        main_layout.addLayout(header_layout)
        
        # Filters
        filter_group = QGroupBox("Filtres")
        filter_group.setStyleSheet("QGroupBox { font-weight: bold; color: #34495e; }")
        filter_layout = QGridLayout(filter_group)
        
        # Date filters
        filter_layout.addWidget(QLabel("Période:"), 0, 0)
        date_layout = QHBoxLayout()
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setDisplayFormat("dd/MM/yyyy")
        date_layout.addWidget(self.from_date)
        date_layout.addWidget(QLabel("au"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setDisplayFormat("dd/MM/yyyy")
        date_layout.addWidget(self.to_date)
        filter_layout.addLayout(date_layout, 0, 1)
        
        # Motif filter
        filter_layout.addWidget(QLabel("Motif:"), 1, 0)
        self.motif_filter = QComboBox()
        for label, code in self.motif_options:
            self.motif_filter.addItem(label, code)
        filter_layout.addWidget(self.motif_filter, 1, 1)
        
        # Severity filter
        filter_layout.addWidget(QLabel("Gravité:"), 2, 0)
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["Toutes", "Faible", "Moyen", "Élevé"])
        filter_layout.addWidget(self.severity_filter, 2, 1)
        
        # Search
        filter_layout.addWidget(QLabel("Recherche:"), 3, 0)
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Code patient, nom...")
        self.search_entry.returnPressed.connect(self.refresh)
        search_layout.addWidget(self.search_entry)
        search_btn = QPushButton("Recherche")
        search_btn.clicked.connect(self.refresh)
        search_btn.setStyleSheet("padding: 5px;")
        search_layout.addWidget(search_btn)
        filter_layout.addLayout(search_layout, 3, 1)
        
        # Action buttons
        action_layout = QHBoxLayout()
        filter_btn = QPushButton("Appliquer Filtres")
        filter_btn.clicked.connect(self.refresh)
        filter_btn.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; font-weight: bold;
                          padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        action_layout.addWidget(filter_btn)
        reset_btn = QPushButton("Réinitialiser")
        reset_btn.clicked.connect(self._reset_filters)
        reset_btn.setStyleSheet("padding: 8px;")
        action_layout.addWidget(reset_btn)
        filter_layout.addLayout(action_layout, 4, 0, 1, 2)
        main_layout.addWidget(filter_group)
        
        # Table - 8 colonnes
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Code Patient", "Patient", "Date", "Motif", "Gravité", 
            "Diagnostic", "Traitement"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.cellClicked.connect(self.on_select)
        self.table.setStyleSheet("QTableWidget::item:selected { background-color: #b8e6f3; }")
        main_layout.addWidget(self.table, 1)
        
        # Bottom actions
        footer_layout = QHBoxLayout()
        self.view_btn = QPushButton("Voir/Éditer")
        self.view_btn.clicked.connect(self.view_record)
        self.view_btn.setEnabled(False)
        self.view_btn.setStyleSheet("padding: 8px;")
        footer_layout.addWidget(self.view_btn)
        
        self.prescribe_btn = QPushButton("Prescrire")
        self.prescribe_btn.clicked.connect(self.prescribe_record)
        self.prescribe_btn.setEnabled(False)
        self.prescribe_btn.setStyleSheet("padding: 8px;")
        footer_layout.addWidget(self.prescribe_btn)
        
        export_layout = QHBoxLayout()
        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.clicked.connect(self.export_pdf)
        export_pdf_btn.setStyleSheet("padding: 8px; background-color: #3498db; color: white; border-radius: 4px;")
        export_layout.addWidget(export_pdf_btn)
        export_excel_btn = QPushButton("Export Excel")
        export_excel_btn.clicked.connect(self.export_excel)
        export_excel_btn.setStyleSheet("padding: 8px; background-color: #27ae60; color: white; border-radius: 4px;")
        export_layout.addWidget(export_excel_btn)
        footer_layout.addLayout(export_layout)
        footer_layout.addStretch()
        
        # Pagination
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Précédent")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setStyleSheet("padding: 5px;")
        pagination_layout.addWidget(self.prev_btn)
        self.page_label = QLabel("Page 1")
        pagination_layout.addWidget(self.page_label)
        self.next_btn = QPushButton("Suivant")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setStyleSheet("padding: 5px;")
        pagination_layout.addWidget(self.next_btn)
        footer_layout.addLayout(pagination_layout)
        main_layout.addLayout(footer_layout)
        self._update_pagination_buttons()

    def _reset_filters(self):
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate())
        self.motif_filter.setCurrentIndex(0)
        self.severity_filter.setCurrentIndex(0)
        self.search_entry.clear()
        self.page = 1
        self.refresh()

    def _create_new(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Nouveau Dossier Médical")
        dialog.setModal(True)
        dialog.resize(900, 700)
        current_user = getattr(self.controllers, "current_user", None)
        form_view = MedicalRecordFormView(
            parent=dialog,
            controllers=self.controllers,
            current_user=current_user,
            on_save=lambda: self._on_record_saved(dialog)
        )
        layout = QVBoxLayout(dialog)
        layout.addWidget(form_view)
        dialog.exec()

    def _on_record_saved(self, dialog):
        dialog.accept()
        self.refresh()
        QMessageBox.information(self, "Succès", "Dossier médical créé avec succès")

    def refresh(self):
        date_from = self.from_date.date().toString("yyyy-MM-dd")
        date_to = self.to_date.date().toString("yyyy-MM-dd")
        motif = self.motif_filter.currentData()
        severity = self.severity_filter.currentText()
        if severity == "Toutes": severity = None
        search = self.search_entry.text().strip() or None

        try:
            response = self.controller.list_medical_records(
                page=self.page, per_page=self.per_page,
                date_from=date_from, date_to=date_to,
                motif_code=motif if motif else None,
                severity=severity, search=search
            )

            if isinstance(response, dict) and 'error' in response:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger les dossiers: {response.get('details', 'Erreur inconnue')}")
                return

            records = response.get('data', []) if isinstance(response, dict) else (response or [])
            total_count = response.get('total', len(records)) if isinstance(response, dict) else len(records)
            self.total_pages = response.get('total_pages', max(1, (total_count + self.per_page - 1) // self.per_page))

            filtered_records = self._get_filtered_records(records)
            total_count = len(filtered_records)
            self.total_pages = max(1, (total_count + self.per_page - 1) // self.per_page)
            start = (self.page - 1) * self.per_page
            end = start + self.per_page
            page_records = filtered_records[start:end]

            self.table.setRowCount(0)
            for row, record in enumerate(page_records):
                self.table.insertRow(row)
                record_data = self._extract_record_data(record)

                self.table.setItem(row, 0, QTableWidgetItem(str(record_data['record_id'])))
                self.table.setItem(row, 1, QTableWidgetItem(record_data['patient_code']))
                self.table.setItem(row, 2, QTableWidgetItem(record_data['patient_name']))
                self.table.setItem(row, 3, QTableWidgetItem(record_data['consultation_date']))
                self.table.setItem(row, 4, QTableWidgetItem(record_data['motif_code']))

                severity_item = QTableWidgetItem(record_data['severity'])
                if record_data['severity'] == "high":
                    severity_item.setBackground(QColor(255, 200, 200))
                elif record_data['severity'] == "medium":
                    severity_item.setBackground(QColor(255, 255, 200))
                elif record_data['severity'] == "low":
                    severity_item.setBackground(QColor(200, 255, 200))
                self.table.setItem(row, 5, severity_item)

                self.table.setItem(row, 6, QTableWidgetItem(record_data['diagnosis_display']))
                self.table.setItem(row, 7, QTableWidgetItem(record_data['treatment_display']))

                if record_data['record_id']:
                    self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, record_data['record_id'])
                    self.table.item(row, 6).setToolTip(record_data['diagnosis'])
                    self.table.item(row, 7).setToolTip(record_data['treatment'])

            self.page_label.setText(f"Page {self.page} sur {self.total_pages}")
            self._update_pagination_buttons()

        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")
            self._update_pagination_buttons()

    def _extract_record_data(self, record):
        """Extrait les données avec récupération patient via patient_id si nécessaire"""
        if isinstance(record, dict):
            record_id = record.get('record_id', '')
            patient_id = record.get('patient_id')
            patient_obj = record.get('patient')
            consultation_date = record.get('consultation_date', '')
            motif_code = record.get('motif_code', '')
            severity = record.get('severity', '')
            diagnosis = record.get('diagnosis', '') or ''
            treatment = record.get('treatment', '') or ''
        else:
            record_id = getattr(record, 'record_id', '')
            patient_id = getattr(record, 'patient_id', None)
            patient_obj = getattr(record, 'patient', None)
            consultation_date = getattr(record, 'consultation_date', '')
            motif_code = getattr(record, 'motif_code', '')
            severity = getattr(record, 'severity', '')
            diagnosis = getattr(record, 'diagnosis', '') or ''
            treatment = getattr(record, 'treatment', '') or ''

        # Formater la date
        if isinstance(consultation_date, datetime):
            consultation_date = consultation_date.strftime('%Y-%m-%d')
        elif isinstance(consultation_date, str) and len(consultation_date) > 10:
            consultation_date = consultation_date[:10]

        # Raccourcir les textes
        diagnosis_display = diagnosis[:30] + "..." if len(diagnosis) > 30 else diagnosis
        treatment_display = treatment[:30] + "..." if len(treatment) > 30 else treatment

        # === RÉCUPÉRATION DU PATIENT ===
        patient_code = ""
        patient_name = ""

        if patient_obj:
            # Cas 1 : patient inclus
            if isinstance(patient_obj, dict):
                patient_code = patient_obj.get('code_patient', '')
                patient_name = f"{patient_obj.get('last_name', '')} {patient_obj.get('first_name', '')}".strip()
            else:
                patient_code = getattr(patient_obj, 'code_patient', '')
                patient_name = f"{getattr(patient_obj, 'last_name', '')} {getattr(patient_obj, 'first_name', '')}".strip()
        elif patient_id and self.patient_controller:
            # Cas 2 : charger via patient_id
            try:
                patient_data = self.patient_controller.get_patient(patient_id)
                if isinstance(patient_data, dict):
                    patient_code = patient_data.get('code_patient', '')
                    patient_name = f"{patient_data.get('last_name', '')} {patient_data.get('first_name', '')}".strip()
                else:
                    patient_code = getattr(patient_data, 'code_patient', '')
                    patient_name = f"{getattr(patient_data, 'last_name', '')} {getattr(patient_data, 'first_name', '')}".strip()
            except Exception:
                patient_code = "Inconnu"
                patient_name = "Patient non trouvé"

        return {
            'record_id': record_id,
            'patient_code': patient_code or "N/A",
            'patient_name': patient_name or "Inconnu",
            'consultation_date': consultation_date,
            'motif_code': motif_code or "N/A",
            'severity': severity or "N/A",
            'diagnosis': diagnosis,
            'treatment': treatment,
            'diagnosis_display': diagnosis_display,
            'treatment_display': treatment_display
        }

    def _parse_to_date(self, value):
        if value is None: return None
        if isinstance(value, datetime): return value.date()
        from datetime import date as _date
        if isinstance(value, _date): return value
        if isinstance(value, str) and len(value) >= 10:
            try: return datetime.strptime(value[:10], '%Y-%m-%d').date()
            except: pass
        return None

    def _get_filtered_records(self, records):
        from_d = self.from_date.date().toPyDate()
        to_d = self.to_date.date().toPyDate()
        filtered_recs = []

        for record in records:
            consult_raw = record.get('consultation_date') if isinstance(record, dict) else getattr(record, 'consultation_date', '')
            consult_date = self._parse_to_date(consult_raw)
            if consult_date is None or not (from_d <= consult_date <= to_d):
                continue
            filtered_recs.append(record)

        if self.motif_filter.currentText() != "Tous":
            motif_code = self.motif_filter.currentData()
            filtered_recs = [r for r in filtered_recs if
                            (isinstance(r, dict) and r.get('motif_code') == motif_code) or
                            (getattr(r, 'motif_code', None) == motif_code)]

        if self.severity_filter.currentText() != "Toutes":
            sev_text = self.severity_filter.currentText()
            mapping = {"Faible": "low", "Moyen": "medium", "Élevé": "high"}
            sev_db = mapping.get(sev_text, sev_text.lower())
            filtered_recs = [r for r in filtered_recs if
                            (isinstance(r, dict) and r.get('severity') == sev_db) or
                            (getattr(r, 'severity', None) == sev_db)]

        search_term = self.search_entry.text().strip().lower()
        if search_term:
            filtered_recs = [r for r in filtered_recs if self._record_matches_search(r, search_term)]

        def _key_date(r):
            raw = r.get('consultation_date') if isinstance(r, dict) else getattr(r, 'consultation_date', '')
            d = self._parse_to_date(raw)
            return d or datetime(1900, 1, 1).date()
        filtered_recs.sort(key=_key_date, reverse=True)
        return filtered_recs

    def _record_matches_search(self, record, search_term):
        patient_code = ""
        patient_name = ""
        if isinstance(record, dict):
            patient = record.get('patient', {})
            patient_code = patient.get('code_patient', '').lower() if isinstance(patient, dict) else ''
            last_name = patient.get('last_name', '').lower() if isinstance(patient, dict) else ''
            first_name = patient.get('first_name', '').lower() if isinstance(patient, dict) else ''
        else:
            patient = getattr(record, 'patient', None)
            if patient:
                patient_code = getattr(patient, 'code_patient', '').lower()
                last_name = getattr(patient, 'last_name', '').lower()
                first_name = getattr(patient, 'first_name', '').lower()
        return (search_term in patient_code or search_term in f"{last_name} {first_name}".lower())

    def on_select(self, row, column):
        self.selected_record = None
        if row >= 0 and self.table.item(row, 0):
            self.selected_record = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.view_btn.setEnabled(self.selected_record is not None)
        self.prescribe_btn.setEnabled(self.selected_record is not None)

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self.refresh()

    def _update_pagination_buttons(self):
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < self.total_pages)

    def view_record(self):
        if not self.selected_record: return
        dialog = QDialog(self)
        dialog.setWindowTitle("Éditer Dossier Médical")
        dialog.setModal(True)
        dialog.resize(800, 600)
        current_user = getattr(self.controllers, "current_user", None)
        edit_view = MedicalRecordFormView(
            parent=dialog, controllers=self.controllers,
            current_user=current_user, record_id=self.selected_record,
            on_save=self.refresh
        )
        layout = QVBoxLayout(dialog)
        layout.addWidget(edit_view)
        dialog.exec()

    def prescribe_record(self):
        if not self.selected_record: return
        try:
            record_data = self.controller.get_medical_record(self.selected_record)
            if isinstance(record_data, dict) and 'error' in record_data:
                QMessageBox.warning(self, "Erreur", f"Impossible de récupérer le dossier: {record_data.get('details', 'Erreur inconnue')}")
                return
            patient_id = record_data.get('patient_id') if isinstance(record_data, dict) else getattr(record_data, 'patient_id', None)
            if patient_id and self.on_prescribe:
                self.on_prescribe(patient_id=patient_id, medical_record_id=self.selected_record)
            else:
                QMessageBox.warning(self, "Erreur", "Impossible de déterminer le patient")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de la récupération: {str(e)}")

    def export_pdf(self):
        self._export_to(format="pdf")

    def export_excel(self):
        self._export_to(format="excel")

    def _export_to(self, format: str):
        try:
            date_from = self.from_date.date().toString("yyyy-MM-dd")
            date_to = self.to_date.date().toString("yyyy-MM-dd")
            motif = self.motif_filter.currentData()
            severity = self.severity_filter.currentText()
            if severity == "Toutes": severity = None
            search = self.search_entry.text().strip() or None

            response = self.controller.list_medical_records(
                page=1, per_page=1000000,
                date_from=date_from, date_to=date_to,
                motif_code=motif if motif else None,
                severity=severity, search=search
            )
            if isinstance(response, dict) and 'error' in response:
                QMessageBox.warning(self, "Erreur", f"Impossible d'exporter: {response.get('details', 'Erreur inconnue')}")
                return
            records = response.get('data', []) if isinstance(response, dict) else response

            data = []
            for record in records:
                rec_data = self._extract_record_data(record)
                bp = record.get("bp", "") if isinstance(record, dict) else getattr(record, "bp", "")
                temp = record.get("temperature", "") if isinstance(record, dict) else getattr(record, "temperature", "")
                weight = record.get("weight", "") if isinstance(record, dict) else getattr(record, "weight", "")
                height = record.get("height", "") if isinstance(record, dict) else getattr(record, "height", "")

                data.append({
                    'record_id': rec_data['record_id'],
                    'consultation_date': rec_data['consultation_date'],
                    'patient_name': rec_data['patient_name'],
                    'patient_code': rec_data['patient_code'],
                    'motif_code': rec_data['motif_code'],
                    'severity': rec_data['severity'],
                    'bp': bp,
                    'temperature': temp,
                    'weight': weight,
                    'height': height,
                    'diagnosis': rec_data['diagnosis'],
                    'treatment': rec_data['treatment']
                })

            default_name = "dossiers_medicaux"
            file_filter = "PDF Files (*.pdf)" if format == "pdf" else "Excel Files (*.xlsx)"
            file_path, _ = QFileDialog.getSaveFileName(
                self, f"Exporter en {format.upper()}",
                os.path.expanduser(f"~/{default_name}.{format}"),
                file_filter
            )
            if not file_path: return

            if format == "pdf":
                export_medical_records_to_pdf(data, file_path)
            else:
                export_medical_records_to_excel(data, file_path)

            QMessageBox.information(
                self, f"Export {format.upper()}",
                f"Export réussi vers:\n{file_path}\n\n{len(data)} dossiers exportés"
            )
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'export: {str(e)}")