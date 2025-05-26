# AH2
git pour le projet de systeme de gestion hospitalier

self.dashboard_frame = DashboardView(
                parent     = self,
                user       = user,
                controller = self.controller,      # ← passez ici votre AuthController
                on_logout  = self._on_logout
            )
            self.dashboard_frame.pack(expand=True, fill="both")

Admin123!  admin_test

 username = self.username_entry.get().strip()
            password = self.password_entry.get().strip()

            # On vérifie d'abord l'existence et l'état actif du compte
            tmp = self.controller.user_repo.get_user_by_username(username)
            if tmp and not tmp.is_active:
                # Compte désactivé : on l’affiche clairement
                self._show_error("Votre compte a été désactivé. Contactez l'administrateur.")
                   return

            user = self.controller.authenticate(username, password)