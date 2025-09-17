# view_pyqt6/appointment_views/appointments_book_viewqt.py
from typing import Any, Optional, Callable
from datetime import date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QMessageBox, QDateEdit, QFormLayout
)
from PyQt6.QtCore import QDate

from view_pyqt6.controller_resolver import ControllerResolver


class AppointmentsBookDialog(QDialog):
    def __init__(self, parent, controllers: Any, current_user: Any,
                 appointment: Optional[Any] = None, on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.setWindowTitle("Prendre un RDV" if appointment is None else "Éditer un RDV")
        self.setModal(True)
        self.resize(420, 260)

        self.resolver = ControllerResolver(controllers)
        self.appt_ctrl = self.resolver.appointment_controller()
        self.patient_ctrl = self.resolver.patient_controller()
        self.current_user = current_user
        self.appointment = appointment
        self.on_save = on_save

        self.patient_id = None

        self._build_ui()
        self._load_specialties()
        if self.appointment:
            self._prefill_fields()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        # code patient
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Ex: AH2-000818AQ")
        # use editingFinished OR focusOut; editingFinished triggers on Enter or losing focus
        self.code_edit.editingFinished.connect(self._on_code_focus_out)
        form.addRow("Code patient:", self.code_edit)

        # readonly info labels
        self.lbl_name = QLabel("Prénom Nom : –")
        self.lbl_phone = QLabel("Téléphone : –")
        form.addRow(self.lbl_name)
        form.addRow(self.lbl_phone)

        # specialty
        self.spec_combo = QComboBox()
        form.addRow("Spécialité:", self.spec_combo)

        # date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date:", self.date_edit)

        # time
        self.time_combo = QComboBox()
        times = [f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30)]
        self.time_combo.addItems(times)
        form.addRow("Heure:", self.time_combo)

        # reason
        self.reason_edit = QLineEdit()
        form.addRow("Raison:", self.reason_edit)

        layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Annuler")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self._on_save)
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def _load_specialties(self):
        """
        Charge les spécialités de façon robuste : essaie plusieurs noms (list_specialties, list_specialty, get_all_specialties...)
        """
        try:
            specs = []
            # try common method names on appointment controller (proxy)
            candidates = ["list_specialties", "list_specialty", "get_all_specialties", "get_all_speciality", "list_speciality"]
            for name in candidates:
                if hasattr(self.appt_ctrl, name):
                    try:
                        fn = getattr(self.appt_ctrl, name)
                        specs = fn() or []
                        break
                    except Exception as e:
                        print(f"[DEBUG] specialties call {name} failed: {e}")
                        continue
            # normalize structure (proxy may return {"data": [...]})
            if isinstance(specs, dict) and "data" in specs:
                specs = specs["data"]
            specs = [str(s) for s in specs] if specs else []
            self.spec_combo.clear()
            if not specs:
                self.spec_combo.addItem("")  # empty allowed
            else:
                self.spec_combo.addItems(specs)
        except Exception as e:
            print("[DEBUG] load_specialties error:", e)
            self.spec_combo.clear()
            self.spec_combo.addItem("")

    def _on_code_focus_out(self):
        code_raw = self.code_edit.text().strip()
        if not code_raw:
            self._set_patient(None, None, None)
            return

        code = code_raw.upper()
        if not code.startswith("AH2-"):
            code = f"AH2-{code}"
        self.code_edit.setText(code)

        patient = None
        try:
            pc = self.patient_ctrl
            print(f"[DEBUG] lookup patient code -> {code}")
            # 1) prefer dedicated find_by_code if present
            if hasattr(pc, "find_patient_by_code"):
                try:
                    res = pc.find_patient_by_code(code)
                    print("[DEBUG] patient_ctrl.find_patient_by_code ->", res)
                    if isinstance(res, dict) and not res.get("error"):
                        patient = res
                    elif isinstance(res, list) and res:
                        patient = res[0]
                except Exception as e:
                    print("[DEBUG] find_patient_by_code exception:", e)

            # 2) fallback: find_patient (may hit wrong endpoint sometimes) - still try
            if not patient and hasattr(pc, "find_patient"):
                try:
                    res = pc.find_patient(code)
                    print("[DEBUG] patient_ctrl.find_patient ->", res)
                    if isinstance(res, dict) and not res.get("error"):
                        patient = res
                except Exception as e:
                    print("[DEBUG] find_patient exception:", e)

            # 3) fallback reliable: list_patients(search=code)
            if not patient and hasattr(pc, "list_patients"):
                try:
                    res = pc.list_patients(page=1, per_page=5, search=code)
                    print("[DEBUG] patient_ctrl.list_patients ->", res)
                    if isinstance(res, list) and res:
                        patient = res[0]
                except Exception as e:
                    print("[DEBUG] list_patients exception:", e)

        except Exception as e:
            print("[DEBUG] patient lookup exception:", e)
            patient = None

        if not patient:
            self._set_patient(None, None, "Code introuvable")
            return

        # obtain PID, name and phone robustly
        if isinstance(patient, dict):
            pid = patient.get("patient_id") or patient.get("id")
            name = f"{patient.get('first_name','')} {patient.get('last_name','')}".strip()
            phone = patient.get("contact_phone") or patient.get("residence") or ""
        else:
            pid = getattr(patient, "patient_id", None) or getattr(patient, "id", None)
            name = f"{getattr(patient,'first_name','')} {getattr(patient,'last_name','')}".strip()
            phone = getattr(patient, "contact_phone", None) or getattr(patient, "residence", "") or ""

        self._set_patient(pid, name, phone)

    def _set_patient(self, pid, name, phone_or_msg=None):
        self.patient_id = pid
        if pid is None:
            if phone_or_msg:
                self.lbl_name.setText(phone_or_msg)
                self.lbl_phone.setText("")
            else:
                self.lbl_name.setText("Prénom Nom : –")
                self.lbl_phone.setText("Téléphone : –")
        else:
            self.lbl_name.setText(f"Prénom Nom : {name}")
            self.lbl_phone.setText(f"Téléphone : {phone_or_msg or '-'}")

    def _prefill_fields(self):
        appt = self.appointment
        try:
            def g(k):
                return appt.get(k) if isinstance(appt, dict) else getattr(appt, k, None)
            # patient nested object
            if g("patient"):
                patient = g("patient")
                code = patient.get("code_patient") if isinstance(patient, dict) else getattr(patient, "code_patient", None)
                if code:
                    self.code_edit.setText(code)
                    self._on_code_focus_out()
                else:
                    pid = g("patient_id") or getattr(appt, "patient_id", None)
                    if pid and hasattr(self.patient_ctrl, "get_patient"):
                        try:
                            p = self.patient_ctrl.get_patient(pid)
                            if p:
                                code = p.get("code_patient") if isinstance(p, dict) else getattr(p, "code_patient", None)
                                if code:
                                    self.code_edit.setText(code)
                                    self._on_code_focus_out()
                        except Exception:
                            pass
            spec = g("specialty") or ""
            idx = self.spec_combo.findText(str(spec))
            if idx >= 0:
                self.spec_combo.setCurrentIndex(idx)
            if g("appointment_date"):
                ad = g("appointment_date")
                if isinstance(ad, str):
                    d = QDate.fromString(ad[:10], "yyyy-MM-dd")
                    if d.isValid():
                        self.date_edit.setDate(d)
                else:
                    try:
                        self.date_edit.setDate(QDate(ad.year, ad.month, ad.day))
                    except Exception:
                        pass
            if g("appointment_time"):
                tt = g("appointment_time")
                tstr = tt.strftime("%H:%M") if hasattr(tt, "strftime") else str(tt)
                idx2 = self.time_combo.findText(tstr)
                if idx2 >= 0:
                    self.time_combo.setCurrentIndex(idx2)
            self.reason_edit.setText(g("reason") or "")
        except Exception as e:
            print("[DEBUG] prefill error:", e)

    def _on_save(self):
        if not self.patient_id:
            QMessageBox.warning(self, "Validation", "Veuillez saisir un code patient valide.")
            return

        data = {
            "patient_id": int(self.patient_id),
            "specialty": str(self.spec_combo.currentText()).strip() or None,
            "appointment_date": self.date_edit.date().toPyDate().isoformat(),
            "appointment_time": self.time_combo.currentText(),
            "reason": self.reason_edit.text().strip()
        }

        try:
            if self.appointment and (isinstance(self.appointment, dict) and self.appointment.get("appointment_id") or hasattr(self.appointment, "id")):
                appt_id = (self.appointment.get("appointment_id") if isinstance(self.appointment, dict) else getattr(self.appointment, "id"))
                if hasattr(self.appt_ctrl, "modify_appointment"):
                    res = self.appt_ctrl.modify_appointment(int(appt_id), data)
                elif hasattr(self.appt_ctrl, "update_appointment"):
                    res = self.appt_ctrl.update_appointment(int(appt_id), data)
                else:
                    # fallback: try create (not ideal)
                    res = self.appt_ctrl.create(data) if hasattr(self.appt_ctrl, "create") else None
            else:
                if hasattr(self.appt_ctrl, "book_appointment"):
                    res = self.appt_ctrl.book_appointment(data)
                elif hasattr(self.appt_ctrl, "create_appointment"):
                    res = self.appt_ctrl.create_appointment(data)
                else:
                    res = self.appt_ctrl.create(data) if hasattr(self.appt_ctrl, "create") else None

            if isinstance(res, dict) and res.get("error"):
                QMessageBox.critical(self, "Erreur", str(res.get("details") or res.get("error")))
                return

            QMessageBox.information(self, "Succès", "RDV enregistré.")
            if callable(self.on_save):
                try:
                    self.on_save()
                except Exception:
                    pass
            self.accept()
        except Exception as e:
            print("[DEBUG] save appointment error:", e)
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le RDV: {e}")

