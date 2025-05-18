# app.py
import psycopg2
from passlib.hash import bcrypt
import customtkinter as ctk
import tkinter.messagebox as messagebox


class AuthService:
    """Service chargé de l'authentification."""
    def __init__(self, db_config):
        self.db_config = db_config

    def authenticate(self, username: str, password: str) -> bool:
        # 1) Connexion à la BDD
        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()
        cur.execute(
            "SELECT password_hash FROM public.users WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return False

        stored_hash = row[0]
        # 2) Vérification du mot de passe
        return bcrypt.verify(password, stored_hash)


class LoginView(ctk.CTk):
    """Vue : la fenêtre de connexion."""
    def __init__(self):
        super().__init__()
        self.title("Connexion")
        self.geometry("300x180")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.username_input = ctk.CTkEntry(self, placeholder_text="Nom d’utilisateur")
        self.username_input.pack(pady=(20, 10), padx=20)

        self.password_input = ctk.CTkEntry(self, placeholder_text="Mot de passe", show="*")
        self.password_input.pack(pady=10, padx=20)

        self.login_button = ctk.CTkButton(self, text="Se connecter")
        self.login_button.pack(pady=20)

    def show_error(self, msg: str):
        messagebox.showerror(title="Erreur", message=msg)


class MainView(ctk.CTk):
    """Vue principale, après connexion réussie."""
    def __init__(self):
        super().__init__()
        self.title("Application Médicale")
        self.geometry("400x300")
        label = ctk.CTkLabel(self, text="Bienvenue dans l’application !")
        label.pack(pady=50)


class AuthController:
    """Contrôleur : relie la vue au service."""
    def __init__(self, db_config):
        # initialisation
        self.auth_service = AuthService(db_config)
        self.login_view = LoginView()
        # liaison du bouton au handler
        self.login_view.login_button.configure(command=self.handle_login)
        self.login_view.mainloop()

    def handle_login(self):
        user = self.login_view.username_input.get()
        pwd  = self.login_view.password_input.get()

        if self.auth_service.authenticate(user, pwd):
            # succès : fermer le login et ouvrir la fenêtre principale
            self.login_view.destroy()
            main_view = MainView()
            main_view.mainloop()
        else:
            # échec : message d’erreur
        # affichage de l’erreur
            self.login_view.show_error("Identifiants invalides !")



if __name__ == "__main__":
    # Configuration de connexion à PostgreSQL
    db_conf = {
        "host":     "localhost",
        "dbname":   "AH2",
        "user":     "postgres",
        "password": "Admin_2025",
        "port":     5432,
    }
    AuthController(db_conf)
