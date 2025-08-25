import winsound
import tkinter as tk
import customtkinter as ctk
from datetime import datetime, date
from tkcalendar import DateEntry
from tkinter import messagebox
from typing import Any, Dict, Optional


class MedicalRecordFormView(ctk.CTkFrame):
    """Formulaire d'édition/création d'un dossier médical (optimisé)."""

    def __init__(self, parent, controller, record_id: Optional[int] = None):
        super().__init__(parent)
        # Unwrap controller si on reçoit le contrôleur global
        self.controller = getattr(controller, "medical_record_controller", controller)
        self.record_id = record_id
        self.current_user = getattr(controller, "current_user", None)

        # Layout
        self.grid_columnconfigure(1, weight=1)

        # UI state
        self._feedback_labels = []
        self._highlighted = []

        # Build UI
        self._build_search_section()
        self._build_fields()
        self._build_buttons()

        # Load existing record
        if self.record_id:
            self._load_record()

    # -------------------------
    # Construction UI
    # -------------------------
    def _build_search_section(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, columnspan=6, pady=5, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Rechercher Patient (ID ou Code):").grid(row=0, column=0)
        self.search_entry = ctk.CTkEntry(frame, placeholder_text="ID ou Code")
        self.search_entry.grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(frame, text="🔍", command=self._on_search).grid(row=0, column=2, padx=5)

        # patient infos
        self.patient_id_var = tk.StringVar()
        self.patient_code_var = tk.StringVar()
        self.patient_name_var = tk.StringVar()
        labels = [("ID:", self.patient_id_var), ("Code:", self.patient_code_var), ("Nom:", self.patient_name_var)]
        for i, (lbl_text, var) in enumerate(labels, start=1):
            ctk.CTkLabel(frame, text=lbl_text).grid(row=i, column=0, sticky="e", padx=5)
            ctk.CTkLabel(frame, textvariable=var).grid(row=i, column=1, columnspan=2, sticky="w", padx=5)

    def _build_fields(self) -> None:
        fields = [
            ("Date Consultation", "consultation_date"),
            ("Statut matrimonial", "marital_status"),
            ("Tension artérielle", "bp"),
            ("Température", "temperature"),
            ("Poids (kg)", "weight"),
            ("Taille (cm)", "height"),
            ("Antécédents", "medical_history"),
            ("Allergies", "allergies"),
            ("Symptômes", "symptoms"),
            ("Diagnostic", "diagnosis"),
            ("Traitement", "treatment"),
            ("Gravité", "severity"),
            ("Notes", "notes"),
        ]
        self.entries: Dict[str, Any] = {}

        # options
        self.marital_options = [
            ("Single / Célibataire", "Single"),
            ("Married / Marié(e)", "Married"),
            ("Divorced / Divorcé(e)", "Divorced"),
            ("Widowed / Veuf(ve)", "Widowed"),
        ]
        self.severity_options = [
            ("Low / Faible", "low"),
            ("Medium / Moyen", "medium"),
            ("High / Élevé", "high"),
        ]

        # motifs (filtrage strict pour éviter None dans les clés)
        motifs = []
        try:
            motifs = self.controller.list_motifs() or []
        except Exception:
            motifs = []
        # garder uniquement les dicts ayant un code str non vide
        motifs_valid = [ m for m in motifs    if isinstance(m, dict) and isinstance(m.get("code"), str) and (m.get("code") or "").strip()]
        codes = [m["code"] for m in motifs_valid]
        self.code_to_label: Dict[str, str] = {m["code"]: (m.get("label_fr") or "") for m in motifs_valid}
        self.label_to_code: Dict[str, str] = {label: code for code, label in self.code_to_label.items()}

        # construire champs
        idx = 2
        for idx, (label_text, key) in enumerate(fields, start=2):
            ctk.CTkLabel(self, text=label_text + ":").grid(row=idx, column=0, padx=10, pady=5, sticky="e")
            if key == "consultation_date":
                widget = DateEntry(self, date_pattern="yyyy-mm-dd")
                self.date_widget = widget
            elif key == "marital_status":
                self.marital_var = tk.StringVar()
                widget = ctk.CTkOptionMenu(self, values=[d for d, _ in self.marital_options], variable=self.marital_var)
                self.marital_widget = widget
            elif key == "severity":
                self.severity_var = tk.StringVar()
                widget = ctk.CTkOptionMenu(self, values=[d for d, _ in self.severity_options], variable=self.severity_var)
                self.severity_widget = widget
            elif key == "notes":
                widget = ctk.CTkTextbox(self, width=400, height=80)
                self.notes_widget = widget
            else:
                widget = ctk.CTkEntry(self, placeholder_text=label_text)
            widget.grid(row=idx, column=1, padx=10, pady=5, sticky="ew")
            self.entries[key] = widget

        # motif dropdown (garantir qu'on passe des labels valides)
        ctk.CTkLabel(self, text="Motif:").grid(row=idx + 1, column=0, sticky="e", padx=10)
        labels_list = [self.code_to_label[c] for c in codes if c in self.code_to_label]
        default_label = labels_list[0] if labels_list else ""
        self.motif_var = tk.StringVar(value=default_label)
        self.motif_widget = ctk.CTkOptionMenu(self, values=labels_list, variable=self.motif_var)
        self.motif_widget.grid(row=idx + 1, column=1, padx=10, pady=5, sticky="ew")

    def _build_buttons(self) -> None:
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=100, column=0, columnspan=6, pady=15)
        ctk.CTkButton(btn_frame, text="Enregistrer", command=self._on_save).pack(side="left", padx=10)
        if self.record_id:
            ctk.CTkButton(btn_frame, text="Supprimer", fg_color="#D32F2F", command=self._on_delete).pack(side="right", padx=10)

    # -------------------------
    # Helpers
    # -------------------------
    def _get_widget_text(self, key: str) -> str:
        w = self.entries.get(key)
        try:
            if w is None:
                return ""
            if hasattr(w, "get"):
                return w.get().strip()
        except Exception:
            pass
        return ""

    def _safe_insert(self, widget: Any, value: Any) -> None:
        v = "" if value is None else str(value)
        try:
            # Entry-like
            if hasattr(widget, "delete") and hasattr(widget, "insert"):
                widget.delete(0, tk.END)
                widget.insert(0, v)
            # Textbox
            elif isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
                widget.insert("1.0", v)
        except Exception:
            pass

    # -------------------------
    # Actions
    # -------------------------
    def _on_search(self) -> None:
        q = self.search_entry.get().strip()
        try:
            rec = self.controller.find_patient(q)
        except Exception as e:
            return self._show_error(f"Erreur recherche patient: {e}")

        if rec:
            pid = rec["patient_id"] if isinstance(rec, dict) else getattr(rec, "patient_id", "")
            self.patient_id_var.set(str(pid))
            code = rec["code_patient"] if isinstance(rec, dict) else getattr(rec, "code_patient", "")
            self.patient_code_var.set(str(code))
            first = rec.get("first_name", "") if isinstance(rec, dict) else getattr(rec, "first_name", "")
            last = rec.get("last_name", "") if isinstance(rec, dict) else getattr(rec, "last_name", "")
            self.patient_name_var.set(f"{last} {first}".strip())
        else:
            self.patient_id_var.set("")
            self.patient_code_var.set("")
            self.patient_name_var.set("")

    def _on_save(self) -> None:
        # clear visuals
        self._clear_feedback()
        self._clear_highlights()

        # validation basique
        pid = self.patient_id_var.get().strip()
        date_raw = ""
        try:
            date_raw = self.date_widget.get().strip()
        except Exception:
            date_raw = ""
        ms = self.marital_var.get().strip() if hasattr(self, "marital_var") else ""
        sv = self.severity_var.get().strip() if hasattr(self, "severity_var") else ""
        motif_label = self.motif_var.get().strip() if hasattr(self, "motif_var") else ""

        if not pid or not pid.isdigit():
            return self._error_field(self.search_entry, "Veuillez sélectionner un patient valide.")
        if not date_raw:
            return self._error_field(self.date_widget, "Le champ Date Consultation est obligatoire.")
        if not ms:
            return self._error_field(self.marital_widget, "Le champ Statut matrimonial est obligatoire.")
        if not sv:
            return self._error_field(self.severity_widget, "Le champ Gravité est obligatoire.")
        if not motif_label:
            return self._error_field(self.motif_widget, "Le champ Motif est obligatoire.")

        # numeric validation
        numeric_specs = {
            "temperature": ("Température", 30, 45),
            "weight": ("Poids (kg)", 0, 1000),
            "height": ("Taille (cm)", 30, 250),
        }
        for key, (label, mn, mx) in numeric_specs.items():
            raw = self._get_widget_text(key)
            if raw:
                try:
                    val = float(raw)
                except ValueError:
                    return self._error_field(self.entries[key], f"{label} doit être un nombre.")
                if not (mn <= val < mx):
                    return self._error_field(self.entries[key], f"{label} doit être entre {mn} et {mx}.")

        # build data
        data: Dict[str, Any] = {"patient_id": int(pid)}
        try:
            data["consultation_date"] = datetime.strptime(date_raw, "%Y-%m-%d")
        except Exception:
            try:
                data["consultation_date"] = datetime.fromisoformat(date_raw)
            except Exception:
                data["consultation_date"] = datetime.now()

        data["marital_status"] = next(v for d, v in self.marital_options if d == ms)
        data["bp"] = self._get_widget_text("bp") or None
        for key in numeric_specs:
            raw = self._get_widget_text(key)
            data[key] = float(raw) if raw else None

        for key in ("medical_history", "allergies", "symptoms", "diagnosis", "treatment"):
            data[key] = self._get_widget_text(key) or None

        data["severity"] = next(v for d, v in self.severity_options if d == sv)
        notes_text = ""
        try:
            notes_text = self.notes_widget.get("1.0", "end").strip()
        except Exception:
            notes_text = ""
        data["notes"] = notes_text or None

        # motif_code (recherche inverse)
        data["motif_code"] = self.label_to_code.get(motif_label)

        # audit
        if self.current_user:
            uid = getattr(self.current_user, "user_id", None)
            uname = getattr(self.current_user, "username", None)
            audit: Dict[str, Any] = {
                "created_by": uid,
                "last_updated_by": uid,
                "created_by_name": uname,
                "last_updated_by_name": uname,
            }
            data.update(audit)

        # persist (create or update)
        try:
            if self.record_id:
                # update: si update_record renvoie le record mis à jour, on peut l'utiliser
                updated = self.controller.update_record(self.record_id, data)
                # fermer la fenêtre toplevel (garantit fermeture même si master n'est pas toplevel)
                try:
                    self.winfo_toplevel().destroy()
                except Exception:
                    pass
                return
            else:
                created = self.controller.create_record(data)
                # si le repo renvoie l'objet créé avec id, on le conserve pour la session UI
                if created:
                    new_id = getattr(created, "id", None) or getattr(created, "record_id", None)
                    if new_id:
                        self.record_id = new_id
                # on garde le formulaire ouvert après création mais on reset
                self._show_success_popup("Création réussie !")
                self._reset_form()
                return
        except Exception:
            return self._show_error("Échec de l'enregistrement, veuillez réessayer.")

    def _on_delete(self) -> None:
        if not self.record_id:
            return self._show_error("Aucun enregistrement à supprimer.")
        confirm = messagebox.askyesno("Confirmer", "Voulez-vous vraiment supprimer ce dossier médical ?")
        if not confirm:
            return
        try:
            success = self.controller.delete_record(self.record_id)
            if success:
                self._show_success_popup("Suppression réussie !")
                try:
                    self.winfo_toplevel().destroy()
                except Exception:
                    pass
                return
            else:
                return self._show_error("Impossible de supprimer le dossier.")
        except Exception as e:
            return self._show_error(f"Échec de la suppression : {e}")

    # -------------------------
    # Chargement et UI utils
    # -------------------------
    def _load_record(self) -> None:
        try:
            record = self.controller.get_record(self.record_id)
            if not record:
                return self._show_error("Dossier médical introuvable.")

            def _get(attr: str, default: Any = None) -> Any:
                if isinstance(record, dict):
                    return record.get(attr, default)
                return getattr(record, attr, default)

            # date
            consult_val = _get("consultation_date")
            if isinstance(consult_val, str):
                try:
                    self.date_widget.set_date(datetime.fromisoformat(consult_val).date())
                except Exception:
                    try:
                        self.date_widget.set_date(date.fromisoformat(consult_val))
                    except Exception:
                        pass
            elif isinstance(consult_val, datetime):
                self.date_widget.set_date(consult_val.date())
            elif isinstance(consult_val, date):
                self.date_widget.set_date(consult_val)

            # marital
            ms_val = _get("marital_status")
            if ms_val:
                try:
                    ms_label = next(d for d, v in self.marital_options if v == ms_val)
                    self.marital_var.set(ms_label)
                except StopIteration:
                    pass

            # champs
            for k in ("bp", "temperature", "weight", "height", "medical_history", "allergies", "symptoms", "diagnosis", "treatment"):
                self._safe_insert(self.entries.get(k), _get(k))

            # severity
            sev = _get("severity")
            if sev:
                try:
                    sev_label = next(d for d, v in self.severity_options if v == sev)
                    self.severity_var.set(sev_label)
                except StopIteration:
                    pass

            # notes
            notes_val = _get("notes")
            if notes_val is not None:
                try:
                    self.notes_widget.delete("1.0", "end")
                    self.notes_widget.insert("1.0", str(notes_val))
                except Exception:
                    pass

            # motif
            motif_code = _get("motif_code")
            if motif_code:
                motif_label = self.code_to_label.get(motif_code)
                if motif_label:
                    try:
                        self.motif_var.set(motif_label)
                    except Exception:
                        pass

            # patient info
            pid = _get("patient_id")
            if pid is not None:
                self.patient_id_var.set(str(pid))
            code = _get("code_patient")
            if code is not None:
                self.patient_code_var.set(str(code))
            fname = _get("first_name")
            lname = _get("last_name")
            if fname or lname:
                self.patient_name_var.set(f"{lname or ''} {fname or ''}".strip())

        except Exception as e:
            self._show_error(f"Erreur chargement dossier : {e}")

    # UI helpers: highlights, feedback, reset, popups (inchangés logiquement)
    def _error_field(self, widget: Any, msg: str) -> None:
        self._highlight(widget)
        return self._show_error(msg)

    def _highlight(self, widget: Any) -> None:
        try:
            widget.configure(border_color="red", border_width=2)
        except Exception:
            pass
        self._highlighted.append(widget)

    def _clear_highlights(self) -> None:
        for w in self._highlighted:
            try:
                w.configure(border_color="#E0E0E0", border_width=1)
            except Exception:
                pass
        self._highlighted.clear()

    def _clear_feedback(self) -> None:
        for lbl in self._feedback_labels:
            try:
                lbl.destroy()
            except Exception:
                pass
        self._feedback_labels.clear()

    def _show_error(self, msg: str) -> None:
        lbl = ctk.CTkLabel(self, text=msg, text_color="red")
        lbl.grid(row=0, column=0, columnspan=6, pady=5)
        self._feedback_labels.append(lbl)

    def _show_success_popup(self, message: str) -> None:
        popup = ctk.CTkToplevel(self)
        popup.attributes("-topmost", True)
        popup.title("Succès")
        popup.geometry("300x100")
        ctk.CTkLabel(popup, text=message, text_color="green", font=ctk.CTkFont(size=14)).pack(pady=20)
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
        popup.after(2000, popup.destroy)

    def _reset_form(self) -> None:
        for key, widget in self.entries.items():
            try:
                if hasattr(widget, "delete") and hasattr(widget, "insert"):
                    widget.delete(0, tk.END)
                elif isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", "end")
                elif isinstance(widget, ctk.CTkOptionMenu):
                    vals = widget.cget("values")
                    if vals:
                        widget.set(vals[0])
            except Exception:
                pass
        if hasattr(self, "marital_var"):
            self.marital_var.set(self.marital_options[0][0])
        if hasattr(self, "severity_var"):
            self.severity_var.set(self.severity_options[0][0])
        if hasattr(self, "motif_var") and self.label_to_code:
            first_label = next(iter(self.label_to_code), "")
            if first_label:
                self.motif_var.set(first_label)
        try:
            self.search_entry.delete(0, tk.END)
        except Exception:
            pass
        self.patient_id_var.set("")
        self.patient_code_var.set("")
        self.patient_name_var.set("")
        self.record_id = None
        self._clear_highlights()
