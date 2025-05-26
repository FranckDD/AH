import customtkinter as ctk

class DefaultDashboardView(ctk.CTkFrame):
    """
    Vue par défaut pour les utilisateurs n'ayant pas de dashboard spécifique.
    Affiche un message et un bouton de déconnexion.
    """
    def __init__(self, parent, user, controller, on_logout=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.user = user
        self.controller = controller
        self.on_logout = on_logout

        # Configuration de la frame
        self.configure(fg_color='transparent')
        self._build_ui()

    def _build_ui(self):
        # Message d'information
        message = (
            f"Utilisateur '{self.user.username}'\n"
            "n'a pas encore de dashboard associé à son rôle."
        )
        label = ctk.CTkLabel(
            self,
            text=message,
            justify='center',
            font=('Arial', 16)
        )
        label.pack(expand=True, fill='both', padx=20, pady=20)

        # Bouton de déconnexion
        btn_logout = ctk.CTkButton(
            self,
            text="Se déconnecter",
            height=40,
            corner_radius=10,
            command=self.on_logout
        )
        btn_logout.pack(pady=(0, 20))
