# view/secretaire/cs_list.py

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from utils.export_cs_pdf import export_cs_to_pdf
from view.secretaire.cs_form import CSFormView  # ← Remplace l’ancien import

class CSListView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.filtered = None
        self.page = 0
        self.page_size = 100

        # Title
        ctk.CTkLabel(
            self,
            text="Liste des Consultations Spirituelles",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=5, pady=(10, 5))

        # Filters frame
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10)
        filter_frame.grid_columnconfigure(0, weight=1)

        # Search + button côte à côte
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Rechercher patient...",
            textvariable=self.search_var,
            width=200
        )
        search_entry.grid(row=0, column=0, sticky="w")
        search_entry.bind("<Return>", lambda e: self._apply_filters())
        ctk.CTkButton(
            filter_frame,
            text="🔍",
            width=30,
            command=self._apply_filters
        ).grid(row=0, column=1, padx=(5,20))

        # Type filter dropdown
        types = ["Tous"] + sorted({cs.type_consultation for cs in controller.list_consultations()})
        self.type_var = tk.StringVar(value="Tous")
        ctk.CTkLabel(filter_frame, text="Type:").grid(row=0, column=2, padx=(0,5))
        ctk.CTkOptionMenu(
            filter_frame,
            values=types,
            variable=self.type_var,
            command=lambda _: self._apply_filters()
        ).grid(row=0, column=3)

        # Define columns
        cols = (
            "patient", "type_consultation", "presc_generic", "presc_med_spirituel",
            "mp_type", "fr_registered_at", "fr_appointment_at",
            "fr_amount_paid", "fr_observation"
        )
        headings = {
            "patient": "Patient",
            "type_consultation": "Type",
            "presc_generic": "Presc. Gén.",
            "presc_med_spirituel": "Presc. Méd. Spir.",
            "mp_type": "MP Type",
            "fr_registered_at": "Inscrit le",
            "fr_appointment_at": "Rdv le",
            "fr_amount_paid": "Montant payé",
            "fr_observation": "Observation"
        }

        # Treeview style
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=20)

        # Treeview setup
        self.tree = ttk.Treeview(
            self,
            columns=cols,
            show="headings",
            height=15,
            style="Custom.Treeview"
        )
        for col in cols:
            self.tree.heading(col, text=headings[col], anchor="center")
            self.tree.column(col, anchor="center")
        # Alternating row colors
        self.tree.tag_configure('odd', background='white')
        self.tree.tag_configure('even', background='#f0f0f0')

        self.tree.grid(row=2, column=0, columnspan=5, sticky="nsew", padx=10, pady=5)

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.grid(row=2, column=5, sticky='ns', pady=5)
        h_scroll.grid(row=3, column=0, columnspan=5, sticky='ew', padx=10)

        # Action buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=4, column=0, columnspan=5, pady=(5,0))
        # Si vous souhaitez un bouton "Nouveau" pour créer une consultation, décommentez la ligne ci-dessous :
        # ctk.CTkButton(action_frame, text="Nouveau", command=self._on_create).pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text="Éditer", command=self._edit_selected).pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text="Exporter PDF", command=self._export_pdf).pack(side="left", padx=10)

        # Pagination controls
        pag_frame = ctk.CTkFrame(self)
        pag_frame.grid(row=5, column=0, columnspan=5, pady=(5,10))
        self.prev_btn = ctk.CTkButton(pag_frame, text="Précédent", command=self._prev_page)
        self.next_btn = ctk.CTkButton(pag_frame, text="Suivant", command=self._next_page)
        self.page_label = ctk.CTkLabel(pag_frame, text="Page 1")
        self.prev_btn.pack(side="left", padx=5)
        self.page_label.pack(side="left", padx=5)
        self.next_btn.pack(side="left", padx=5)

        # Configure resizing
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Initial load
        self.load_data()

    def _apply_filters(self):
        """
        Applique le filtre saisi par l’utilisateur :
        - On recherche dans le code_patient OU dans le nom/prénom (case-insensitive).
        - On applique aussi le filtre de type si nécessaire.
        """
        all_cs = self.controller.list_consultations()
        term = self.search_var.get().strip().lower()

        if term:
            def match_patient(cs):
                if not cs.patient:
                    return False
                code = (cs.patient.code_patient or "").lower()
                nom  = (getattr(cs.patient, 'last_name', "") or "").lower()
                pre  = (getattr(cs.patient, 'first_name', "") or "").lower()
                return term in code or term in nom or term in pre

            filtered = [cs for cs in all_cs if match_patient(cs)]
        else:
            filtered = all_cs

        t = self.type_var.get()
        if t != "Tous":
            filtered = [cs for cs in filtered if cs.type_consultation == t]

        self.filtered = filtered
        self.page = 0
        self._populate_tree()


    def load_data(self):
        self.filtered = None
        self.page = 0
        self._populate_tree()

    def _populate_tree(self):
        """
        Remplit le Treeview avec les consultations paginées.
        La colonne “patient” affiche maintenant : 
            <code_patient> – <last_name> <first_name>
        """
        data = self.filtered if self.filtered is not None else self.controller.list_consultations()
        start = self.page * self.page_size
        end = start + self.page_size
        page_data = data[start:end]

        total_pages = max(1, (len(data) + self.page_size - 1) // self.page_size)
        self.page_label.configure(text=f"Page {self.page + 1} / {total_pages}")
        self.prev_btn.configure(state="normal" if self.page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.page < total_pages - 1 else "disabled")

        # Vide le tree
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for idx, cs in enumerate(page_data):
            # Nouveau format pour la colonne patient
            if cs.patient:
                code = cs.patient.code_patient or ""
                nom  = getattr(cs.patient, 'last_name', "") or ""
                pre  = getattr(cs.patient, 'first_name', "") or ""
                patient_display = f"{code} – {nom} {pre}"
            else:
                patient_display = ""

            reg = cs.fr_registered_at.strftime("%Y-%m-%d") if getattr(cs, 'fr_registered_at', None) else ""
            app = cs.fr_appointment_at.strftime("%Y-%m-%d") if getattr(cs, 'fr_appointment_at', None) else ""
            amt = f"{cs.fr_amount_paid:.2f}" if getattr(cs, 'fr_amount_paid', None) is not None else ""
            obs_text = cs.fr_observation or ""
            obs = obs_text[:30] + ("…" if len(obs_text) > 30 else "")

            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree.insert(
                "",
                "end",
                iid=getattr(cs, 'consultation_id', None),
                values=(
                    patient_display,
                    cs.type_consultation,
                    cs.presc_generic,
                    cs.presc_med_spirituel,
                    cs.mp_type,
                    reg,
                    app,
                    amt,
                    obs
                ),
                tags=(tag,)
            )


    def _prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._populate_tree()

    def _next_page(self):
        total = len(self.filtered) if self.filtered is not None else len(self.controller.list_consultations())
        if (self.page + 1) * self.page_size < total:
            self.page += 1
            self._populate_tree()

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Erreur", "Aucune consultation sélectionnée.")
            return

        try:
            cs_id = int(sel[0])
        except ValueError:
            messagebox.showerror("Erreur", f"ID invalide : {sel[0]}")
            return

        try:
            cs_obj = self.controller.get_consultation(cs_id)
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return

        # Ouvre CSFormView en mode édition
        win = CSFormView(
            master=self,
            controller=self.controller,
            patient_ctrl=self.controller.patient_controller,
            consultation=cs_obj,
            on_save=lambda: (self.load_data(), win.destroy())
        )

    # Si vous souhaitez un bouton "Nouveau", décommentez cette méthode :
    # def _on_create(self):
    #     win = CSFormView(
    #         master=self,
    #         controller=self.controller,
    #         patient_ctrl=self.controller.patient_controller,
    #         consultation=None,
    #         on_save=lambda: (self.load_data(), win.destroy())
    #     )

    def _export_pdf(self):
        data = self.filtered if self.filtered is not None else self.controller.list_consultations()
        t = self.type_var.get()
        if t != "Tous":
            data = [cs for cs in data if cs.type_consultation == t]
        export_list = []
        for cs in data:
            export_list.append(type('X', (object,), {
                'patient_id': cs.patient.patient_id if cs.patient else None,
                'code_patient': cs.patient.code_patient if cs.patient else '',
                'type_consultation': cs.type_consultation,
                'fr_registered_at': cs.fr_registered_at,
                'fr_appointment_at': cs.fr_appointment_at,
                'fr_amount_paid': cs.fr_amount_paid,
                'fr_observation': cs.fr_observation
            })())
        out = export_cs_to_pdf(data, title=f"Consultations_{t}")
        messagebox.showinfo("Export PDF", f"Fichier généré : {out}")
