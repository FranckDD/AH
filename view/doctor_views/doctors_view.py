import customtkinter as ctk

class DoctorsView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Liste des Médecins", font=("Arial", 16)).grid(row=0, column=0, pady=10)
        
        # Tableau
        self.tree = ctk.CTkTreeview(self, columns=("Nom", "Spécialité"))
        self.tree.grid(row=1, column=0, padx=10, pady=10)
        
        # Remplir les données
        self._load_data()
    
    def _load_data(self):
        from controller.dashboard_controller import DashboardController
        controller = DashboardController()
        doctors = controller.get_doctors()
        
        for doc in doctors:
            self.tree.insert("", "end", values=(doc.full_name, doc.specialty))