# view_pyqt6/doctor_views/medical_records_modal.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QTextEdit, QPushButton,
    QSplitter, QTabWidget, QScrollArea, QMessageBox, QFormLayout, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime

# try to import MedicalRecordFormView if available
try:
    from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView
except Exception:
    MedicalRecordFormView = None


class MedicalRecordModal(QDialog):
    def __init__(self, parent=None, records=None, medrec_ctrl=None, patient_id=None, presc_ctrl=None, on_prescribe=None):
        super().__init__(parent)
        self.setWindowTitle(f"Dossiers médicaux - Patient {patient_id}")
        self.resize(1000, 700)
        self.setModal(True)

        # controllers / callbacks
        self.medrec_ctrl = medrec_ctrl
        self.presc_ctrl = presc_ctrl
        self.on_prescribe = on_prescribe

        # keep patient id
        self.patient_id = patient_id

        # local state
        self.current_record = None
        self._records = []

        # try to obtain controllers/current_user/patient controller from parent if present
        self._parent_controllers = getattr(parent, "controllers", None)
        self._parent_user = getattr(parent, "user", None)
        self._parent_pat_ctrl = getattr(parent, "pat_ctrl", None)

        # Fonts
        self.title_font = QFont("Arial", 16, QFont.Weight.Bold)
        self.label_font = QFont("Arial", 12, QFont.Weight.Bold)
        self.text_font = QFont("Arial", 12)

        # Build UI and load records (always filtered to this patient)
        self._build_ui()
        self._load_records(records)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(splitter)

        # Left (list)
        left_frame = QWidget()
        left_layout = QVBoxLayout(left_frame)
        title_label = QLabel("Historique des consultations")
        title_label.setFont(self.title_font)
        left_layout.addWidget(title_label)

        actions = QHBoxLayout()
        refresh_btn = QPushButton("Rafraîchir")
        refresh_btn.clicked.connect(self._refresh_records)
        actions.addWidget(refresh_btn)

        new_btn = QPushButton("Nouveau dossier")
        new_btn.clicked.connect(self._create_new_record)
        actions.addWidget(new_btn)

        actions.addStretch()
        left_layout.addLayout(actions)

        self.list_widget = QListWidget()
        # style the list so hover/selection sont visibles
        self.list_widget.setStyleSheet("""
            QListWidget {
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #f0f0f0;
            }
            QListWidget::item:selected {
                background: #e6f0ea;
                color: #0a402e;
                font-weight: 600;
            }
        """)
        self.list_widget.itemSelectionChanged.connect(self.on_select_record)
        left_layout.addWidget(self.list_widget)
        splitter.addWidget(left_frame)
        splitter.setStretchFactor(0, 1)

        # Right (details / edit)
        right_frame = QWidget()
        right_layout = QVBoxLayout(right_frame)

        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # View tab
        view_frame = QWidget()
        view_layout = QVBoxLayout(view_frame)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setFont(self.text_font)
        view_layout.addWidget(self.txt)
        self.tab_widget.addTab(view_frame, "Détails")

        # Edit tab (simple fields mirror used form - but for editing we open the full form)
        edit_frame = QScrollArea()
        edit_widget = QWidget()
        edit_layout = QFormLayout(edit_widget)
        edit_frame.setWidget(edit_widget)
        edit_frame.setWidgetResizable(True)

        diagnosis_label = QLabel("Diagnostic:")
        diagnosis_label.setFont(self.label_font)
        self.diagnosis_text = QTextEdit()
        self.diagnosis_text.setFont(self.text_font)
        self.diagnosis_text.setFixedHeight(100)
        edit_layout.addRow(diagnosis_label, self.diagnosis_text)

        notes_label = QLabel("Notes:")
        notes_label.setFont(self.label_font)
        self.notes_text = QTextEdit()
        self.notes_text.setFont(self.text_font)
        self.notes_text.setFixedHeight(150)
        edit_layout.addRow(notes_label, self.notes_text)

        buttons_layout = QHBoxLayout()
        update_btn = QPushButton("Mettre à jour")
        update_btn.clicked.connect(self.update_record)
        buttons_layout.addWidget(update_btn)

        prescribe_btn = QPushButton("Nouvelle prescription")
        prescribe_btn.clicked.connect(self.create_prescription)
        buttons_layout.addWidget(prescribe_btn)

        buttons_layout.addStretch()
        edit_layout.addRow(buttons_layout)

        self.tab_widget.addTab(edit_frame, "Modifier")

        # bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        right_layout.addLayout(bottom_layout)

        splitter.addWidget(right_frame)
        splitter.setStretchFactor(1, 3)

    # -------------------------
    # Loading & filtering records
    # -------------------------
    def _try_load_from_controller(self):
        """Robuste: tente plusieurs signatures puis renvoie toujours une liste (on filtrera ensuite)."""
        if not self.medrec_ctrl:
            return []

        candidates = [
            ("list_records_for_patient", (self.patient_id,), {}),
            ("list_records_for_patient", (), {"patient_id": self.patient_id, "page": 1, "per_page": 50}),
            ("list_medical_records", (), {"patient_id": self.patient_id, "page": 1, "per_page": 50}),
            ("list_records", (), {"patient_id": self.patient_id, "page": 1, "per_page": 50}),
            ("list_records", (), {"patient": self.patient_id, "page": 1, "per_page": 50}),
            ("get_records", (), {"patient_id": self.patient_id}),
            ("get_records_for_patient", (self.patient_id,), {}),
        ]
        for name, args, kwargs in candidates:
            fn = getattr(self.medrec_ctrl, name, None)
            if callable(fn):
                try:
                    res = fn(*args, **kwargs)
                    # standard paginated dict
                    if isinstance(res, dict) and "data" in res:
                        return list(res.get("data", []) or [])
                    if isinstance(res, list):
                        return res
                    # try iterable
                    try:
                        return list(res)
                    except Exception:
                        pass
                except Exception:
                    # ignore and try next alternative
                    continue
        return []

    def _load_records(self, records):
        """
        Charge la liste des dossiers et s'assure qu'on ne montre que ceux du patient courant.
        """
        try:
            if records:
                fetched = []
                # normalize: if dict with data etc.
                if isinstance(records, dict) and "data" in records:
                    fetched = records.get("data", []) or []
                elif isinstance(records, list):
                    fetched = records
                else:
                    try:
                        fetched = list(records)
                    except Exception:
                        fetched = [records]
            else:
                fetched = self._try_load_from_controller()
        except Exception as e:
            QMessageBox.critical(self, "Erreur chargement dossiers", f"{e}")
            fetched = []

        # ALWAYS filter to the current patient (defensive)
        try:
            filtered = [r for r in (fetched or []) if self._record_belongs_to_patient(r)]
        except Exception:
            filtered = []

        self._records = filtered or []

        # populate list widget
        self.list_widget.clear()
        if not self._records:
            self.list_widget.addItem("Aucun dossier pour ce patient.")
            self.current_record = None
            self.txt.clear()
            self.diagnosis_text.clear()
            self.notes_text.clear()
            return

        for r in self._records:
            label = self._rec_label(r)
            item = QListWidgetItem(label)
            self.list_widget.addItem(item)

        # preserve previous selection if possible (try select first)
        try:
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
        except Exception:
            pass

    def _record_belongs_to_patient(self, r):
        pid = None
        if isinstance(r, dict):
            pid = r.get("patient_id") or (r.get("patient") and r.get("patient").get("patient_id"))
        else:
            pid = getattr(r, "patient_id", None) or (getattr(r, "patient", None) and getattr(getattr(r, "patient", None), "patient_id", None))
        if pid is None:
            return False
        try:
            return str(pid) == str(self.patient_id)
        except Exception:
            return False

    def _rec_label(self, r):
        if isinstance(r, dict):
            date_str = r.get('consultation_date', '') or r.get('date', '')
        else:
            date_str = getattr(r, "consultation_date", "") or getattr(r, "date", "")
        if isinstance(date_str, datetime):
            date_str = date_str.strftime("%d/%m/%Y %H:%M")
        elif isinstance(date_str, str) and date_str:
            try:
                d = datetime.fromisoformat(date_str)
                date_str = d.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
        else:
            date_str = "Date inconnue"

        diag = r.get('diagnosis', '') if isinstance(r, dict) else getattr(r, "diagnosis", "") or getattr(r, "motif_code", "")
        patient_name = ""
        if isinstance(r, dict):
            patient_name = f"{r.get('first_name','')} {r.get('last_name','')}".strip()
        else:
            patient_name = f"{getattr(r,'first_name','')} {getattr(r,'last_name','')}".strip()

        return f"{date_str} — {diag} — {patient_name}"

    # -------------------------
    # Selection / display
    # -------------------------
    def on_select_record(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        index = self.list_widget.row(selected[0])
        if index < 0 or index >= len(self._records):
            return
        self.current_record = self._records[index]

        # Build a styled HTML summary: label bold + value; certain fields highlighted
        parts = []
        def get_field(r, key):
            if isinstance(r, dict):
                return r.get(key)
            return getattr(r, key, None)

        def format_line(label, value, highlight=False, unit=None):
            if value is None:
                return ""
            v = str(value)
            if unit:
                v = f"{v} {unit}"
            label_html = f"<b>{label}</b>"
            if highlight:
                return f"<div style='margin-bottom:6px;'>{label_html}: <span style='color:#0b6b44;font-weight:600'>{v}</span></div>"
            return f"<div style='margin-bottom:6px;'>{label_html}: <span>{v}</span></div>"

        # core fields
        record_id = get_field(self.current_record, "record_id")
        consult_date = get_field(self.current_record, "consultation_date")
        if isinstance(consult_date, str) and consult_date:
            try:
                consult_date = datetime.fromisoformat(consult_date)
            except Exception:
                pass
        if isinstance(consult_date, datetime):
            consult_date = consult_date.strftime("%d/%m/%Y %H:%M")

        parts.append(format_line("ID Dossier", record_id))
        parts.append(format_line("Date Consultation", consult_date))
        parts.append(format_line("Code Patient", get_field(self.current_record, "patient_code")))
        parts.append(format_line("ID Patient", get_field(self.current_record, "patient_id")))
        # patient name
        if isinstance(self.current_record, dict):
            pname = f"{self.current_record.get('first_name','')} {self.current_record.get('last_name','')}".strip()
        else:
            pname = f"{getattr(self.current_record,'first_name','')} {getattr(self.current_record,'last_name','')}".strip()
        parts.append(format_line("Nom Patient", pname))

        # Vital / measurements with highlight and units
        parts.append(format_line("Tension (BP)", get_field(self.current_record, "bp"), highlight=True))
        parts.append(format_line("Température", get_field(self.current_record, "temperature"), highlight=True, unit="°C"))
        parts.append(format_line("Poids", get_field(self.current_record, "weight"), highlight=True, unit="kg"))
        parts.append(format_line("Taille", get_field(self.current_record, "height"), highlight=True, unit="cm"))

        # other textual fields
        for label, key in [
            ("Motif", "motif_code"),
            ("Antécédents", "medical_history"),
            ("Allergies", "allergies"),
            ("Symptômes", "symptoms"),
            ("Diagnostic", "diagnosis"),
            ("Traitement", "treatment"),
            ("Gravité", "severity"),
            ("Notes", "notes")
        ]:
            parts.append(format_line(label, get_field(self.current_record, key)))

        html = "<div style='font-family:Segoe UI, Arial, sans-serif; font-size:12px;'>" + "".join(parts) + "</div>"
        # set HTML into text widget
        self.txt.setHtml(html)

        # Populate edit fields (simple)
        diagnosis = get_field(self.current_record, 'diagnosis') or ""
        notes = get_field(self.current_record, 'notes') or ""
        self.diagnosis_text.setPlainText(diagnosis)
        self.notes_text.setPlainText(notes)

        # switch to view tab
        self.tab_widget.setCurrentIndex(0)

    # -------------------------
    # Update (opens the same MR form used for creation if available)
    # -------------------------
    def update_record(self):
        if not self.current_record:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un dossier à modifier.")
            return

        # prefer to call controller.update_record if it exists and returns truthy,
        # but many projects simply use the MR form to perform the save.
        record_id = None
        if isinstance(self.current_record, dict):
            record_id = self.current_record.get("record_id") or self.current_record.get("id")
        else:
            record_id = getattr(self.current_record, "record_id", None) or getattr(self.current_record, "id", None)

        # If medrec_ctrl has update_record and it's safe to call directly (rare), use it.
        if record_id and self.medrec_ctrl and hasattr(self.medrec_ctrl, "update_record"):
            # build update payload from the small editor (diagnosis/notes) but prefer full-form UX
            new_diagnosis = self.diagnosis_text.toPlainText().strip()
            new_notes = self.notes_text.toPlainText().strip()
            try:
                res = self.medrec_ctrl.update_record(record_id, {"diagnosis": new_diagnosis, "notes": new_notes})
                # if controller returns truthy / dict, refresh
                self._load_and_notify_after_save(res)
                return
            except Exception:
                # fallback to opening form if direct update fails
                pass

        # Otherwise open the full MedicalRecordFormView if available (preferred)
        if MedicalRecordFormView is not None:
            dlg = QDialog(self)
            dlg.setWindowTitle("Éditer Dossier Médical")
            dlg.setModal(True)
            dlg.resize(900, 650)
            layout = QVBoxLayout(dlg)
            try:
                # The example you showed passes controllers + current_user + record_id + on_save
                controllers = self._parent_controllers
                current_user = self._parent_user
                # instantiate form with the same signature as your example if possible
                form = MedicalRecordFormView(parent=dlg, controllers=controllers, current_user=current_user, record_id=record_id, on_save=self._refresh_records)
                layout.addWidget(form)
                dlg.exec()
                # after form closed, refresh list (on_save should have performed actual save)
                self._refresh_records()
                return
            except Exception:
                # if form instantiation fails, fallback to simple message and continue
                try:
                    dlg.close()
                except Exception:
                    pass

        # Final fallback: ask user that the update path is not available
        QMessageBox.critical(self, "Erreur", "Impossible de mettre à jour le dossier: fonctionnalité d'édition non disponible.")

    def _load_and_notify_after_save(self, res):
        """
        Helper: called after medrec_ctrl.update_record attempted; refresh UI and inform user.
        Accepts boolean/dict/whatever returned by controller.
        """
        try:
            QMessageBox.information(self, "Succès", "Dossier médical mis à jour.")
        except Exception:
            pass
        # refresh local list and selection
        self._refresh_records()

    # -------------------------
    # Prescription creation
    # -------------------------
    def create_prescription(self):
        # if no current record, ask user
        if not self.current_record:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un dossier patient.")
            return

        # derive patient_id and medical_record_id robustly
        if isinstance(self.current_record, dict):
            patient_id = self.current_record.get('patient_id') or self.patient_id
            medical_record_id = self.current_record.get('record_id') or self.current_record.get('id')
        else:
            patient_id = getattr(self.current_record, 'patient_id', None) or self.patient_id
            medical_record_id = getattr(self.current_record, 'record_id', None) or getattr(self.current_record, 'id', None)

        if not patient_id:
            QMessageBox.critical(self, "Erreur", "Impossible de déterminer l'ID du patient.")
            return

        # Preferred call: on_prescribe(patient_id=..., medical_record_id=...)
        if callable(self.on_prescribe):
            try:
                # try keyword form first (matches example)
                self.on_prescribe(patient_id=patient_id, medical_record_id=medical_record_id)
                return
            except TypeError:
                try:
                    # fallback to positional
                    self.on_prescribe(patient_id, medical_record_id)
                    return
                except Exception:
                    pass
            except Exception:
                pass

        # controller-level helper
        if self.presc_ctrl:
            # try common names
            try_names = ("create_prescription_for_patient", "create_prescription", "prescribe", "new_prescription")
            for name in try_names:
                fn = getattr(self.presc_ctrl, name, None)
                if callable(fn):
                    try:
                        # try with keywords first
                        try:
                            fn(patient_id=patient_id, medical_record_id=medical_record_id)
                        except TypeError:
                            fn(patient_id, medical_record_id)
                        QMessageBox.information(self, "Info", "Prescription créée (via controller).")
                        return
                    except Exception:
                        continue

        # final fallback
        QMessageBox.information(self, "Info", "Fonctionnalité de prescription non disponible (ouvrir formulaire manuellement).")

    # -------------------------
    # Refresh / create record
    # -------------------------
    def _refresh_records(self):
        # reload from controller and keep the patient-only filter
        self._load_records(None)

    def _create_new_record(self):
        # Try to open the same MedicalRecordFormView used elsewhere, prefill patient fields if possible
        if MedicalRecordFormView is not None:
            dlg = QDialog(self)
            dlg.setWindowTitle("Nouveau dossier médical")
            dlg.setModal(True)
            dlg.resize(900, 650)
            layout = QVBoxLayout(dlg)
            try:
                controllers = self._parent_controllers
                current_user = self._parent_user
                form = MedicalRecordFormView(parent=dlg, controllers=controllers, current_user=current_user, record_id=None, on_save=self._refresh_records)
                layout.addWidget(form)
                # attempt to prefill some fields the form may expose
                try:
                    if hasattr(form, "patient_id_var"):
                        try:
                            form.patient_id_var.setText(str(self.patient_id))
                        except Exception:
                            try:
                                form.patient_id_var = str(self.patient_id)
                            except Exception:
                                pass
                    # try to fetch patient info for code/name
                    if self._parent_pat_ctrl:
                        getp = getattr(self._parent_pat_ctrl, "get_patient", None) or getattr(self._parent_pat_ctrl, "find_patient", None)
                        if callable(getp):
                            try:
                                p = getp(self.patient_id)
                            except Exception:
                                try:
                                    p = getp(id=self.patient_id)
                                except Exception:
                                    p = None
                            if p:
                                code = p.get("code_patient") if isinstance(p, dict) else getattr(p, "code_patient", "")
                                first = p.get("first_name","") if isinstance(p, dict) else getattr(p, "first_name","")
                                last = p.get("last_name","") if isinstance(p, dict) else getattr(p, "last_name","")
                                name = f"{last} {first}".strip()
                                try:
                                    if hasattr(form, "patient_code_var") and code:
                                        form.patient_code_var.setText(code)
                                except Exception:
                                    pass
                                try:
                                    if hasattr(form, "patient_name_var") and name:
                                        form.patient_name_var.setText(name)
                                except Exception:
                                    pass
                except Exception:
                    pass

                dlg.exec()
                # after creation, refresh
                self._refresh_records()
                return
            except Exception:
                try:
                    dlg.close()
                except Exception:
                    pass

        # fallback: try medrec_ctrl.create_record_for_patient
        if self.medrec_ctrl and hasattr(self.medrec_ctrl, "create_record_for_patient"):
            try:
                self.medrec_ctrl.create_record_for_patient(self.patient_id)
                QMessageBox.information(self, "Info", "Nouveau dossier créé (via controller).")
                self._refresh_records()
                return
            except Exception:
                pass

        QMessageBox.information(self, "Info", "Ouvrir formulaire création dossier (non disponible automatiquement).")
