import winsound
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from tkcalendar import DateEntry


class MedicalRecordFormView(ctk.CTkFrame):
    def __init__(self, parent, controller, record_id=None):
        super().__init__(parent)
        # Unwrap controller
        if hasattr(controller, 'medical_record_controller'):
            self.controller = controller.medical_record_controller
        else:
            self.controller = controller
        self.record_id = record_id
        self.current_user = getattr(controller, 'current_user', None)

        # Layout
        self.grid_columnconfigure(1, weight=1)

        # Trackers for feedback
        self._feedback_labels = []
        self._highlighted = []

        # Build UI sections
        self._build_search_section()
        self._build_fields()
        self._build_buttons()

        # Load existing record
        if self.record_id:
            self._load_record()

    def _build_search_section(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, columnspan=6, pady=5, sticky='ew')
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Rechercher Patient (ID ou Code):").grid(row=0, column=0)
        self.search_entry = ctk.CTkEntry(frame, placeholder_text="ID ou Code")
        self.search_entry.grid(row=0, column=1, padx=5, sticky='ew')
        ctk.CTkButton(frame, text="🔍", command=self._on_search).grid(row=0, column=2, padx=5)

        # Display found patient info
        self.patient_id_var = tk.StringVar()
        self.patient_code_var = tk.StringVar()
        self.patient_name_var = tk.StringVar()
        labels = [("ID:", self.patient_id_var), ("Code:", self.patient_code_var), ("Nom:", self.patient_name_var)]
        for i, (lbl_text, var) in enumerate(labels, start=1):
            ctk.CTkLabel(frame, text=lbl_text).grid(row=i, column=0, sticky='e', padx=5)
            ctk.CTkLabel(frame, textvariable=var).grid(row=i, column=1, columnspan=2, sticky='w', padx=5)

    def _build_fields(self):
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
        self.entries = {}

        # Option mappings
        self.marital_options = [
            ("Single / Célibataire", "Single"),
            ("Married / Marié(e)", "Married"),
            ("Divorced / Divorcé(e)", "Divorced"),
            ("Widowed / Veuf(ve)", "Widowed")
        ]
        self.severity_options = [
            ("Low / Faible", "low"),
            ("Medium / Moyen", "medium"),
            ("High / Élevé", "high")
        ]

        # Consultation motifs
        motifs = self.controller.list_motifs()
        codes = [m['code'] for m in motifs]
        self.code_to_label = {m['code']: m['label_fr'] for m in motifs}
        self.label_to_code = {label: code for code, label in self.code_to_label.items()}

        # Create fields
        for idx, (label_text, key) in enumerate(fields, start=2):
            ctk.CTkLabel(self, text=label_text + ":").grid(row=idx, column=0, padx=10, pady=5, sticky='e')
            if key == 'consultation_date':
                widget = DateEntry(self, date_pattern='yyyy-mm-dd')
                self.date_widget = widget
            elif key == 'marital_status':
                self.marital_var = tk.StringVar()
                widget = ctk.CTkOptionMenu(self, values=[d for d, _ in self.marital_options], variable=self.marital_var)
                self.marital_widget = widget
            elif key == 'severity':
                self.severity_var = tk.StringVar()
                widget = ctk.CTkOptionMenu(self, values=[d for d, _ in self.severity_options], variable=self.severity_var)
                self.severity_widget = widget
            elif key == 'notes':
                widget = ctk.CTkTextbox(self, width=400, height=80)
                self.notes_widget = widget
            else:
                widget = ctk.CTkEntry(self, placeholder_text=label_text)
            widget.grid(row=idx, column=1, padx=10, pady=5, sticky='ew')
            self.entries[key] = widget

        # Motif de consultation dropdown
        ctk.CTkLabel(self, text="Motif:").grid(row=idx+1, column=0, sticky='e', padx=10)
        labels_list = [self.code_to_label.get(c, '') for c in codes]
        self.motif_var = tk.StringVar(value=labels_list[0] if labels_list else '')
        self.motif_widget = ctk.CTkOptionMenu(self, values=labels_list, variable=self.motif_var)
        self.motif_widget.grid(row=idx+1, column=1, padx=10, pady=5, sticky='ew')

    def _build_buttons(self):
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=100, column=0, columnspan=6, pady=15)
        ctk.CTkButton(btn_frame, text="Enregistrer", command=self._on_save).pack(side='left', padx=10)
        if self.record_id:
            ctk.CTkButton(btn_frame, text="Supprimer", fg_color="#D32F2F", command=self._on_delete).pack(side='right', padx=10)

    def _on_search(self):
        q = self.search_entry.get().strip()
        rec = self.controller.find_patient(q)
        if rec:
            pid = rec['patient_id'] if isinstance(rec, dict) else rec.patient_id
            self.patient_id_var.set(str(pid))
            code = rec['code_patient'] if isinstance(rec, dict) else rec.code_patient
            self.patient_code_var.set(code)
            name = f"{rec.get('last_name','') if isinstance(rec, dict) else rec.last_name} {rec.get('first_name','') if isinstance(rec, dict) else rec.first_name}"
            self.patient_name_var.set(name)
        else:
            self.patient_id_var.set('')
            self.patient_code_var.set('')
            self.patient_name_var.set('')

    def _on_save(self):
        # Reset visuals
        self._clear_feedback()
        self._clear_highlights()

        # Basic required validation
        pid = self.patient_id_var.get().strip()
        date_raw = self.date_widget.get().strip()
        ms = self.marital_var.get().strip()
        sv = self.severity_var.get().strip()
        motif = self.motif_var.get().strip()
        if not pid or not pid.isdigit():
            return self._error_field(self.search_entry, "Veuillez sélectionner un patient valide.")
        if not date_raw:
            return self._error_field(self.date_widget, "Le champ Date Consultation est obligatoire.")
        if not ms:
            return self._error_field(self.marital_widget, "Le champ Statut matrimonial est obligatoire.")
        if not sv:
            return self._error_field(self.severity_widget, "Le champ Gravité est obligatoire.")
        if not motif:
            return self._error_field(self.motif_widget, "Le champ Motif est obligatoire.")

        # Numeric field validation
        numeric_specs = {
            'temperature': ("Température", 30, 45),
            'weight':      ("Poids (kg)", 0, 1000),
            'height':      ("Taille (cm)", 30, 250)
        }
        for key, (label, mn, mx) in numeric_specs.items():
            raw = self.entries[key].get().strip()
            if raw:
                try:
                    val = float(raw)
                except ValueError:
                    return self._error_field(self.entries[key], f"{label} doit être un nombre.")
                if not (mn <= val < mx):
                    return self._error_field(self.entries[key], f"{label} doit être entre {mn} et {mx}.")

        # Build data dict
        data = {'patient_id': int(pid)}
        data['consultation_date'] = datetime.strptime(date_raw, "%Y-%m-%d")
        data['marital_status'] = next(v for d,v in self.marital_options if d == ms)
        data['bp'] = self.entries['bp'].get().strip() or None
        for key in numeric_specs:
            raw = self.entries[key].get().strip()
            data[key] = float(raw) if raw else None
        for key in ('medical_history','allergies','symptoms','diagnosis','treatment'):
            data[key] = self.entries[key].get().strip() or None
        data['severity'] = next(v for d,v in self.severity_options if d == sv)
        data['notes'] = self.notes_widget.get("1.0","end").strip() or None
        data['motif_code'] = self.label_to_code.get(motif)

        # Audit fields
        if self.current_user:
            uid = self.current_user.user_id
            uname = self.current_user.username
            data.update({'created_by': uid, 'last_updated_by': uid,
                         'created_by_name': uname, 'last_updated_by_name': uname})

        # Persist
        try:
            if self.record_id:
                self.controller.update_record(self.record_id, data)
            else:
                self.controller.create_record(data)
        except Exception:
            return self._show_error("Échec de l’enregistrement, veuillez réessayer.")

        # Success
        if self.record_id:
            self._show_success_popup("Modification réussie !")
            self.master.destroy()
        else:
            self._show_success_popup("Création réussie !")
            self._reset_form()

    def _error_field(self, widget, msg):
        self._highlight(widget)
        return self._show_error(msg)

    def _highlight(self, widget):
        try:
            widget.configure(border_color="red", border_width=2)
        except:
            pass
        self._highlighted.append(widget)

    def _clear_highlights(self):
        for w in self._highlighted:
            try:
                w.configure(border_color="#E0E0E0", border_width=1)
            except:
                pass
        self._highlighted.clear()

    def _clear_feedback(self):
        for lbl in self._feedback_labels:
            lbl.destroy()
        self._feedback_labels.clear()

    def _show_error(self, msg):
        lbl = ctk.CTkLabel(self, text=msg, text_color="red")
        lbl.grid(row=0, column=0, columnspan=6, pady=5)
        self._feedback_labels.append(lbl)

    def _show_info(self, msg):
        lbl = ctk.CTkLabel(self, text=msg, text_color="green")
        lbl.grid(row=0, column=0, columnspan=6, pady=5)
        self._feedback_labels.append(lbl)

    def _show_success_popup(self, message):
        popup = ctk.CTkToplevel(self)
        popup.attributes("-topmost", True)
        popup.title("Succès")
        popup.geometry("300x100")
        ctk.CTkLabel(popup, text=message, text_color="green", font=ctk.CTkFont(size=14)).pack(pady=20)
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            pass
        popup.after(5000, popup.destroy)

    def _reset_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, (tk.Entry, ctk.CTkEntry, DateEntry)):
                widget.delete(0, tk.END)
            elif isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            elif isinstance(widget, ctk.CTkOptionMenu):
                vals = widget.cget("values")
                if vals:
                    widget.set(vals[0])
        if hasattr(self, 'marital_var'):
            self.marital_var.set(self.marital_options[0][0])
        if hasattr(self, 'severity_var'):
            self.severity_var.set(self.severity_options[0][0])
        if hasattr(self, 'motif_var') and self.label_to_code:
            self.motif_var.set(next(iter(self.label_to_code)))
        self.search_entry.delete(0, tk.END)
        self.patient_id_var.set("")
        self.patient_code_var.set("")
        self.patient_name_var.set("")
        self.record_id = None
        self._clear_highlights()
