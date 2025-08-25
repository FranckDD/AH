import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image

from view.laboviews.form_param_view import ParamFormView
from view.laboviews.liste_param_view import ParamListView
from view.laboviews.reference_view import ReferenceRangesView
from view.laboviews.lab_results_views.pending_result import PendingResultsView
from view.laboviews.lab_results_views.completed_result import CompletedResultsView
from view.laboviews.lab_results_views.new_result import NewEntryView



class LaboratoryDashboardView(ctk.CTkFrame):
    def __init__(self, parent, user, controllers, on_logout=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.controllers = controllers
        self.on_logout = on_logout
        self.sidebar_expanded = True
        self.active_menu_btn = None

        # Accès aux sous-contrôleurs
        self.lab_ctrl = controllers.lab_controller

        # Configuration de la grille principale
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Construction des éléments UI
        self._build_sidebar()
        self._build_topbar()
        self._build_content()

        # Affichage initial
        self.show_pending_results()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=200, fg_color="#F8F9FA",
            border_width=1, border_color="#E0E0E0"
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Bouton de toggle
        self.toggle_btn = ctk.CTkButton(
            self.sidebar, text="<", width=30,
            fg_color="transparent", command=self.toggle_sidebar
        )
        self.toggle_btn.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Logo + titre
        img = Image.open(os.path.join("assets", "logo_light.png"))
        logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32))
        self.logo_label = ctk.CTkLabel(
            self.sidebar, image=logo_img, text=" One Health Lab",
            compound="left", text_color="#333",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # Sections du menu
        self.menu_buttons = []
        def make_section(row, title, items, toggle_fn):
            btn = ctk.CTkButton(
                self.sidebar, text=title, fg_color="transparent",
                text_color="#333", anchor="w", command=toggle_fn
            )
            btn.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
            self.menu_buttons.append(btn)
            frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            for txt, cmd in items:
                sub = ctk.CTkButton(
                    frame, text=txt, fg_color="transparent",
                    text_color="#333", anchor="w",
                    command=lambda c=cmd, b=btn: (self._set_active_menu(b), c())
                )
                sub.pack(fill="x", padx=25, pady=2)
                sub.bind("<Enter>", lambda e, w=sub: w.configure(text_color="#007bff"))
                sub.bind("<Leave>", lambda e, w=sub: w.configure(text_color="#333"))
            return btn, frame

        self.results_btn, self.results_sub = make_section(
            2, "Résultats", [
                ("En attente", self.show_pending_results),
                ("Interprétés", self.show_completed_results),
                ("Nouveaux", self.show_new_entry)
            ], self._toggle_results_sub
        )
        self.params_btn, self.params_sub = make_section(
            5, "Paramètres", [
                ("Liste", self.show_param_list),
                ("Ajouter", self.show_param_add)
            ], self._toggle_params_sub
        )
        self.refs_btn, self.refs_sub = make_section(
            8, "Références", [
                ("Plages", self.show_reference_ranges)
            ], self._toggle_refs_sub
        )
        self.stats_btn, self.stats_sub = make_section(
            11, "Statistiques", [
                ("Vue générale", self.show_statistics)
            ], self._toggle_stats_sub
        )

    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(
            self, height=60, fg_color="#007bff",
            corner_radius=0, border_width=1, border_color="#E0E0E0"
        )
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.topbar.grid_propagate(False)
        for idx, w in enumerate((0, 0, 0, 1, 0, 0)):
            self.topbar.grid_columnconfigure(idx, weight=w)

        img_tb = Image.open(os.path.join("assets", "logo_light.png"))
        logo_tb_img = ctk.CTkImage(light_image=img_tb, dark_image=img_tb, size=(24, 24))
        ctk.CTkLabel(
            self.topbar, image=logo_tb_img, text=" One Health Lab",
            compound="left", text_color="white",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=10)

        ctk.CTkButton(
            self.topbar, text="☰", width=30, height=30,
            fg_color="transparent", text_color="white",
            command=self.toggle_sidebar
        ).grid(row=0, column=1, padx=5)

        self.search_entry = ctk.CTkEntry(
            self.topbar, placeholder_text="🔍 Rechercher…", width=150
        )
        self.search_entry.grid(row=0, column=2, padx=10)

        ctk.CTkLabel(self.topbar, text="", fg_color="transparent").grid(row=0, column=3, sticky="ew")
        ctk.CTkButton(
            self.topbar, text="🔔", width=30, height=30,
            fg_color="transparent", text_color="white"
        ).grid(row=0, column=4, padx=5)

        self.profile_btn = ctk.CTkButton(
            self.topbar, text=f"{self.user.full_name} ▼",
            width=120, fg_color="transparent", text_color="white",
            command=self._open_profile_menu
        )
        self.profile_btn.grid(row=0, column=5, padx=10)

        self.profile_menu = tk.Menu(self.profile_btn, tearoff=0)
        for label, cmd in [
            ("Paramètres", self._show_settings),
            ("Éditer Profil", self._show_edit_profile),
            ("Changer MDP", self._show_change_password),
        ]:
            self.profile_menu.add_command(label=label, command=cmd)
        self.profile_menu.add_separator()
        self.profile_menu.add_command(label="Déconnexion", command=self._logout)

    def _build_content(self):
        self.content = ctk.CTkScrollableFrame(
            self, fg_color="#F5F5F5", corner_radius=0
        )
        self.content.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.content.grid_columnconfigure(0, weight=1)

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.configure(width=60)
            self.toggle_btn.configure(text=">")
            self.logo_label.configure(text="")
            for btn in self.menu_buttons:
                btn.configure(text="")
            self._hide_all_submenus()
        else:
            self.sidebar.configure(width=200)
            self.toggle_btn.configure(text="<")
            self.logo_label.configure(text=" One Health Lab")
            titles = ["Résultats", "Paramètres", "Références", "Statistiques"]
            for btn, txt in zip(self.menu_buttons, titles):
                btn.configure(text=txt)
        self.sidebar_expanded = not self.sidebar_expanded

    def _hide_all_submenus(self):
        for sub in (self.results_sub, self.params_sub, self.refs_sub, self.stats_sub):
            sub.grid_forget()

    def _toggle_results_sub(self):
        self._hide_all_submenus()
        if not self.results_sub.winfo_ismapped():
            self.results_sub.grid(row=3, column=0, sticky="nw")
        else:
            self.results_sub.grid_forget()

    def _toggle_params_sub(self):
        self._hide_all_submenus()
        if not self.params_sub.winfo_ismapped():
            self.params_sub.grid(row=6, column=0, sticky="nw")
        else:
            self.params_sub.grid_forget()

    def _toggle_refs_sub(self):
        self._hide_all_submenus()
        if not self.refs_sub.winfo_ismapped():
            self.refs_sub.grid(row=9, column=0, sticky="nw")
        else:
            self.refs_sub.grid_forget()

    def _toggle_stats_sub(self):
        self._hide_all_submenus()
        if not self.stats_sub.winfo_ismapped():
            self.stats_sub.grid(row=12, column=0, sticky="nw")
        else:
            self.stats_sub.grid_forget()

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _set_active_menu(self, btn):
        if self.active_menu_btn:
            self.active_menu_btn.configure(text_color="#333")
        btn.configure(text_color="#007bff")
        self.active_menu_btn = btn

    def show_pending_results(self):
        self._clear_content()
        self._set_active_menu(self.results_btn)
        view = PendingResultsView(self.content, controller=self.lab_ctrl, on_complete=self.show_completed_results)
        view.pack(fill="both", expand=True)

    def show_completed_results(self):
        self._clear_content()
        self._set_active_menu(self.results_btn)
        view = CompletedResultsView(self.content, controller=self.lab_ctrl)
        view.pack(fill="both", expand=True)

    def show_new_entry(self):
        self._clear_content()
        self._set_active_menu(self.results_btn)
        view = NewEntryView(self.content, controller=self.lab_ctrl, on_saved=self.show_pending_results)
        view.pack(fill="both", expand=True)

    def show_param_list(self):
        self._clear_content()
        self._set_active_menu(self.params_btn)
        view = ParamListView(
            parent=self.content,
            controller=self.lab_ctrl
        )
        view.pack(fill="both", expand=True)

    def show_param_add(self, param_id=None):
        self._clear_content()
        self._set_active_menu(self.params_btn)
        form = ParamFormView(
            master=self,
            controller=self.lab_ctrl,
            exams=self.lab_ctrl.list_examens(),
            param=self.lab_ctrl.get_param(param_id) if param_id else None,
            on_save=lambda: self.show_param_list()
        )
        form.grab_set()

    def show_reference_ranges(self):
        self._clear_content()
        self._set_active_menu(self.refs_btn)
        view = ReferenceRangesView(
            parent=self.content,
            controller=self.lab_ctrl
        )
        view.pack(fill="both", expand=True)

    def show_statistics(self):
        self._clear_content()
        self._set_active_menu(self.stats_btn)
        # TODO: connect StatisticsView via self.lab_ctrl

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
