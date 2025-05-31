# view/secretaire/stock_form.py
import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox

class StockFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, on_save=None):
        super().__init__(master)
        self.title("Enregistrer Produit")
        self.controller = controller
        self.on_save = on_save
        self.patient_id = None
        self.prescriber_id = None

        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="x")

        # Code patient (optionnel)
        ctk.CTkLabel(frame, text="Code patient (opt.)").grid(row=0, column=0, sticky="w")
        self.var_code = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.var_code).grid(row=0, column=1)
        ctk.CTkButton(frame, text="Charger", command=self.load_patient).grid(row=0, column=2, padx=5)

        # Prescripteur (opt.)
        ctk.CTkLabel(frame, text="Code prescripteur (opt.)").grid(row=1, column=0, sticky="w")
        self.var_prescriber = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.var_prescriber).grid(row=1, column=1)
        ctk.CTkButton(frame, text="Charger", command=self.load_prescriber).grid(row=1, column=2, padx=5)

        # Drug name
        ctk.CTkLabel(frame, text="Nom du produit").grid(row=2, column=0, sticky="w")
        self.var_name = ctk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.var_name).grid(row=2, column=1, columnspan=2, sticky="ew")

        # Quantity
        ctk.CTkLabel(frame, text="Quantité").grid(row=3, column=0, sticky="w")
        self.var_qty = tk.IntVar()
        ctk.CTkEntry(frame, textvariable=self.var_qty).grid(row=3, column=1, columnspan=2, sticky="ew")

        # Type
        ctk.CTkLabel(frame, text="Type").grid(row=4, column=0, sticky="w")
        self.var_type = ctk.StringVar(value="Naturel")
        ctk.CTkComboBox(frame, variable=self.var_type, values=["Naturel","Pharmaceutique"]).grid(row=4, column=1, columnspan=2, sticky="ew")

        # Save
        ctk.CTkButton(self, text="Enregistrer", command=self.save).pack(pady=10)

    def load_patient(self):
        code = self.var_code.get().strip()
        from controller.patient_controller import PatientController
        p = self.master.controllers.patient_controller.find_by_code(code)
        if not p:
            messagebox.showerror("Erreur", "Patient introuvable")
            return
        self.patient_id = p['patient_id']

    def load_prescriber(self):
        code = self.var_prescriber.get().strip()
        from repositories.user_repo import UserRepository
        from controller.user_controller import UserController
        # suppose UserController.find_by_username
        u = self.master.controllers.user_controller.find_by_username(code)
        if not u:
            messagebox.showerror("Erreur", "Utilisateur introuvable")
            return
        self.prescriber_id = u.user_id

    def save(self):
        data = {
            'patient_id': self.patient_id,
            'drug_name': self.var_name.get().strip(),
            'quantity': self.var_qty.get(),
            'medication_type': self.var_type.get(),
            'prescribed_by': self.prescriber_id
        }
        try:
            self.controller.create_product(data)
            messagebox.showinfo("Succès", "Produit enregistré")
            if self.on_save: self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))