import customtkinter as ctk
from models.database import DatabaseManager
from controller.patient_controller import PatientController
from view.patient_view.patient_form_view import PatientView



class SIHApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SIH - One Hand Humanity")
        self.geometry("800x600")
        
        # Configuration de la base de données
        self.db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
        
        # Initialisation des contrôleurs
        self.patient_controller = PatientController(self.db)
        
        # Interface utilisateur
        self.show_patient_view()
    
    def show_patient_view(self):
        # Remplacer par l'utilisateur authentifié réel
        dummy_user = type('User', (), {'role': 'app_medical', 'id': 1})
        PatientView(self, self.patient_controller, dummy_user).pack(expand=True, fill='both')

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = SIHApp()
    app.mainloop()