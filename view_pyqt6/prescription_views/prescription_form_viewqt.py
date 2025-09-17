# view_pyqt6/prescription_views/prescription_form.py
from typing import Any, Dict, Optional, Callable
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QDateEdit, QMessageBox, QFormLayout, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QDate

from view_pyqt6.controller_resolver import ControllerResolver


class PrescriptionFormView(QWidget):
    """
    Formulaire PyQt6 pour création / édition de prescription.
    Signature:
      PrescriptionFormView(parent, controllers, current_user,
                           prescription_id=None, patient_id=None, medical_record_id=None, on_save=None)
    - controllers : objet global contenant gateway / controller / fallback_controller (utilisé par ControllerResolver)
    - on_save : callback facultatif appelé après création/édition réussie
    """

    def __init__(
        self,
        parent,
        controllers: Any,
        current_user: Any,
        prescription_id: Optional[int] = None,
        patient_id: Optional[int] = None,
        medical_record_id: Optional[int] = None,
        on_save: Optional[Callable] = None
    ):
        super().__init__(parent)
        self.resolver = ControllerResolver(controllers)
        # controller CRUD pour prescriptions
        self.controller = self.resolver.prescription_controller()
        self.current_user = current_user

        # instance state
        self.prescription_id = prescription_id
        self.patient_id = patient_id
        self.medical_record_id = medical_record_id
        self.on_save = on_save
        self.is_new = prescription_id is None

        # UI widgets (déclarés pour l'accès dans méthodes)
        self.code_edit: QLineEdit
        self.patient_name_label: QLabel
        self.medrec_edit: QLineEdit
        self.medication_edit: QLineEdit
        self.dosage_edit: QLineEdit
        self.frequency_edit: QLineEdit
        self.duration_edit: QLineEdit
        self.start_date: QDateEdit
        self.end_date: QDateEdit
        self.notes_text: QTextEdit

        # build UI
        self._build_ui()

        # load if editing
        if not self.is_new:
            self._load()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        title = QLabel("Prescription")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        main.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        # code patient
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Ex : AH2-00123")
        # lookup on finish editing
        self.code_edit.editingFinished.connect(self._on_code_focus_out)
        form.addRow("Code patient:", self.code_edit)

        # patient name display
        self.patient_name_label = QLabel("-")
        self.patient_name_label.setStyleSheet("color: gray;")
        form.addRow("Patient:", self.patient_name_label)

        # medical record id (optional)
        self.medrec_edit = QLineEdit()
        self.medrec_edit.setPlaceholderText("ID Dossier Médical (optionnel)")
        if self.medical_record_id:
            self.medrec_edit.setText(str(self.medical_record_id))
            self.medrec_edit.setEnabled(False)
        form.addRow("ID Dossier Méd.:", self.medrec_edit)

        # medication fields
        self.medication_edit = QLineEdit()
        self.medication_edit.setPlaceholderText("Ex: Paracétamol")
        form.addRow("Médicament*:", self.medication_edit)

        self.dosage_edit = QLineEdit()
        self.dosage_edit.setPlaceholderText("Ex: 500mg")
        form.addRow("Dosage*:", self.dosage_edit)

        self.frequency_edit = QLineEdit()
        self.frequency_edit.setPlaceholderText("Ex: 2 fois/jour")
        form.addRow("Fréquence*:", self.frequency_edit)

        self.duration_edit = QLineEdit()
        self.duration_edit.setPlaceholderText("Ex: 5 jours")
        form.addRow("Durée:", self.duration_edit)

        # dates
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate())
        form.addRow("Date début*:", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        form.addRow("Date fin:", self.end_date)

        # notes
        self.notes_text = QTextEdit()
        self.notes_text.setMaximumHeight(120)
        self.notes_text.setPlaceholderText("Notes (posologie, remarques...)")
        form.addRow("Notes :", self.notes_text)

        main.addLayout(form)

        # Spacer
        main.addItem(QSpacerItem(20, 8))

        # actions (aligned right)
        actions = QHBoxLayout()
        actions.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self._cancel)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        actions.addWidget(cancel_btn)

        save_label = "Enregistrer" if self.is_new else "Modifier"
        save_btn = QPushButton(save_label)
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("font-weight:600; padding:6px 12px;")
        actions.addWidget(save_btn)

        main.addLayout(actions)

        # cosmetic: small guidance under form
        hint = QLabel("Les champs marqués * sont obligatoires.")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main.addWidget(hint)

        # initial visual reset
        self._clear_validation_styles()

    # ---------------- Patient lookup / focus ----------------
    def _on_code_focus_out(self) -> None:
        """
        Lookup patient when user finishes editing the code field.
        This implementation:
         - tries patient_controller.find_by_patient_presc(...) if available
         - falls back to gateway.find_patient_for_prescription(...)
         - falls back to list_patients(search=...)
         - normalizes different return shapes
        """
        code = self.code_edit.text().strip()
        print(f"[DEBUG] _on_code_focus_out: code saisi -> '{code}'")

        if not code:
            # reset
            self.patient_id = None
            self.patient_name_label.setText("-")
            print("[DEBUG] code vide -> patient reset")
            return

        patient = None
        try:
            # resolver -> patient controller (can be ApiControllerProxy)
            patient_ctrl = None
            try:
                patient_ctrl = self.resolver.patient_controller()
                print(f"[DEBUG] patient_controller obtenu: {type(patient_ctrl)}")
            except Exception as e:
                print(f"[DEBUG] impossible obtenir patient_controller: {e}")
                patient_ctrl = None

            # 1) Preferred: patient_ctrl.find_by_patient_presc(q)
            if patient_ctrl and hasattr(patient_ctrl, "find_by_patient_presc"):
                try:
                    print(f"[DEBUG] tentative patient_ctrl.find_by_patient_presc('{code}')")
                    res = patient_ctrl.find_by_patient_presc(code)
                    print(f"[DEBUG] find_by_patient_presc -> {res}")
                    if isinstance(res, dict):
                        # Could be {"error":...} from gateway proxy; treat it
                        if res.get("error"):
                            print(f"[DEBUG] backend returned error: {res}")
                        else:
                            patient = res
                    else:
                        patient = res
                except Exception as e:
                    print(f"[DEBUG] erreur find_by_patient_presc: {e}")

            # 2) Gateway-level call: resolvers/gateway may expose method find_patient_for_prescription
            if not patient:
                gw = None
                try:
                    # attempt to get gateway from controllers object via resolver
                    gw = getattr(self.resolver, "gateway", None) or getattr(self.resolver, "controllers", None) and getattr(self.resolver.controllers, "gateway", None)
                except Exception:
                    gw = None

                # Common place: controller proxy might expose gateway as attribute
                if not gw and patient_ctrl and hasattr(patient_ctrl, "gateway"):
                    gw = getattr(patient_ctrl, "gateway", None)

                if gw and hasattr(gw, "find_patient_for_prescription"):
                    try:
                        print(f"[DEBUG] tentative gateway.find_patient_for_prescription('{code}')")
                        res = gw.find_patient_for_prescription(code)
                        print(f"[DEBUG] gateway.find_patient_for_prescription -> {res}")
                        if isinstance(res, dict) and res.get("error"):
                            print(f"[DEBUG] gateway returned error: {res}")
                        else:
                            # response may be dict with patient or list/paginated -> normalize
                            if isinstance(res, list):
                                patient = res[0] if res else None
                            elif isinstance(res, dict) and "data" in res:
                                patient = res["data"][0] if res.get("data") else None
                            else:
                                patient = res
                    except Exception as e:
                        print(f"[DEBUG] erreur gateway find_patient_for_prescription: {e}")

            # 3) fallback: try patient_ctrl.list_patients(search=code) if available
            if not patient and patient_ctrl and hasattr(patient_ctrl, "list_patients"):
                try:
                    print(f"[DEBUG] tentative list_patients(search={code})")
                    res = patient_ctrl.list_patients(page=1, per_page=5, search=code)
                    print(f"[DEBUG] list_patients -> {res}")
                    if isinstance(res, list):
                        patient = res[0] if res else None
                    elif isinstance(res, dict) and "data" in res:
                        patient = res["data"][0] if res.get("data") else None
                except Exception as e:
                    print(f"[DEBUG] erreur list_patients: {e}")

            # 4) last fallback: try controller.find_patient (some proxies have this)
            if not patient and hasattr(self.controller, "find_patient"):
                try:
                    print(f"[DEBUG] tentative controller.find_patient({code})")
                    res = self.controller.find_patient(code)
                    print(f"[DEBUG] controller.find_patient -> {res}")
                    if isinstance(res, list):
                        patient = res[0] if res else None
                    elif isinstance(res, dict) and "data" in res:
                        patient = res["data"][0] if res.get("data") else None
                    else:
                        patient = res
                except Exception as e:
                    print(f"[DEBUG] erreur controller.find_patient: {e}")

        except Exception as e:
            print(f"[DEBUG] Erreur lookup patient: {e}")
            patient = None

        if not patient:
            print("[DEBUG] patient non trouvé")
            self.patient_id = None
            self.patient_name_label.setText("Code introuvable")
            return

        # Normalize patient if dict or object
        if isinstance(patient, dict):
            pid = patient.get("patient_id") or patient.get("id") or patient.get("patientId")
            name = f"{patient.get('last_name','')} {patient.get('first_name','')}".strip()
        else:
            pid = getattr(patient, "patient_id", None) or getattr(patient, "id", None)
            name = f"{getattr(patient, 'last_name','')} {getattr(patient, 'first_name','')}".strip()

        print(f"[DEBUG] patient trouvé -> id: {pid}, name: {name}")
        self.patient_id = pid
        self.patient_name_label.setText(name or "-")






    def _set_patient(self, patient_id: Optional[int], name: str) -> None:
        """Set patient id and UI feedback (name label + input style)."""
        self.patient_id = patient_id
        if patient_id:
            self.patient_name_label.setText(name or "-")
            self.code_edit.setStyleSheet("")  # clear error style
        else:
            self.patient_name_label.setText(name or "-")
            # highlight not-found
            if name:
                self.code_edit.setStyleSheet("border: 1px solid #e74c3c;")
            else:
                self.code_edit.setStyleSheet("")


    # ---------------- Validation helpers ----------------
    def _clear_validation_styles(self) -> None:
        widgets = [
            self.code_edit, self.medrec_edit, self.medication_edit,
            self.dosage_edit, self.frequency_edit, self.duration_edit,
            self.start_date, self.end_date, self.notes_text
        ]
        for w in widgets:
            try:
                w.setStyleSheet("")
            except Exception:
                pass

    def _mark_invalid(self, widgets: list) -> None:
        for w in widgets:
            try:
                w.setStyleSheet("border: 1px solid red;")
            except Exception:
                pass

    def _validate(self) -> Optional[str]:
        """
        Returns error message or None.
        Also applies inline visual highlight for invalid fields.
        """
        self._clear_validation_styles()
        missing = []

        if not getattr(self, "patient_id", None):
            missing.append(("Code patient", self.code_edit))
        if not self.medication_edit.text().strip():
            missing.append(("Médicament", self.medication_edit))
        if not self.dosage_edit.text().strip():
            missing.append(("Dosage", self.dosage_edit))
        if not self.frequency_edit.text().strip():
            missing.append(("Fréquence", self.frequency_edit))
        if not self.start_date.date().isValid():
            missing.append(("Date début", self.start_date))
        if self.end_date.date().isValid() and self.end_date.date() < self.start_date.date():
            missing.append(("Période invalide", self.end_date))

        if missing:
            # visual
            self._mark_invalid([w for _, w in missing])
            # message list
            labels = [lbl for lbl, _ in missing]
            return "Champs obligatoires manquants / invalides : " + ", ".join(labels)
        return None

    # ---------------- Save / Reset / Load ----------------
    def _on_save(self) -> None:
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Validation", err)
            return

        # prepare payload
        sd = self.start_date.date().toPyDate().isoformat() if self.start_date.date().isValid() else None
        ed = None
        if self.end_date.date().isValid():
            ed = self.end_date.date().toPyDate().isoformat()

        # medical_record_id integer if provided
        medrec_val = None
        medrec_text = self.medrec_edit.text().strip()
        if medrec_text:
            try:
                medrec_val = int(medrec_text)
            except Exception:
                medrec_val = None

        data: Dict[str, Any] = {
            "patient_id": self.patient_id,
            "medical_record_id": medrec_val or self.medical_record_id,
            "medication": self.medication_edit.text().strip(),
            "dosage": self.dosage_edit.text().strip(),
            "frequency": self.frequency_edit.text().strip(),
            "duration": self.duration_edit.text().strip() or None,
            "start_date": sd,
            "end_date": ed,
            "notes": self.notes_text.toPlainText().strip() or None
        }

        # ensure keys exist (backend expectation)
        for k in ("patient_id", "medical_record_id", "medication", "dosage", "frequency", "duration", "start_date", "end_date", "notes"):
            data.setdefault(k, None)

        # debug print (console)
        try:
            import json
            print("DEBUG PRESCRIPTION PAYLOAD:", json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print("DEBUG PRESCRIPTION PAYLOAD:", data)

        try:
            # call create / update
            if self.is_new:
                res = self.controller.create_prescription(data)
            else:
                res = self.controller.update_prescription(self.prescription_id, data)

            # normal success cases:
            # - controller returns True
            # - controller returns {"success": True, ...}
            # - controller returns an object (prescription)
            if res is True or (isinstance(res, dict) and (res.get("success") or "id" in res or "prescription_id" in res)):
                QMessageBox.information(self, "Succès", "Prescription enregistrée !")
                if callable(self.on_save):
                    try:
                        self.on_save()
                    except Exception:
                        pass
                if self.is_new:
                    self._reset_form()
                else:
                    self._close_form()
                return

            # server-side returned structured error dict
            if isinstance(res, dict) and res.get("error"):
                detail = res.get("details") or res.get("message") or str(res)
                QMessageBox.critical(self, "Erreur serveur", f"Échec enregistrement : {detail}")
                return

            # otherwise accept other truthy responses as success
            if res:
                QMessageBox.information(self, "Succès", "Prescription enregistrée !")
                if callable(self.on_save):
                    try:
                        self.on_save()
                    except Exception:
                        pass
                if self.is_new:
                    self._reset_form()
                else:
                    self._close_form()
                return

            # fallback: falsy response
            QMessageBox.critical(self, "Erreur", "Échec de l'enregistrement (réponse inattendue).")

        except Exception as e:
            # ApiControllerProxy may raise a RuntimeError containing "Gateway error: ... - <detail>"
            print(f"[DEBUG] Erreur technique (prescription save): {e}")

            # Tentative de mitigation : vérifier si la prescription existe déjà (post-mortem check)
            try:
                found = False
                candidates = []
                # try common listing methods to confirm creation
                if hasattr(self.controller, "list_prescriptions"):
                    try:
                        lst = self.controller.list_prescriptions(patient_id=self.patient_id, page=1, per_page=20)
                        if isinstance(lst, dict) and "data" in lst:
                            candidates = lst.get("data", [])
                        elif isinstance(lst, list):
                            candidates = lst
                    except Exception:
                        pass

                if not candidates and hasattr(self.controller, "get_prescriptions_for_patient"):
                    try:
                        lst = self.controller.get_prescriptions_for_patient(self.patient_id)
                        if isinstance(lst, dict) and "data" in lst:
                            candidates = lst.get("data", [])
                        elif isinstance(lst, list):
                            candidates = lst
                    except Exception:
                        pass

                # normalize predicate: match medication + start_date (best-effort)
                for p in (candidates or []):
                    try:
                        med = p.get("medication") if isinstance(p, dict) else getattr(p, "medication", None)
                        sd_p = p.get("start_date") if isinstance(p, dict) else getattr(p, "start_date", None)
                        if med and med == data["medication"]:
                            if not data["start_date"]:
                                found = True
                                break
                            if sd_p and str(sd_p).startswith(str(data["start_date"])):
                                found = True
                                break
                    except Exception:
                        continue

                if found:
                    QMessageBox.information(self, "Succès (confirmé après erreur)", "Prescription enregistrée malgré une erreur serveur. Veuillez vérifier les logs serveur.")
                    if callable(self.on_save):
                        try:
                            self.on_save()
                        except Exception:
                            pass
                    if self.is_new:
                        self._reset_form()
                    else:
                        self._close_form()
                    return
            except Exception:
                pass

            # si pas confirmé : montrer message d'erreur avec détail (si possible)
            # essayer extraire détail s'il s'agit d'une RuntimeError générée par ApiControllerProxy
            msg = str(e)
            try:
                # ApiControllerProxy lève "RuntimeError(f'Gateway error: {...} - {msg}')"
                msg = msg.replace("RuntimeError(", "").strip()
            except Exception:
                pass

            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue lors de l'enregistrement : {msg}")

    def _reset_form(self) -> None:
        self.patient_id = None
        self.code_edit.clear()
        self.patient_name_label.setText("-")
        self.medrec_edit.setEnabled(True)
        self.medrec_edit.clear()
        self.medication_edit.clear()
        self.dosage_edit.clear()
        self.frequency_edit.clear()
        self.duration_edit.clear()
        self.start_date.setDate(QDate.currentDate())
        self.end_date.setDate(QDate.currentDate())
        self.notes_text.clear()
        self._clear_validation_styles()

    def _load(self) -> None:
        """Charge prescription existante pour édition (doit gérer dict ou objet)."""
        try:
            rec = self.controller.get_prescription(self.prescription_id)
            if not rec:
                QMessageBox.warning(self, "Erreur", "Prescription introuvable")
                return
            # helper access
            def _get(k):
                return rec.get(k) if isinstance(rec, dict) else getattr(rec, k, None)

            # patient code & name
            code = None
            if isinstance(rec, dict):
                patient_obj = rec.get("patient") or {}
                code = patient_obj.get("code_patient") if patient_obj else None
                name = (patient_obj.get("last_name","") + " " + patient_obj.get("first_name","")).strip()
            else:
                patient_obj = getattr(rec, "patient", None)
                code = getattr(patient_obj, "code_patient", None) if patient_obj else None
                name = f"{getattr(patient_obj,'last_name','')} {getattr(patient_obj,'first_name','')}".strip() if patient_obj else ""

            if code:
                self.code_edit.setText(str(code))
                self.patient_name_label.setText(name or "-")

            self.patient_id = _get("patient_id") or getattr(rec, "patient_id", None)
            medrec = _get("medical_record_id") or getattr(rec, "medical_record_id", None)
            if medrec:
                self.medrec_edit.setText(str(medrec))
                self.medrec_edit.setEnabled(False)

            self.medication_edit.setText(str(_get("medication") or ""))
            self.dosage_edit.setText(str(_get("dosage") or ""))
            self.frequency_edit.setText(str(_get("frequency") or ""))
            self.duration_edit.setText(str(_get("duration") or ""))

            if _get("start_date"):
                try:
                    self.start_date.setDate(QDate.fromString(str(_get("start_date"))[:10], "yyyy-MM-dd"))
                except Exception:
                    pass
            if _get("end_date"):
                try:
                    self.end_date.setDate(QDate.fromString(str(_get("end_date"))[:10], "yyyy-MM-dd"))
                except Exception:
                    pass

            if _get("notes"):
                self.notes_text.setPlainText(str(_get("notes")))
        except Exception as e:
            print(f"[DEBUG] Erreur load prescription: {e}")
            QMessageBox.warning(self, "Erreur", "Impossible de charger la prescription.")

    # ---------------- Window helpers ----------------
    def _cancel(self) -> None:
        """
        Ferme proprement la fenêtre/dialog contenant ce widget.
        Si le widget est intégré dans un stacked widget, tente de close parent.
        """
        # chercher parent ayant la méthode close()
        parent = self.parent()
        while parent is not None and not hasattr(parent, "close"):
            parent = parent.parent()
        if parent:
            try:
                parent.close()
                return
            except Exception:
                pass

        # fallback
        try:
            self.hide()
            self.deleteLater()
        except Exception:
            pass

    def _close_form(self) -> bool:
        """Close + cleanup, retourne True si réussi."""
        parent = self.parent()
        while parent is not None and not hasattr(parent, "close"):
            parent = parent.parent()
        if parent:
            try:
                parent.close()
                return True
            except Exception:
                pass
        try:
            self.hide()
            self.deleteLater()
            return True
        except Exception:
            return False
