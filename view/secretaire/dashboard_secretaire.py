# view/secretaire/dashboard_secretaire_view.py
import tkinter as tk
import customtkinter as ctk
from PIL import Image
import os
from view.patient_view.patient_form_view import PatientFormView
from view.patient_view.patients_list_view import PatientListView
from view.secretaire.cs_form import CSFormView
from view.secretaire.cs_list import CSListView
from view.secretaire.stock_form import StockFormView
from view.secretaire.stock_list import StockListView
from view.secretaire.caisse_form import CaisseFormView
from view.secretaire.caisse_list import CaisseListView

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class SecretaireDashboardView(ctk.CTkFrame):
    def __init__(self, parent, user, controllers, on_logout=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.controllers = controllers
        self.on_logout = on_logout
        self.sidebar_expanded = True
        self.active_menu_btn = None

        self.locale = "fr"

        # controllers
        self.patient_ctrl = controllers.patient_controller
        self.cs_ctrl = controllers.consultation_spirituel_controller
        self.stock_ctrl = controllers.stock_controller
        self.tx_ctrl = controllers.caisse_controller
        self.pharmacy_ctrl = controllers.pharmacy_controller
        self.caisse_retrait_ctrl = controllers.caisse_retrait_controller
        

        # grid config
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # build UI
        self._build_sidebar()
        self._build_topbar()
        self._build_content()

        # init view
        self.show_dashboard()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color="#F8F9FA", border_width=1, border_color="#E0E0E0")
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # toggle button
        self.toggle_btn = ctk.CTkButton(
            self.sidebar,
            text="<",
            width=30,
            fg_color="transparent",
            command=self.toggle_sidebar
        )
        self.toggle_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # logo
        img = Image.open(os.path.join("assets", "logo_light.png"))
        logo = ctk.CTkImage(light_image=img, dark_image=img, size=(32,32))
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            image=logo,
            text=" Secrétariat",
            compound="left",
            text_color="#333",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # menu
        self.menu_buttons = []
        def make_btn(row, text, cmd):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                fg_color="transparent",
                text_color="#333",
                anchor="w",
                command=lambda: (self._set_active_menu(btn), self._clear_content(), cmd())
            )
            btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
            self.menu_buttons.append(btn)
            return btn

        r = 2
        self.btn_dashboard      = make_btn(r, "Tableau de bord", self.show_dashboard);      r+=1
        self.btn_patient_add    = make_btn(r, "Enr. patient",    self.show_patient_add);    r+=1
        self.btn_patient_list   = make_btn(r, "Liste patients",   self.show_patient_list);   r+=1
        self.btn_cs_add         = make_btn(r, "Nouvelle CS",      self.show_cs_form);        r+=1
        self.btn_cs_list        = make_btn(r, "Liste CS",         self.show_cs_list);        r+=1
        self.btn_stock_add      = make_btn(r, "Stock: enr.",      self.show_stock_form);     r+=1
        self.btn_stock_list     = make_btn(r, "Stock: liste",     self.show_stock_list);    r+=1
        self.btn_tx_add         = make_btn(r, "Caisse: vente",    self.show_tx_form);        r+=1
        self.btn_tx_list        = make_btn(r, "Caisse: liste",    self.show_tx_list)

    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(
            self,
            height=60,
            fg_color="#007bff",
            corner_radius=0,
            border_width=1,
            border_color="#E0E0E0"
        )
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        for i in range(6):
            self.topbar.grid_columnconfigure(i, weight=(3 if i == 3 else 0))

        # welcome text
        self.lbl_welcome = ctk.CTkLabel(
            self.topbar,
            text=f"Bienvenue {self.user.full_name}",
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_welcome.grid(row=0, column=0, padx=10)

        # spacer
        spacer = ctk.CTkLabel(self.topbar, text="", fg_color="transparent")
        spacer.grid(row=0, column=1, sticky="ew")

        # profile button
        self.profile_btn = ctk.CTkButton(
            self.topbar,
            text=self.user.full_name + " ▼",
            fg_color="transparent",
            text_color="white",
            command=self._open_profile_menu
        )
        self.profile_btn.grid(row=0, column=2, padx=10)

        # profile menu
        self.profile_menu = tk.Menu(self.profile_btn, tearoff=0)
        for label, cmd in [
            ("Paramètres", self._show_settings),
            ("Éditer Profil", self._show_edit_profile),
            ("Changer MDP", self._show_change_password)
        ]:
            self.profile_menu.add_command(label=label, command=cmd)
        self.profile_menu.add_separator()
        self.profile_menu.add_command(label="Déconnexion", command=self._logout)

    def _build_content(self):
        self.content = ctk.CTkScrollableFrame(
            self,
            fg_color="#F5F5F5",
            corner_radius=0
        )
        self.content.grid(row=1, column=1, sticky="nsew", padx=(0,10), pady=(0,10))
        self.content.grid_columnconfigure(0, weight=1)

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.configure(width=60)
            self.toggle_btn.configure(text=">")
            self.logo_label.configure(text="")
            for btn in self.menu_buttons:
                btn.configure(text="")
        else:
            self.sidebar.configure(width=200)
            self.toggle_btn.configure(text="<")
            self.logo_label.configure(text=" Secrétariat")
            texts = [
                "Tableau de bord", "Enr. patient", "Liste patients",
                "Nouvelle CS", "Liste CS", "Stock: enr.", "Stock: liste",
                "Caisse: vente", "Caisse: liste"
            ]
            for btn, txt in zip(self.menu_buttons, texts):
                btn.configure(text=txt)
        self.sidebar_expanded = not self.sidebar_expanded

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _set_active_menu(self, btn):
        if self.active_menu_btn:
            self.active_menu_btn.configure(text_color="#333")
        btn.configure(text_color="#007bff")
        self.active_menu_btn = btn

    def _open_profile_menu(self):
        x, y = (
            self.profile_btn.winfo_rootx(),
            self.profile_btn.winfo_rooty() + self.profile_btn.winfo_height()
        )
        self.profile_menu.tk_popup(x, y)

    def _show_settings(self): pass
    def _show_edit_profile(self): pass
    def _show_change_password(self): pass

    def _logout(self):
        if callable(self.on_logout):
            self.on_logout()

    # ————— Vues —————
    def show_dashboard(self):
        self._clear_content()
        lbl = ctk.CTkLabel(
            self.content,
            text="Dashboard Secrétaire",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        lbl.pack(pady=20)

    def show_patient_add(self):
        """
        Ouvre le formulaire de création de patient. On transmet `on_save=self.show_cs_form`
        pour que, dès qu'un patient est créé, on bascule vers le formulaire de CS avec le
        code_patient prérempli.
        """
        self._clear_content()
        self._set_active_menu(self.btn_patient_add)

        form = PatientFormView(
            parent=self.content,
            controller=self.patient_ctrl,
            current_user=self.user,
            patient_id=None,
            on_save=self.show_cs_form
        )
        form.grid(sticky="nsew", padx=10, pady=10)

    def show_patient_list(self):
        self._set_active_menu(self.btn_patient_list)
        patients = self.patient_ctrl.list_spiritual_patients()
        view = PatientListView(
            self.content,
            controller=self.patient_ctrl,
            patients=patients
        )
        view.pack(fill="both", expand=True)

    def show_cs_form(self, patient_code=None):
        """
        Ouvre le formulaire de Consultation Spirituelle. Si `patient_code` est fourni,
        on le préremplit et on charge le patient correspondant.
        """
        modal = CSFormView(
            master=self,
            controller=self.cs_ctrl,
            patient_ctrl=self.patient_ctrl,
            on_save=self.show_cs_form
        )
        if patient_code:
            modal.var_code.set(patient_code)
            modal.load_patient()
        modal.grab_set()

    def show_cs_list(self):
        self._set_active_menu(self.btn_cs_list)
        view = CSListView(self.content, controller=self.cs_ctrl)
        view.pack(fill="both", expand=True)

    def show_stock_form(self):
        self._set_active_menu(self.btn_stock_add)
        modal = StockFormView(master=self, controller=self.stock_ctrl)
        modal.grab_set()

    def show_stock_list(self):
        self._set_active_menu(self.btn_stock_list)
        view = StockListView(self.content, controller=self.stock_ctrl)
        view.pack(fill="both", expand=True)

    def show_tx_form(self):
        self._set_active_menu(self.btn_tx_add)
        modal = CaisseFormView(
                master=self,
                controller=self.tx_ctrl,
                patient_ctrl=self.patient_ctrl,
                pharmacy_ctrl=self.pharmacy_ctrl,   # ← on passe bien le controller pharmacie
                on_save=self.show_tx_list
            )
        modal.grab_set()

    def show_tx_list(self):
        self._set_active_menu(self.btn_tx_list)
        view = CaisseListView(
           parent=self.content,
           controller=self.tx_ctrl,
           patient_ctrl=self.patient_ctrl,
           pharmacy_ctrl=self.pharmacy_ctrl,
           caisse_retrait_controller=self.caisse_retrait_ctrl,
           locale=self.locale
       )
        view.pack(fill="both", expand=True)
