import customtkinter as ctk
from controller.dashboard_controller import DashboardController

class DoctorsEditView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        ctk.CTkLabel(self, text="Ajouter / Éditer Médecin", font=(None, 16)).pack(pady=(10, 0))

        form = ctk.CTkFrame(self)
        form.pack(padx=20, pady=20, fill="x")

        # Champ Nom complet
        ctk.CTkLabel(form, text="Nom complet").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ctk.CTkEntry(form)
        self.name_entry.grid(row=0, column=1, pady=5, sticky="ew")

        # Champ Spécialité
        ctk.CTkLabel(form, text="Spécialité").grid(row=1, column=0, sticky="w", pady=5)
        self.spec_entry = ctk.CTkEntry(form)
        self.spec_entry.grid(row=1, column=1, pady=5, sticky="ew")

        form.grid_columnconfigure(1, weight=1)

        # Bouton Enregistrer
        self.save_btn = ctk.CTkButton(self, text="Enregistrer", command=self._on_save)
        self.save_btn.pack(pady=10)

    def _on_save(self):
        name = self.name_entry.get().strip()
        spec = self.spec_entry.get().strip()
        # TODO: appeler DashboardController pour créer ou mettre à jour
        controller = DashboardController()
        # ex: controller.create_doctor(name, spec)
        print(f"Enregistré: {name}, spécialité: {spec}")
