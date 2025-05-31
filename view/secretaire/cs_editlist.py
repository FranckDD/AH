import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime

class CSEditView(ctk.CTkFrame):
    def __init__(self, parent, controller, consultation=None, on_save=None, on_delete=None):
        super().__init__(parent)
        self.controller = controller
        self.consultation = consultation  # instance or None for new
        self.on_save = on_save
        self.on_delete = on_delete
        self._build_form()
        if consultation:
            self._load_consultation()

    def _build_form(self):
        # Grid layout
        for i in range(2): self.grid_columnconfigure(i, weight=1)
        row = 0
        # Patient code (searchable)
        ctk.CTkLabel(self, text="Patient (code):").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.patient_code_var = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self.patient_code_var)
        entry.grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        entry.bind("<Return>", lambda e: self._search_patient())
        row += 1
        # Type consultation
        ctk.CTkLabel(self, text="Type de consultation:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.type_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.type_var).grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        # Prescriptions
        ctk.CTkLabel(self, text="Presc. Générique:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.presc_gen_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.presc_gen_var).grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        ctk.CTkLabel(self, text="Presc. Méd. Spir.:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.presc_med_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.presc_med_var).grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        # MP type
        ctk.CTkLabel(self, text="MP Type:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.mp_type_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.mp_type_var).grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        # Dates
        ctk.CTkLabel(self, text="Date inscription:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.registered_entry = DateEntry(self, date_pattern='yyyy-mm-dd')
        self.registered_entry.grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        ctk.CTkLabel(self, text="Date RDV:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.appointment_entry = DateEntry(self, date_pattern='yyyy-mm-dd')
        self.appointment_entry.grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        # Amount paid
        ctk.CTkLabel(self, text="Montant payé:").grid(row=row, column=0, sticky='e', padx=10, pady=5)
        self.amount_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self.amount_var).grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        # Observation
        ctk.CTkLabel(self, text="Observation:").grid(row=row, column=0, sticky='ne', padx=10, pady=5)
        self.observation_text = ctk.CTkTextbox(self, width=300, height=80)
        self.observation_text.grid(row=row, column=1, sticky='ew', padx=10, pady=5)
        row += 1
        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="Enregistrer", command=self._on_save).pack(side='left', padx=10)
        if self.consultation:
            ctk.CTkButton(btn_frame, text="Supprimer", fg_color="#D32F2F", command=self._on_delete).pack(side='left', padx=10)

    def _search_patient(self):
        code = self.patient_code_var.get().strip()
        patient = self.controller.find_patient(code)
        if patient:
            # maybe show patient name or ID
            tk.messagebox.showinfo("Patient trouvé", f"Patient: {patient.last_name} {patient.first_name}")
        else:
            tk.messagebox.showerror("Introuvable", "Aucun patient avec ce code.")

    def _load_consultation(self):
        cs = self.consultation
        # Remplissage du code patient
        self.patient_code_var.set(cs.patient.code_patient if cs.patient else "")

        # Type de consultation
        self.type_var.set(cs.type_consultation or "")

        # Prescriptions
        self.presc_gen_var.set(cs.presc_generic or "")
        self.presc_med_var.set(cs.presc_med_spirituel or "")
        self.mp_type_var.set(cs.mp_type or "")

        # Dates (DateEntry accepte déjà une date ou on laisse vide si None)
        if cs.fr_registered_at:
            self.registered_entry.set_date(cs.fr_registered_at)
        else:
            # optionnel : vider la DateEntry si le widget le permet
            pass

        if cs.fr_appointment_at:
            self.appointment_entry.set_date(cs.fr_appointment_at)
        else:
            pass

        # Montant payé : on ne formatte que si ce n'est pas None
        if cs.fr_amount_paid is not None:
            self.amount_var.set(f"{cs.fr_amount_paid:.2f}")
        else:
            self.amount_var.set("")

        # Observation (CTkTextbox)
        self.observation_text.delete("1.0", "end")
        if cs.fr_observation:
            self.observation_text.insert("1.0", cs.fr_observation)


    def _on_save(self):
        data = {}
        # Gather and validate fields
        data['patient_code'] = self.patient_code_var.get().strip()
        data['type_consultation'] = self.type_var.get().strip()
        data['presc_generic'] = self.presc_gen_var.get().strip()
        data['presc_med_spirituel'] = self.presc_med_var.get().strip()
        data['mp_type'] = self.mp_type_var.get().strip()
        try:
            data['registered_at'] = datetime.strptime(self.registered_entry.get(), "%Y-%m-%d")
            data['appointment_at'] = datetime.strptime(self.appointment_entry.get(), "%Y-%m-%d")
            data['amount_paid'] = float(self.amount_var.get().strip() or 0)
        except Exception as e:
            return tk.messagebox.showerror("Erreur", str(e))
        data['observation'] = self.observation_text.get("1.0", "end").strip()

        if self.consultation:
            self.controller.update_consultation(self.consultation.consultation_id, data)
        else:
            self.controller.create_consultation(data)
        if self.on_save:
            self.on_save()

    def _on_delete(self):
        if tk.messagebox.askyesno("Confirmer", "Supprimer cette consultation ?"):
            self.controller.delete_consultation(self.consultation.consultation_id)
            if self.on_delete:
                self.on_delete()
