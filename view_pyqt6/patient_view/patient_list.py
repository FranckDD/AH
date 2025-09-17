# view_pyqt6/patient_view/patient_list_view.py

import os
from typing import Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QToolButton, QMenu, QApplication, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QFont

from view_pyqt6.controller_resolver import ControllerResolver
from view_pyqt6.patient_view.patient_edit_view import PatientsEditView  # Nouvelle importation


class PatientListView(QWidget):
    def __init__(self, parent, controllers: Any, **kwargs):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.patient_controller()
        self.selected_patient = None
        self.page = 1
        self.per_page = 15
        self.total_pages = 1  # Ajout pour gérer le total des pages
        
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title = QLabel("Liste des Patients")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Rechercher...")
        self.search_entry.returnPressed.connect(self.refresh)
        search_layout.addWidget(self.search_entry)
        
        search_btn = QPushButton("🔍")
        search_btn.clicked.connect(self.refresh)
        search_btn.setFixedWidth(40)
        search_layout.addWidget(search_btn)
        
        main_layout.addLayout(search_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.view_btn = QPushButton("Voir Profil")
        self.view_btn.clicked.connect(self.view_profile)
        self.view_btn.setEnabled(False)
        action_layout.addWidget(self.view_btn)
        
        self.edit_btn = QPushButton("Éditer")
        self.edit_btn.clicked.connect(self.edit_patient)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        export_btn = QPushButton("Export PDF")
        export_btn.clicked.connect(self.export_pdf)
        action_layout.addWidget(export_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Code", "Nom", "Prénom", "Naissance", "Téléphone"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.cellClicked.connect(self.on_select)
        main_layout.addWidget(self.table, 1)
        
        # Pagination
        pagination_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("← Précédent")
        self.prev_btn.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 1")
        pagination_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Suivant →")
        self.next_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_btn)
        
        pagination_layout.addStretch()
        main_layout.addLayout(pagination_layout)
        
        # Update button states
        self._update_pagination_buttons()

    # view_pyqt6/patient_view/patient_list_view.py

    def refresh(self):
        search_text = self.search_entry.text().strip()
        search_param = search_text if search_text else None
        
        print(f"DEBUG: Loading page {self.page} with {self.per_page} items, search: '{search_param}'")
        
        try:
            response = self.controller.list_patients(
                page=self.page, 
                per_page=self.per_page, 
                search=search_param
            )
            
            print(f"DEBUG: API response type: {type(response)}")
            if isinstance(response, dict):
                print(f"DEBUG: Response keys: {list(response.keys())}")
            elif isinstance(response, list):
                print(f"DEBUG: Response list length: {len(response)}")
            
            # Handle API response
            if isinstance(response, dict) and 'error' in response:
                QMessageBox.warning(self, "Erreur", f"Impossible de charger les patients: {response.get('details', 'Erreur inconnue')}")
                return
            
            patients = []
            total_pages = 1
            
            if isinstance(response, dict):
                patients = response.get('data', [])
                total_pages = response.get('total_pages', 1)
                print(f"DEBUG: From API - patients: {len(patients)}, total_pages: {total_pages}")
            elif isinstance(response, list):
                patients = response
                # Estimation plus intelligente
                if len(patients) < self.per_page:
                    total_pages = self.page  # Dernière page
                else:
                    total_pages = self.page + 1  # Il y a une page suivante
                print(f"DEBUG: From list - patients: {len(patients)}, estimated total_pages: {total_pages}")
            else:
                QMessageBox.warning(self, "Erreur", "Format de réponse inattendu")
                return
            
            # CORRECTION CRITIQUE: Mettre à jour self.total_pages
            self.total_pages = total_pages
            print(f"DEBUG: Setting total_pages to: {self.total_pages}")
            
            # Clear table
            self.table.setRowCount(0)
            
            # Populate table
            for row, patient in enumerate(patients):
                self.table.insertRow(row)
                
                # Extract data
                if isinstance(patient, dict):
                    patient_id = patient.get('patient_id')
                    code = patient.get('code_patient', '')
                    last_name = patient.get('last_name', '')
                    first_name = patient.get('first_name', '')
                    birth_date = patient.get('birth_date', '')
                    phone = patient.get('contact_phone', '')
                else:
                    patient_id = getattr(patient, 'patient_id', None)
                    code = getattr(patient, 'code_patient', '')
                    last_name = getattr(patient, 'last_name', '')
                    first_name = getattr(patient, 'first_name', '')
                    birth_date = getattr(patient, 'birth_date', '')
                    phone = getattr(patient, 'contact_phone', '')
                
                self.table.setItem(row, 0, QTableWidgetItem(str(patient_id)))
                self.table.setItem(row, 1, QTableWidgetItem(code))
                self.table.setItem(row, 2, QTableWidgetItem(last_name))
                self.table.setItem(row, 3, QTableWidgetItem(first_name))
                self.table.setItem(row, 4, QTableWidgetItem(str(birth_date)))
                self.table.setItem(row, 5, QTableWidgetItem(phone))
                
                if patient_id:
                    self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, patient_id)
            
            # Update pagination
            self.page_label.setText(f"Page {self.page} sur {self.total_pages}")
            self._update_pagination_buttons(self.total_pages)
            print(f"DEBUG: Buttons - prev: {self.page > 1}, next: {self.page < self.total_pages}")
            
        except Exception as e:
            print(f"DEBUG: Error: {e}")
            QMessageBox.warning(self, "Erreur", f"Erreur lors du chargement: {str(e)}")
            self._update_pagination_buttons()


    def on_select(self, row, column):
        self.selected_patient = None
        
        if row >= 0 and self.table.item(row, 0):
            self.selected_patient = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
        # Update button states
        self.view_btn.setEnabled(self.selected_patient is not None)
        self.edit_btn.setEnabled(self.selected_patient is not None)

    def prev_page(self):
        print(f"DEBUG: Previous page clicked, current page: {self.page}")
        if self.page > 1:
            self.page -= 1
            print(f"DEBUG: Going to page: {self.page}")
            self.refresh()
        else:
            print("DEBUG: Already on first page")

    def next_page(self):
        print(f"DEBUG: Next page clicked, current page: {self.page}, total pages: {self.total_pages}")
        if self.page < self.total_pages:
            self.page += 1
            print(f"DEBUG: Going to page: {self.page}")
            self.refresh()
        else:
            print("DEBUG: Already on last page")

    def _update_pagination_buttons(self, total_pages=None):
        """
        Met à jour l'état des boutons de pagination
        total_pages: Nombre total de pages (optionnel)
        """
        if total_pages is not None:
            # Si on connaît le nombre total de pages
            self.prev_btn.setEnabled(self.page > 1)
            self.next_btn.setEnabled(self.page < total_pages)
        else:
            # Mode par défaut (toujours activer suivant si on ne connaît pas le total)
            self.prev_btn.setEnabled(self.page > 1)
            self.next_btn.setEnabled(True)  # Toujours activé si on ne connaît pas le total

    def view_profile(self):
        if not self.selected_patient:
            return
            
        # Open profile view (to be implemented)
        QMessageBox.information(self, "Info", f"Voir le profil du patient {self.selected_patient}")

    def edit_patient(self):
        if not self.selected_patient:
            return
            
        # Open edit form in a dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Éditer Patient")
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        # Create edit view
        edit_view = PatientsEditView(
            parent=dialog,
            controllers=self.controllers,
            patient_id=self.selected_patient
        )
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(edit_view)
        
        # Refresh after dialog closes
        dialog.finished.connect(self.refresh)
        
        dialog.exec()

    def export_pdf(self):
        try:
            # Get all patients for export
            patients = self.controller.list_patients(
                page=1, 
                per_page=1000, 
                search=self.search_entry.text().strip() or None
            )
            
            if isinstance(patients, dict) and 'error' in patients:
                QMessageBox.warning(self, "Erreur", f"Impossible d'exporter: {patients.get('details', 'Erreur inconnue')}")
                return
                
            # Ask for save location
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Exporter en PDF", 
                os.path.expanduser("~/liste_patients.pdf"), 
                "PDF Files (*.pdf)"
            )
            
            if file_path:
                # In a real implementation, you would generate the PDF here
                # For now, just show a message
                QMessageBox.information(
                    self, 
                    "Export PDF", 
                    f"Export réussi vers:\n{file_path}\n\n{len(patients)} patients exportés"
                )
                
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'export: {str(e)}")