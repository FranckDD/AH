import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QFrame, QComboBox, QMessageBox,
    QScrollBar, QHeaderView
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt
from view_pyqt6.secretaire.cs_form import CSFormView
from view_pyqt6.api_controller import ApiGatewayError
from view_pyqt6.controller_resolver import ControllerResolver
from utils.export_cs_pdf import export_cs_to_pdf
from datetime import datetime

logger = logging.getLogger(__name__)

class CSListView(QWidget):
    def __init__(self, parent, controllers):
        super().__init__(parent)
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.consultation_spirituel_controller()
        self.patient_ctrl = self.resolver.patient_controller()
        self.controllers = controllers
        self.filtered = None
        self.page = 0
        self.page_size = 20
        self.locale = "fr"

        self.texts = {
            "fr": {
                "title": "Liste des Consultations Spirituelles",
                "new_cs": "Nouvelle Consultation",
                "filter": "Rechercher patient...",
                "type": "Type:",
                "edit": "Éditer",
                "export": "Exporter PDF",
                "prev": "◄ Précédent",
                "next": "Suivant ►",
                "page": "Page {0} / {1}",
                "error_no_selection": "Aucune consultation sélectionnée.",
                "error_invalid_id": "ID invalide.",
                "error_network": "Erreur réseau : impossible de charger les données.",
                "error_unexpected": "Une erreur inattendue s'est produite.",
                "no_data": "Aucune consultation trouvée.",
                "pdf_success": "Fichier PDF généré : {0}"
            },
            "en": {
                "title": "Spiritual Consultations List",
                "new_cs": "New Consultation",
                "filter": "Search patient...",
                "type": "Type:",
                "edit": "Edit",
                "export": "Export PDF",
                "prev": "◄ Previous",
                "next": "Next ►",
                "page": "Page {0} / {1}",
                "error_no_selection": "No consultation selected.",
                "error_invalid_id": "Invalid ID.",
                "error_network": "Network error: unable to load data.",
                "error_unexpected": "An unexpected error occurred.",
                "no_data": "No consultations found.",
                "pdf_success": "PDF file generated: {0}"
            }
        }

        try:
            self._setup_ui()
            self.load_data()
        except Exception as e:
            logger.exception("Failed to initialize CSListView: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _setup_ui(self):
        logger.debug("Setting up CSListView UI")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Title and New Consultation Button
        header_layout = QHBoxLayout()
        title = QLabel(self.texts[self.locale]["title"])
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        new_btn = QPushButton(self.texts[self.locale]["new_cs"])
        new_btn.setIcon(QIcon("assets/add.png"))
        new_btn.clicked.connect(self._create_new)
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
                cursor: pointer;
            }
        """)
        header_layout.addWidget(new_btn)
        layout.addLayout(header_layout)

        # Filters
        filter_group = QFrame()
        filter_group.setStyleSheet("QFrame { border: 1px solid #E0E0E0; border-radius: 5px; }")
        filter_layout = QHBoxLayout(filter_group)
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText(self.texts[self.locale]["filter"])
        self.search_entry.textChanged.connect(self._apply_filters)
        search_btn = QPushButton("🔍")
        search_btn.setFixedWidth(40)
        search_btn.clicked.connect(self._apply_filters)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                cursor: pointer;
            }
        """)
        lbl_type = QLabel(self.texts[self.locale]["type"])
        self.combo_type = QComboBox()
        types = ["Tous"]
        try:
            consultations = self.controller.list_consultations()
            types += sorted({cs.get('type_consultation', '') for cs in consultations if cs.get('type_consultation')})
        except Exception as e:
            logger.exception("Error loading consultation types: %s", e)
            types = ["Tous", "Spiritual", "FamilyRestoration"]
        self.combo_type.addItems(types)
        self.combo_type.currentTextChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_entry, 1)
        filter_layout.addWidget(search_btn)
        filter_layout.addWidget(lbl_type)
        filter_layout.addWidget(self.combo_type)
        layout.addWidget(filter_group)

        # Table
        self.table = QTableWidget()
        cols = (
            "patient", "type_consultation", "presc_generic", "presc_med_spirituel",
            "mp_type", "fr_registered_at", "fr_appointment_at",
            "fr_amount_paid", "fr_observation"
        )
        headings = {
            "patient": "Patient",
            "type_consultation": "Type",
            "presc_generic": "Presc. Gén.",
            "presc_med_spirituel": "Presc. Méd. Spir.",
            "mp_type": "Prayer Book",
            "fr_registered_at": "Inscrit le",
            "fr_appointment_at": "Rdv le",
            "fr_amount_paid": "Montant",
            "fr_observation": "Observation"
        }
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([headings[col] for col in cols])
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget::item:selected { background-color: #b8e6f3; }
        """)
        layout.addWidget(self.table, 1)

        # Action Buttons and Pagination
        footer_layout = QHBoxLayout()
        btn_edit = QPushButton(self.texts[self.locale]["edit"])
        btn_edit.setIcon(QIcon("assets/edit.png"))
        btn_edit.clicked.connect(self._edit_selected)
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                cursor: pointer;
            }
        """)
        btn_export = QPushButton(self.texts[self.locale]["export"])
        btn_export.setIcon(QIcon("assets/pdf.png"))
        btn_export.clicked.connect(self._export_pdf)
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #27ae60;
                cursor: pointer;
            }
        """)
        footer_layout.addWidget(btn_edit)
        footer_layout.addWidget(btn_export)
        footer_layout.addStretch()

        # Pagination
        self.prev_btn = QPushButton(self.texts[self.locale]["prev"])
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton(self.texts[self.locale]["next"])
        self.next_btn.clicked.connect(self._next_page)
        self.page_label = QLabel(self.texts[self.locale]["page"].format(1, 1))
        footer_layout.addWidget(self.prev_btn)
        footer_layout.addWidget(self.page_label)
        footer_layout.addWidget(self.next_btn)
        layout.addLayout(footer_layout)

        self.setStyleSheet("""
            QWidget { background: #F5F5F5; }
            QPushButton { color: white; border-radius: 4px; padding: 8px; }
            QPushButton:hover { cursor: pointer; }
            QLineEdit, QComboBox { border: 1px solid #E0E0E0; border-radius: 5px; padding: 5px; }
            QLabel { color: #333333; }
        """)

    def _create_new(self):
        logger.debug("Creating new consultation")
        try:
            form = CSFormView(
                parent=self,
                controllers=self.controllers,
                consultation=None,
                on_save=lambda: (self.load_data(), form.close())
            )
            form.show()
        except Exception as e:
            logger.exception("Error creating new consultation: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _apply_filters(self):
        logger.debug("Applying filters with search: %s, type: %s", self.search_entry.text(), self.combo_type.currentText())
        try:
            all_cs = self.controller.list_consultations()
            term = self.search_entry.text().strip().lower()

            if term:
                def match_patient(cs):
                    patient = cs.get('patient', {})
                    if not patient:
                        return False
                    code = (patient.get('code_patient', '') or '').lower()
                    nom = (patient.get('last_name', '') or '').lower()
                    pre = (patient.get('first_name', '') or '').lower()
                    return term in code or term in nom or term in pre
                filtered = [cs for cs in all_cs if match_patient(cs)]
            else:
                filtered = all_cs

            t = self.combo_type.currentText()
            if t != "Tous":
                filtered = [cs for cs in filtered if cs.get('type_consultation') == t]

            self.filtered = filtered
            self.page = 0
            self._populate_table()
        except ApiGatewayError as e:
            logger.exception("API error applying filters: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_network"])
        except Exception as e:
            logger.exception("Unexpected error applying filters: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def load_data(self):
        logger.debug("Loading consultation data")
        self.filtered = None
        self.page = 0
        self._populate_table()

    def _populate_table(self):
        logger.debug("Populating table, page: %d", self.page)
        try:
            data = self.filtered if self.filtered is not None else self.controller.list_consultations()
            start = self.page * self.page_size
            end = start + self.page_size
            page_data = data[start:end]

            total_pages = max(1, (len(data) + self.page_size - 1) // self.page_size)
            self.page_label.setText(self.texts[self.locale]["page"].format(self.page + 1, total_pages))
            self.prev_btn.setEnabled(self.page > 0)
            self.next_btn.setEnabled(self.page < total_pages - 1)

            self.table.setRowCount(0)
            self.table.setRowCount(len(page_data))

            for row, cs in enumerate(page_data):
                patient = cs.get('patient', {})
                patient_display = ""
                if patient:
                    code = patient.get('code_patient', '') or ''
                    nom = patient.get('last_name', '') or ''
                    pre = patient.get('first_name', '') or ''
                    patient_display = f"{code} – {nom} {pre}"

                reg = cs.get('fr_registered_at', '')
                if reg and isinstance(reg, datetime):
                    reg = reg.strftime("%Y-%m-%d")
                elif reg and isinstance(reg, str):
                    reg = reg
                app = cs.get('fr_appointment_at', '')
                if app and isinstance(app, datetime):
                    app = app.strftime("%Y-%m-%d")
                elif app and isinstance(app, str):
                    app = app
                amt = cs.get('fr_amount_paid', '')
                if amt and isinstance(amt, str):
                    try:
                        amt = f"{float(amt):.2f}"
                    except ValueError:
                        amt = amt
                elif amt and isinstance(amt, (int, float)):
                    amt = f"{amt:.2f}"
                else:
                    amt = ""
                obs = (cs.get('fr_observation', '') or '')[:30] + ("…" if len(cs.get('fr_observation', '') or '') > 30 else "")

                self.table.setItem(row, 0, QTableWidgetItem(patient_display))
                self.table.setItem(row, 1, QTableWidgetItem(cs.get('type_consultation', '')))
                self.table.setItem(row, 2, QTableWidgetItem(str(cs.get('presc_generic', ''))))
                self.table.setItem(row, 3, QTableWidgetItem(str(cs.get('presc_med_spirituel', ''))))
                self.table.setItem(row, 4, QTableWidgetItem(cs.get('mp_type', '')))
                self.table.setItem(row, 5, QTableWidgetItem(reg))
                self.table.setItem(row, 6, QTableWidgetItem(app))
                self.table.setItem(row, 7, QTableWidgetItem(amt))
                self.table.setItem(row, 8, QTableWidgetItem(obs))
                self.table.setRowHeight(row, 25)

                # Store ID in first column
                item = self.table.item(row, 0)
                item.setData(Qt.ItemDataRole.UserRole, cs.get('consultation_id'))
        except Exception as e:
            logger.exception("Error populating table: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._populate_table()

    def _next_page(self):
        total = len(self.filtered) if self.filtered is not None else len(self.controller.list_consultations())
        if (self.page + 1) * self.page_size < total:
            self.page += 1
            self._populate_table()

    def _edit_selected(self):
        logger.debug("Editing selected consultation")
        try:
            row = self.table.currentRow()
            if row < 0:
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_no_selection"])
                return

            cs_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if not cs_id:
                QMessageBox.warning(self, "Erreur", self.texts[self.locale]["error_invalid_id"])
                return

            cs_obj = self.controller.get_consultation(cs_id)
            form = CSFormView(
                parent=self,
                controllers=self.controllers,
                consultation=cs_obj,
                on_save=lambda: (self.load_data(), form.close())
            )
            form.show()
        except ApiGatewayError as e:
            logger.exception("API error editing consultation: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_network"])
        except Exception as e:
            logger.exception("Unexpected error editing consultation: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])

    def _export_pdf(self):
        logger.debug("Exporting consultations to PDF")
        try:
            data = self.filtered if self.filtered is not None else self.controller.list_consultations()
            t = self.combo_type.currentText()
            if t != "Tous":
                data = [cs for cs in data if cs.get('type_consultation') == t]
            export_list = []
            for cs in data:
                patient = cs.get('patient', {})
                export_list.append({
                    'patient_id': patient.get('patient_id'),
                    'code_patient': patient.get('code_patient', '') or '',
                    'type_consultation': cs.get('type_consultation', ''),
                    'fr_registered_at': cs.get('fr_registered_at'),
                    'fr_appointment_at': cs.get('fr_appointment_at'),
                    'fr_amount_paid': cs.get('fr_amount_paid'),
                    'fr_observation': cs.get('fr_observation', '')
                })
            out = export_cs_to_pdf(export_list, title=f"Consultations_{t}")
            QMessageBox.information(self, "Succès", self.texts[self.locale]["pdf_success"].format(out))
        except Exception as e:
            logger.exception("Error exporting PDF: %s", e)
            QMessageBox.critical(self, "Erreur", self.texts[self.locale]["error_unexpected"])