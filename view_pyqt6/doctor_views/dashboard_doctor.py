# view_pyqt6/doctor_views/doctors_dashboard_view.py
import threading
import inspect
from datetime import datetime, date, timedelta
from functools import partial

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QFrame, QGridLayout, QMessageBox, QSpacerItem, QSizePolicy, QDialog, QScrollArea
)
from PyQt6.QtCore import QTimer, Qt, QDate

from view_pyqt6.controller_resolver import ControllerResolver

# Try imports of forms (may be None if not present)
try:
    from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView
except Exception:
    MedicalRecordFormView = None

try:
    from view_pyqt6.prescription_views.prescription_form_viewqt import PrescriptionFormView
except Exception:
    PrescriptionFormView = None

# modal expected in your project
try:
    from .medical_records_modal import MedicalRecordModal
except Exception:
    MedicalRecordModal = None


# small UI styles to improve selection/hover/press feedback
TREE_STYLE = """
QTreeWidget {
    background: transparent;
    border-radius: 6px;
}
QTreeView::item {
    padding: 6px;
    border-radius: 4px;
}
QTreeView::item:hover {
    background: rgba(200,200,200,0.12);
}
QTreeView::item:selected {
    background: rgba(180, 200, 220, 0.18);
    color: inherit;
    font-weight: 600;
}
"""

BUTTON_STYLE = """
QPushButton {
    background-color: #2e7d32;
    color: white;
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 90px;
}
QPushButton:hover {
    background-color: #27632a;
}
QPushButton:pressed {
    background-color: #204e23;
    padding-top: 7px;
    padding-bottom: 5px;
}
"""


class DoctorsDashboardView(QWidget):
    """
    Dashboard médecin PyQt6, résilient aux différences de noms de méthodes entre controllers/gateway.
    """

    def __init__(self, parent, user, controllers, on_logout=None, on_start_consultation=None, on_open_record=None):
        super().__init__(parent)

        self.user = user
        self.controllers = controllers
        self.resolver = ControllerResolver(controllers)
        self.on_logout = on_logout
        self.on_start_consultation = on_start_consultation
        self.on_open_record = on_open_record

        # controllers (peuvent être None)
        try:
            self.appt_ctrl = self.resolver.appointment_controller()
        except Exception:
            self.appt_ctrl = None
        try:
            self.pat_ctrl = self.resolver.patient_controller()
        except Exception:
            self.pat_ctrl = None
        try:
            self.presc_ctrl = self.resolver.prescription_controller()
        except Exception:
            self.presc_ctrl = None
        try:
            self.medrec_ctrl = self.resolver.medical_record_controller()
        except Exception:
            self.medrec_ctrl = None
        try:
            self.lab_ctrl = self.resolver.lab_controller()
        except Exception:
            self.lab_ctrl = None

        # ui storage
        self.canvas = None
        self._appt_objects = []
        self._patient_map = {}

        # top-level scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(scroll_area)

        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setWidget(content_widget)

        # build UI
        self._build_header()
        main_layout.addWidget(self.header)
        self._build_kpis()
        main_layout.addWidget(self.kpi_frame)
        # build sessions area (contains graph now)
        self._build_sessions_area()
        main_layout.addWidget(self.sessions)

        # initial load
        self._refresh_all_async()

    # ---------------------------
    # Utilities
    # ---------------------------
    def _get_attr(self, obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _try_methods(self, obj, names, *args, **kwargs):
        """
        Essaye plusieurs noms de méthodes sur `obj`.
        Retourne la première valeur renvoyée avec succès ou None.
        Essaie plusieurs signatures (positional, kwargs, no-args).
        """
        if obj is None:
            return None
        for name in names:
            fn = getattr(obj, name, None)
            if not callable(fn):
                continue
            # Try direct call
            try:
                return fn(*args, **kwargs)
            except TypeError:
                # try kwargs-only
                try:
                    return fn(**kwargs)
                except TypeError:
                    # try building positional args from kwargs by matching signature
                    try:
                        sig = inspect.signature(fn)
                        pos_args = []
                        for p in sig.parameters.values():
                            if p.name in kwargs:
                                pos_args.append(kwargs[p.name])
                        if pos_args:
                            return fn(*pos_args)
                    except Exception:
                        pass
                    # try no-arg
                    try:
                        return fn()
                    except Exception:
                        pass
            except Exception:
                # method raised; ignore and try next
                continue
        return None

    # ---------------------------
    # Header & KPIs
    # ---------------------------
    def _build_header(self):
        self.header = QFrame(self)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 6, 8, 6)

        role_name = ""
        try:
            role_obj = self._get_attr(self.user, "application_role", None)
            role_name = (self._get_attr(role_obj, "role_name", "") or "").lower()
        except Exception:
            role_name = ""

        title_prefix = "M."
        if "med" in role_name:
            title_prefix = "Dr."
        elif "infirm" in role_name or "nurs" in role_name:
            title_prefix = "M./Mme"

        fullname = self._get_attr(self.user, "full_name", self._get_attr(self.user, "username", ""))
        title_text = f"Bienvenue {title_prefix} {fullname} — {role_name.title() if role_name else ''}"
        self.title_lbl = QLabel(title_text)
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.title_lbl)

        now = datetime.now().strftime("%A %d %B %Y %H:%M")
        self.date_lbl = QLabel(now)
        header_layout.addWidget(self.date_lbl)

        header_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if callable(self.on_logout):
            btn = QPushButton("Se déconnecter")
            btn.setStyleSheet(BUTTON_STYLE)
            btn.clicked.connect(self.on_logout)
            header_layout.addWidget(btn)

    def _build_kpis(self):
        self.kpi_frame = QFrame(self)
        kpi_layout = QGridLayout(self.kpi_frame)
        kpi_layout.setContentsMargins(8, 0, 8, 8)

        def make_card(title):
            f = QFrame()
            f.setFrameShape(QFrame.Shape.StyledPanel)
            fl = QVBoxLayout(f)
            fl.setContentsMargins(12, 8, 12, 0)
            lbl_title = QLabel(title)
            lbl_value = QLabel("—")
            lbl_value.setStyleSheet("font-size: 20px; font-weight: bold;")
            fl.addWidget(lbl_title)
            fl.addWidget(lbl_value)
            return f, lbl_value

        # top row (5)
        self.card1_frame, self.lbl_total_patients = make_card("Patients distincts (7j)")
        kpi_layout.addWidget(self.card1_frame, 0, 0)
        self.card2_frame, self.lbl_appts_today = make_card("RDV prévus aujourd'hui")
        kpi_layout.addWidget(self.card2_frame, 0, 1)
        self.card3_frame, self.lbl_completed = make_card("RDV complétés (auj.)")
        kpi_layout.addWidget(self.card3_frame, 0, 2)
        self.card4_frame, self.lbl_cancelled = make_card("RDV annulés (auj.)")
        kpi_layout.addWidget(self.card4_frame, 0, 3)
        self.card5_frame, self.lbl_pending = make_card("RDV en attente (auj.)")
        kpi_layout.addWidget(self.card5_frame, 0, 4)

        # bottom row (4)
        self.card6_frame, self.lbl_renewals = make_card("Ordonnances à renouveler (14j)")
        kpi_layout.addWidget(self.card6_frame, 1, 0)
        self.card7_frame, self.lbl_patients_registered = make_card("Patients enregistrés (auj.)")
        kpi_layout.addWidget(self.card7_frame, 1, 1)
        self.card8_frame, self.lbl_consultations_today = make_card("Consultations (auj.)")
        kpi_layout.addWidget(self.card8_frame, 1, 2)
        self.card9_frame, self.lbl_prescriptions_today = make_card("Prescriptions (auj.)")
        kpi_layout.addWidget(self.card9_frame, 1, 3)

        refresh_btn = QPushButton("Rafraîchir")
        refresh_btn.setStyleSheet(BUTTON_STYLE)
        refresh_btn.clicked.connect(self._refresh_all_async)
        kpi_layout.addWidget(refresh_btn, 1, 4)

    # ---------------------------
    # Sessions area
    # ---------------------------
    def _build_sessions_area(self):
        self.sessions = QFrame(self)
        sessions_layout = QGridLayout(self.sessions)
        sessions_layout.setContentsMargins(8, 0, 8, 8)
        sessions_layout.setColumnStretch(0, 1)
        sessions_layout.setColumnStretch(1, 1)
        sessions_layout.setRowStretch(0, 1)
        sessions_layout.setRowStretch(1, 1)

        # left: consultations RDV today
        self.consult_frame = QFrame(self.sessions)
        self.consult_frame.setMinimumHeight(300)
        sessions_layout.addWidget(self.consult_frame, 0, 0)
        self._build_consult_section(self.consult_frame)

        # right top: patients suivis
        self.patients_frame = QFrame(self.sessions)
        self.patients_frame.setMinimumHeight(300)
        sessions_layout.addWidget(self.patients_frame, 0, 1)
        self._build_patients_section(self.patients_frame)

        # bottom: two columns (left -> graph (7j), right -> all consultations)
        bottom_frame = QFrame(self.sessions)
        bottom_layout = QGridLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 6, 0, 0)
        bottom_layout.setColumnStretch(0, 1)
        bottom_layout.setColumnStretch(1, 1)
        bottom_layout.setColumnMinimumWidth(0, 400)
        bottom_layout.setColumnMinimumWidth(1, 400)
        sessions_layout.addWidget(bottom_frame, 1, 0, 1, 2)

        # left bottom: graph RDV(7j) (remplace l'ancien panneau Patients enregistrés)
        self.graph_frame = QFrame(bottom_frame)
        self.graph_frame.setMinimumHeight(300)
        self.graph_layout = QVBoxLayout(self.graph_frame)
        self.graph_layout.setContentsMargins(8, 0, 8, 8)
        lbl = QLabel("Graphique RDV (7j)")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.graph_layout.addWidget(lbl)
        self._draw_empty_chart()
        bottom_layout.addWidget(self.graph_frame, 0, 0)

        # right bottom: all consultations
        self.all_consults_frame = QFrame(bottom_frame)
        self.all_consults_layout = QVBoxLayout(self.all_consults_frame)
        bottom_layout.addWidget(self.all_consults_frame, 0, 1)
        self._build_all_consults_section()

    def _build_consult_section(self, parent):
        layout = QVBoxLayout(parent)
        lbl = QLabel("Mes consultations sur RDV - Aujourd'hui")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl)

        self.tree_appts = QTreeWidget()
        self.tree_appts.setColumnCount(5)
        self.tree_appts.setHeaderLabels(["Nom Patient", "Code Patient", "Motif", "Heure", "Status"])
        self.tree_appts.setColumnWidth(0, 150)
        self.tree_appts.setColumnWidth(1, 100)
        self.tree_appts.setColumnWidth(2, 200)
        self.tree_appts.setColumnWidth(3, 100)
        self.tree_appts.setColumnWidth(4, 100)
        self.tree_appts.setStyleSheet(TREE_STYLE)
        layout.addWidget(self.tree_appts)

        actions = QHBoxLayout()
        btn_start = QPushButton("Démarrer consultation")
        btn_start.setStyleSheet(BUTTON_STYLE)
        btn_start.clicked.connect(self._start_selected_consult)
        actions.addWidget(btn_start)
        btn_open = QPushButton("Ouvrir dossier patient")
        btn_open.setStyleSheet(BUTTON_STYLE)
        btn_open.clicked.connect(self._open_selected_patient_from_appt)
        actions.addWidget(btn_open)
        actions.addStretch()
        btn_refresh = QPushButton("Rafraîchir")
        btn_refresh.setStyleSheet(BUTTON_STYLE)
        btn_refresh.clicked.connect(self._refresh_consultations_async)
        actions.addWidget(btn_refresh)
        layout.addLayout(actions)

    def _build_patients_section(self, parent):
        layout = QVBoxLayout(parent)
        lbl = QLabel("Mes patients suivis")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl)

        self.tree_patients = QTreeWidget()
        self.tree_patients.setColumnCount(3)
        self.tree_patients.setHeaderLabels(["Nom", "Code Patient", "ID"])
        self.tree_patients.setColumnWidth(0, 150)
        self.tree_patients.setColumnWidth(1, 100)
        self.tree_patients.setColumnHidden(2, True)
        self.tree_patients.setStyleSheet(TREE_STYLE)
        layout.addWidget(self.tree_patients)

        # action buttons: Ouvrir / Nouvelle consultation / Nouvelle prescription
        btn_row = QHBoxLayout()
        btn_open = QPushButton("Ouvrir dossier sélectionné")
        btn_open.setStyleSheet(BUTTON_STYLE)
        btn_open.clicked.connect(self._open_selected_patient)
        btn_row.addWidget(btn_open)

        btn_new_consult = QPushButton("Nouvelle consultation")
        btn_new_consult.setStyleSheet(BUTTON_STYLE)
        btn_new_consult.clicked.connect(self._new_consultation_for_selected_patient)
        btn_row.addWidget(btn_new_consult)

        btn_new_presc = QPushButton("Nouvelle prescription")
        btn_new_presc.setStyleSheet(BUTTON_STYLE)
        btn_new_presc.clicked.connect(self._new_prescription_for_selected_patient)
        btn_row.addWidget(btn_new_presc)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _build_all_consults_section(self):
        lbl = QLabel("Préconsultations - Aujourd'hui")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.all_consults_layout.addWidget(lbl)

        self.tree_consults = QTreeWidget()
        self.tree_consults.setColumnCount(5)
        self.tree_consults.setHeaderLabels(["Patient", "Motif", "Date", "Patient ID", "Record ID"])
        self.tree_consults.setColumnWidth(0, 150)
        self.tree_consults.setColumnWidth(1, 200)
        self.tree_consults.setColumnWidth(2, 100)
        self.tree_consults.setColumnHidden(3, True)
        self.tree_consults.setColumnHidden(4, True)
        self.tree_consults.setMinimumHeight(300)
        self.tree_consults.setStyleSheet(TREE_STYLE)
        self.all_consults_layout.addWidget(self.tree_consults)

        actions = QHBoxLayout()
        btn_open = QPushButton("Ouvrir dossier")
        btn_open.setStyleSheet(BUTTON_STYLE)
        btn_open.clicked.connect(self._open_selected_consultation)
        actions.addWidget(btn_open)
        btn_complete = QPushButton("Compléter consultation")
        btn_complete.setStyleSheet(BUTTON_STYLE)
        btn_complete.clicked.connect(self._complete_consultation)
        actions.addWidget(btn_complete)
        actions.addStretch()
        btn_refresh = QPushButton("Rafraîchir")
        btn_refresh.setStyleSheet(BUTTON_STYLE)
        btn_refresh.clicked.connect(self._refresh_all_consultations_async)
        actions.addWidget(btn_refresh)
        self.all_consults_layout.addLayout(actions)

    def _draw_empty_chart(self):
        if self.canvas:
            try:
                self.canvas.setParent(None)
                self.canvas.deleteLater()
            except Exception:
                pass
        fig = Figure(figsize=(5, 4))
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Chargement...", ha="center", va="center")
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas = FigureCanvas(fig)
        self.graph_layout.addWidget(self.canvas)

    # ---------------------------
    # Async loaders
    # ---------------------------
    def _refresh_all_async(self):
        threading.Thread(target=self._refresh_all_worker, daemon=True).start()

    def _refresh_all_worker(self):
        today = date.today()
        week_start = today - timedelta(days=6)

        try:
            # -- appointments week -> distinct patients
            week_appts_resp = self._try_methods(self.appt_ctrl, ("list_appointments", "list", "get_appointments_by_day"),
                                               page=1, per_page=1000, date_from=week_start.isoformat(), date_to=today.isoformat())
            week_appts = week_appts_resp.get('data', []) if isinstance(week_appts_resp, dict) else (week_appts_resp or [])
            distinct_pids = {self._get_attr(a, 'patient_id') for a in week_appts if self._get_attr(a, 'patient_id')}
            total_patients = len(distinct_pids)

            # -- today's appointments (for KPIs & lists)
            today_appts_resp = self._try_methods(self.appt_ctrl, ("list_appointments", "list", "get_by_day", "get_appointments_by_day"),
                                                page=1, per_page=1000, date_from=today.isoformat(), date_to=today.isoformat())
            today_appts = today_appts_resp.get('data', []) if isinstance(today_appts_resp, dict) else (today_appts_resp or [])
            appts_today = len(today_appts)

            # breakdown statuses
            status_break = {'completed': 0, 'cancelled': 0, 'pending': 0}
            for a in today_appts:
                st = str(self._get_attr(a, 'status', '') or '').lower()
                if st in status_break:
                    status_break[st] += 1
            completed = status_break['completed']
            cancelled = status_break['cancelled']
            pending = status_break['pending']

            # renewals (try multiple method names)
            renewals = self._try_methods(self.presc_ctrl, ("renewals_for_doctor", "get_renewals_for_doctor", "renewals"), within_days=14) or []

            # patients registered today (gateway/controller might expose get_registered_patients_count or get_patients_registered_on)
            reg = self._try_methods(self.pat_ctrl, ("get_registered_patients_count", "get_patients_registered_on"), period="day") or {'count': 0}
            if isinstance(reg, dict):
                patients_registered = reg.get("count", 0)
            elif isinstance(reg, int):
                patients_registered = reg
            else:
                patients_registered = 0

            # consultations & prescriptions counts
            consultations_resp = self._try_methods(self.medrec_ctrl, ("count_consultations", "count_records_for_doctor"), period="day") or {'count': 0}
            if isinstance(consultations_resp, dict):
                consultations_today = consultations_resp.get("count", 0)
            else:
                consultations_today = consultations_resp or 0

            prescriptions_resp = self._try_methods(self.presc_ctrl, ("get_prescriptions_count", "prescriptions_count"), period="day") or {'count': 0}
            if isinstance(prescriptions_resp, dict):
                prescriptions_today = prescriptions_resp.get("count", 0)
            else:
                prescriptions_today = prescriptions_resp or 0

            # recent medical records
            recent_results = []
            recs = self._try_methods(self.medrec_ctrl, ("list_medical_records", "list_records", "recent_records"), page=1, per_page=10) or []
            if isinstance(recs, dict):
                recs = recs.get('data', []) or []
            for r in recs:
                recent_results.append(f"{self._get_attr(r,'code_patient','')} — {self._get_attr(r,'diagnosis','')}")

            # timeseries: try multiple names
            timeseries = self._try_methods(self.appt_ctrl, ("appointments_time_series", "get_appointments_time_series", "appointments_per_day_for_doctor"),
                                          week_start, today) or []

        except Exception as e:
            QTimer.singleShot(0, partial(QMessageBox.critical, self, "Erreur KPI", f"Impossible de charger les KPI: {e}"))
            return

        # update UI on main thread
        QTimer.singleShot(0, partial(self._update_kpis_ui,
                                     total_patients, appts_today, completed, cancelled, pending,
                                     renewals, patients_registered, consultations_today,
                                     prescriptions_today, recent_results, timeseries))

        # refresh sub-lists (no more "new patients" panel)
        self._refresh_consultations_async()
        self._refresh_patients_async()
        self._refresh_all_consultations_async()

    def _update_kpis_ui(self, total_patients, appts_today, completed, cancelled, pending,
                       renewals, patients_registered, consultations_today,
                       prescriptions_today, recent_results, timeseries):
        try:
            self.lbl_total_patients.setText(str(total_patients))
            self.lbl_appts_today.setText(str(appts_today))
            self.lbl_completed.setText(str(completed))
            self.lbl_cancelled.setText(str(cancelled))
            self.lbl_pending.setText(str(pending))
            self.lbl_renewals.setText(str(len(renewals or [])))
            self.lbl_patients_registered.setText(str(patients_registered))
            self.lbl_consultations_today.setText(str(consultations_today))
            self.lbl_prescriptions_today.setText(str(prescriptions_today))
            # chart
            self._draw_timeseries_chart(timeseries)
        except Exception as e:
            print(" update_kpi exception:", e)
            #print(f"DEBUG: _update_kpis_ui exception: {e}")
            try:
                QMessageBox.critical(self, "Erreur UI", f"Erreur mise à jour KPI: {e}")
            except Exception:
                pass

    # ---------------------------
    # Consultations (today)
    # ---------------------------
    def _refresh_consultations_async(self):
        threading.Thread(target=self._refresh_consultations_worker, daemon=True).start()

    def _refresh_consultations_worker(self):
        today = date.today()
        appts = []
        try:
            appts_resp = self._try_methods(self.appt_ctrl, ("list_appointments", "get_by_day", "get_appointments_by_day"),
                                          page=1, per_page=1000, date_from=today.isoformat(), date_to=today.isoformat()) or []
            if isinstance(appts_resp, dict):
                appts = appts_resp.get('data', []) or []
            else:
                appts = appts_resp or []
        except Exception as e:
            QTimer.singleShot(0, partial(QMessageBox.critical, self, "Erreur RDV", f"Impossible de charger RDV: {e}"))
            return

        QTimer.singleShot(0, partial(self._populate_appointments_list, appts))

    def _populate_appointments_list(self, appts):
        self.tree_appts.clear()
        self._appt_objects = []
        for a in (appts or []):
            try:
                patient = self._get_attr(a, "patient", None)
                code = ''
                name = ''
                if patient:
                    code = self._get_attr(patient, "code_patient", '')
                    name = f"{self._get_attr(patient, 'first_name', '')} {self._get_attr(patient, 'last_name', '')}".strip()
                else:
                    pid = self._get_attr(a, "patient_id", None)
                    if pid and self.pat_ctrl:
                        p = self._try_methods(self.pat_ctrl, ("get_patient", "find_patient"), pid) or {}
                        code = self._get_attr(p, "code_patient", '')
                        name = f"{self._get_attr(p, 'first_name', '')} {self._get_attr(p, 'last_name', '')}".strip()

                motif = self._get_attr(a, 'reason', '') or ''
                heure = self._get_attr(a, 'appointment_time', '') or ''
                if hasattr(heure, "strftime"):
                    try:
                        heure = heure.strftime("%H:%M")
                    except Exception:
                        heure = str(heure)
                status = self._get_attr(a, 'status', '') or ''
            except Exception:
                name = "Unknown"
                code = ""
                motif = ""
                heure = ""
                status = ""

            item = QTreeWidgetItem([name, code, motif, str(heure), status])
            item.setData(0, Qt.ItemDataRole.UserRole, a)
            self.tree_appts.addTopLevelItem(item)
            self._appt_objects.append(a)

    # ---------------------------
    # Patients list (unique patients from today's appts)
    # ---------------------------
    def _refresh_patients_async(self):
        threading.Thread(target=self._refresh_patients_worker, daemon=True).start()

    def _refresh_patients_worker(self):
        patients = []
        try:
            today = date.today()
            appts_resp = self._try_methods(self.appt_ctrl, ("list_appointments", "get_by_day"), page=1, per_page=1000, date_from=today.isoformat(), date_to=today.isoformat())
            appts = appts_resp.get('data', []) if isinstance(appts_resp, dict) else (appts_resp or [])
            seen = {}
            for a in appts:
                pid = self._get_attr(a, "patient_id", None)
                if not pid or pid in seen:
                    continue
                seen[pid] = True
                p = self._get_attr(a, "patient", None)
                if not p:
                    p = self._try_methods(self.pat_ctrl, ("get_patient", "find_patient"), pid) or {}
                code = self._get_attr(p, "code_patient", '')
                name = f"{self._get_attr(p, 'first_name', '')} {self._get_attr(p, 'last_name', '')}".strip()
                patients.append((name, code, pid))
        except Exception:
            patients = []

        QTimer.singleShot(0, partial(self._populate_patients_list, patients))

    def _populate_patients_list(self, patients):
        self.tree_patients.clear()
        self._patient_map = {}
        for name, code, pid in (patients or []):
            item = QTreeWidgetItem([name, code, str(pid)])
            self.tree_patients.addTopLevelItem(item)
            self._patient_map[name] = pid

    # ---------------------------
    # All consultations loader
    # ---------------------------
    def _refresh_all_consultations_async(self):
        threading.Thread(target=self._refresh_all_consultations_worker, daemon=True).start()

    def _refresh_all_consultations_worker(self):
        try:
            today = date.today()
            consultations = []
            consultations_resp = self._try_methods(self.medrec_ctrl, ("list_medical_records", "list_records"), date_from=today.isoformat(), date_to=today.isoformat()) or []
            if isinstance(consultations_resp, dict):
                consultations = consultations_resp.get('data', []) or []
            else:
                consultations = consultations_resp or []

            display = []
            for c in (consultations or []):
                try:
                    patient_id = self._get_attr(c, "patient_id", None)
                    patient_info = ""
                    if patient_id:
                        p = self._try_methods(self.pat_ctrl, ("get_patient", "find_patient"), patient_id) or {}
                        patient_info = f"{self._get_attr(p,'code_patient','')} - {self._get_attr(p,'first_name','')} {self._get_attr(p,'last_name','')}".strip()
                    motif = self._get_attr(c, "motif_code", "Non spécifié")
                    consult_date = self._get_attr(c, "consultation_date", None)
                    if isinstance(consult_date, str):
                        try:
                            consult_date = datetime.fromisoformat(consult_date)
                        except Exception:
                            consult_date = None
                    date_str = consult_date.strftime("%Y-%m-%d %H:%M") if consult_date else "Date inconnue"
                    record_id = self._get_attr(c, "record_id", None)
                    display.append((patient_info, motif, date_str, patient_id, record_id))
                except Exception:
                    continue
        except Exception as e:
            QTimer.singleShot(0, partial(QMessageBox.critical, self, "Erreur Consultations", f"Impossible de charger les consultations: {e}"))
            return

        QTimer.singleShot(0, partial(self._populate_all_consults_list, display))

    def _populate_all_consults_list(self, display):
        self.tree_consults.clear()
        for patient, motif, date_str, patient_id, record_id in (display or []):
            item = QTreeWidgetItem([patient, motif, date_str, str(patient_id), str(record_id)])
            self.tree_consults.addTopLevelItem(item)

    # ---------------------------
    # Actions (open / start / complete)
    # ---------------------------
    def _open_selected_patient_from_all(self):
        selected = self.tree_consults.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez une consultation.")
            return
        item = selected[0]
        patient_id = item.text(3)
        self._open_patient_records_modal(patient_id)

    def _open_patient_records_modal(self, patient_id):
        if callable(self.on_open_record):
            try:
                self.on_open_record(patient_id)
                return
            except Exception:
                pass

        medctrl = self.medrec_ctrl
        recs = None
        if medctrl:
            recs = self._try_methods(medctrl, ("list_records_for_patient", "list_records", "list_medical_records"), patient_id=patient_id, page=1, per_page=50) or None
            if isinstance(recs, dict):
                recs = recs.get('data', []) or []

        modal_cls = MedicalRecordModal
        if modal_cls is None:
            QMessageBox.information(self, "Ouverture dossier", f"Ouvrir dossier patient id={patient_id}")
            return

        modal = modal_cls(self, records=recs or [], medrec_ctrl=medctrl, patient_id=patient_id)
        try:
            modal.exec()
        except Exception:
            try:
                modal.show()
            except Exception:
                pass

    def _start_selected_consult(self):
        selected = self.tree_appts.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez un rendez-vous dans la liste.")
            return
        item = selected[0]
        appt = item.data(0, Qt.ItemDataRole.UserRole)

        if callable(self.on_start_consultation):
            try:
                self.on_start_consultation(appt)
                return
            except Exception:
                pass

        # try set status "in_progress" through many candidate method names
        try:
            appt_id = self._get_attr(appt, "id", None) or self._get_attr(appt, "appointment_id", None)
            if appt_id and self.appt_ctrl:
                tried = False
                for name in ("set_status", "set_appointment_status", "update_status", "update_appointment", "update", "change_status", "mark_in_progress"):
                    fn = getattr(self.appt_ctrl, name, None)
                    if callable(fn):
                        try:
                            try:
                                fn(appt_id, "in_progress")
                            except TypeError:
                                try:
                                    fn(appt_id, status="in_progress")
                                except TypeError:
                                    try:
                                        fn(appt_id, {"status": "in_progress"})
                                    except TypeError:
                                        fn(appt_id)
                            tried = True
                            break
                        except Exception:
                            continue
                if not tried and hasattr(self.appt_ctrl, "modify_appointment"):
                    try:
                        self.appt_ctrl.modify_appointment(appt_id, status="in_progress")
                    except Exception:
                        pass
        except Exception:
            pass

        pid = self._get_attr(appt, "patient_id", None) or (self._get_attr(appt, "patient", None) and self._get_attr(self._get_attr(appt, "patient", None), "patient_id", None))
        try:
            record_id = self._get_attr(appt, "record_id", None) or self._get_attr(appt, "medical_record_id", None)
            if record_id:
                self._open_medical_record_modal(record=appt, patient_id=pid, is_update=True)
            else:
                self._open_medical_record_modal(record=None, patient_id=pid, is_update=False)
        except Exception:
            self._open_medical_record_modal(record=None, patient_id=pid, is_update=False)

    def _open_selected_patient(self):
        selected = self.tree_patients.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez un patient.")
            return
        item = selected[0]
        pid = item.text(2)
        if not pid:
            QMessageBox.information(self, "Info", "Impossible de retrouver le patient sélectionné.")
            return
        if callable(self.on_open_record):
            try:
                self.on_open_record(pid)
                return
            except Exception:
                pass
        try:
            self._open_patient_records_modal(pid)
            return
        except Exception:
            pass
        QMessageBox.information(self, "Ouverture dossier", f"Ouvrir dossier patient id={pid}")

    def _open_selected_patient_from_appt(self):
        selected = self.tree_appts.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez un rendez-vous.")
            return
        item = selected[0]
        appt = item.data(0, Qt.ItemDataRole.UserRole)
        pid = self._get_attr(appt, "patient_id", None) or (self._get_attr(appt, "patient", None) and self._get_attr(self._get_attr(appt, "patient", None), "patient_id", None))
        if not pid:
            QMessageBox.information(self, "Info", "Impossible de retrouver le patient.")
            return
        self._open_patient_records_modal(pid)

    def _open_medical_record_modal(self, record=None, patient_id=None, is_update=False, appointment_id=None):
        if MedicalRecordFormView is None:
            QMessageBox.critical(self, "Erreur", "Formulaire dossier médical introuvable (import failed).")
            return

        rec_id = None
        if record:
            rec_id = self._get_attr(record, "record_id", None) or self._get_attr(record, "id", None)

        top = QDialog(self)
        top.setWindowTitle("Dossier médical")
        top.resize(900, 650)
        top.setModal(True)
        layout = QVBoxLayout(top)
        form = MedicalRecordFormView(top, self.controllers, self.user, record_id=rec_id)
        layout.addWidget(form)

        pid = patient_id or (self._get_attr(record, "patient_id", None) if record else None)
        if pid:
            patient = self._try_methods(self.pat_ctrl, ("get_patient", "find_patient"), pid) or {}
            code = self._get_attr(patient, "code_patient", "") or ""
            first = self._get_attr(patient, "first_name", "") or ""
            last = self._get_attr(patient, "last_name", "") or ""
            try:
                # set fields on the form if exist (tolerant)
                if hasattr(form, "patient_id_var"):
                    try:
                        form.patient_id_var.setText(str(pid))
                    except Exception:
                        try:
                            form.patient_id_var = str(pid)
                        except Exception:
                            pass
                if hasattr(form, "patient_code_var"):
                    try:
                        form.patient_code_var.setText(str(code))
                    except Exception:
                        try:
                            form.patient_code_var = str(code)
                        except Exception:
                            pass
                if hasattr(form, "patient_name_var"):
                    try:
                        form.patient_name_var.setText(f"{last} {first}".strip())
                    except Exception:
                        try:
                            form.patient_name_var = f"{last} {first}".strip()
                        except Exception:
                            pass
                # set date widget safely
                try:
                    if hasattr(form, "date_widget"):
                        # use current date to prefill
                        form.date_widget.setDate(QDate.currentDate())
                except Exception:
                    pass
            except Exception:
                pass

        if is_update and rec_id:
            try:
                form.record_id = rec_id
                if hasattr(form, "_load_record"):
                    form._load_record()
            except Exception:
                pass

        top.exec()

    def _open_selected_patient_from_new(self):
        # kept for backward compatibility but not used anymore in the UI
        selected = getattr(self, "tree_new_patients", None)
        if not selected:
            QMessageBox.information(self, "Info", "Section non disponible.")
            return

    def _open_selected_consultation(self):
        selected = self.tree_consults.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez une consultation.")
            return
        item = selected[0]
        patient_id = item.text(3)
        self._open_patient_records_modal(patient_id)

    def _complete_consultation(self):
        selected = self.tree_consults.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez une consultation.")
            return
        item = selected[0]
        record_id = item.text(4)
        record = self._try_methods(self.medrec_ctrl, ("get_medical_record", "get_record", "get"), record_id)
        if record:
            self._open_medical_record_modal(record, is_update=True)

    # ---------------------------
    # New actions for selected patient in tree_patients
    # ---------------------------
    def _new_consultation_for_selected_patient(self):
        selected = self.tree_patients.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez un patient.")
            return
        item = selected[0]
        patient_id = item.text(2)
        # open MR form for creation; reuse existing helper
        self._open_medical_record_modal(record=None, patient_id=patient_id, is_update=False)

    def _new_prescription_for_selected_patient(self):
        selected = self.tree_patients.selectedItems()
        if not selected:
            QMessageBox.information(self, "Info", "Sélectionnez un patient.")
            return
        item = selected[0]
        patient_id = item.text(2)

        # resolver helper
        if hasattr(self.resolver, "show_prescription_form"):
            try:
                self.resolver.show_prescription_form(patient_id, None)
                return
            except Exception:
                pass

        if PrescriptionFormView is None:
            # try calling on_open_record style prescription callback via resolver
            QMessageBox.critical(self, "Erreur", "Formulaire prescription introuvable (import failed).")
            return

        top = QDialog(self)
        top.setWindowTitle("Nouvelle prescription")
        top.resize(700, 520)
        top.setModal(True)
        layout = QVBoxLayout(top)
        form = PrescriptionFormView(top, self.controllers, self.user, prescription_id=None, patient_id=patient_id, medical_record_id=None)
        layout.addWidget(form)

        # try prefill code/name
        try:
            pat = self._try_methods(self.pat_ctrl, ("get_patient", "find_patient"), patient_id) or {}
            if pat:
                code = self._get_attr(pat, "code_patient", "")
                name = f"{self._get_attr(pat,'last_name','')} {self._get_attr(pat,'first_name','')}".strip()
                try:
                    form.patient_code_var.setText(code)
                except Exception:
                    pass
                try:
                    form.patient_name_var.setText(name)
                except Exception:
                    pass
        except Exception:
            pass

        top.exec()

    # ---------------------------
    # Charting
    # ---------------------------
    def _draw_timeseries_chart(self, timeseries):
        if self.canvas:
            try:
                self.canvas.setParent(None)
                self.canvas.deleteLater()
            except Exception:
                pass

        fig = Figure(figsize=(5, 4))
        ax = fig.add_subplot(111)
        if not timeseries:
            ax.text(0.5, 0.5, "Pas de données", ha="center", va="center")
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            labels = [str(d) for d, _ in timeseries]
            counts = [int(c) for _, c in timeseries]
            x = list(range(len(labels)))
            ax.plot(x, counts, marker="o")
            ax.set_title("RDV (période)")
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=30, ha="right")
            ax.set_ylabel("Nombre RDV")
        fig.tight_layout()
        self.canvas = FigureCanvas(fig)
        # ensure the graph layout exists
        try:
            self.graph_layout.addWidget(self.canvas)
        except Exception:
            # fallback: add to a temporary frame
            if hasattr(self, "graph_frame"):
                self.graph_frame.layout().addWidget(self.canvas)

    # ---------------------------
    @staticmethod
    def _get_week_range():
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    def closeEvent(self, event):
        if self.canvas:
            try:
                self.canvas.deleteLater()
            except Exception:
                pass
        super().closeEvent(event)
