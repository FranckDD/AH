import customtkinter as ctk
from PIL import Image
from view.factory.dashboard_factory import get_dashboard_class
import os

# Appliquer thème plus doux
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

# ================== AuthView ==================
class AuthView(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("One Health - Authentification")
        self.geometry("400x600")  # Taille login
        self.resizable(False, False)
        

        # Intercepter fermeture fenêtre (croix)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.dashboard_frame = None
        self._setup_ui()


    def _setup_ui(self):
        # (Re)création du formulaire de login
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill="both", padx=40, pady=40)

        # Logo
        logo = ctk.CTkImage(
            light_image=Image.open("assets/logo_light.png"),
            dark_image=Image.open("assets/logo_dark.png"),
            size=(150, 150)
        )
        ctk.CTkLabel(self.main_frame, image=logo, text="").pack(pady=20)

        # Champs login
        self.username_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Nom d'utilisateur", height=50, corner_radius=10)
        self.username_entry.pack(fill="x", pady=10)
        self.password_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Mot de passe", show="•", height=50, corner_radius=10)
        self.password_entry.pack(fill="x", pady=10)

        # Bouton connexion
        ctk.CTkButton(
            self.main_frame,
            text="Se connecter",
            height=50,
            corner_radius=10,
            command=self._on_login
        ).pack(fill="x", pady=20)

    def _on_login(self):
        try:
            username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()

            # On vérifie d'abord l'existence et l'état actif du compte
            tmp = self.controller.user_repo.get_user_by_username(username)
            if tmp and not tmp.is_active:
                # Compte désactivé : on l’affiche clairement
                self._show_error("Votre compte a été désactivé. Contactez l'administrateur.")
                return

            user = self.controller.authenticate(username, password)
            if not user:
                raise ValueError("Identifiants incorrects")
            
            #print(f"[Console] Rôle métier récupéré : {user.application_role.role_name}")

            # Importer et afficher DashboardView
            from view.dashboard_view import DashboardView
            
            # → ICI : on choisit la bonne classe de Dashboard
            role_key = user.application_role.role_name
            DashboardCls = get_dashboard_class(role_key)

            # et on l’affiche
            self.dashboard_frame  = DashboardCls(
            self,              # parent
            user,              # User SQLAlchemy
            self.controller,   # AuthController
            self._on_logout    # callback
            )
            self.dashboard_frame.pack(expand=True, fill="both")

             # Détruire le login
            self.main_frame.destroy()

            # Ajuster la taille pour le dashboard
            self.geometry("1024x768")
            self.resizable(True, True)

        except Exception as e:
            # Afficher l'erreur
            self._show_error(str(e))

    def _show_error(self, message):
        # Supprime anciens messages
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and getattr(widget, 'fg_color', '') == "#FEE2E2":
                widget.destroy()
        # Affiche le nouveau
        error_frame = ctk.CTkFrame(self.main_frame, fg_color="#FEE2E2")
        ctk.CTkLabel(error_frame, text=message, text_color="#DC2626").pack(padx=10, pady=5)
        error_frame.pack(fill="x", pady=10)

    def _on_logout(self):
        # **Ici** : déconnexion → on ne ferme PAS l'app, juste on revient au login.
        # 1) Détruit le dashboard
        if self.dashboard_frame:
            self.dashboard_frame.destroy()
            self.dashboard_frame = None

        # 2) Réinitialise la taille & UI login
        self.geometry("400x600")
        self.resizable(False, False)
        # Supprime éventuels restes
        for widget in self.winfo_children():
            widget.destroy()
        # Recrée l'UI de login
        self._setup_ui()

    def _on_closing(self):
        # Détruire d’abord le Dashboard si présent
        if hasattr(self, "dashboard_frame") and self.dashboard_frame:
            self.dashboard_frame.destroy()

        try:
            self.quit()
        except Exception:
            pass

        super().destroy()

    def _tk_error_handler(self, exc, val, tb):
        # Ici on ignore simplement les erreurs après destruction
        return