import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime
from tkinter import messagebox

class PrescriptionFormView(ctk.CTkFrame):
    def __init__(self, parent, controller, prescription_id=None, patient_id=None, medical_record_id=None):
        super().__init__(parent, fg_color="white", corner_radius=8)
        self.controller = controller
        self.prescription_id = prescription_id
        self.patient_id = patient_id
        self.medical_record_id = medical_record_id

        # Variables pour le code et le nom du patient
        self.patient_code_var = tk.StringVar()
        self.patient_name_var = tk.StringVar()

        # Placement du frame avec padding
        self.pack(fill='both', expand=True, padx=10, pady=10)

        self._build()
        if prescription_id:
            self._load()

    def _build(self):
        # on définit nos champs avec placeholders
        fields = [
            ('code_patient',      'Code Patient*',    'code',       'Ex : AH2-00123'),
            ('patient_name',      'Nom Patient',      'label',      ''),
            ('medical_record_id','ID Dossier Méd.',   'entry',      'Ex : 12345'),
            ('medication',       'Médicament*',      'entry',      'Ex : Paracétamol'),
            ('dosage',           'Dosage*',          'entry',      'Ex : 500mg'),
            ('frequency',        'Fréquence*',       'entry',      'Ex : 2 fois/jour'),
            ('duration',         'Durée',            'entry',      'Ex : 5 jours'),
            ('start_date',       'Date début*',      'date',       ''),
            ('end_date',         'Date fin',         'date',       ''),
            ('notes',            'Notes',            'text',       ''),
        ]
        self.entries = {}

        for i, (key, label, typ, placeholder) in enumerate(fields):
            ctk.CTkLabel(self, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=3)

            if typ == 'date':
                w = DateEntry(self, date_pattern='yyyy-mm-dd')
                # highlight via internal entry widget
                try:
                    w._entry.configure(highlightthickness=1, highlightbackground="#ccc")
                except Exception:
                    pass
            elif typ == 'text':
                w = ctk.CTkTextbox(self, height=60)
                w.configure(border_width=1, border_color="#ccc")
            elif typ == 'code':
                w = ctk.CTkEntry(self, textvariable=self.patient_code_var,
                                placeholder_text=placeholder)
                w.configure(border_width=1, border_color="#ccc")
                w.bind("<FocusOut>", self._on_code_focus_out)
            elif typ == 'label':
                w = ctk.CTkLabel(self, textvariable=self.patient_name_var, text_color="gray")
            else:
                w = ctk.CTkEntry(self, placeholder_text=placeholder)
                w.configure(border_width=1, border_color="#ccc")
                if key == 'medical_record_id' and self.medical_record_id:
                    w.insert(0, str(self.medical_record_id))
                    w.configure(state='disabled')

            w.grid(row=i, column=1, sticky='ew', padx=5, pady=3)
            self.entries[key] = w

        btn_text = "Modifier" if self.prescription_id else "Enregistrer"
        ctk.CTkButton(self, text=btn_text, command=self._on_save) \
            .grid(row=len(fields), column=0, columnspan=2, pady=10)

    def _on_code_focus_out(self, event):
        code = self.entries['code_patient'].get().strip()
        if not code:
            self.patient_name_var.set("")
            self.patient_id = None
            return
        try:
            rec = self.controller.find_patient(code)
        except Exception as e:
            print(f"[DEBUG] Erreur find_patient: {e}")
            rec = None
        if not rec:
            self.patient_name_var.set("❌ Code introuvable")
            self.patient_id = None
        else:
            if isinstance(rec, dict):
                last = rec.get('last_name', '')
                first = rec.get('first_name', '')
                pid  = rec.get('patient_id')
            else:
                last  = getattr(rec, 'last_name', '')
                first = getattr(rec, 'first_name', '')
                pid   = getattr(rec, 'patient_id', None)
            self.patient_name_var.set(f"{last} {first}")
            self.patient_id = pid

    def _reset_highlights(self):
        for key, w in self.entries.items():
            if isinstance(w, DateEntry):
                try:
                    w._entry.configure(highlightthickness=1, highlightbackground="#ccc")
                except Exception:
                    pass
            elif isinstance(w, ctk.CTkTextbox):
                w.configure(border_width=1, border_color="#ccc")
            elif isinstance(w, ctk.CTkEntry):
                w.configure(border_width=1, border_color="#ccc")

    def _highlight(self, key):
        w = self.entries.get(key)
        if isinstance(w, DateEntry):
            try:
                w._entry.configure(highlightthickness=2, highlightbackground="red")
            except Exception:
                pass
        elif isinstance(w, ctk.CTkTextbox):
            w.configure(border_width=2, border_color="red")
        elif isinstance(w, ctk.CTkEntry):
            w.configure(border_width=2, border_color="red")

    def _on_save(self):
        self._reset_highlights()
        missing = []
        if not self.patient_id:
            missing.append('code_patient')
        start = self.entries['start_date'].get_date()
        end = self.entries['end_date'].get_date()
        if not start:
            missing.append('start_date')
        if end and end < start:
            missing.extend(['start_date', 'end_date'])
        for key in ('medication', 'dosage', 'frequency'):
            if not self.entries[key].get().strip():
                missing.append(key)

        if missing:
            for key in set(missing):
                self._highlight(key)
            return messagebox.showerror(
                "Erreur", 
                "Veuillez remplir tous les champs obligatoires en rouge."
            )

        data = {
            'patient_id':        self.patient_id,
            'medical_record_id': self.medical_record_id,
            'medication':        self.entries['medication'].get().strip(),
            'dosage':            self.entries['dosage'].get().strip(),
            'frequency':         self.entries['frequency'].get().strip(),
            'duration':          self.entries['duration'].get().strip() or None,
            'start_date':        start,
            'end_date':          end if end else None,
            'notes':             self.entries['notes'].get("1.0", "end-1c").strip() or None
        }

        try:
            if self.prescription_id:
                self.controller.update_prescription(self.prescription_id, data)
            else:
                self.controller.create_prescription(data)
            messagebox.showinfo("Succès", "Prescription enregistrée !")
            self.after(2000, self._reset_form)
        except Exception as e:
            print(f"[DEBUG] Erreur technique: {e}")
            messagebox.showerror(
                "Erreur", 
                "Une erreur est survenue. Veuillez réessayer ou contacter l'administrateur."
            )

    def _reset_form(self):
        self.patient_id = None
        self.patient_code_var.set("")
        self.patient_name_var.set("")
        for key, w in self.entries.items():
            if isinstance(w, ctk.CTkEntry):
                w.configure(state="normal")
                w.delete(0, 'end')
            elif isinstance(w, ctk.CTkTextbox):
                w.delete("1.0", "end")
            elif isinstance(w, DateEntry):
                w.set_date(datetime.today())

    def _load(self):
        rec = self.controller.get_prescription(self.prescription_id)
        # Recharge chaque widget avec les données de la prescription
        for key, w in self.entries.items():
            val = getattr(rec, key, None)
            if val is None:
                continue
            if isinstance(w, DateEntry):
                w.set_date(val)
            elif isinstance(w, ctk.CTkTextbox):
                w.delete("1.0", "end")
                w.insert("1.0", val)
            else:
                w.delete(0, 'end')
                w.insert(0, str(val))
                if key == 'medical_record_id':
                    self.medical_record_id = rec.medical_record_id
                    w.configure(state='disabled')
        # Et on pré-remplit code_patient + patient_name_var
        if rec.patient:
            self.patient_code_var.set(rec.patient.code_patient)
            self.patient_name_var.set(f"{rec.patient.last_name} {rec.patient.first_name}")
            self.patient_id = rec.patient_id

