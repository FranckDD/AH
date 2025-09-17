# view_pyqt6/prescription_list.py
from typing import Any, List, Optional, Dict
from datetime import date, datetime
from math import ceil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDateEdit, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor

from view_pyqt6.controller_resolver import ControllerResolver
from view_pyqt6.prescription_views.prescription_form_viewqt import PrescriptionFormView
import logging
import json


logger = logging.getLogger(__name__)


class PrescriptionListView(QWidget):
    def __init__(self, parent, controllers: Any, current_user: Any, per_page: int = 20):
        super().__init__(parent)
        self.resolver = ControllerResolver(controllers)
        self.ctrl = self.resolver.prescription_controller()
        self.current_user = current_user
        self.per_page = per_page
        self.page = 1
        self.total = 0
        self._selection_connected = False

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("Recherche (code patient / médoc):"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Code patient ou médicament...")
        # validation recherche par Enter
        self.search_edit.returnPressed.connect(self._on_search)
        top_bar.addWidget(self.search_edit, 1)

        # bouton recherche
        self.btn_search = QPushButton("🔍")
        self.btn_search.clicked.connect(self._on_search)
        top_bar.addWidget(self.btn_search)

        top_bar.addWidget(QLabel("Date from"))
        self.from_d = QDateEdit()
        self.from_d.setCalendarPopup(True)
        self.from_d.setDisplayFormat("yyyy-MM-dd")
        # par défaut : 1 mois en arrière
        self.from_d.setDate(QDate.currentDate().addMonths(-1))
        top_bar.addWidget(self.from_d)

        top_bar.addWidget(QLabel("to"))
        self.to_d = QDateEdit()
        self.to_d.setCalendarPopup(True)
        self.to_d.setDisplayFormat("yyyy-MM-dd")
        self.to_d.setDate(QDate.currentDate())
        top_bar.addWidget(self.to_d)

        filter_btn = QPushButton("Filtrer")
        filter_btn.clicked.connect(self._on_filter)
        top_bar.addWidget(filter_btn)

        new_btn = QPushButton("Nouvelle")
        new_btn.clicked.connect(self._new)
        top_bar.addWidget(new_btn)

        layout.addLayout(top_bar)

        # table: ID, Code Patient, Médoc, Dosage, Freq, Début, Fin
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Code Patient", "Médoc", "Dosage", "Freq", "Début", "Fin"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.cellDoubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table, 1)

        # actions & pagination
        actions = QHBoxLayout()
        self.edit_btn = QPushButton("Aff/Edit")
        self.edit_btn.clicked.connect(self._edit_selected)
        self.del_btn = QPushButton("Supprimer")
        self.del_btn.clicked.connect(self._delete_selected)
        actions.addStretch()
        actions.addWidget(self.edit_btn)
        actions.addWidget(self.del_btn)

        # pagination controls
        self.btn_prev = QPushButton("← Précédent")
        self.btn_prev.clicked.connect(self.prev_page)
        actions.addWidget(self.btn_prev)

        self.page_label = QLabel("Page 1")
        actions.addWidget(self.page_label)

        self.btn_next = QPushButton("Suivant →")
        self.btn_next.clicked.connect(self.next_page)
        actions.addWidget(self.btn_next)

        layout.addLayout(actions)

    # UI actions
    def _on_search(self):
        self.page = 1
        self.refresh()

    def _on_filter(self):
        self.page = 1
        self.refresh()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        # allow next only if more pages exist (setEnabled below)
        self.page += 1
        self.refresh()

    def _get_selected_id(self) -> Optional[int]:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        try:
            row = sel[0].row()
            item = self.table.item(row, 0)
            if item:
                return int(item.text())
        except Exception:
            return None
        return None

    def _edit_selected(self, *_):
        pid = self._get_selected_id()
        if not pid:
            QMessageBox.information(self, "Info", "Aucune ligne sélectionnée")
            return
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Éditer Prescription")
        dlg.setModal(True)
        dlg.resize(700, 450)
        box = QVBoxLayout(dlg)
        form = PrescriptionFormView(dlg, self.resolver, self.current_user, prescription_id=pid, on_save=self.refresh)
        box.addWidget(form)
        dlg.exec()
        self.refresh()

    def _new(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Nouvelle Prescription")
        dlg.setModal(True)
        dlg.resize(700, 450)
        box = QVBoxLayout(dlg)
        form = PrescriptionFormView(dlg, self.resolver, self.current_user, on_save=self.refresh)
        box.addWidget(form)
        dlg.exec()
        self.refresh()

    def _delete_selected(self):
        pid = self._get_selected_id()
        if not pid:
            QMessageBox.information(self, "Info", "Aucune ligne sélectionnée")
            return
        ok = QMessageBox.question(self, "Confirmer", "Supprimer cette prescription ?")
        if ok != QMessageBox.StandardButton.Yes:
            return
        try:
            res = self.ctrl.delete_prescription(pid)
            if isinstance(res, dict) and res.get("error"):
                QMessageBox.warning(self, "Erreur", str(res.get("details", "Erreur inconnue")))
                return
            QMessageBox.information(self, "Succès", "Supprimé")
            self.refresh()
        except Exception as e:
            logger.exception("Erreur delete_prescription: %s", e)
            QMessageBox.warning(self, "Erreur", "Impossible de supprimer la prescription.")

    # Refresh logic: call controller with page/per_page/search/date range
    def refresh(self):
        try:
            page = max(1, int(self.page or 1))
            per_page = int(self.per_page or 20)
            q = self.search_edit.text().strip()
            # convert dates to iso strings for controller
            fd = self.from_d.date().toPyDate()
            td = self.to_d.date().toPyDate()

            params = {"page": page, "per_page": per_page}
            if q:
                params["search"] = q

            # pass date filters to controller (server-side)
            if fd:
                params["date_from"] = fd.isoformat()
            if td:
                params["date_to"] = td.isoformat()

            # call controller & normalize response
            raw = []
            try:
                raw = self.ctrl.list_prescriptions(**params)
                if isinstance(raw, dict) and raw.get("invalid"):
                    # créer un preview lisible
                    invalid_preview = []
                    for it in raw["invalid"]:
                        try:
                            preview = json.dumps(it, default=str)  # JSON safe
                        except Exception:
                            try:
                                preview = repr(it)[:200]            # fallback
                            except Exception:
                                preview = "<unprintable object>"
                        invalid_preview.append(preview)
                    logger.warning(
                        "Prescriptions invalides retournées par API: %s",
                        invalid_preview
                    )

            except Exception as e:
                logger.exception("Erreur appel list_prescriptions: %s", e)
                QMessageBox.warning(self, "Erreur réseau", f"Impossible de récupérer les prescriptions: {e}")
                raw = {"data": [], "total": 0}

            # extract
            if isinstance(raw, dict) and "data" in raw:
                results = raw.get("data") or []
                total = raw.get("total") or 0
            elif isinstance(raw, list):
                results = raw
                total = len(results)
            else:
                results = []
                total = 0

            # populate table rows
            self.table.setRowCount(0)
            today = date.today()
            for r in results:
                # support dict or ORM-like
                if isinstance(r, dict):
                    pres_id = r.get("prescription_id") or r.get("id")
                    patient = r.get("patient") or {}
                    patient_code = patient.get("code_patient") if isinstance(patient, dict) else ""
                    medication = r.get("medication") or ""
                    dosage = r.get("dosage") or ""
                    frequency = r.get("frequency") or ""
                    start = r.get("start_date") or ""
                    end = r.get("end_date") or ""
                else:
                    pres_id = getattr(r, "prescription_id", getattr(r, "id", None))
                    patient_obj = getattr(r, "patient", None)
                    patient_code = getattr(patient_obj, "code_patient", "") if patient_obj else ""
                    medication = getattr(r, "medication", "") or ""
                    dosage = getattr(r, "dosage", "") or ""
                    frequency = getattr(r, "frequency", "") or ""
                    start = getattr(r, "start_date", "")
                    end = getattr(r, "end_date", "")

                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(pres_id or "")))
                self.table.setItem(row, 1, QTableWidgetItem(str(patient_code or "")))
                self.table.setItem(row, 2, QTableWidgetItem(str(medication or "")))
                self.table.setItem(row, 3, QTableWidgetItem(str(dosage or "")))
                self.table.setItem(row, 4, QTableWidgetItem(str(frequency or "")))
                # normalize date display to YYYY-MM-DD
                s_display = ""
                if start:
                    try:
                        if isinstance(start, str):
                            s_display = start[:10]
                        else:
                            s_display = start.strftime("%Y-%m-%d")
                    except Exception:
                        s_display = str(start)
                e_display = ""
                if end:
                    try:
                        if isinstance(end, str):
                            e_display = end[:10]
                        else:
                            e_display = end.strftime("%Y-%m-%d")
                    except Exception:
                        e_display = str(end)

                self.table.setItem(row, 5, QTableWidgetItem(s_display))
                end_item = QTableWidgetItem(e_display)
                self.table.setItem(row, 6, end_item)

                # color-code end date cell depending on proximity
                try:
                    if end:
                        if isinstance(end, str):
                            end_date = datetime.fromisoformat(end[:10]).date()
                        else:
                            end_date = end if isinstance(end, date) else end.date()
                        days_left = (end_date - today).days
                        color = None
                        if days_left < 0:
                            color = QColor(200, 200, 200)  # past -> grey
                        elif days_left <= 3:
                            color = QColor(220, 50, 50)    # red
                        elif days_left <= 7:
                            color = QColor(255, 140, 0)   # orange
                        elif days_left <= 14:
                            color = QColor(255, 215, 0)   # yellow
                        else:
                            color = QColor(144, 238, 144) # green
                        if color:
                            end_item.setBackground(color)
                except Exception:
                    pass

            # pagination UI updates
            self.total = int(total or 0)
            total_pages = max(1, ceil(self.total / per_page))
            self.page_label.setText(f"Page {page} / {total_pages}")
            self.btn_prev.setEnabled(page > 1)
            self.btn_next.setEnabled(page < total_pages)

            # connect selection changed
            try:
                if not self._selection_connected:
                    sel_model = self.table.selectionModel()
                    if sel_model:
                        sel_model.selectionChanged.connect(lambda *_: self._on_selection_changed())
                        self._selection_connected = True
            except Exception:
                pass

            # default disable actions
            self._set_selection_enabled(False)

        except Exception as e:
            logger.exception("Erreur refresh prescriptions: %s", e)
            QMessageBox.warning(self, "Erreur", "Impossible de charger les prescriptions.")

    def _set_selection_enabled(self, enabled: bool):
        for btn in (self.edit_btn, self.del_btn):
            btn.setEnabled(enabled)

    def _on_selection_changed(self):
        ok = bool(self._get_selected_id())
        self._set_selection_enabled(ok)
