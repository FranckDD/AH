import customtkinter as ctk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PatientsDashboardView(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        # Titre
        ctk.CTkLabel(self, text="Dashboard des Patients", font=(None, 24, "bold")).pack(pady=20)

        # Cartes statistiques fictives
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        # Carte 1: Nombre total de patients
        card1 = ctk.CTkFrame(stats_frame, corner_radius=10, fg_color="#E0F7FA")
        card1.pack(side="left", expand=True, fill="both", padx=10)
        ctk.CTkLabel(card1, text="Nombre total de patients", font=(None, 14)).pack(pady=(10,0))
        ctk.CTkLabel(card1, text="124", font=(None, 20, "bold")).pack(pady=(0,10))

        # Carte 2: Moyenne de RDV par patient
        card2 = ctk.CTkFrame(stats_frame, corner_radius=10, fg_color="#F1F8E9")
        card2.pack(side="left", expand=True, fill="both", padx=10)
        ctk.CTkLabel(card2, text="Moyenne de RDV / patient", font=(None, 14)).pack(pady=(10,0))
        ctk.CTkLabel(card2, text="2.5", font=(None, 20, "bold")).pack(pady=(0,10))

        # Carte 3: Patients actifs ce mois
        card3 = ctk.CTkFrame(stats_frame, corner_radius=10, fg_color="#FFF3E0")
        card3.pack(side="left", expand=True, fill="both", padx=10)
        ctk.CTkLabel(card3, text="Patients actifs ce mois", font=(None, 14)).pack(pady=(10,0))
        ctk.CTkLabel(card3, text="45", font=(None, 20, "bold")).pack(pady=(0,10))

        # Graphique des RDV sur la semaine
        chart_frame = ctk.CTkFrame(self)
        chart_frame.pack(fill="both", expand=True, padx=20, pady=10)

        days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        appointments = [12, 17, 9, 14, 20, 7, 5]

        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(days, appointments, marker='o')
        ax.set_title("RDV planifiés cette semaine")
        ax.set_xlabel("Jour")
        ax.set_ylabel("Nombre de RDV")

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
