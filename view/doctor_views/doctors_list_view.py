import customtkinter as ctk
from controller.dashboard_controller import DashboardController

class DoctorsListView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        ctk.CTkLabel(self, text="Liste des Médecins", font=(None, 16)).pack(pady=(10, 0))

        # Table des médecins
        self.tree = ctk.CTkTreeview(self, columns=("Nom", "Spécialité"), show='headings')
        self.tree.heading("Nom", text="Nom")
        self.tree.heading("Spécialité", text="Spécialité")
        self.tree.pack(expand=True, fill="both", padx=10, pady=10)

        self._load_data()

    def _load_data(self):
        controller = DashboardController()
        doctors = controller.get_doctors()
        for doc in doctors:
            self.tree.insert("", "end", values=(doc.full_name, getattr(doc, 'specialty', '')))