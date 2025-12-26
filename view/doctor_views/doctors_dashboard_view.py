# view/doctor_views/doctors_dashboard_view.py
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
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
        kpi_frame.grid_columnconfigure((0,1,2,3,4), weight=1)  # 5 colonnes par ligne
        kpi_frame.grid_rowconfigure((0,1), weight=1)  # 2 lignes

        def make_card(parent, title):
            f = ctk.CTkFrame(parent, corner_radius=8, height=80)
            f.pack_propagate(False)
            lbl_title = ctk.CTkLabel(f, text=title, anchor="w", font=ctk.CTkFont(size=12))
            lbl_value = ctk.CTkLabel(f, text="—", anchor="w", font=ctk.CTkFont(size=20, weight="bold"))
            lbl_title.pack(anchor="w", padx=12, pady=(8,0))
            lbl_value.pack(anchor="w", padx=12)
            return f, lbl_value

        # Première ligne (5 cartes)
        self.card1_frame, self.lbl_total_patients = make_card(kpi_frame, "Patients distincts (7j)")
        self.card1_frame.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        self.card2_frame, self.lbl_appts_today = make_card(kpi_frame, "RDV prévus aujourd'hui")
        self.card2_frame.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")

        self.card3_frame, self.lbl_completed = make_card(kpi_frame, "RDV complétés")
        self.card3_frame.grid(row=0, column=2, padx=6, pady=6, sticky="nsew")

        self.card4_frame, self.lbl_cancelled = make_card(kpi_frame, "RDV annulés")
        self.card4_frame.grid(row=0, column=3, padx=6, pady=6, sticky="nsew")

        self.card5_frame, self.lbl_pending = make_card(kpi_frame, "RDV en attente")
        self.card5_frame.grid(row=0, column=4, padx=6, pady=6, sticky="nsew")

        # Deuxième ligne (4 cartes + bouton)
        self.card6_frame, self.lbl_renewals = make_card(kpi_frame, "Ordonnances à renouveler (14j)")
        self.card6_frame.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")

        self.card7_frame, self.lbl_patients_registered = make_card(kpi_frame, "Patients enregistrés (auj.)")
        self.card7_frame.grid(row=1, column=1, padx=6, pady=6, sticky="nsew")

        self.card8_frame, self.lbl_consultations_today = make_card(kpi_frame, "Consultations (auj.)")
        self.card8_frame.grid(row=1, column=2, padx=6, pady=6, sticky="nsew")

        self.card9_frame, self.lbl_prescriptions_today = make_card(kpi_frame, "Prescriptions (auj.)")
        self.card9_frame.grid(row=1, column=3, padx=6, pady=6, sticky="nsew")

        # Bouton rafraîchir sur la deuxième ligne
        ctk.CTkButton(kpi_frame, text="Rafraîchir", width=90, command=self._refresh_all_async).grid(
            row=1, column=4, padx=6, pady=6, sticky="nsew")

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

        # Bottom: Deux sections côte à côte
        bottom_frame = ctk.CTkFrame(sessions, corner_radius=8)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(6,0))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        # Left bottom: Patients enregistrés aujourd'hui
        self.new_patients_frame = ctk.CTkFrame(bottom_frame, corner_radius=8)
        self.new_patients_frame.grid(row=0, column=0, sticky="nsew", padx=(0,6), pady=6)
        self._build_new_patients_section(self.new_patients_frame)
        
        # Right bottom: Toutes les consultations
        self.all_consults_frame = ctk.CTkFrame(bottom_frame, corner_radius=8)
        self.all_consults_frame.grid(row=0, column=1, sticky="nsew", padx=(6,0), pady=6)
        self._build_all_consults_section(self.all_consults_frame)

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
        """Toutes les préconsultations enregistrées aujourd'hui."""
        lbl = ctk.CTkLabel(parent, text="Préconsultations - Aujourd'hui", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=(0,8))

        # Remplacer le listbox par une treeview pour plus d'informations
        columns = ("patient", "motif", "date")
        self.tree_consults = ttk.Treeview(frame, columns=columns, show="headings", height=10)
        
        # Définir les en-têtes
        self.tree_consults.heading("patient", text="Patient")
        self.tree_consults.heading("motif", text="Motif")
        self.tree_consults.heading("date", text="Date")
        
        # Définir la largeur des colonnes
        self.tree_consults.column("patient", width=150)
        self.tree_consults.column("motif", width=200)
        self.tree_consults.column("date", width=100)
        
        # Ajouter une scrollbar
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree_consults.yview)
        self.tree_consults.configure(yscrollcommand=sb.set)
        
        self.tree_consults.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(0,12))
        
        ctk.CTkButton(actions, text="Ouvrir dossier", command=self._open_selected_consultation).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Compléter consultation", command=self._complete_consultation).pack(side="left", padx=6)
        ctk.CTkButton(actions, text="Rafraîchir", command=self._refresh_all_consultations_async).pack(side="right", padx=6)

    def _build_new_patients_section(self, parent):
        """Patients créés/enregistrés aujourd'hui (tous utilisateurs)."""
        lbl = ctk.CTkLabel(parent, text="Patients enregistrés - Aujourd'hui", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,6))

        # Créer un frame avec une treeview pour afficher plus d'informations
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=12, pady=(0,8))
        
        # Créer une treeview avec des colonnes
        columns = ("code", "nom", "âge")
        self.tree_new_patients = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        
        # Définir les en-têtes
        self.tree_new_patients.heading("code", text="Code Patient")
        self.tree_new_patients.heading("nom", text="Nom")
        self.tree_new_patients.heading("âge", text="Âge")
        
        # Définir la largeur des colonnes
        self.tree_new_patients.column("code", width=100)
        self.tree_new_patients.column("nom", width=150)
        self.tree_new_patients.column("âge", width=50)
        
        # Ajouter une scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree_new_patients.yview)
        self.tree_new_patients.configure(yscrollcommand=scrollbar.set)
        
        self.tree_new_patients.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Frame pour les boutons
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0,12))
        
        ctk.CTkButton(btn_frame, text="Ouvrir dossier", command=self._open_selected_patient_from_new).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Nouvelle consultation", command=self._new_consultation_for_selected).pack(side="left", padx=6)
        ctk.CTkButton(btn_frame, text="Nouvelle prescription", command=self._new_prescription_for_selected).pack(side="left", padx=6)

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
            # Données existantes
            total_patients = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "distinct_patients_count"):
                total_patients = self.appt_ctrl.distinct_patients_count(start=week_start, end=today) or 0

            appts_today = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "total_appointments"):
                appts_today = self.appt_ctrl.total_appointments(start=today, end=today) or 0

            # Récupération détaillée du breakdown RDV
            completed = 0
            cancelled = 0
            pending = 0
            if self.appt_ctrl and hasattr(self.appt_ctrl, "count_by_status"):
                status_break = self.appt_ctrl.count_by_status(start=today, end=today) or {}
                completed = status_break.get('completed', 0)
                cancelled = status_break.get('cancelled', 0)
                pending = status_break.get('pending', 0)

            renewals = []
            if self.presc_ctrl and hasattr(self.presc_ctrl, "renewals_for_doctor"):
                renewals = self.presc_ctrl.renewals_for_doctor(within_days=14) or []

            # Nouvelles données
            patients_registered = 0
            if self.pat_ctrl and hasattr(self.pat_ctrl, "count_registered"):
                patients_registered = self.pat_ctrl.count_registered(period="day") or 0

            consultations_today = 0
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "count_consultations"):
                consultations_today = self.medrec_ctrl.count_consultations(period="day") or 0

            prescriptions_today = 0
            if self.presc_ctrl and hasattr(self.presc_ctrl, "count_prescriptions"):
                prescriptions_today = self.presc_ctrl.count_prescriptions(period="day") or 0

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
            self.after(0, lambda err=e: messagebox.showerror("Erreur KPI", f"Impossible de charger les KPI: {err}"))
            return

        # push UI updates
        self.after(0, lambda: self._update_kpis_ui(
            total_patients, appts_today, completed, cancelled, pending, 
            renewals, patients_registered, consultations_today, 
            prescriptions_today, recent_results, timeseries
        ))

        # refresh lists aussi (asynchrone)
        self._refresh_consultations_async()
        self._refresh_patients_async()
        self._refresh_new_patients_async()  # Ajouté pour rafraîchir les nouveaux patients
        self._refresh_all_consultations_async()  # Ajouté pour rafraîchir toutes les consultations

    def _update_kpis_ui(self, total_patients, appts_today, completed, cancelled, pending, 
                   renewals, patients_registered, consultations_today, 
                   prescriptions_today, recent_results, timeseries):
        try:
            self.lbl_total_patients.configure(text=str(total_patients))
        except Exception:
            pass
        try:
            self.lbl_appts_today.configure(text=str(appts_today))
        except Exception:
            pass

        # Breakdown RDV décomposé
        try:
            self.lbl_completed.configure(text=str(completed))
        except Exception:
            pass
            
        try:
            self.lbl_cancelled.configure(text=str(cancelled))
        except Exception:
            pass
            
        try:
            self.lbl_pending.configure(text=str(pending))
        except Exception:
            pass

        try:
            self.lbl_renewals.configure(text=str(len(renewals or [])))
        except Exception:
            pass

        # Nouvelles valeurs
        try:
            self.lbl_patients_registered.configure(text=str(patients_registered))
        except Exception:
            pass
            
        try:
            self.lbl_consultations_today.configure(text=str(consultations_today))
        except Exception:
            pass
            
        try:
            self.lbl_prescriptions_today.configure(text=str(prescriptions_today))
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
            
            # Calculer l'âge des patients
            today = date.today()
            display = []
            for p in (pats or []):
                if isinstance(p, dict):
                    code = p.get('code_patient', '')
                    nom = f"{p.get('first_name','')} {p.get('last_name','')}"
                    birth_date = p.get('birth_date')
                    if birth_date:
                        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    else:
                        age = "N/A"
                    pid = p.get('patient_id') or p.get('id')
                else:
                    code = getattr(p, 'code_patient', '')
                    nom = f"{getattr(p,'first_name','')} {getattr(p,'last_name','')}".strip()
                    birth_date = getattr(p, 'birth_date', None)
                    if birth_date:
                        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    else:
                        age = "N/A"
                    pid = getattr(p, 'patient_id', None) or getattr(p, 'id', None)
                
                display.append((code, nom, age, pid))
                
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur Patients", f"Impossible de charger patients: {err}"))
            return

        self.after(0, lambda: self._populate_new_patients_list(display))

    def _populate_new_patients_list(self, display):
        # Vider la treeview
        for item in self.tree_new_patients.get_children():
            self.tree_new_patients.delete(item)
        
        # Remplir avec les nouvelles données
        for code, nom, age, pid in (display or []):
            self.tree_new_patients.insert("", "end", values=(code, nom, age, pid))

    def _refresh_all_consultations_worker(self):
        """Charge toutes les préconsultations du jour."""
        try:
            today = date.today()
            consultations = []
            
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "get_by_day"):
                consultations = self.medrec_ctrl.get_by_day(today) or []
            
            # Normaliser l'affichage
            display = []
            for c in (consultations or []):
                try:
                    # Récupérer les informations du patient
                    patient_id = getattr(c, "patient_id", None)
                    patient_info = ""
                    if patient_id and self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                        p = self.pat_ctrl.get_patient(patient_id)
                        if isinstance(p, dict):
                            patient_info = f"{p.get('code_patient','')} - {p.get('first_name','')} {p.get('last_name','')}"
                        else:
                            patient_info = f"{getattr(p,'code_patient','')} - {getattr(p,'first_name','')} {getattr(p,'last_name','')}"
                    
                    motif = getattr(c, "motif_code", "Non spécifié")
                    consult_date = getattr(c, "consultation_date", None)
                    date_str = consult_date.strftime("%Y-%m-%d %H:%M") if consult_date else "Date inconnue"
                    record_id = getattr(c, "record_id", None)
                    
                    display.append((patient_info, motif, date_str, patient_id, record_id))
                except Exception as e:
                    print(f"Erreur traitement consultation: {e}")
                    continue
                    
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Erreur Consultations", f"Impossible de charger les consultations: {err}"))
            return

        self.after(0, lambda: self._populate_all_consults_list(display))

    def _populate_all_consults_list(self, display):
        # Vider la treeview
        for item in self.tree_consults.get_children():
            self.tree_consults.delete(item)
        
        # Remplir avec les nouvelles données
        for patient, motif, date_str, patient_id, record_id in (display or []):
            self.tree_consults.insert("", "end", values=(patient, motif, date_str, patient_id, record_id))


    # ---------------------------
    # Actions spécifiques aux nouvelles listes
    # ---------------------------
    def _open_selected_patient_from_all(self):
        selection = self.tree_consults.selection()
        if not selection:
            messagebox.showinfo("Info", "Sélectionnez une consultation.")
            return
        
        item = self.tree_consults.item(selection[0])
        values = item['values']
        if len(values) >= 4:
            patient_id = values[3]  # L'ID patient est stocké dans la 4ème colonne
            self._open_patient_records_modal(patient_id)


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

        # priorité au callback parent si fourni
        if callable(self.on_start_consultation):
            self.on_start_consultation(appt)
            return

        # --- Tentative de synchroniser le statut RDV -> "in_progress" ---
        try:
            appt_id = getattr(appt, "id", None) or getattr(appt, "appointment_id", None)
            if appt_id and self.appt_ctrl:
                # essais sur des noms de méthodes courants (robuste)
                tried = False
                for name in ("set_status", "set_appointment_status", "update_status", "update_appointment", "update", "change_status", "mark_in_progress"):
                    fn = getattr(self.appt_ctrl, name, None)
                    if callable(fn):
                        try:
                            # essayer différentes signatures
                            try:
                                fn(appt_id, "in_progress")
                            except TypeError:
                                try:
                                    fn(appt_id, status="in_progress")
                                except TypeError:
                                    try:
                                        fn(appt_id, {"status": "in_progress"})
                                    except TypeError:
                                        fn(appt_id)
                            tried = True
                            break
                        except Exception:
                            # ignorer et essayer la méthode suivante
                            continue
                # si pas de méthode dédiée, tenter update via un update générique si présent
                if not tried and hasattr(self.appt_ctrl, "update"):
                    try:
                        self.appt_ctrl.update(appt_id, {"status": "in_progress"})
                    except Exception:
                        pass
        except Exception:
            pass
        # ---------------------------------------------------------------

        # ouvrir formulaire (prérempli par patient)
        pid = getattr(appt, "patient_id", None) or (getattr(appt, "patient", None) and getattr(getattr(appt, "patient", None), "patient_id", None))
        try:
            record_id = getattr(appt, "record_id", None) or getattr(appt, "medical_record_id", None)
            if record_id:
                self._open_medical_record_modal(record=appt, patient_id=pid, is_update=True)
            else:
                self._open_medical_record_modal(record=None, patient_id=pid, is_update=False)
        except Exception:
            self._open_medical_record_modal(record=None, patient_id=pid, is_update=False)



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
        # callback parent prioritaire
        if callable(self.on_open_record):
            self.on_open_record(pid)
            return

        # privilégier ouverture directe du modal de dossiers médicaux (même comportement que section Préconsultations)
        try:
            self._open_patient_records_modal(pid)
            return
        except Exception:
            pass

        # fallback : essayer un opener exposé par le controller
        opener = getattr(self.controller, "show_medical_record_form", None) or getattr(self.controller, "show_medical_record_list", None)
        if callable(opener):
            try:
                opener(pid)
            except TypeError:
                try:
                    opener()
                except Exception:
                    messagebox.showinfo("Ouverture dossier", f"Ouvrir dossier patient id={pid}")
            return

        messagebox.showinfo("Ouverture dossier", f"Ouvrir dossier patient id={pid}")




    def _open_medical_record_modal(self, record=None, patient_id=None, is_update=False, appointment_id=None):
        """Ouvre la fenêtre du formulaire MedicalRecord (création ou édition).

        - record: un objet record existant (optionnel)
        - patient_id: id du patient pour pré-remplir le formulaire (optionnel)
        - is_update: si True, appelle _load_record() pour charger les données
        - appointment_id: id du RDV associé (optionnel) -> passé au formulaire pour synchronisation
        """
        # import local pour éviter erreurs d'import cycle/chemin
        try:
            from ..medical_record.medical_record_form_view import MedicalRecordFormView
        except Exception:
            try:
                from view.medical_record.medical_record_form_view import MedicalRecordFormView
            except Exception:
                MedicalRecordFormView = None

        if MedicalRecordFormView is None:
            messagebox.showerror("Erreur", "Formulaire dossier médical introuvable (import failed).")
            return

               # créer ScrollableToplevel (contient top.form_frame)
        try:
            from utils.scrollable_toplevel import ScrollableToplevel as TopClass
        except Exception:
            TopClass = globals().get("ScrollableToplevel", None)

        # déterminer record_id si on a un objet record
        rec_id = None
        if record:
            rec_id = getattr(record, "record_id", None) or getattr(record, "id", None)

        if TopClass is None:
            # fallback -> comportement originel si util non disponible
            top = tk.Toplevel(self)
            top.title("Dossier médical")
            top.geometry("900x650")
            try:
                top.transient(self.winfo_toplevel())
            except Exception:
                pass
            form = MedicalRecordFormView(top, self.controller, record_id=rec_id)
            form.pack(fill="both", expand=True)
        else:
            top = TopClass(self, title="Dossier médical", size="900x650")
            # instancier le formulaire DANS top.form_frame pour rendre le contenu scrollable
            form = MedicalRecordFormView(top.form_frame, self.controller, record_id=rec_id)
            form.pack(fill="both", expand=True)

        # Pré-remplir patient si patient_id fourni
        pid = patient_id or (getattr(record, "patient_id", None) if record else None)
        if pid:
            patient = None
            try:
                if self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                    patient = self.pat_ctrl.get_patient(pid)
                if not patient and hasattr(self.controller, "find_patient"):
                    patient = self.controller.find_patient(str(pid))
            except Exception:
                patient = None

            try:
                if isinstance(patient, dict):
                    code = patient.get("code_patient", "") or ""
                    first = patient.get("first_name", "") or ""
                    last = patient.get("last_name", "") or ""
                else:
                    code = getattr(patient, "code_patient", "") or ""
                    first = getattr(patient, "first_name", "") or ""
                    last = getattr(patient, "last_name", "") or ""

                try:
                    form.patient_id_var.set(str(pid))
                except Exception:
                    pass
                try:
                    form.patient_code_var.set(str(code))
                except Exception:
                    pass
                try:
                    form.patient_name_var.set(f"{last} {first}".strip())
                except Exception:
                    pass

                try:
                    form.date_widget.set_date(date.today())
                except Exception:
                    pass
            except Exception:
                pass

        # si on ouvre en mode update et qu'on a un record, recharger
        if is_update and rec_id:
            try:
                form.record_id = rec_id
                form._load_record()
            except Exception:
                pass

        try:
            top.grab_set()
        except Exception:
            pass


    


    def _open_selected_patient_from_new(self):
        selection = self.tree_new_patients.selection()
        if not selection:
            messagebox.showinfo("Info", "Sélectionnez un patient.")
            return
        
        item = self.tree_new_patients.item(selection[0])
        values = item['values']
        if len(values) >= 4:
            patient_id = values[3]  # L'ID patient est stocké dans la 4ème colonne
            self._open_patient_records_modal(patient_id)

    def _open_selected_consultation(self):
        """Ouvre le dossier de la consultation sélectionnée"""
        selection = self.tree_consults.selection()
        if not selection:
            messagebox.showinfo("Info", "Sélectionnez une consultation.")
            return
        
        item = self.tree_consults.item(selection[0])
        values = item['values']
        if len(values) >= 4:
            patient_id = values[3]  # L'ID patient est stocké dans la 4ème colonne
            self._open_patient_records_modal(patient_id)

    def _complete_consultation(self):
        """Complète la consultation sélectionnée"""
        selection = self.tree_consults.selection()
        if not selection:
            messagebox.showinfo("Info", "Sélectionnez une consultation.")
            return
        
        item = self.tree_consults.item(selection[0])
        values = item['values']
        if len(values) >= 5:
            record_id = values[4]  # L'ID record est stocké dans la 5ème colonne
            
            # Ouvrir le formulaire de mise à jour du medical record
            if self.medrec_ctrl and hasattr(self.medrec_ctrl, "get_record"):
                record = self.medrec_ctrl.get_record(record_id)
                if record:
                    # Ouvrir une modale pour compléter la consultation
                    self._open_medical_record_modal(record, is_update=True)

    def _new_consultation_for_selected(self):
        """Ouvre le formulaire de nouvelle consultation pour le patient sélectionné"""
        selection = self.tree_new_patients.selection()
        if not selection:
            messagebox.showinfo("Info", "Sélectionnez un patient.")
            return
        
        item = self.tree_new_patients.item(selection[0])
        values = item['values']
        if len(values) >= 4:
            patient_id = values[3]  # L'ID patient est stocké dans la 4ème colonne
            
            # Ouvrir le formulaire de nouveau medical record
            self._open_medical_record_modal(None, patient_id=patient_id)

    def _new_prescription_for_selected(self):
        selection = self.tree_new_patients.selection()
        if not selection:
            messagebox.showinfo("Info", "Sélectionnez un patient.")
            return

        item = self.tree_new_patients.item(selection[0])
        values = item['values']
        if len(values) >= 4:
            patient_id = values[3]  # ID patient

            # priorité : si controller expose un helper, l'utiliser
            if hasattr(self.controller, "show_prescription_form"):
                try:
                    self.controller.show_prescription_form(patient_id, None)
                    return
                except Exception:
                    pass

            # sinon ouvrir PrescriptionFormView dans un Toplevel
            try:
                try:
                    from ..prescription_views.prescription_form import PrescriptionFormView
                except Exception:
                    from view.prescription_views.prescription_form import PrescriptionFormView
            except Exception:
                PrescriptionFormView = None

            if PrescriptionFormView is None:
                messagebox.showerror("Erreur", "Formulaire prescription introuvable (import failed).")
                return

                       # créer ScrollableToplevel pour la prescription
            try:
                from utils.scrollable_toplevel import ScrollableToplevel as TopClass
            except Exception:
                TopClass = globals().get("ScrollableToplevel", None)

            if TopClass is None:
                top = tk.Toplevel(self)
                top.title("Nouvelle prescription")
                top.geometry("700x520")
                try:
                    top.transient(self.winfo_toplevel())
                except Exception:
                    pass
                form = PrescriptionFormView(top, self.controller, prescription_id=None, patient_id=patient_id, medical_record_id=None)
                form.pack(fill="both", expand=True)
            else:
                top = TopClass(self, title="Nouvelle prescription", size="700x520")
                # instancier la prescription DANS top.form_frame
                form = PrescriptionFormView(top.form_frame, self.controller, prescription_id=None, patient_id=patient_id, medical_record_id=None)

            # pré-remplir nom/code patient si possible
            try:
                pat = None
                if self.pat_ctrl and hasattr(self.pat_ctrl, "get_patient"):
                    pat = self.pat_ctrl.get_patient(patient_id)
                if not pat and hasattr(self.controller, "find_patient"):
                    pat = self.controller.find_patient(str(patient_id))
                if pat:
                    if isinstance(pat, dict):
                        code = pat.get("code_patient","")
                        name = f"{pat.get('last_name','')} {pat.get('first_name','')}".strip()
                    else:
                        code = getattr(pat, "code_patient", "")
                        name = f"{getattr(pat,'last_name','')} {getattr(pat,'first_name','')}".strip()
                    try:
                        form.patient_code_var.set(code)
                    except Exception:
                        pass
                    try:
                        form.patient_name_var.set(name)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                top.grab_set()
            except Exception:
                pass


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

        # Utiliser une frame existante - par exemple, la frame des consultations
        if hasattr(self, 'all_consults_frame'):
            self.chart_canvas = FigureCanvasTkAgg(fig, master=self.all_consults_frame)
        else:
            # Fallback: utiliser la frame principale
            self.chart_canvas = FigureCanvasTkAgg(fig, master=self)
            
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
        super(DoctorsDashboardView, self).destroy()
