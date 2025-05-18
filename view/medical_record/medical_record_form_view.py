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
        # Recherche patient
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, columnspan=6, pady=5, sticky='ew')
        search_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(search_frame, text="Rechercher Patient (ID ou Code):").grid(row=0, column=0)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="ID ou Code")
        self.search_entry.grid(row=0, column=1, padx=5, sticky='ew')
        ctk.CTkButton(search_frame, text="🔍", command=self._on_search).grid(row=0, column=2, padx=5)

        # Affichage des infos du patient trouvé
        ctk.CTkLabel(search_frame, text="ID:").grid(row=1, column=0, sticky='e', padx=5)
        self.patient_id_var = tk.StringVar()
        ctk.CTkLabel(search_frame, textvariable=self.patient_id_var).grid(row=1, column=1, sticky='w', padx=5)
        ctk.CTkLabel(search_frame, text="Code:").grid(row=1, column=2, sticky='e', padx=5)
        self.patient_code_var = tk.StringVar()
        ctk.CTkLabel(search_frame, textvariable=self.patient_code_var).grid(row=1, column=3, sticky='w', padx=5)
        ctk.CTkLabel(search_frame, text="Nom:").grid(row=1, column=4, sticky='e', padx=5)
        self.patient_name_var = tk.StringVar()
        ctk.CTkLabel(search_frame, textvariable=self.patient_name_var).grid(row=1, column=5, sticky='w', padx=5)

        # Champs de formulaire
        fields = [
            ("Date Consultation",  "consultation_date"),
            ("Statut matrimonial", "marital_status"),
            ("Tension artérielle", "bp"),
            ("Température",        "temperature"),
            ("Poids (kg)",         "weight"),
            ("Taille (cm)",        "height"),
            ("Antécédents",        "medical_history"),
            ("Allergies",          "allergies"),
            ("Symptômes",          "symptoms"),
            ("Diagnostic",         "diagnosis"),
            ("Traitement",         "treatment"),
            ("Gravité",            "severity"),
            ("Notes",              "notes"),
        ]
        self.entries = {}

        # mapping statut matrimonial FR/EN → BD
        self.marital_options = [
            ("Single / Célibataire", "Single"),
            ("Married / Marié(e)",    "Married"),
            ("Divorced / Divorcé(e)", "Divorced"),
            ("Widowed / Veuf(ve)",    "Widowed")
        ]
        # mapping gravité FR/EN → BD
        self.severity_options = [
            ("Low / Faible",   "low"),
            ("Medium / Moyen", "medium"),
            ("High / Élevé",   "high")
        ]

        # Motif mapping code → label and inverse
        motifs = self.controller.list_motifs()
        # list of codes, e.g. ['consultation', ...]
        codes = [m['code'] for m in motifs]
        # map code to label_fr
        self.code_to_label = {m['code']: m['label_fr'] for m in motifs}
        # inverse map label → code
        self.label_to_code = {label:code for code,label in self.code_to_label.items()}

        for idx, (label, key) in enumerate(fields, start=2):
            ctk.CTkLabel(self, text=label+":").grid(row=idx, column=0, padx=10, pady=5, sticky='e')
            if key == 'consultation_date':
                widget = DateEntry(self, date_pattern='yyyy-mm-dd')
                widget.grid(row=idx, column=1, padx=10, pady=5, sticky='ew')
            elif key == 'marital_status':
                self.marital_var = tk.StringVar()
                widget = ctk.CTkOptionMenu(self, values=[opt[0] for opt in self.marital_options], variable=self.marital_var)
                widget.grid(row=idx, column=1, padx=10, pady=5, sticky='ew')
            elif key == 'severity':
                self.severity_var = tk.StringVar()
                widget = ctk.CTkOptionMenu(self, values=[opt[0] for opt in self.severity_options], variable=self.severity_var)
                widget.grid(row=idx, column=1, padx=10, pady=5, sticky='ew')
            elif key == 'notes':
                widget = ctk.CTkTextbox(self, width=400, height=80)
                widget.grid(row=idx, column=1, padx=10, pady=5, sticky='ew')
            else:
                widget = ctk.CTkEntry(self, placeholder_text=label)
                widget.grid(row=idx, column=1, padx=10, pady=5, sticky='ew')
            self.entries[key] = widget

        # Motif de consultation
        ctk.CTkLabel(self, text="Motif:").grid(row=idx+1, column=0, sticky='e', padx=10)
        # display labels
        labels = [self.code_to_label[code] for code in codes]
        self.motif_var = tk.StringVar(value=labels[0] if labels else '')
        self.motif_menu = ctk.CTkOptionMenu(self, values=labels, variable=self.motif_var)
        self.motif_menu.grid(row=idx+1, column=1, padx=10, pady=5, sticky='ew')

        # Boutons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=idx+2, column=0, columnspan=6, pady=15)
        ctk.CTkButton(btn_frame, text="Enregistrer", command=self._on_save).pack(side='left', padx=10)
        if self.record_id:
            ctk.CTkButton(btn_frame, text="Supprimer", fg_color="#D32F2F", command=self._on_delete).pack(side='right', padx=10)

        # Chargement si édition
        if self.record_id:
            self._load_record()

    def _on_search(self):
        q = self.search_entry.get().strip()
        rec = self.controller.find_patient(q)
        if rec:
            pid = rec['patient_id'] if isinstance(rec, dict) else rec.patient_id
            self.patient_id_var.set(str(pid))
            code = rec['code_patient'] if isinstance(rec, dict) else rec.code_patient
            self.patient_code_var.set(code)
            name = f"{rec.get('last_name','') if isinstance(rec, dict) else rec.last_name} {(rec.get('first_name','') if isinstance(rec, dict) else rec.first_name)}"
            self.patient_name_var.set(name)
        else:
            self.patient_id_var.set('')
            self.patient_code_var.set('')
            self.patient_name_var.set('')

    def _on_save(self):
        data = {}
        # 0) reset visuel des champs et des messages
        self._clear_highlights()
        self._clear_feedback()

        # 1) patient_id : seulement lors de la création (pas en update)
        if not self.record_id:
            pid = self.patient_id_var.get()
            if not pid.isdigit():
                self._highlight(self.search_entry)
                return self._show_error("Veuillez sélectionner un patient valide.")
            data['patient_id'] = int(pid)

        # 2. consultation_date
        raw = self.entries['consultation_date'].get()
        try:
            data['consultation_date'] = datetime.strptime(raw, "%Y-%m-%d")
        except:
            data['consultation_date'] = None

        # 3. marital_status
        disp = self.marital_var.get()
        data['marital_status'] = next(val for d, val in self.marital_options if d == disp)

        # 4. Tension artérielle (bp) traité comme chaîne (varchar en BD)
        data['bp'] = self.entries['bp'].get().strip() or None

        # 5. validation des autres champs numériques
        numeric_specs = {
            'temperature': ("Température", 30, 45),
            'weight':      ("Poids (kg)",  0, 1000),
            'height':      ("Taille (cm)", 30, 250),
        }
        for key, (label, mn, mx) in numeric_specs.items():
            raw = self.entries[key].get().strip()
            if not raw:
                data[key] = None
                continue
            try:
                val = float(raw)
            except ValueError:
                self._highlight(self.entries[key])
                return self._show_error(f"{label} doit être un nombre.")
            if not (mn <= val < mx):
                self._highlight(self.entries[key])
                return self._show_error(f"{label} doit être entre {mn} et {mx}.")
            data[key] = val

        # 6. champs textes non-numériques
        for key in ('medical_history','allergies','symptoms','diagnosis','treatment'):
            txt = self.entries[key].get().strip()
            data[key] = txt or None

        # 7. severity
        disp_s = self.severity_var.get()
        data['severity'] = next(val for d, val in self.severity_options if d == disp_s)

        # 8. notes
        notes_widget = self.entries['notes']
        data['notes'] = notes_widget.get("1.0", "end").strip() or None

        # 9. motif_code
        lab = self.motif_var.get()
        data['motif_code'] = self.label_to_code.get(lab)

        # 10. audit fields
        if self.current_user:
            data['created_by'] = data['last_updated_by'] = self.current_user.user_id
            data['created_by_name'] = data['last_updated_by_name'] = self.current_user.username
        else:
            for f in ('created_by','last_updated_by','created_by_name','last_updated_by_name'):
                data[f] = None

        # 11. appel BD
        try:
            if self.record_id:
                self.controller.update_record(self.record_id, data)
            else:
                self.controller.create_record(data)
        except Exception as e:
            print("[DEV] Erreur SQL brute:", e)
            return self._show_error("Échec de l’enregistrement, veuillez réessayer.")

        # 12. succès : popup + reset
        if self.record_id:
            self._show_success_popup("Modification réussie !")
            self.master.destroy()  # Ferme le frame courant (la fenêtre d'édition)
        else:
            self._show_success_popup("Création réussie !")
            self._reset_form()     # Réinitialise le formulaire pour un nouveau enregistrement

   



    # —————— helpers visuels et popup ——————

    def _highlight(self, widget):
        """Encadre en rouge uniquement les CTkEntry / CTkTextbox."""
        if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox)):
            widget.configure(border_color="red", border_width=2)

    def _clear_highlights(self):
        """Remise à blanc de tous les CTkEntry / CTkTextbox."""
        if isinstance(self.search_entry, (ctk.CTkEntry, ctk.CTkTextbox)):
            self.search_entry.configure(border_color="#E0E0E0", border_width=1)
        for w in self.entries.values():
            if isinstance(w, (ctk.CTkEntry, ctk.CTkTextbox)):
                w.configure(border_color="#E0E0E0", border_width=1)

    def _clear_feedback(self):
        if hasattr(self, '_feedback_labels'):
            for label in self._feedback_labels:
                label.destroy()
        self._feedback_labels = []

    def _show_error(self, msg):
        self._clear_feedback()
        lbl = ctk.CTkLabel(self, text=msg, text_color="red")
        lbl.grid(row=0, column=0, columnspan=6, pady=5)
        self._feedback_labels = [lbl]

    def _show_info(self, msg):
        self._clear_feedback()
        lbl = ctk.CTkLabel(self, text=msg, text_color="green")
        lbl.grid(row=0, column=0, columnspan=6, pady=5)
        self._feedback_labels = [lbl]


    def _show_success_popup(self, message):
        popup = ctk.CTkToplevel(self)
        def fade_in(popup, alpha=0.0):
            alpha = round(alpha + 0.05, 2)
            if alpha <= 1.0:
                popup.attributes("-alpha", alpha)
                popup.after(30, lambda: fade_in(popup, alpha))

        popup.attributes("-alpha", 0.0)
        fade_in(popup)

        popup.title("Succès")
        popup.geometry("300x100")
        popup.attributes("-topmost", True)

        # Centrage dynamique
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 50
        popup.geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(popup, text=message, text_color="green", font=ctk.CTkFont(size=14))
        label.pack(pady=20)

        # Effet sonore simple
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except:
            pass

        # Fermeture après 5 sec
        popup.after(5000, popup.destroy)


    def _reset_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, (tk.Entry, ctk.CTkEntry)):
                widget.delete(0, tk.END)
            elif isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", tk.END)
            elif isinstance(widget, ctk.CTkOptionMenu):
                values = widget.cget("values")
                if values:
                    widget.set(values[0])  # Première option disponible

        # Menus déroulants à part si reliés à d'autres variables
        if hasattr(self, 'marital_var') and self.marital_options:
            self.marital_var.set(self.marital_options[0][0])

        if hasattr(self, 'severity_var') and self.severity_options:
            self.severity_var.set(self.severity_options[0][0])

        if hasattr(self, 'motif_var') and self.label_to_code:
            default = next(iter(self.label_to_code))  # Premier label
            self.motif_var.set(default)

        # Champs liés au patient
        self.patient_id_var.set("")
        if hasattr(self, 'search_entry'):
            self.search_entry.delete(0, tk.END)

        self.record_id = None

        # Nettoyer visuel
        self._clear_highlights()
        self._clear_feedback()


    def _on_delete(self):
        if not self.record_id: return
        try:
            self.controller.delete_record(self.record_id)
            self._show_info("Supprimé")
        except Exception as e:
            self._show_error(f"Erreur suppression : {e}")

    def _load_record(self):
        rec = self.controller.get_record(self.record_id)
        if not rec:
            return

        # ID du patient
        pid = rec['patient_id'] if isinstance(rec, dict) else rec.patient_id
        self.patient_id_var.set(str(pid))

        # Remplissage des champs
        for key, widget in self.entries.items():
            val = rec[key] if isinstance(rec, dict) else getattr(rec, key)

            # zone de texte multiline
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
                widget.insert("1.0", val or "")

            # date
            elif isinstance(widget, DateEntry):
                if val:
                    widget.set_date(val)

            # champ classique
            elif isinstance(widget, ctk.CTkEntry):
                widget.delete(0, tk.END)
                widget.insert(0, val or "")

            # CTkOptionMenu dans self.entries : on ignore, il est géré plus bas
            # (sinon on planterait car CTkOptionMenu n’a pas delete/insert)

        # Positionnement des OptionMenus hors self.entries
        # motif
        label = self.code_to_label.get(
            rec['motif_code'] if isinstance(rec, dict) else rec.motif_code
        )
        self.motif_var.set(label)

        # marital_status
        ms = rec['marital_status'] if isinstance(rec, dict) else rec.marital_status
        self.marital_var.set(next(d for d, v in self.marital_options if v == ms))

        # severity
        sv = rec['severity'] if isinstance(rec, dict) else rec.severity
        self.severity_var.set(next(d for d, v in self.severity_options if v == sv))


    def _show_error(self, msg):
        ctk.CTkLabel(self, text=msg, text_color="red").grid(row=0, column=0, columnspan=6, pady=5)
    def _show_info(self, msg):
        ctk.CTkLabel(self, text=msg, text_color="green").grid(row=0, column=0, columnspan=6, pady=5)


    
