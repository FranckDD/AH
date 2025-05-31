# view/admin_view/dashboard_admin_view.py

import os
import customtkinter as ctk
from tkinter import ttk, messagebox
from PIL import Image
from datetime import date
from view.admin_view.user_form_view import UserFormView

class AdminDashboardView(ctk.CTkFrame):
    def __init__(self, parent, user, controller, on_logout=None):
        super().__init__(parent)

        # Réglage de la grille : topbar en row=0, sidebar+content en row=1
        self.grid_rowconfigure(0, weight=0)   # topbar fixe
        self.grid_rowconfigure(1, weight=1)   # sidebar + content
        self.grid_columnconfigure(0, weight=0)  # sidebar fixe
        self.grid_columnconfigure(1, weight=1)  # content extensible

        self.user            = user
        self.controller      = controller
        self.on_logout       = on_logout
        self.user_controller = controller.user_controller

        # Sidebar state
        self.sidebar_expanded = True
        self.expanded_width   = 200
        self.collapsed_width  = 60

        self._build_sidebar()
        self._build_topbar()
        self._build_content()
        self.show_overview()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=self.expanded_width, fg_color="#F8F9FA")
        # on place la sidebar en row=1 pour laisser le topbar en row=0
        self.sidebar.grid(row=1, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        # Logo
        logo_path = os.path.join("assets", "logo_light.png")
        if os.path.exists(logo_path):
            img      = Image.open(logo_path)
            logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(40, 40))
            ctk.CTkLabel(self.sidebar, image=logo_img, text="", fg_color="transparent")\
               .grid(row=0, column=0, pady=(10, 20))
        else:
            ctk.CTkLabel(
                self.sidebar,
                text="Logo",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#333"
            ).grid(row=0, column=0, pady=(10, 20))

        # Menu buttons
        self.menu_defs = [
            ("Synthèses",   "📈", self.show_overview),
            ("Statistiques","📊", self.show_statistics),
            ("Utilisateurs","👤", self.show_user_management),
        ]
        self.menu_buttons = []
        for idx, (label, icon, cmd) in enumerate(self.menu_defs, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}  {label}",
                fg_color="transparent",
                text_color="#333",
                anchor="w",
                hover_color="#E0E0E0",
                command=lambda c=cmd: self._switch(c)
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=10, pady=5)
            self.menu_buttons.append(btn)

    def _build_topbar(self):
        # Topbar en row=0 sur les 2 colonnes
        top = ctk.CTkFrame(self, height=60, fg_color="#007bff")
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.grid_propagate(False)

        # Toggle sidebar
        self.toggle_btn = ctk.CTkButton(
            top,
            text="⮜" if self.sidebar_expanded else "⮞",
            width=30,
            fg_color="transparent",
            text_color="white",
            hover_color="#0056b3",
            command=self._toggle_sidebar
        )
        self.toggle_btn.pack(side="left", padx=10, pady=10)

        # Bouton déconnexion
        ctk.CTkButton(
            top,
            text="Déconnexion",
            fg_color="transparent",
            text_color="white",
            hover_color="#0056b3",
            command=self._logout
        ).pack(side="right", padx=10, pady=10)

    def _build_content(self):
        self.content = ctk.CTkScrollableFrame(self, fg_color="#F5F5F5")
        self.content.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.content.grid_columnconfigure(0, weight=1)

    def _toggle_sidebar(self):
        if self.sidebar_expanded:
            # collapse
            self.sidebar.configure(width=self.collapsed_width)
            self.toggle_btn.configure(text="⮞")
            for btn, (_, icon, _) in zip(self.menu_buttons, self.menu_defs):
                btn.configure(text=f"{icon}")
        else:
            # expand
            self.sidebar.configure(width=self.expanded_width)
            self.toggle_btn.configure(text="⮜")
            for btn, (label, icon, _) in zip(self.menu_buttons, self.menu_defs):
                btn.configure(text=f"  {icon}  {label}")
        self.sidebar_expanded = not self.sidebar_expanded

    def _switch(self, fn):
        for w in self.content.winfo_children():
            w.destroy()
        fn()

    def show_overview(self):
        aps   = self.controller.appointment_controller.get_by_day(date.today())
        pres  = self.controller.prescription_controller.get_by_day(date.today())
        exams = self.controller.medical_record_controller.get_by_day(date.today())

        ctk.CTkLabel(
            self.content,
            text="Synthèse du Jour",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#333"
        ).pack(pady=10)

        for label, count in [("Rendez-vous", len(aps)),
                             ("Prescriptions", len(pres)),
                             ("Consultations", len(exams))]:
            ctk.CTkLabel(
                self.content,
                text=f"{label} : {count}",
                text_color="#333"
            ).pack(anchor="w", padx=20, pady=2)

    def show_statistics(self):
        ctk.CTkLabel(
            self.content,
            text="Statistiques Clés",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#333"
        ).pack(pady=10)
        # TODO: integrate matplotlib charts via python_user_visible

    def show_user_management(self):
        # Title + toolbar
        ctk.CTkLabel(
            self.content,
            text="Gestion des Utilisateurs",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#333"
        ).pack(pady=10)

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(0,10))

        self.user_search = ctk.StringVar()
        entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Rechercher…",
            textvariable=self.user_search,
            width=200
        )
        entry.pack(side="left", padx=(0,5))
        entry.bind("<Return>", lambda e: self._load_users())

        ctk.CTkButton(toolbar, text="🔍", width=30, command=self._load_users) \
            .pack(side="left", padx=(0,5))
        ctk.CTkButton(toolbar, text="Créer", command=self._create_user) \
            .pack(side="left", padx=(0,5))
        self.btn_edit_toolbar = ctk.CTkButton(
            toolbar,
            text="Éditer",
            state="disabled",
            command=self._edit_user
        )
        self.btn_edit_toolbar.pack(side="left", padx=(0,5))
        self.btn_delete_toolbar = ctk.CTkButton(
            toolbar,
            text="Supprimer",
            state="disabled",
            command=self._delete_user
        )
        self.btn_delete_toolbar.pack(side="left")

        # Styled Treeview
        style = ttk.Style()
        style.configure("mystyle.Treeview",
                        highlightthickness=0, bd=0,
                        font=(None,12), rowheight=28)
        style.configure("mystyle.Treeview.Heading",
                        font=(None,13,'bold'))
        style.layout("mystyle.Treeview",
                     [('Treeview.treearea',{'sticky':'nswe'})])

        cols = ("ID","Username","Rôle","Spécialité","Actif")
        self.tree = ttk.Treeview(
            self.content,
            columns=cols,
            show="headings",
            style="mystyle.Treeview",
            height=10
        )
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center")
        self.tree.tag_configure('odd',  background='#FFFFFF')
        self.tree.tag_configure('even', background='#F3F4F6')

        vsb = ttk.Scrollbar(
            self.content, orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_user_select)
        self._load_users()

    def _load_users(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        term = self.user_search.get().lower().strip()
        users = (self.user_controller.search_users(term)
                 if term else self.user_controller.list_users())

        for i, u in enumerate(users):
            tag = 'even' if i%2==0 else 'odd'
            role = (u.application_role.role_name
                    if getattr(u, 'application_role', None) else '')
            spec = (u.specialty.name
                    if getattr(u, 'specialty', None) else '')
            self.tree.insert(
                '',
                'end',
                iid=u.user_id,
                tags=(tag,),
                values=(u.user_id, u.username, role, spec,
                        'Oui' if u.is_active else 'Non')
            )

        self.btn_edit_toolbar.configure(state="disabled")
        self.btn_delete_toolbar.configure(state="disabled")

    def _on_user_select(self, _=None):
        ok = bool(self.tree.selection())
        state = "normal" if ok else "disabled"
        self.btn_edit_toolbar.configure(state=state)
        self.btn_delete_toolbar.configure(state=state)

    def _create_user(self):
        # Instancie directement UserFormView (qui est un CTkToplevel)
        modal = UserFormView(
            master     = self.winfo_toplevel(),
            controller = self.user_controller,
            on_save    = self._load_users
        )
        # Rend modal
        modal.grab_set()

    def _edit_user(self):
        sel  = self.tree.selection()[0]
        uid  = int(sel)
        user = self.user_controller.get_user_by_id(uid)
        # Si vous utilisez application_role pour le nom du rôle :
        if getattr(user, 'application_role', None):
            user.role_name = user.application_role.role_name

        # Instancie directement UserFormView
        modal = UserFormView(
            master     = self.winfo_toplevel(),
            controller = self.user_controller,
            user       = user,
            on_save    = self._load_users
        )
        modal.grab_set()

        

    def _delete_user(self):
        sel = self.tree.selection()[0]
        uid = int(sel)
        if not messagebox.askyesno("Confirmation", "Supprimer cet utilisateur ?"):
            return
        try:
            self.user_controller.delete_user(uid)
        except AttributeError:
            usr = self.user_controller.get_user_by_id(uid)
            self.controller.user_repo.session.delete(usr)
            self.controller.user_repo.session.commit()
        self._load_users()

    def _logout(self):
        if callable(self.on_logout):
            self.on_logout()
