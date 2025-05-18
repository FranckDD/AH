# hospital_sih.py
import tkinter as tk
import customtkinter as ctk
from PIL import Image

# -------------------- Modèle --------------------
class HospitalModel:
    def __init__(self):
        self.stats = {
            'patients': 890,
            'surgeries': 3,
            'discharges': 2,
            'opd_patients': 360,
            'lab_tests': 980,
            'earnings': 98000
        }
    
    def get_stats(self):
        return self.stats.copy()

# ----------------- Contrôleur -------------------
class HospitalController:
    def __init__(self, model):
        self.model = model
        
    def get_current_stats(self):
        return self.model.get_stats()
    
    def update_statistic(self, stat_key, new_value):
        if stat_key in self.model.stats:
            self.model.stats[stat_key] = new_value
            return True
        return False

# -------------------- Vue -----------------------
class HospitalApp(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._configure_app()
        self._create_interface()
        
    def _configure_app(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("Gestion Hospitalière SIH")
        self.geometry("1280x800")
        self.minsize(1024, 600)
        
    def _create_interface(self):
        self._setup_sidebar()
        self._setup_main_content()
        
    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        # En-tête sidebar
        ctk.CTkLabel(self.sidebar, 
                   text="SIH Médical",
                   font=ctk.CTkFont(size=22, weight="bold")).pack(pady=40)
        
        # Menu de navigation
        nav_items = [
            ("Tableau de bord", "home"),
            ("Gestion patients", "patients"),
            ("Personnel médical", "staff"),
            ("Planning", "calendar"),
            ("Urgences", "emergency")
        ]
        
        for text, icon in nav_items:
            self._create_nav_item(text, icon)
            
    def _create_nav_item(self, text, icon_name):
        btn = ctk.CTkButton(
            self.sidebar,
            text=text,
            image=ctk.CTkImage(Image.open(f"assets/logo_light.png")),
            compound="left",
            anchor="w",
            fg_color="transparent",
            hover_color="#e0e0e0"
        )
        btn.pack(fill="x", padx=15, pady=8)
    
    def _setup_main_content(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # En-tête principal
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill="x")
        
        ctk.CTkLabel(header, 
                   text="Bonjour, Dr. Patrick Kim",
                   font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        # Conteneur des statistiques
        self.stats_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.stats_container.pack(fill="both", expand=True, pady=30)
        
        # Mise à jour initiale
        self.update_statistics_display()
        
    def update_statistics_display(self):
        stats = self.controller.get_current_stats()
        
        stats_data = [
            ("Patients", stats['patients'], "+40%"),
            ("Chirurgies", stats['surgeries'], "+15%"),
            ("Sorties", stats['discharges'], "+5%"),
            ("Consultations", stats['opd_patients'], "+30%"),
            ("Analyses", stats['lab_tests'], "+60%"),
            ("Revenus", f"${stats['earnings']:,}", "+20%")
        ]
        
        # Nettoyer l'affichage existant
        for widget in self.stats_container.winfo_children():
            widget.destroy()
            
        # Créer les nouvelles cartes
        row = col = 0
        for title, value, variation in stats_data:
            self._create_stat_card(title, value, variation, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
    def _create_stat_card(self, title, value, variation, row, col):
        card = ctk.CTkFrame(self.stats_container, width=320, height=160)
        card.grid(row=row, column=col, padx=15, pady=15)
        
        # Style de la carte
        card.configure(border_width=1, border_color="#e0e0e0")
        
        # Contenu
        ctk.CTkLabel(card, 
                    text=title,
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(15, 5), padx=15)
        
        ctk.CTkLabel(card, 
                    text=str(value),
                    font=ctk.CTkFont(size=28)).pack(anchor="w", padx=15)
        
        ctk.CTkLabel(card, 
                    text=variation,
                    text_color="#2ecc71",
                    font=ctk.CTkFont(size=12)).pack(anchor="w", pady=5, padx=15)

# ----------------- Lancement --------------------
if __name__ == "__main__":
    # Configuration initiale
    ctk.set_appearance_mode("light")
    
    # Création des composants
    model = HospitalModel()
    controller = HospitalController(model)
    app = HospitalApp(controller)
    
    # Lancement de l'application
    app.mainloop()