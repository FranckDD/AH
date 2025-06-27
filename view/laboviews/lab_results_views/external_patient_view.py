import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox


class ExternalPatientForm(ctk.CTkFrame):
    def __init__(self, parent, controller, on_submit=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.on_submit = on_submit
        self._build_ui()
        
    def _build_ui(self):
        form = ctk.CTkFrame(self)
        form.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Champs pour les informations du patient
        ctk.CTkLabel(form, text="Prénom:").grid(row=0, column=0, sticky="w")
        self.first_name = ctk.CTkEntry(form)
        self.first_name.grid(row=0, column=1, pady=5, sticky="ew")
        
        ctk.CTkLabel(form, text="Nom:").grid(row=1, column=0, sticky="w")
        self.last_name = ctk.CTkEntry(form)
        self.last_name.grid(row=1, column=1, pady=5, sticky="ew")
        
        ctk.CTkLabel(form, text="Date de naissance:").grid(row=2, column=0, sticky="w")
        self.birth_date = ctk.CTkEntry(form, placeholder_text="JJ/MM/AAAA")
        self.birth_date.grid(row=2, column=1, pady=5, sticky="ew")
        
        ctk.CTkLabel(form, text="Sexe:").grid(row=3, column=0, sticky="w")
        self.sex = ctk.CTkComboBox(form, values=["M", "F"])
        self.sex.grid(row=3, column=1, pady=5, sticky="ew")
        
        # Bouton de soumission
        submit_btn = ctk.CTkButton(
            form, 
            text="Enregistrer Patient Externe",
            command=self._submit
        )
        submit_btn.grid(row=4, column=0, columnspan=2, pady=10)
        
        form.grid_columnconfigure(1, weight=1)
        
    def _submit(self):
        # Récupérer les données
        data = {
            "first_name": self.first_name.get(),
            "last_name": self.last_name.get(),
            "birth_date": self.birth_date.get(),
            "sex": self.sex.get()
        }
        
        # Générer le code patient externe
        code_patient = self.controller.generate_external_patient_code()
        
        # Si callback fourni, transmettre données + code
        if callable(self.on_submit):
            self.on_submit(data, code_patient)