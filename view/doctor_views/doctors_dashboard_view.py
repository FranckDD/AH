# view/doctors_dashboard_view.py
import customtkinter as ctk

class DoctorsDashboardView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        ctk.CTkLabel(self, text="Tableau de bord Médecins", font=(None, 20)).pack(pady=20)
        # TODO: Ajouter des statistiques globales (ex: nombre de médecins actifs, etc.)