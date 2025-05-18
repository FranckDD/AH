import tkinter as tk
import customtkinter as ctk
from PIL import Image
import os

# Tes vues existantes
from view.doctor_views.doctors_dashboard_view import DoctorsDashboardView
from view.doctor_views.doctors_list_view import DoctorsListView
from view.doctor_views.doctors_edit_view import DoctorsEditView
from view.patient_view.patients_dashboard_view import PatientsDashboardView
from view.patient_view.patients_list_view import PatientListView
from view.patient_view.patients_edit_view import PatientsEditView
from view.appointment_views.appointments_dashboard_view import AppointmentsDashboardView
from view.appointment_views.appointments_list_view import AppointmentsListView
from view.appointment_views.appointments_book_view import AppointmentsBookView

# Appliquer thème
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, user, on_logout=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.on_logout = on_logout
        self.sidebar_expanded = True

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_topbar()
        self._build_content()

        self.show_doctors_dashboard()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color="#FFFFFF", corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.toggle_btn = ctk.CTkButton(self.sidebar, text="<", width=30, command=self.toggle_sidebar)
        self.toggle_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        img = Image.open(os.path.join("assets", "logo_light.png"))
        logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
        self.logo_label = ctk.CTkLabel(self.sidebar, image=logo_img, text=" One Health", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # Médecins
        self.docs_btn = ctk.CTkButton(self.sidebar, text="Médecins", command=self._toggle_docs_sub)
        self.docs_btn.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.docs_sub = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ctk.CTkButton(self.docs_sub, text="Dashboard Médecins", command=self.show_doctors_dashboard).pack(fill="x", padx=25, pady=2)
        ctk.CTkButton(self.docs_sub, text="Liste Médecins", command=self.show_doctors_list).pack(fill="x", padx=25, pady=2)
        ctk.CTkButton(self.docs_sub, text="Ajouter/Éditer Médecin", command=self.show_doctors_edit).pack(fill="x", padx=25, pady=2)

        # Patients
        self.pats_btn = ctk.CTkButton(self.sidebar, text="Patients", command=self._toggle_pats_sub)
        self.pats_btn.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        self.pats_sub = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ctk.CTkButton(self.pats_sub, text="Dashboard Patients", command=self.show_patients_dashboard).pack(fill="x", padx=25, pady=2)
        ctk.CTkButton(self.pats_sub, text="Liste Patients", command=self.show_patients_list).pack(fill="x", padx=25, pady=2)
        ctk.CTkButton(self.pats_sub, text="Ajouter/Éditer Patient", command=self.show_patients_edit).pack(fill="x", padx=25, pady=2)

        # RDV
        self.apps_btn = ctk.CTkButton(self.sidebar, text="RDV", command=self._toggle_apps_sub)
        self.apps_btn.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
        self.apps_sub = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        ctk.CTkButton(self.apps_sub, text="Dashboard RDV", command=self.show_appointments_dashboard).pack(fill="x", padx=25, pady=2)
        ctk.CTkButton(self.apps_sub, text="Liste RDV", command=self.show_appointments_list).pack(fill="x", padx=25, pady=2)
        ctk.CTkButton(self.apps_sub, text="Prendre RDV", command=self.show_appointments_book).pack(fill="x", padx=25, pady=2)

    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(self, height=60, fg_color="#FFFFFF", corner_radius=0)
        self.topbar.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 0))
        for idx, w in enumerate((0, 0, 1, 0, 0)):
            self.topbar.grid_columnconfigure(idx, weight=w)

        img = Image.open(os.path.join("assets", "logo_light.png"))
        burger_img = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
        ctk.CTkButton(self.topbar, image=burger_img, command=self.toggle_sidebar, fg_color="transparent", corner_radius=0, width=30, height=30).grid(row=0, column=0, padx=10)

        self.search_entry = ctk.CTkEntry(self.topbar, placeholder_text="🔍 Rechercher...")
        self.search_entry.grid(row=0, column=2, sticky="ew", padx=10)

        self.notif_btn = ctk.CTkButton(self.topbar, text="🔔", width=30, height=30, fg_color="transparent")
        self.notif_btn.grid(row=0, column=3, padx=10)

        self.profile_btn = ctk.CTkButton(self.topbar, text=self.user.full_name + " ▼", width=120, command=self._open_profile_menu)
        self.profile_btn.grid(row=0, column=4, padx=10)

        self.profile_menu = tk.Menu(self.profile_btn, tearoff=0)
        self.profile_menu.add_command(label="Paramètres", command=self._show_settings)
        self.profile_menu.add_command(label="Éditer Profil", command=self._show_edit_profile)
        self.profile_menu.add_command(label="Changer MDP", command=self._show_change_password)
        self.profile_menu.add_separator()
        self.profile_menu.add_command(label="Déconnexion", command=self._logout)

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color="#F5F5F5", corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=(10, 10))

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.configure(width=60)
            self.toggle_btn.configure(text=">")
            self.logo_label.configure(text="")
            for btn in (self.docs_btn, self.pats_btn, self.apps_btn):
                btn.configure(text="")
            self._hide_all_submenus()
        else:
            self.sidebar.configure(width=200)
            self.toggle_btn.configure(text="<")
            self.logo_label.configure(text=" One Health")
            self.docs_btn.configure(text="Médecins")
            self.pats_btn.configure(text="Patients")
            self.apps_btn.configure(text="RDV")
        self.sidebar_expanded = not self.sidebar_expanded

    def _hide_all_submenus(self):
        self.docs_sub.grid_forget()
        self.pats_sub.grid_forget()
        self.apps_sub.grid_forget()

    def _toggle_docs_sub(self):
        self._hide_all_submenus()
        if self.docs_sub.winfo_ismapped():
            self.docs_sub.grid_forget()
        else:
            self.docs_sub.grid(row=3, column=0, sticky="nw")

    def _toggle_pats_sub(self):
        self._hide_all_submenus()
        if self.pats_sub.winfo_ismapped():
            self.pats_sub.grid_forget()
        else:
            self.pats_sub.grid(row=5, column=0, sticky="nw")

    def _toggle_apps_sub(self):
        self._hide_all_submenus()
        if self.apps_sub.winfo_ismapped():
            self.apps_sub.grid_forget()
        else:
            self.apps_sub.grid(row=7, column=0, sticky="nw")

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def show_doctors_dashboard(self):
        self._clear_content()
        DoctorsDashboardView(self.content).pack(expand=True, fill="both")

    def show_doctors_list(self):
        self._clear_content()
        DoctorsListView(self.content).pack(expand=True, fill="both")

    def show_doctors_edit(self):
        self._clear_content()
        DoctorsEditView(self.content).pack(expand=True, fill="both")

    def show_patients_dashboard(self):
        self._clear_content()
        PatientsDashboardView(self.content).pack(expand=True, fill="both")

    def show_patients_list(self):
        self._clear_content()
        PatientListView(self.content).pack(expand=True, fill="both")

    def show_patients_edit(self):
        self._clear_content()
        PatientsEditView(self.content).pack(expand=True, fill="both")

    def show_appointments_dashboard(self):
        self._clear_content()
        AppointmentsDashboardView(self.content).pack(expand=True, fill="both")

    def show_appointments_list(self):
        self._clear_content()
        AppointmentsListView(self.content).pack(expand=True, fill="both")

    def show_appointments_book(self):
        self._clear_content()
        AppointmentsBookView(self.content).pack(expand=True, fill="both")

    def _open_profile_menu(self):
        x = self.profile_btn.winfo_rootx()
        y = self.profile_btn.winfo_rooty() + self.profile_btn.winfo_height()
        self.profile_menu.tk_popup(x, y)

    def _show_settings(self): pass
    def _show_edit_profile(self): pass
    def _show_change_password(self): pass

    def _logout(self):
        if callable(self.on_logout):
            self.on_logout()


#main
from models.database import DatabaseManager
from view.auth_view import AuthView
from controller.auth_controller import AuthController
import sys

def main():
    # Initialisation de la base de données
    db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
    db.create_tables()

    # Initialisation du contrôleur
    auth_controller = AuthController()

    # Création de la vue
    app = AuthView(auth_controller)
    
    try:
        app.mainloop()
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
    finally:
        db.engine.dispose()

if __name__ == "__main__":
    main()