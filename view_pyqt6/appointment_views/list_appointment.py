# view_pyqt6/appointment_views/list_appointment.py
from typing import Any, Optional, Dict, List
from datetime import date
from math import ceil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLineEdit, QLabel, QAbstractItemView, QMessageBox,
    QSpacerItem, QSizePolicy, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from view_pyqt6.controller_resolver import ControllerResolver
import logging

logger = logging.getLogger(__name__)


class AppointmentsListView(QWidget):
    """
    Vue PyQt6 conversion de la liste des RDV.
    - controllers : objet global (passé depuis dashboard)
    - on_book : callable()
    - on_edit : callable(appointment_id)  <-- important : on passe l'ID, pas un repo.obj
    """

    def __init__(self, parent, controllers: Any, *, on_book=None, on_edit=None, per_page=20, target_date: Optional[date] = None):
        super().__init__(parent)
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.on_book = on_book
        self.on_edit = on_edit
        self.per_page = per_page
        self.page = 1
        self.target_date = target_date

        # Flag pour éviter de brancher plusieurs fois le signal selectionChanged
        self._selection_connected = False

        self._build_ui()
        # initial load
        self.refresh(target_date=self.target_date)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # Control bar
        ctrl = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher code ou nom patient...")
        self.search_edit.returnPressed.connect(self._on_search)
        ctrl.addWidget(self.search_edit)

        self.btn_search = QPushButton("🔍")
        self.btn_search.clicked.connect(self._on_search)
        ctrl.addWidget(self.btn_search)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["Tous", "pending", "completed", "cancelled"])
        self.status_filter.currentIndexChanged.connect(lambda _: self.refresh())
        ctrl.addWidget(self.status_filter)

        self.date_filter = QComboBox()
        self.date_filter.addItems(["Toutes", "Aujourd'hui", "Personnalisée"])
        self.date_filter.currentIndexChanged.connect(self._on_date_filter_changed)
        ctrl.addWidget(self.date_filter)

        self.custom_date = QDateEdit()
        self.custom_date.setCalendarPopup(True)
        self.custom_date.setDisplayFormat("yyyy-MM-dd")
        self.custom_date.setDate(QDate.currentDate())
        self.custom_date.setVisible(False)
        ctrl.addWidget(self.custom_date)

        spacer = QSpacerItem(20, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        ctrl.addItem = lambda *a, **k: None  # noop (compat)
        ctrl.addWidget(QLabel())  # tiny spacer hack

        self.btn_book = QPushButton("Prendre RDV")
        self.btn_book.clicked.connect(lambda: self.on_book() if callable(self.on_book) else None)
        ctrl.addWidget(self.btn_book)

        root.addLayout(ctrl)

        # Table
        self.table = QTableWidget(0, 9, self)
        headers = ["ID", "Code Patient", "Patient", "Téléphone", "Médecin", "Date", "Heure", "Raison", "Statut"]
        self.table.setHorizontalHeaderLabels(headers)

        # CORRECTION PyQt6 : utiliser les enums correctement
        # Selection behavior & mode
        try:
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        except Exception:
            # fallback safe values if PyQt version difference
            pass

        # Edit triggers (désactiver édition)
        try:
            # PyQt6 exposes enum as EditTrigger with member NoEditTriggers
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        except Exception:
            # fallback : si signature plus ancienne / conversion diffère, ignore
            try:
                self.table.setEditTriggers(0)
            except Exception:
                pass

        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        root.addWidget(self.table, stretch=1)

        # Actions & pagination
        actions = QHBoxLayout()
        self.btn_accept = QPushButton("Accepter")
        self.btn_accept.clicked.connect(self.accept_selected)
        self.btn_accept.setEnabled(False)
        actions.addWidget(self.btn_accept)

        self.btn_reject = QPushButton("Refuser")
        self.btn_reject.clicked.connect(self.reject_selected)
        self.btn_reject.setEnabled(False)
        actions.addWidget(self.btn_reject)

        self.btn_complete = QPushButton("Compléter")
        self.btn_complete.clicked.connect(self.complete_selected)
        self.btn_complete.setEnabled(False)
        actions.addWidget(self.btn_complete)

        self.btn_edit = QPushButton("Éditer")
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_edit.setEnabled(False)
        actions.addWidget(self.btn_edit)

        actions.addStretch()

        self.btn_prev = QPushButton("← Précédent")
        self.btn_prev.clicked.connect(self.prev_page)
        actions.addWidget(self.btn_prev)

        self.page_label = QLabel("Page 1")
        actions.addWidget(self.page_label)

        self.btn_next = QPushButton("Suivant →")
        self.btn_next.clicked.connect(self.next_page)
        actions.addWidget(self.btn_next)

        root.addLayout(actions)

    # UI helpers
    def _on_date_filter_changed(self, index):
        mode = self.date_filter.currentText()
        self.custom_date.setVisible(mode == "Personnalisée")
        self.page = 1
        self.refresh()

    def _on_search(self):
        self.page = 1
        self.refresh()

    def _set_selection_enabled(self, enabled: bool):
        for btn in (self.btn_accept, self.btn_reject, self.btn_complete, self.btn_edit):
            btn.setEnabled(enabled)

    # Paging
    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        self.page += 1
        self.refresh()

    # Selection helpers
    def _get_selected_appointment_id(self):
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

    def _on_cell_double_clicked(self, row, col):
        appt_id = self._get_selected_appointment_id()
        if appt_id and callable(self.on_edit):
            try:
                self.on_edit(appt_id)
            except Exception as e:
                logger.exception("on_edit callback failed: %s", e)

    def edit_selected(self):
        appt_id = self._get_selected_appointment_id()
        if appt_id and callable(self.on_edit):
            self.on_edit(appt_id)

    # Actions
    def accept_selected(self):
        appt_id = self._get_selected_appointment_id()
        if not appt_id:
            return
        try:
            ctrl = self.resolver.appointment_controller()
            # prefer server dedicated endpoints if present on controller/gateway
            if hasattr(ctrl, "accept_appointment"):
                # controller/gateway implements accept_appointment(appointment_id)
                ctrl.accept_appointment(appt_id)
            elif hasattr(ctrl, "modify_appointment"):
                # modify_appointment expects (id, data: dict)
                ctrl.modify_appointment(appt_id, {"status": "pending"})
            else:
                raise RuntimeError("accept method not available")
            QMessageBox.information(self, "Succès", f"RDV #{appt_id} mis à jour.")
            self.refresh()
        except Exception as e:
            logger.exception("Impossible d'accepter: %s", e)
            QMessageBox.critical(self, "Erreur", f"Impossible d'accepter : {e}")

    def reject_selected(self):
        appt_id = self._get_selected_appointment_id()
        if not appt_id:
            return
        try:
            ctrl = self.resolver.appointment_controller()
            if hasattr(ctrl, "cancel_appointment"):
                ctrl.cancel_appointment(appt_id)
            elif hasattr(ctrl, "modify_appointment"):
                ctrl.modify_appointment(appt_id, {"status": "cancelled"})
            else:
                raise RuntimeError("cancel method not available")
            QMessageBox.information(self, "Succès", f"RDV #{appt_id} annulé.")
            self.refresh()
        except Exception as e:
            logger.exception("Impossible d'annuler: %s", e)
            QMessageBox.critical(self, "Erreur", f"Impossible d'annuler : {e}")

    def complete_selected(self):
        appt_id = self._get_selected_appointment_id()
        if not appt_id:
            return
        try:
            ctrl = self.resolver.appointment_controller()
            if hasattr(ctrl, "complete_appointment"):
                ctrl.complete_appointment(appt_id)
            elif hasattr(ctrl, "modify_appointment"):
                ctrl.modify_appointment(appt_id, {"status": "completed"})
            else:
                raise RuntimeError("complete method not available")
            QMessageBox.information(self, "Succès", f"RDV #{appt_id} complété.")
            self.refresh()
        except Exception as e:
            logger.exception("Impossible de compléter: %s", e)
            QMessageBox.critical(self, "Erreur", f"Impossible de compléter : {e}")

    # Helper to fetch appointment object (tries controller/gateway robustly)
    def _fetch_appointment_obj(self, appt_id: int) -> Optional[Any]:
        try:
            ctrl = self.resolver.appointment_controller()
            if hasattr(ctrl, "get_appointment"):
                try:
                    return ctrl.get_appointment(appt_id)
                except Exception:
                    # some proxies expect string ids or different signature; try other ways below
                    pass
            # fallback: controller.repo.get_by_id (local controller)
            if hasattr(ctrl, "repo") and hasattr(ctrl.repo, "get_by_id"):
                try:
                    return ctrl.repo.get_by_id(appt_id)
                except Exception:
                    pass
        except Exception:
            pass
        return None

    # Refresh main
    def refresh(self, target_date: Optional[date] = None):
        # resolve controllers
        try:
            appt_ctrl = self.resolver.appointment_controller()
        except Exception:
            appt_ctrl = None
        # patient_ctrl not used per-row to avoid many calls (performance)
        # try to use included patient data from appointment payloads
        try:
            patient_ctrl = self.resolver.patient_controller()
        except Exception:
            patient_ctrl = None

        page = max(1, int(self.page or 1))
        per_page = self.per_page
        params: Dict[str, Any] = {"page": page, "per_page": per_page}

        # status filter
        st = self.status_filter.currentText()
        status_filter = None if st == "Tous" else st

        # date filter
        if target_date:
            params["date_from"] = target_date.isoformat()
            params["date_to"] = target_date.isoformat()
        else:
            dfmode = self.date_filter.currentText()
            if dfmode == "Aujourd'hui":
                t = date.today()
                params["date_from"] = t.isoformat()
                params["date_to"] = t.isoformat()
            elif dfmode == "Personnalisée":
                dt = self.custom_date.date().toPyDate()
                params["date_from"] = dt.isoformat()
                params["date_to"] = dt.isoformat()

        # search -> try to resolve patient code -> patient_id (best-effort)
        search_term = self.search_edit.text().strip()
        if search_term:
            resolved_patient_id = None
            try:
                if patient_ctrl:
                    for try_name in ("find_patient_by_code", "find_by_code", "find_by_patient_code", "find_patient"):
                        if hasattr(patient_ctrl, try_name):
                            try:
                                r = getattr(patient_ctrl, try_name)(search_term)
                                if isinstance(r, dict) and r.get("patient_id"):
                                    resolved_patient_id = r["patient_id"]
                                    break
                                if isinstance(r, list) and r:
                                    if isinstance(r[0], dict) and r[0].get("patient_id"):
                                        resolved_patient_id = r[0]["patient_id"]
                                        break
                            except Exception:
                                pass
                    if not resolved_patient_id and hasattr(patient_ctrl, "list_patients"):
                        try:
                            lst = patient_ctrl.list_patients(page=1, per_page=5, search=search_term)
                            if isinstance(lst, list) and lst:
                                first = lst[0]
                                if isinstance(first, dict) and first.get("patient_id"):
                                    resolved_patient_id = first["patient_id"]
                        except Exception:
                            pass
            except Exception:
                pass

            if resolved_patient_id:
                params["patient_id"] = resolved_patient_id
            else:
                params["search"] = search_term

        # call appt controller
        raw_results = []
        try:
            if appt_ctrl and hasattr(appt_ctrl, "list_appointments"):
                raw_results = appt_ctrl.list_appointments(**params)
            elif appt_ctrl and hasattr(appt_ctrl, "repo") and hasattr(appt_ctrl.repo, "list_all"):
                # local repo fallback (non-paginated)
                raw_results = appt_ctrl.repo.list_all()
            else:
                raw_results = []
        except Exception as e:
            logger.exception("Erreur appel list_appointments: %s", e)
            QMessageBox.warning(self, "Erreur réseau", f"Impossible de récupérer la liste des RDV: {e}")
            raw_results = []

        # normalize results & extract total if present
        results: List[Any] = []
        total = None
        try:
            if isinstance(raw_results, dict) and "data" in raw_results:
                results = raw_results.get("data") or []
                total = raw_results.get("total")  # may be None
            elif isinstance(raw_results, list):
                results = raw_results
            elif raw_results:
                results = [raw_results]
            else:
                results = []
        except Exception:
            results = []

        # client-side status filter (only if server didn't filter)
        if status_filter:
            tmp = []
            for r in results:
                s = (r.get("status") if isinstance(r, dict) else getattr(r, "status", None))
                if s == status_filter:
                    tmp.append(r)
            results = tmp

        # populate table (avoid per-item remote patient calls => rely on included patient)
        self.table.setRowCount(0)
        for r in results:
            if isinstance(r, dict):
                appt_id = r.get("appointment_id") or r.get("id") or r.get("id_")
                try:
                    appt_id = int(appt_id) if appt_id is not None else None
                except Exception:
                    appt_id = None

                # Use patient payload when provided by API. Do NOT auto-fetch per-row (slow).
                patient = r.get("patient") or {}
                p_code = ""
                p_name = ""
                phone = ""
                if patient and isinstance(patient, dict):
                    p_code = patient.get("code_patient") or ""
                    p_name = " ".join(filter(None, [patient.get("first_name", ""), patient.get("last_name", "")])).strip()
                    phone = patient.get("contact_phone") or ""
                else:
                    # If API didn't provide patient object, try to use fallback names in appointment record
                    p_code = r.get("patient_code") or r.get("code_patient") or ""
                    p_name = r.get("patient_name") or r.get("patient_full_name") or ""
                    phone = r.get("contact_phone") or ""

                doctor = r.get("doctor") or {}
                doc_name = ""
                if isinstance(doctor, dict):
                    doc_name = doctor.get("full_name") or doctor.get("username") or ""
                appt_date = r.get("appointment_date") or r.get("date") or ""
                appt_time = r.get("appointment_time") or r.get("time") or ""
                reason = r.get("reason") or ""
                status = r.get("status") or ""
            else:
                # ORM-like object
                try:
                    appt_id = getattr(r, "id", None)
                except Exception:
                    appt_id = None
                patient = getattr(r, "patient", None)
                if patient:
                    p_code = getattr(patient, "code_patient", "") or ""
                    p_name = " ".join(filter(None, [getattr(patient, "first_name", ""), getattr(patient, "last_name", "")])).strip()
                    phone = getattr(patient, "contact_phone", "") or ""
                else:
                    p_code = ""
                    p_name = ""
                    phone = ""
                doctor = getattr(r, "doctor", None)
                doc_name = (getattr(doctor, "full_name", None) or getattr(doctor, "username", "")) if doctor else ""
                appt_date = getattr(r, "appointment_date", "")
                if hasattr(appt_date, "strftime"):
                    appt_date = appt_date.strftime("%Y-%m-%d")
                appt_time = getattr(r, "appointment_time", "")
                if hasattr(appt_time, "strftime"):
                    appt_time = appt_time.strftime("%H:%M")
                reason = getattr(r, "reason", "") or ""
                status = getattr(r, "status", "") or ""

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(appt_id or "")))
            self.table.setItem(row, 1, QTableWidgetItem(p_code))
            self.table.setItem(row, 2, QTableWidgetItem(p_name))
            self.table.setItem(row, 3, QTableWidgetItem(phone))
            self.table.setItem(row, 4, QTableWidgetItem(doc_name))
            self.table.setItem(row, 5, QTableWidgetItem(str(appt_date)))
            self.table.setItem(row, 6, QTableWidgetItem(str(appt_time)))
            self.table.setItem(row, 7, QTableWidgetItem(reason))
            self.table.setItem(row, 8, QTableWidgetItem(status))

        # update pagination label & buttons
        if total is None:
            # If server didn't provide total, try to infer (we show only current page number)
            self.total = 0
            self.page_label.setText(f"Page {page}")
            # enable next (optimistic) if we returned 'per_page' items
            self.btn_next.setEnabled(len(results) >= per_page)
        else:
            self.total = int(total or 0)
            total_pages = max(1, ceil(self.total / per_page))
            self.page_label.setText(f"Page {page} / {total_pages}")
            self.btn_next.setEnabled(page < total_pages)

        self.btn_prev.setEnabled(page > 1)

        # connect selection changed only once
        try:
            if not self._selection_connected:
                sel_model = self.table.selectionModel()
                if sel_model:
                    sel_model.selectionChanged.connect(lambda *_: self._on_selection_changed())
                    self._selection_connected = True
        except Exception:
            pass

        # default disable actions until selection
        self._set_selection_enabled(False)

    def _on_selection_changed(self):
        ok = bool(self._get_selected_appointment_id())
        self._set_selection_enabled(ok)
