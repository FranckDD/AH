# view/secretaire/tx_form.py
import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox

class TxFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, patient_ctrl, tx_type, on_save=None):
        super().__init__(master)
        self.title("Nouvelle Transaction")
        self.controller = controller
        self.patient_ctrl = patient_ctrl
        self.tx_type = tx_type
        self.on_save = on_save
        self.patient_id = None

        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20)

        # Code patient
        ctk.CTkLabel(frame, text="Code patient:").grid(row=0, column=0, sticky="w")
        self.var_code = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.var_code).grid(row=0, column=1)
        ctk.CTkButton(frame, text="Charger", command=self.load_patient).grid(row=0, column=2, padx=5)

        # Montant
        ctk.CTkLabel(frame, text="Montant:").grid(row=1, column=0, sticky="w")
        self.var_amt = tk.DoubleVar()
        ctk.CTkEntry(frame, textvariable=self.var_amt).grid(row=1, column=1)

        # Date
        ctk.CTkLabel(frame, text="Date:").grid(row=2, column=0, sticky="w")
        self.date_entry = DateEntry(frame, date_pattern='yyyy-MM-dd')
        self.date_entry.grid(row=2, column=1)

        # Save
        ctk.CTkButton(self, text="Enregistrer", command=self.save).pack(pady=10)

    def load_patient(self):
        code = self.var_code.get().strip()
        p = self.patient_ctrl.find_by_code(code)
        if not p:
            messagebox.showerror("Erreur", "Patient introuvable")
            return
        self.patient_id = p['patient_id']

    def save(self):
        if not self.patient_id:
            messagebox.showerror("Erreur", "Chargez un patient d'abord")
            return
        data = {
            'patient_id': self.patient_id,
            'amount': self.var_amt.get(),
            'date': self.date_entry.get_date()
        }
        try:
            self.controller.create_transaction(data)
            messagebox.showinfo("Succès", "Transaction enregistrée")
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

