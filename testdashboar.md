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



    def count_by_status(self,
                        doctor_id: Optional[int] = None,
                        start: Optional[date] = None,
                        end: Optional[date] = None) -> Dict[str, int]:
        doctor_id = doctor_id or getattr(self.user, 'user_id', None)
        if doctor_id is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.count_by_status_for_doctor(doctor_id, start, end)

    def total_appointments(self,
                           doctor_id: Optional[int] = None,
                           start: Optional[date] = None,
                           end: Optional[date] = None) -> int:
        doctor_id = doctor_id or getattr(self.user, 'user_id', None)
        if doctor_id is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.count_total_for_doctor(doctor_id, start, end)

    def appointments_time_series(self,
                                 doctor_id: Optional[int] = None,
                                 start: Optional[date] = None,
                                 end: Optional[date] = None) -> List[Tuple[str, int]]:
        doctor_id = doctor_id or getattr(self.user, 'user_id', None)
        if doctor_id is None:
            raise RuntimeError("Doctor id non disponible")
        # start/end peuvent être None : le repo doit gérer None ou on peut fournir des valeurs ici
        return self.repo.appointments_per_day_for_doctor(doctor_id, start, end)

    def distinct_patients_count(self,
                                doctor_id: Optional[int] = None,
                                start: Optional[date] = None,
                                end: Optional[date] = None) -> int:
        doctor_id = doctor_id or getattr(self.user, 'user_id', None)
        if doctor_id is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.count_distinct_patients_for_doctor(doctor_id, start, end)

    def monthly_breakdown(self, doctor_id: Optional[int] = None, year: Optional[int] = None):
        doctor_id = doctor_id or getattr(self.user, 'user_id', None)
        if doctor_id is None:
            raise RuntimeError("Doctor id non disponible")
        if year is None:
            year = date.today().year
        return self.repo.appointments_per_month_for_doctor(doctor_id, year)

# KPI Medical record repositories

def count_records_for_doctor(self,
                                 doctor_id: int,
                                 start_date: Optional[date] = None,
                                 end_date: Optional[date] = None) -> int:
        # NOTE: si tu n'as pas de doctor_id dans medical_records, on peut compter par created_by
        q = self.session.query(func.count(self.model.record_id))
        q = q.filter(self.model.created_by == doctor_id)
        if start_date:
            q = q.filter(func.date(self.model.consultation_date) >= start_date)
        if end_date:
            q = q.filter(func.date(self.model.consultation_date) <= end_date)
        return int(q.scalar() or 0)

    def breakdown_by_motif_for_doctor(self, doctor_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, int]:
        query = self.session.query(
            MedicalRecord.motif_code, 
            func.count(MedicalRecord.record_id)
        ).filter(MedicalRecord.created_by == doctor_id)
        
        if start_date:
            query = query.filter(MedicalRecord.consultation_date >= start_date)
        if end_date:
            query = query.filter(MedicalRecord.consultation_date <= end_date)
        
        results = query.group_by(MedicalRecord.motif_code).all()
        return {motif: count for motif, count in results}

# dashboard doctor
# view/doctor_views/doctors_dashboard_view.py
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class DoctorsDashboardView(ctk.CTkFrame):
    """
    Dashboard Médecin (vue principale).
    Signature :
      parent, user, controller, on_logout=None

    Le `controller` passé doit exposer au minimum :
      - appointment_controller (avec les wrappers KPI : count_by_status, total_appointments, ...)
      - patient_controller
      - prescription_controller (renewals_for_doctor)
      - medical_record_controller (count_records_for_doctor, consultation_type_distribution)
    Tous les appels sont faits de façon défensive (try/except).
    """
    def __init__(self, parent, user, controller, on_logout=None, on_start_consultation=None, on_open_record=None):
        super().__init__(parent)

        # stocker refs
        self.user = user
        self.controller = controller
        self.on_logout = on_logout
        self.on_start_consultation = on_start_consultation
        self.on_open_record = on_open_record

        # controllers shortcuts (peuvent être None)
        self.appt_ctrl = getattr(controller, "appointment_controller", None)
        self.pat_ctrl = getattr(controller, "patient_controller", None)
        self.presc_ctrl = getattr(controller, "prescription_controller", None)
        self.medrec_ctrl = getattr(controller, "medical_record_controller", None)
        self.lab_ctrl = getattr(controller, "lab_controller", None)

        # Layout grid
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=0)   # KPI row
        self.grid_rowconfigure(2, weight=1)   # sessions area
        self.grid_rowconfigure(3, weight=1)   # results / bottom area
        self.grid_columnconfigure(0, weight=1)

        # build UI
        self._build_header()
        self._build_kpis()
        self._build_sessions_area()

        # initial load (async)
        self._refresh_all_async()

    # ---------------------------
    # Header
    # ---------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, height=60, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        header.grid_propagate(False)

        # determine title prefix based on role
        role_name = ""
        try:
            role_obj = getattr(self.user, "application_role", None)
            role_name = (getattr(role_obj, "role_name", "") or "").lower()
        except Exception:
            role_name = ""

        title_prefix = "M."  # fallback neutral
        if "med" in role_name:
            title_prefix = "Dr."
        elif "infirm" in role_name or "nurs" in role_name:
            title_prefix = "M./Mme"  # we don't infer gender here

        fullname = getattr(self.user, "full_name", getattr(self.user, "username", ""))
        title_text = f"Bienvenue {title_prefix} {fullname} — {role_name.title() if role_name else ''}"
        self.title_lbl = ctk.CTkLabel(header, text=title_text, font=ctk.CTkFont(size=16, weight="bold"))
        self.title_lbl.pack(side="left", padx=(16,8))

        # date/time
        now = datetime.now().strftime("%A %d %B %Y %H:%M")
        self.date_lbl = ctk.CTkLabel(header, text=now)
        self.date_lbl.pack(side="left", padx=8)

        # spacer
        spacer = ctk.CTkLabel(header, text="")
        spacer.pack(side="left", expand=True)

        # logout
        if callable(self.on_logout):
            ctk.CTkButton(header, text="Se déconnecter", command=self.on_logout).pack(side="right", padx=12)

    # ---------------------------
    # KPI cards row
    # ---------------------------
    def _build_kpis(self):
        kpi_frame = ctk.CTkFrame(self)
        kpi_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0,8))
        kpi_frame.grid_columnconfigure((0,1,2,3), weight=1)  # 4 cards

        # card helpers
        def make_card(parent, title):
            f = ctk.CTkFrame(parent, corner_radius=8, height=80)
            f.pack_propagate(False)
            lbl_title = ctk.CTkLabel(f, text=title, anchor="w", font=ctk.CTkFont(size=12))
            lbl_value = ctk.CTkLabel(f, text="—", anchor="w", font=ctk.CTkFont(size=20, weight="bold"))
            lbl_title.pack(anchor="w", padx=12, pady=(8,0))
            lbl_value.pack(anchor="w", padx=12)
            return f, lbl_value

        # Card 1 : Total patients distincts (période par défaut: semaine)
        self.card1_frame, self.lbl_total_patients = make_card(kpi_frame, "Patients distincts (7j)")
        self.card1_frame.grid(row=0, column=0, padx=6, sticky="nsew")

        # Card 2 : RDV prévus aujourd'hui
        self.card2_frame, self.lbl_appts_today = make_card(kpi_frame, "RDV prévus aujourd'hui")
        self.card2_frame.grid(row=0, column=1, padx=6, sticky="nsew")

        # Card 3 : RDV statut breakdown (pending / completed / cancelled)
        self.card3_frame, self.lbl_status_breakdown = make_card(kpi_frame, "Breakdown RDV (aujourd'hui)")
        self.card3_frame.grid(row=0, column=2, padx=6, sticky="nsew")

        # Card 4 : Ordonnances à renouveler (14j)
        self.card4_frame, self.lbl_renewals = make_card(kpi_frame, "Ordonnances à renouveler (14j)")
        self.card4_frame.grid(row=0, column=3, padx=6, sticky="nsew")

        # small refresh
        ctk.CTkButton(kpi_frame, text="Rafraîchir", width=90, command=self._refresh_all_async).grid(row=0, column=4, padx=(8,0))

    # ---------------------------
    # Sessions area (3 blocs)
    # ---------------------------
    def _build_sessions_area(self):
        sessions = ctk.CTkFrame(self)
        sessions.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0,8))
        sessions.grid_columnconfigure(0, weight=1)
        sessions.grid_columnconfigure(1, weight=1)
        sessions.grid_rowconfigure(0, weight=1)
        sessions.grid_rowconfigure(1, weight=1)  # pour la zone résultats sous les 2 colonnes

        # Left column: Consultations du jour (session)
        self.consult_frame = ctk.CTkFrame(sessions, corner_radius=8)
        self.consult_frame.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=6)
        self._build_consult_section(self.consult_frame)

        # Right top: Patients suivis (session)
        self.patients_frame = ctk.CTkFrame(sessions, corner_radius=8)
        self.patients_frame.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=6)
        self._build_patients_section(self.patients_frame)

        # Results section: placed under both columns, row=1, columnspan=2
        self.results_frame = ctk.CTkFrame(sessions, corner_radius=8)
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(6,0))
        self._build_results_section(self.results_frame)


    # ---------------------------
    # Consultations section
    # ---------------------------
    def _build_consult_section(self, parent):
        lbl = ctk.CTkLabel(parent, text="Mes consultations - Aujourd'hui", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        # simple listbox for appointments
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=(0,8))

        self.lst_appts = tk.Listbox(frame, height=10)
        self.lst_appts.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.lst_appts.yview)
        self.lst_appts.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # actions
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkButton(actions, text="Démarrer consultation", command=self._start_selected_consult).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Ouvrir dossier patient", command=self._open_selected_patient).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Rafraîchir", command=self._refresh_consultations_async).pack(side="right", padx=6)

    # ---------------------------
    # Patients section
    # ---------------------------
    def _build_patients_section(self, parent):
        lbl = ctk.CTkLabel(parent, text="Mes patients suivis", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        self.lst_patients = tk.Listbox(parent, height=12)
        self.lst_patients.pack(fill="both", expand=True, padx=12, pady=(0,8))

        ctk.CTkButton(parent, text="Ouvrir dossier sélectionné", command=self._open_selected_patient).pack(padx=12, pady=(0,12))

    # ---------------------------
    # Results/Examens section (placeholder: derniers dossiers / examens)
    # ---------------------------
    def _build_results_section(self, parent):
        lbl = ctk.CTkLabel(parent, text="Examens & résultats récents", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        # A gauche un tableau résumé (Listbox simple)
        inner = tk.Frame(parent)
        inner.pack(fill="both", expand=True, padx=12, pady=(0,12))

        self.lst_results = tk.Listbox(inner, height=8)
        self.lst_results.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(inner, orient="vertical", command=self.lst_results.yview)
        self.lst_results.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # petit graphique (RDV sur 7 jours)
        chart_container = ctk.CTkFrame(parent, fg_color="transparent")
        chart_container.pack(fill="x", padx=12, pady=(0,12))
        self.fig_ax = None
        self.chart_canvas = None
        self._build_empty_chart(chart_container)

    def _build_empty_chart(self, parent):
        fig, ax = plt.subplots(figsize=(5,2.2))
        ax.text(0.5, 0.5, "Chargement...", ha="center", va="center")
        ax.set_xticks([])
        ax.set_yticks([])
        self.fig_ax = (fig, ax)
        if self.chart_canvas:
            try:
                self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass
        self.chart_canvas = FigureCanvasTkAgg(fig, master=parent)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="x")

    # ---------------------------
    # Data loaders (async)
    # ---------------------------
    def _refresh_all_async(self):
        threading.Thread(target=self._refresh_all_worker, daemon=True).start()

    def _refresh_all_worker(self):
        # KPI timespan defaults
        today = date.today()
        week_start = today - timedelta(days=6)

        # gather KPIs (defensive calls)
        try:
            total_patients = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "distinct_patients_count"):
                total_patients = self.appt_ctrl.distinct_patients_count(start=week_start, end=today)
            appts_today = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "total_appointments"):
                appts_today = self.appt_ctrl.total_appointments(start=today, end=today)
            status_break = {}
            if self.appt_ctrl and hasattr(self.appt_ctrl, "count_by_status"):
                status_break = self.appt_ctrl.count_by_status(start=today, end=today) or {}
            renewals = []
            if self.presc_ctrl and hasattr(self.presc_ctrl, "renewals_for_doctor"):
                renewals = self.presc_ctrl.renewals_for_doctor(within_days=14)
            # recent results: try medical records last 10
            recent_results = []
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "list_records"):
                try:
                    recent = self.medrec_ctrl.list_records(page=1, per_page=10)
                    # normalize recent entries to strings
                    for r in (recent or []):
                        # r peut être ORM obj ou dict selon implémentation ; tentative prudente:
                        if isinstance(r, dict):
                            recent_results.append(f"{r.get('code_patient','')} — {r.get('diagnosis','')}")
                        else:
                            pid = getattr(r, "patient_id", "")
                            d = getattr(r, "consultation_date", "")
                            diag = getattr(r, "diagnosis", "")
                            recent_results.append(f"Patient {pid} — {d} — {diag}")
                except Exception:
                    recent_results = []
            # time series for chart
            timeseries = []
            if self.appt_ctrl and hasattr(self.appt_ctrl, "appointments_time_series"):
                start = week_start
                end = today
                timeseries = self.appt_ctrl.appointments_time_series(start=start, end=end) or []
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur KPI", f"Impossible de charger les KPI: {err}"))
            return

        # push UI updates to main thread
        self.after(0, lambda: self._update_kpis_ui(
            total_patients, appts_today, status_break, renewals, recent_results, timeseries
        ))

        # also refresh lists
        self._refresh_consultations_async()
        self._refresh_patients_async()
        self._refresh_results_async()

    def _update_kpis_ui(self, total_patients, appts_today, status_break, renewals, recent_results, timeseries):
        self.lbl_total_patients.configure(text=str(total_patients))
        self.lbl_appts_today.configure(text=str(appts_today))

        # format breakdown (e.g. pending:3, completed:2)
        if status_break:
            parts = [f"{k}:{v}" for k, v in status_break.items()]
            self.lbl_status_breakdown.configure(text=" • ".join(parts))
        else:
            self.lbl_status_breakdown.configure(text="—")

        self.lbl_renewals.configure(text=str(len(renewals) if renewals is not None else 0))

        # draw timeseries chart (7 days)
        try:
            self._draw_timeseries_chart(timeseries)
        except Exception:
            pass

    # ---------------------------
    # refresh specific lists
    # ---------------------------
    def _refresh_consultations_async(self):
        threading.Thread(target=self._refresh_consultations_worker, daemon=True).start()

    def _refresh_consultations_worker(self):
        today = date.today()
        appts = []
        try:
            # preferer wrapper get_by_day / upcoming_today
            if self.appt_ctrl and hasattr(self.appt_ctrl, "get_by_day"):
                # get_by_day(date, doctor_id optional)
                appts = self.appt_ctrl.get_by_day(today) or []
            elif self.appt_ctrl and hasattr(self.appt_ctrl, "upcoming_today"):
                appts = self.appt_ctrl.upcoming_today() or []
            elif self.appt_ctrl and hasattr(self.appt_ctrl, "search_by_doctor"):
                appts = self.appt_ctrl.search_by_doctor() or []
                appts = [a for a in appts if getattr(a, "appointment_date", None) == today]
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur RDV", f"Impossible de charger RDV: {err}"))
            return

        self.after(0, lambda: self._populate_appointments_list(appts))


    def _populate_appointments_list(self, appts):
        self.lst_appts.delete(0, tk.END)
        self._appt_objects = []
        for a in (appts or []):
            # try to get patient code / name safely
            try:
                patient = getattr(a, "patient", None)
                if patient:
                    pname = getattr(patient, "code_patient", None) or f"{getattr(patient,'first_name','')} {getattr(patient,'last_name','')}"
                else:
                    # maybe appointment stores patient_id and controller can return patient dict
                    pid = getattr(a, "patient_id", None)
                    pname = ""
                    if pid and self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                        p = self.pat_ctrl.get_patient(pid)
                        if isinstance(p, dict):
                            pname = f"{p.get('code_patient', '')} - {p.get('first_name','')} {p.get('last_name','')}".strip()
                        else:
                            pname = str(getattr(p, "first_name", getattr(p, "username", pid)))
                timestr = ""
                ad = getattr(a, "appointment_date", None)
                at = getattr(a, "appointment_time", None)
                if ad:
                    timestr = str(ad)
                if at:
                    timestr = f"{timestr} {str(at)}"
                entry = f"{pname} — {timestr} — {getattr(a,'reason','') or ''} — {getattr(a,'status','')}"
            except Exception:
                entry = f"RDV #{getattr(a,'id', '')}"
            self.lst_appts.insert(tk.END, entry)
            self._appt_objects.append(a)

    def _refresh_patients_async(self):
        threading.Thread(target=self._refresh_patients_worker, daemon=True).start()

    def _refresh_patients_worker(self):
        patients = []
        try:
            # si patient_controller propose patients_for_day => l'utiliser (plus fiable)
            if self.pat_ctrl and hasattr(self.pat_ctrl, "patients_for_day"):
                pats = self.pat_ctrl.patients_for_day(date.today()) or []
                for p in pats:
                    if isinstance(p, dict):
                        label = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}"
                        pid = p.get('patient_id')
                    else:
                        label = f"{getattr(p,'code_patient', '')} - {getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()
                        pid = getattr(p, 'patient_id', None)
                    patients.append((label, pid))
            else:
                # fallback: build patients from upcoming appointments
                appts = []
                if self.appt_ctrl and hasattr(self.appt_ctrl, "upcoming_today"):
                    appts = self.appt_ctrl.upcoming_today() or []
                elif self.appt_ctrl and hasattr(self.appt_ctrl, "get_by_day"):
                    appts = self.appt_ctrl.get_by_day(date.today()) or []
                seen = {}
                for a in appts:
                    pid = getattr(a, "patient_id", None)
                    if not pid or pid in seen:
                        continue
                    seen[pid] = True
                    p = None
                    if self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                        p = self.pat_ctrl.get_patient(pid)
                    if isinstance(p, dict):
                        label = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}"
                    else:
                        label = f"Patient {pid}"
                    patients.append((label, pid))
        except Exception:
            patients = []

        self.after(0, lambda: self._populate_patients_list(patients))


    def _populate_patients_list(self, patients):
        self.lst_patients.delete(0, tk.END)
        self._patient_map = {}
        for label, pid in (patients or []):
            self.lst_patients.insert(tk.END, label)
            self._patient_map[label] = pid

    def _refresh_results_async(self):
        threading.Thread(target=self._refresh_results_worker, daemon=True).start()

    def _refresh_results_worker(self):
        results = []
        try:
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "list_records"):
                recs = self.medrec_ctrl.list_records(page=1, per_page=10) or []
                for r in recs:
                    if isinstance(r, dict):
                        results.append(f"{r.get('code_patient','')} — {r.get('diagnosis','')}")
                    else:
                        results.append(f"Patient {getattr(r,'patient_id','')} — {getattr(r,'consultation_date','')}")
        except Exception:
            results = []

        self.after(0, lambda: self._populate_results_list(results))

    def _populate_results_list(self, results):
        self.lst_results.delete(0, tk.END)
        for r in (results or []):
            self.lst_results.insert(tk.END, r)

    # ---------------------------
    # Actions
    # ---------------------------
    def _start_selected_consult(self):
        sel = self.lst_appts.curselection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez un rendez-vous dans la liste.")
            return
        idx = sel[0]
        appt = self._appt_objects[idx]
        if callable(self.on_start_consultation):
            self.on_start_consultation(appt)
        else:
            messagebox.showinfo("Info", f"Démarrer consultation (non implémenté) — RDV id={getattr(appt,'id',None)}")

    def _open_selected_patient(self):
        sel = self.lst_patients.curselection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez un patient.")
            return
        label = self.lst_patients.get(sel[0])
        pid = self._patient_map.get(label)
        if not pid:
            messagebox.showinfo("Info", "Impossible de retrouver le patient sélectionné.")
            return
        # If parent controller exposes a method to open the medical record view, prefer that
        if callable(self.on_open_record):
            self.on_open_record(pid)
            return
        # else try to open via passed controller (convention : controller.show_medical_record)
        opener = getattr(self.controller, "show_medical_record_form", None) or getattr(self.controller, "show_medical_record_list", None)
        if callable(opener):
            opener()
        else:
            messagebox.showinfo("Ouverture dossier", f"Ouvrir dossier patient id={pid}")

    # ---------------------------
    # Charting helper
    # ---------------------------
    def _draw_timeseries_chart(self, timeseries):
        # timeseries is expected [(YYYY-MM-DD, count), ...] — if other format adapt
        fig, ax = plt.subplots(figsize=(5,2.2))
        if not timeseries:
            ax.text(0.5, 0.5, "Pas de données", ha="center", va="center")
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            dates = [d for d, c in timeseries]
            counts = [c for d, c in timeseries]
            ax.plot(dates, counts, marker="o")
            ax.set_title("RDV (période)")
            ax.set_xticklabels(dates, rotation=30, ha="right")
            ax.set_ylabel("Nombre RDV")
            # attempt tight layout
        fig.tight_layout()

        # replace canvas
        if self.chart_canvas:
            try:
                self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.results_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="x", padx=12, pady=(0,12))


    @staticmethod
    def _get_week_range():
        today = date.today()
        start = today - timedelta(days=today.weekday())   # lundi
        end = start + timedelta(days=6)
        return start, end

    def _load_kpis_async(self):
        """Charge KPIs en background et met à jour l'UI."""
        def worker():
            try:
                # plages de dates (uniformes via helper)
                today = date.today()
                week_start, week_end = self._get_week_range()
                month_start = date(today.year, today.month, 1)

                # appels controller (défensifs) — utiliser les wrappers que tu as définis
                total_today = 0
                if self.appt_ctrl and hasattr(self.appt_ctrl, "total_appointments"):
                    total_today = self.appt_ctrl.total_appointments(start=today, end=today)

                by_status_today = {}
                if self.appt_ctrl and hasattr(self.appt_ctrl, "count_by_status"):
                    by_status_today = self.appt_ctrl.count_by_status(start=today, end=today) or {}

                week_series = []
                if self.appt_ctrl and hasattr(self.appt_ctrl, "appointments_time_series"):
                    week_series = self.appt_ctrl.appointments_time_series(start=week_start, end=week_end) or []

                distinct_patients_week = 0
                if self.appt_ctrl and hasattr(self.appt_ctrl, "distinct_patients_count"):
                    distinct_patients_week = self.appt_ctrl.distinct_patients_count(start=week_start, end=week_end) or 0

                ordos_renew = []
                if self.presc_ctrl and hasattr(self.presc_ctrl, "renewals_for_doctor"):
                    # renewals_for_doctor(doctor_id:Optional[int]=None, within_days:int=14)
                    ordos_renew = self.presc_ctrl.renewals_for_doctor(within_days=14) or []

                motifs = {}
                if self.medrec_ctrl and hasattr(self.medrec_ctrl, "consultation_type_distribution"):
                    motifs = self.medrec_ctrl.consultation_type_distribution(start=week_start, end=week_end) or {}

                kpis = {
                    'total_today': total_today,
                    'by_status_today': by_status_today,
                    'week_series': week_series,
                    'distinct_patients_week': distinct_patients_week,
                    'renewals': ordos_renew,
                    'motifs': motifs
                }
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Erreur KPI", f"Impossible de charger les KPI: {err}"))
                return

            # Update UI sur thread principal
            def ui_update():
                try:
                    self.lbl_total_patients.configure(text=str(kpis['distinct_patients_week']))
                except Exception:
                    pass
                try:
                    self.lbl_appts_today.configure(text=str(kpis['total_today']))
                except Exception:
                    pass
                try:
                    if kpis['by_status_today']:
                        parts = [f"{k}:{v}" for k, v in kpis['by_status_today'].items()]
                        self.lbl_status_breakdown.configure(text=" • ".join(parts))
                    else:
                        self.lbl_status_breakdown.configure(text="—")
                except Exception:
                    pass
                try:
                    self.lbl_renewals.configure(text=str(len(kpis['renewals'] or [])))
                except Exception:
                    pass

                try:
                    self._draw_timeseries_chart(kpis['week_series'])
                except Exception:
                    pass

            self.after(0, ui_update)

        threading.Thread(target=worker, daemon=True).start()




        # ---------------------------
        # Misc helpers
        # ---------------------------
    
    def destroy(self):
            # cleanup matplotlib figures to avoid memory leaks
            try:
                if self.chart_canvas:
                    self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            super().destroy()




# Au va sou
# view/doctor_views/doctors_dashboard_view.py
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .medicalrecordmodal import MedicalRecordModal

class DoctorsDashboardView(ctk.CTkFrame):
    """
    Dashboard Médecin (vue principale).
    Le `controller` passé doit exposer au minimum :
      - appointment_controller (wrappers: total_appointments, count_by_status, appointments_time_series,
          distinct_patients_count, get_by_day or upcoming_today)
      - patient_controller (get_patient, patients_for_day optional)
      - prescription_controller (renewals_for_doctor)
      - medical_record_controller (consultation_type_distribution, list_records)
    """

    def __init__(self, parent, user, controller, on_logout=None, on_start_consultation=None, on_open_record=None):
        super().__init__(parent)

        # références
        self.user = user
        self.controller = controller
        self.on_logout = on_logout
        self.on_start_consultation = on_start_consultation
        self.on_open_record = on_open_record

        # controllers shortcuts (peuvent être None)
        self.appt_ctrl = getattr(controller, "appointment_controller", None)
        self.pat_ctrl = getattr(controller, "patient_controller", None)
        self.presc_ctrl = getattr(controller, "prescription_controller", None)
        self.medrec_ctrl = getattr(controller, "medical_record_controller", None)
        self.lab_ctrl = getattr(controller, "lab_controller", None)

        # Layout grid
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=0)   # KPI row
        self.grid_rowconfigure(2, weight=1)   # sessions area
        self.grid_rowconfigure(3, weight=1)   # results / bottom area
        self.grid_columnconfigure(0, weight=1)

        # containers graphiques
        self.chart_canvas = None
        self._appt_objects = []    # stockage local des objets RDV
        self._patient_map = {}

        # build UI
        self._build_header()
        self._build_kpis()
        self._build_sessions_area()

        # initial load (async)
        self._refresh_all_async()

    # ---------------------------
    # Header
    # ---------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, height=60, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        header.grid_propagate(False)

        # determine title prefix based on role
        role_name = ""
        try:
            role_obj = getattr(self.user, "application_role", None)
            role_name = (getattr(role_obj, "role_name", "") or "").lower()
        except Exception:
            role_name = ""

        title_prefix = "M."
        if "med" in role_name:
            title_prefix = "Dr."
        elif "infirm" in role_name or "nurs" in role_name:
            title_prefix = "M./Mme"

        fullname = getattr(self.user, "full_name", getattr(self.user, "username", ""))
        title_text = f"Bienvenue {title_prefix} {fullname} — {role_name.title() if role_name else ''}"
        self.title_lbl = ctk.CTkLabel(header, text=title_text, font=ctk.CTkFont(size=16, weight="bold"))
        self.title_lbl.pack(side="left", padx=(16,8))

        now = datetime.now().strftime("%A %d %B %Y %H:%M")
        self.date_lbl = ctk.CTkLabel(header, text=now)
        self.date_lbl.pack(side="left", padx=8)

        spacer = ctk.CTkLabel(header, text="")
        spacer.pack(side="left", expand=True)

        if callable(self.on_logout):
            ctk.CTkButton(header, text="Se déconnecter", command=self.on_logout).pack(side="right", padx=12)

    # ---------------------------
    # KPI cards row
    # ---------------------------
    def _build_kpis(self):
        kpi_frame = ctk.CTkFrame(self)
        kpi_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0,8))
        kpi_frame.grid_columnconfigure((0,1,2,3), weight=1)

        def make_card(parent, title):
            f = ctk.CTkFrame(parent, corner_radius=8, height=80)
            f.pack_propagate(False)
            lbl_title = ctk.CTkLabel(f, text=title, anchor="w", font=ctk.CTkFont(size=12))
            lbl_value = ctk.CTkLabel(f, text="—", anchor="w", font=ctk.CTkFont(size=20, weight="bold"))
            lbl_title.pack(anchor="w", padx=12, pady=(8,0))
            lbl_value.pack(anchor="w", padx=12)
            return f, lbl_value

        self.card1_frame, self.lbl_total_patients = make_card(kpi_frame, "Patients distincts (7j)")
        self.card1_frame.grid(row=0, column=0, padx=6, sticky="nsew")

        self.card2_frame, self.lbl_appts_today = make_card(kpi_frame, "RDV prévus aujourd'hui")
        self.card2_frame.grid(row=0, column=1, padx=6, sticky="nsew")

        self.card3_frame, self.lbl_status_breakdown = make_card(kpi_frame, "Breakdown RDV (aujourd'hui)")
        self.card3_frame.grid(row=0, column=2, padx=6, sticky="nsew")

        self.card4_frame, self.lbl_renewals = make_card(kpi_frame, "Ordonnances à renouveler (14j)")
        self.card4_frame.grid(row=0, column=3, padx=6, sticky="nsew")

        ctk.CTkButton(kpi_frame, text="Rafraîchir", width=90, command=self._refresh_all_async).grid(row=0, column=4, padx=(8,0))

    # ---------------------------
    # Sessions area (3 blocs)
    # ---------------------------
    def _build_sessions_area(self):
        sessions = ctk.CTkFrame(self)
        sessions.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0,8))
        sessions.grid_columnconfigure(0, weight=1)
        sessions.grid_columnconfigure(1, weight=1)
        sessions.grid_rowconfigure(0, weight=1)
        sessions.grid_rowconfigure(1, weight=1)

        # Left column: Consultations du jour
        self.consult_frame = ctk.CTkFrame(sessions, corner_radius=8)
        self.consult_frame.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=6)
        self._build_consult_section(self.consult_frame)

        # Right top: Patients suivis
        self.patients_frame = ctk.CTkFrame(sessions, corner_radius=8)
        self.patients_frame.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=6)
        self._build_patients_section(self.patients_frame)

        # Results section: under both columns
        self.results_frame = ctk.CTkFrame(sessions, corner_radius=8)
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(6,0))
        self._build_all_consults_section(self.consult_frame)   # <-- nouvelle
        self._build_new_patients_section(self.patients_frame) 
        self._build_results_section(self.results_frame)

    # ---------------------------
    # Subsections builders
    # ---------------------------
    def _build_consult_section(self, parent):
        lbl = ctk.CTkLabel(parent, text="Mes consultations sur RDV - Aujourd'hui", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=(0,8))

        self.lst_appts = tk.Listbox(frame, height=10)
        self.lst_appts.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.lst_appts.yview)
        self.lst_appts.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkButton(actions, text="Démarrer consultation", command=self._start_selected_consult).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Ouvrir dossier patient", command=self._open_selected_patient).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Rafraîchir", command=self._refresh_consultations_async).pack(side="right", padx=6)

    def _build_patients_section(self, parent):
        lbl = ctk.CTkLabel(parent, text="Mes patients suivis", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        self.lst_patients = tk.Listbox(parent, height=12)
        self.lst_patients.pack(fill="both", expand=True, padx=12, pady=(0,8))

        ctk.CTkButton(parent, text="Ouvrir dossier sélectionné", command=self._open_selected_patient).pack(padx=12, pady=(0,12))

    def _build_all_consults_section(self, parent):
        """Toutes les consultations du jour (tous médecins)."""
        lbl = ctk.CTkLabel(parent, text="Toutes les consultations - Aujourd'hui", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=(0,8))

        self.lst_all_appts = tk.Listbox(frame, height=10)
        self.lst_all_appts.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(frame, orient="vertical", command=self.lst_all_appts.yview)
        self.lst_all_appts.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(0,12))
        ctk.CTkButton(actions, text="Ouvrir dossier patient", command=self._open_selected_patient_from_all).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Rafraîchir", command=self._refresh_all_consultations_async).pack(side="right", padx=6)

    def _build_new_patients_section(self, parent):
        """Patients créés/enregistrés aujourd'hui (tous utilisateurs)."""
        lbl = ctk.CTkLabel(parent, text="Patients enregistrés - Aujourd'hui", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        self.lst_new_patients = tk.Listbox(parent, height=8)
        self.lst_new_patients.pack(fill="both", expand=True, padx=12, pady=(0,8))

        ctk.CTkButton(parent, text="Ouvrir dossier sélectionné", command=self._open_selected_patient_from_new).pack(padx=12, pady=(0,12))

    def _build_results_section(self, parent):
        lbl = ctk.CTkLabel(parent, text="Examens & résultats récents", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        inner = tk.Frame(parent)
        inner.pack(fill="both", expand=True, padx=12, pady=(0,12))

        self.lst_results = tk.Listbox(inner, height=8)
        self.lst_results.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(inner, orient="vertical", command=self.lst_results.yview)
        self.lst_results.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        chart_container = ctk.CTkFrame(parent, fg_color="transparent")
        chart_container.pack(fill="x", padx=12, pady=(0,12))
        self.fig_ax = None
        self.chart_canvas = None
        self._build_empty_chart(chart_container)

    def _build_empty_chart(self, parent):
        fig, ax = plt.subplots(figsize=(5,2.2))
        ax.text(0.5, 0.5, "Chargement...", ha="center", va="center")
        ax.set_xticks([])
        ax.set_yticks([])
        self.fig_ax = (fig, ax)
        if self.chart_canvas:
            try:
                self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass
        self.chart_canvas = FigureCanvasTkAgg(fig, master=parent)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="x")
        plt.close(fig)  # éviter accumulation de figures

    # ---------------------------
    # Data loaders (async)
    # ---------------------------
    def _refresh_all_async(self):
        threading.Thread(target=self._refresh_all_worker, daemon=True).start()

    def _refresh_all_worker(self):
        today = date.today()
        week_start = today - timedelta(days=6)

        try:
            total_patients = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "distinct_patients_count"):
                total_patients = self.appt_ctrl.distinct_patients_count(start=week_start, end=today) or 0

            appts_today = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "total_appointments"):
                appts_today = self.appt_ctrl.total_appointments(start=today, end=today) or 0

            status_break = {}
            if self.appt_ctrl and hasattr(self.appt_ctrl, "count_by_status"):
                status_break = self.appt_ctrl.count_by_status(start=today, end=today) or {}

            renewals = []
            if self.presc_ctrl and hasattr(self.presc_ctrl, "renewals_for_doctor"):
                renewals = self.presc_ctrl.renewals_for_doctor(within_days=14) or []

            recent_results = []
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "list_records"):
                try:
                    recent = self.medrec_ctrl.list_records(page=1, per_page=10) or []
                    for r in recent:
                        if isinstance(r, dict):
                            recent_results.append(f"{r.get('code_patient','')} — {r.get('diagnosis','')}")
                        else:
                            recent_results.append(f"Patient {getattr(r,'patient_id','')} — {getattr(r,'consultation_date','')}")
                except Exception:
                    recent_results = []

            timeseries = []
            if self.appt_ctrl and hasattr(self.appt_ctrl, "appointments_time_series"):
                timeseries = self.appt_ctrl.appointments_time_series(start=week_start, end=today) or []

        except Exception as e:
            # on capture l'exception et affiche dans le thread principal
            self.after(0, lambda err=e: messagebox.showerror("Erreur KPI", f"Impossible de charger les KPI: {err}"))
            return

        # push UI updates
        self.after(0, lambda: self._update_kpis_ui(
            total_patients, appts_today, status_break, renewals, recent_results, timeseries
        ))

        # refresh lists aussi (asynchrone)
        self._refresh_consultations_async()
        self._refresh_patients_async()
        self._refresh_results_async()

    def _update_kpis_ui(self, total_patients, appts_today, status_break, renewals, recent_results, timeseries):
        try:
            self.lbl_total_patients.configure(text=str(total_patients))
        except Exception:
            pass
        try:
            self.lbl_appts_today.configure(text=str(appts_today))
        except Exception:
            pass

        if status_break:
            parts = [f"{k}:{v}" for k, v in status_break.items()]
            self.lbl_status_breakdown.configure(text=" • ".join(parts))
        else:
            self.lbl_status_breakdown.configure(text="—")

        try:
            self.lbl_renewals.configure(text=str(len(renewals or [])))
        except Exception:
            pass

        try:
            self._draw_timeseries_chart(timeseries)
        except Exception:
            pass

    # ---------------------------
    # refresh specific lists
    # ---------------------------
    def _refresh_consultations_async(self):
        threading.Thread(target=self._refresh_consultations_worker, daemon=True).start()

    def _refresh_consultations_worker(self):
        today = date.today()
        appts = []
        try:
            # Priorité : wrappers fournis par le controller
            if self.appt_ctrl and hasattr(self.appt_ctrl, "get_by_day"):
                # si get_by_day accepte doctor id, il doit être géré côté controller
                appts = self.appt_ctrl.get_by_day(today) or []
            elif self.appt_ctrl and hasattr(self.appt_ctrl, "upcoming_today"):
                appts = self.appt_ctrl.upcoming_today() or []
            elif self.appt_ctrl and hasattr(self.appt_ctrl, "search_by_doctor"):
                appts = self.appt_ctrl.search_by_doctor() or []
                appts = [a for a in appts if getattr(a, "appointment_date", None) == today]
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur RDV", f"Impossible de charger RDV: {err}"))
            return

        self.after(0, lambda: self._populate_appointments_list(appts))

    def _populate_appointments_list(self, appts):
        self.lst_appts.delete(0, tk.END)
        self._appt_objects = []
        for a in (appts or []):
            try:
                patient = getattr(a, "patient", None)
                if patient:
                    pname = getattr(patient, "code_patient", None) or f"{getattr(patient,'first_name','')} {getattr(patient,'last_name','')}"
                else:
                    pid = getattr(a, "patient_id", None)
                    pname = ""
                    if pid and self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                        p = self.pat_ctrl.get_patient(pid)
                        if isinstance(p, dict):
                            pname = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}".strip()
                        else:
                            pname = str(getattr(p, "first_name", getattr(p, "username", pid)))
                timestr = ""
                ad = getattr(a, "appointment_date", None)
                at = getattr(a, "appointment_time", None)
                if ad:
                    timestr = str(ad)
                if at:
                    timestr = f"{timestr} {str(at)}"
                aid = getattr(a, "id", None) or getattr(a, "appointment_id", None)
                entry = f"{pname} — {timestr} — {getattr(a,'reason','') or ''} — {getattr(a,'status','')} (#{aid})"
            except Exception:
                entry = f"RDV #{getattr(a,'id', getattr(a, 'appointment_id', ''))}"
            self.lst_appts.insert(tk.END, entry)
            self._appt_objects.append(a)

    def _refresh_patients_async(self):
        threading.Thread(target=self._refresh_patients_worker, daemon=True).start()

    def _refresh_patients_worker(self):
        patients = []
        try:
            if self.pat_ctrl and hasattr(self.pat_ctrl, "patients_for_day"):
                pats = self.pat_ctrl.patients_for_day(date.today()) or []
                for p in pats:
                    if isinstance(p, dict):
                        label = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}"
                        pid = p.get('patient_id')
                    else:
                        label = f"{getattr(p,'code_patient','')} - {getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()
                        pid = getattr(p, 'patient_id', None)
                    patients.append((label, pid))
            else:
                # fallback -> construire à partir des RDV
                appts = []
                if self.appt_ctrl and hasattr(self.appt_ctrl, "upcoming_today"):
                    appts = self.appt_ctrl.upcoming_today() or []
                elif self.appt_ctrl and hasattr(self.appt_ctrl, "get_by_day"):
                    appts = self.appt_ctrl.get_by_day(date.today()) or []
                seen = {}
                for a in appts:
                    pid = getattr(a, "patient_id", None)
                    if not pid or pid in seen:
                        continue
                    seen[pid] = True
                    p = None
                    if self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                        p = self.pat_ctrl.get_patient(pid)
                    if isinstance(p, dict):
                        label = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}"
                    else:
                        label = f"Patient {pid}"
                    patients.append((label, pid))
        except Exception:
            patients = []

        self.after(0, lambda: self._populate_patients_list(patients))

    def _populate_patients_list(self, patients):
        self.lst_patients.delete(0, tk.END)
        self._patient_map = {}
        for label, pid in (patients or []):
            self.lst_patients.insert(tk.END, label)
            self._patient_map[label] = pid

    def _refresh_results_async(self):
        threading.Thread(target=self._refresh_results_worker, daemon=True).start()

    def _refresh_results_worker(self):
        results = []
        try:
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "list_records"):
                recs = self.medrec_ctrl.list_records(page=1, per_page=10) or []
                for r in recs:
                    if isinstance(r, dict):
                        results.append(f"{r.get('code_patient','')} — {r.get('diagnosis','')}")
                    else:
                        results.append(f"Patient {getattr(r,'patient_id','')} — {getattr(r,'consultation_date','')}")
        except Exception:
            results = []

        self.after(0, lambda: self._populate_results_list(results))

    def _populate_results_list(self, results):
        self.lst_results.delete(0, tk.END)
        for r in (results or []):
            self.lst_results.insert(tk.END, r)

    # ---------------------------
    # Refresh / loaders pour nouvelles sections
    # ---------------------------
    def _refresh_all_consultations_async(self):
        threading.Thread(target=self._refresh_all_consultations_worker, daemon=True).start()

    def _refresh_all_consultations_worker(self):
        """Charge toutes les consultations du jour (sans filtrage doctor par défaut)."""
        try:
            today = date.today()
            appts = []
            # priorité : controller.get_by_day (retourne tous les rdv pour une date)
            if self.appt_ctrl and hasattr(self.appt_ctrl, "get_by_day"):
                appts = self.appt_ctrl.get_by_day(today) or []
            else:
                # fallback direct repo si disponible
                repo = getattr(self.appt_ctrl, "repo", None)
                if repo and hasattr(repo, "find_by_date_range"):
                    appts = repo.find_by_date_range(today, today) or []
            # normaliser l'affichage
            display = []
            for a in (appts or []):
                try:
                    patient = getattr(a, "patient", None)
                    pname = (getattr(patient,"code_patient", None) or
                             f"{getattr(patient,'first_name','')} {getattr(patient,'last_name','')}" if patient else f"Patient {getattr(a,'patient_id', '')}")
                    timestr = ""
                    ad = getattr(a, "appointment_date", None)
                    at = getattr(a, "appointment_time", None)
                    if ad:
                        timestr = str(ad)
                    if at:
                        timestr = f"{timestr} {str(at)}"
                    aid = getattr(a, "id", None) or getattr(a, "appointment_id", None)
                    display.append((f"{pname} — {timestr} — {getattr(a,'status','')} (#{aid})", a))
                except Exception:
                    display.append((f"RDV #{getattr(a,'id', getattr(a,'appointment_id',''))}", a))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur RDV", f"Impossible de charger toutes les consultations: {err}"))
            return

        self.after(0, lambda: self._populate_all_consults_list(display))

    def _populate_all_consults_list(self, display):
        self.lst_all_appts.delete(0, tk.END)
        self._all_appt_objects = []
        for label, obj in (display or []):
            self.lst_all_appts.insert(tk.END, label)
            self._all_appt_objects.append(obj)

    def _refresh_new_patients_async(self):
        threading.Thread(target=self._refresh_new_patients_worker, daemon=True).start()

    def _refresh_new_patients_worker(self):
        try:
            today = date.today()
            pats = []
            # priorité : patient_controller.patients_for_day(date)
            if self.pat_ctrl and hasattr(self.pat_ctrl, "patients_for_day"):
                pats = self.pat_ctrl.patients_for_day(today) or []
            else:
                # fallback direct repo if available : find patients created today
                repo = getattr(self.pat_ctrl, "repo", None)
                if repo and hasattr(repo, "find_by_creation_date"):
                    pats = repo.find_by_creation_date(today) or []
                else:
                    # dernier fallback: lister tous et filtrer (coûteux mais safe)
                    if self.pat_ctrl and hasattr(self.pat_ctrl, "list_patients"):
                        allp = self.pat_ctrl.list_patients() or []
                        for p in allp:
                            created = getattr(p, "created_at", None) or getattr(p, "date_created", None)
                            if created and getattr(created, "date", lambda: created)() == today:
                                pats.append(p)
            display = []
            for p in (pats or []):
                if isinstance(p, dict):
                    label = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}"
                    pid = p.get('patient_id') or p.get('id')
                else:
                    label = f"{getattr(p,'code_patient','')} - {getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()
                    pid = getattr(p, 'patient_id', None) or getattr(p, 'id', None)
                display.append((label, pid))
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur Patients", f"Impossible de charger patients: {err}"))
            return

        self.after(0, lambda: self._populate_new_patients_list(display))

    def _populate_new_patients_list(self, display):
        self.lst_new_patients.delete(0, tk.END)
        self._new_patient_map = {}
        for label, pid in (display or []):
            self.lst_new_patients.insert(tk.END, label)
            self._new_patient_map[label] = pid

    # ---------------------------
    # Actions spécifiques aux nouvelles listes
    # ---------------------------
    def _open_selected_patient_from_all(self):
        sel = self.lst_all_appts.curselection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez un rendez-vous dans la liste.")
            return
        idx = sel[0]
        appt = self._all_appt_objects[idx]
        pid = getattr(appt, "patient_id", None) or getattr(getattr(appt, "patient", None), "patient_id", None)
        if pid:
            self._open_patient_records_modal(pid)

    def _open_selected_patient_from_new(self):
        sel = self.lst_new_patients.curselection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez un patient.")
            return
        label = self.lst_new_patients.get(sel[0])
        pid = self._new_patient_map.get(label)
        if pid:
            self._open_patient_records_modal(pid)

    def _open_patient_records_modal(self, patient_id):
        """Ouvre une Toplevel listant les dossiers médicaux pour le patient donné."""
        # si on a déjà un callback parent pour ouvrir le dossier, l'utiliser
        if callable(self.on_open_record):
            try:
                self.on_open_record(patient_id)
                return
            except Exception:
                pass

        # sinon, utiliser medrec_ctrl s'il expose une méthode utile
        medctrl = self.medrec_ctrl
        recs = None
        if medctrl:
            if hasattr(medctrl, "list_records_for_patient"):
                recs = medctrl.list_records_for_patient(patient_id)
            elif hasattr(medctrl, "list_records"):
                # essayer d'appeler list_records avec filtre patient_id
                try:
                    recs = medctrl.list_records(patient_id=patient_id, page=1, per_page=50)
                except TypeError:
                    # méthode ne prend pas patient_id
                    recs = None

        modal = MedicalRecordModal(self.winfo_toplevel(), records=recs or [], medrec_ctrl=medctrl, patient_id=patient_id)
        modal.grab_set()
    

    # ---------------------------
    # Actions
    # ---------------------------
    def _start_selected_consult(self):
        sel = self.lst_appts.curselection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez un rendez-vous dans la liste.")
            return
        idx = sel[0]
        appt = self._appt_objects[idx]
        if callable(self.on_start_consultation):
            self.on_start_consultation(appt)
        else:
            messagebox.showinfo("Info", f"Démarrer consultation (non implémenté) — RDV id={getattr(appt,'id', getattr(appt,'appointment_id',None))}")

    def _open_selected_patient(self):
        sel = self.lst_patients.curselection()
        if not sel:
            messagebox.showinfo("Info", "Sélectionnez un patient.")
            return
        label = self.lst_patients.get(sel[0])
        pid = self._patient_map.get(label)
        if not pid:
            messagebox.showinfo("Info", "Impossible de retrouver le patient sélectionné.")
            return
        if callable(self.on_open_record):
            self.on_open_record(pid)
            return
        opener = getattr(self.controller, "show_medical_record_form", None) or getattr(self.controller, "show_medical_record_list", None)
        if callable(opener):
            opener()
        else:
            messagebox.showinfo("Ouverture dossier", f"Ouvrir dossier patient id={pid}")

    # ---------------------------
    # Charting helper (fix warnings & leaks)
    # ---------------------------
    def _draw_timeseries_chart(self, timeseries):
        # timeseries expected [(label, count), ...] where label can be str (date) or anything
        fig, ax = plt.subplots(figsize=(5,2.2))

        if not timeseries:
            ax.text(0.5, 0.5, "Pas de données", ha="center", va="center")
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            labels = [str(d) for d, _ in timeseries]
            counts = [int(c) for _, c in timeseries]

            x = list(range(len(labels)))
            ax.plot(x, counts, marker="o")
            ax.set_title("RDV (période)")
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=30, ha="right")
            ax.set_ylabel("Nombre RDV")

        fig.tight_layout()

        # cleanup previous canvas
        if self.chart_canvas:
            try:
                self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass

        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.results_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="x", padx=12, pady=(0,12))

        plt.close(fig)  # évite accumulation de figures en mémoire

    # ---------------------------
    # Misc
    # ---------------------------
    @staticmethod
    def _get_week_range():
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    def destroy(self):
        try:
            if self.chart_canvas:
                self.chart_canvas.get_tk_widget().destroy()
        except Exception:
            pass
        super().destroy()

# api_controller 
# view_pyqt6/api_controller.py
import inspect
from typing import Any, Callable, Dict, Iterable

# Proxy générique adaptatif vers RemoteGateway
class ApiControllerProxy:
    """
    Proxy adaptatif qui forwarde dynamiquement les appels vers `gateway`.
    Il tente plusieurs stratégies si les signatures ne correspondent pas :
      - appel direct gateway.fn(*args, **kwargs)
      - remappage de kwargs communs (page/per_page -> skip/limit, search -> q/query, ...)
      - transformation en args positionnels selon la signature du target
      - normalisation des réponses (ex: {'data': [...]}) pour les méthodes list_*
    """

    def __init__(self, gateway: Any):
        if gateway is None:
            raise ValueError("gateway cannot be None for ApiControllerProxy")
        self.gateway = gateway

    # utilitaires
    def _normalize_list_response(self, name: str, res: Any):
        """Si méthode list_... renvoie enveloppe {'data':[...]}, retourne la liste."""
        if res is None:
            return []
        if isinstance(res, dict):
            for k in ("data", "items", "results", "rows"):
                if k in res and isinstance(res[k], list):
                    return res[k]
            # parfois la gateway renvoie {'_items': [...]} ou {'payload': {'data':[...]}}
            if "_items" in res and isinstance(res["_items"], list):
                return res["_items"]
            if "payload" in res and isinstance(res["payload"], dict) and isinstance(res["payload"].get("data"), list):
                return res["payload"]["data"]
        # si c'est déjà une itérable de données, renvoyer tel quel (mais pas str)
        if isinstance(res, list):
            return res
        if isinstance(res, Iterable) and not isinstance(res, (str, bytes, dict)):
            try:
                return list(res)
            except Exception:
                pass
        return res

    def _remap_kwargs_common(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applique des règles courantes :
          page+per_page -> skip, limit
          per_page -> limit
          page -> skip (assume per_page=15 si absent)
          search -> q / query
        """
        kw = dict(kwargs)  # copy
        # page/per_page -> skip/limit
        page = kw.pop("page", None)
        per_page = kw.pop("per_page", None) or kw.pop("limit", None) or None
        if page is not None:
            try:
                per = int(per_page) if per_page is not None else 15
                skip = max(0, (int(page) - 1) * per)
                kw.setdefault("skip", skip)
                kw.setdefault("limit", per)
            except Exception:
                # fallback safe: expose page as-is if conversion fails
                kw.setdefault("page", page)
                if per_page is not None:
                    kw.setdefault("limit", per_page)
        else:
            # only per_page -> limit
            if per_page is not None:
                kw.setdefault("limit", per_page)

        # search -> q/query
        if "search" in kw:
            sval = kw.pop("search")
            # some gateways expect 'q' or 'query' or 'search'
            if "q" not in kw:
                kw["q"] = sval
            if "query" not in kw:
                kw["query"] = sval

        # unify id names often used
        if "patient_id" in kw and "id" not in kw:
            kw.setdefault("id", kw["patient_id"])
        if "record_id" in kw and "id" not in kw:
            kw.setdefault("id", kw["record_id"])

        return kw

    def _build_positional_from_kwargs(self, fn: Callable, kwargs: Dict[str, Any]):
        """
        Construire une liste d'args positionnels à partir des kwargs
        en respectant l'ordre des paramètres de la signature du callable.
        """
        try:
            sig = inspect.signature(fn)
            params = []
            for p in sig.parameters.values():
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                    params.append(p.name)
            args = []
            for name in params:
                if name in kwargs:
                    args.append(kwargs[name])
            return args
        except Exception:
            return []

    def __getattr__(self, name: str):
        """
        Retourne un wrapper qui appellera la méthode correspondante sur la gateway.
        Si la gateway ne dispose pas de la méthode, on lève AttributeError.
        """
        gw = self.gateway
        target = getattr(gw, name, None)
        if target is None:
            # some remote layer may use different prefixes (ex: list_patients -> patients_list)
            alt = None
            # try common alternatives
            alternatives = [
                name,
                name.replace("list_", ""),
                name.replace("get_", "get"),
                name.replace("create_", "post_"),
            ]
            for a in alternatives:
                if a != name and hasattr(gw, a):
                    alt = getattr(gw, a)
                    break
            if alt is None:
                raise AttributeError(f"Gateway has no attribute '{name}'")
            target = alt

        def wrapper(*args, **kwargs):
            # 1) try direct call
            try:
                return self._post_process(name, target(*args, **kwargs))
            except TypeError as e_direct:
                # capture message to test if it's "unexpected keyword argument"
                last_exc = e_direct
                # 2) try remap common kwargs (page->skip etc.)
                try:
                    remapped = self._remap_kwargs_common(kwargs)
                    # if args empty, try direct with remapped kwargs
                    try:
                        return self._post_process(name, target(*args, **remapped))
                    except TypeError as e2:
                        last_exc = e2
                        # 3) try to call with positional args built from remapped kwargs
                        pos = self._build_positional_from_kwargs(target, remapped)
                        try:
                            return self._post_process(name, target(*pos))
                        except Exception as e_pos:
                            last_exc = e_pos
                except Exception:
                    pass

                # 4) try to build positional args from original kwargs (fallback)
                try:
                    pos2 = self._build_positional_from_kwargs(target, kwargs)
                    try:
                        return self._post_process(name, target(*pos2))
                    except Exception as e3:
                        last_exc = e3
                except Exception:
                    pass

                # 5) final attempt: call with no kwargs/args
                try:
                    return self._post_process(name, target())
                except Exception as e_final:
                    last_exc = e_final

                # none of attempts worked -> reraised original info
                raise last_exc from last_exc
            except Exception as e:
                # other exceptions come from gateway and should remonter
                raise

        return wrapper

    def _post_process(self, name: str, res: Any):
        # pour les méthodes de type "list_*" on normalise si l'enveloppe contient "data"/"items"
        if name.startswith("list_") or name.endswith("_list") or name.endswith("s_list"):
            return self._normalize_list_response(name, res)
        # sinon renvoyer tel quel
        return res


