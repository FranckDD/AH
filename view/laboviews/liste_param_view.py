# view/laboviews/liste_param_view.py

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from view.laboviews.form_param_view import ParamFormView
from utils.export_params_pdf import export_params_to_pdf

class ParamListView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.filtered = None
        self.page = 0
        self.page_size = 50

        # Titre
        ctk.CTkLabel(
            self,
            text="Liste des Paramètres de Laboratoire",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=6, pady=(10, 5), sticky="w")

        # Cadre de filtres
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=10)
        filter_frame.grid_columnconfigure(0, weight=1)

        # Recherche
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Rechercher paramètre...",
            textvariable=self.search_var,
            width=250
        )
        search_entry.grid(row=0, column=0, sticky="w")
        search_entry.bind("<Return>", lambda e: self._apply_filters())
        ctk.CTkButton(filter_frame, text="🔍", width=30, command=self._apply_filters).grid(row=0, column=1, padx=(5,20))

        # Catégorie d'examen
        categories = ["Tous"] + sorted({e['categorie'] for e in controller.list_examens()})
        self.cat_var = tk.StringVar(value="Tous")
        ctk.CTkLabel(filter_frame, text="Catégorie:").grid(row=0, column=2, padx=(0,5))
        ctk.CTkOptionMenu(
            filter_frame,
            values=categories,
            variable=self.cat_var,
            command=lambda _: self._apply_filters()
        ).grid(row=0, column=3)

        # Treeview
        cols = ("ID", "Nom_parametre", "Unite", "Type_valeur", "Examen")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for col in cols:
            self.tree.heading(col, text=col.replace("_", " "), anchor="center")
            self.tree.column(col, anchor="center")
        self.tree.tag_configure('odd', background='white')
        self.tree.tag_configure('even', background='#f0f0f0')
        self.tree.grid(row=2, column=0, columnspan=6, sticky="nsew", padx=10, pady=5)

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.grid(row=2, column=6, sticky='ns', pady=5)
        h_scroll.grid(row=3, column=0, columnspan=6, sticky='ew', padx=10)

        # Boutons d'action
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=4, column=0, columnspan=6, pady=(5,0))
        ctk.CTkButton(action_frame, text="Nouveau", fg_color="green", command=self._on_create).pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text="Éditer", command=self._edit_selected).pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text="Exporter PDF", command=self._export_pdf).pack(side="left", padx=10)

        # Pagination
        pag_frame = ctk.CTkFrame(self)
        pag_frame.grid(row=5, column=0, columnspan=6, pady=(5,10))
        self.prev_btn = ctk.CTkButton(pag_frame, text="Précédent", command=self._prev_page)
        self.next_btn = ctk.CTkButton(pag_frame, text="Suivant", command=self._next_page)
        self.page_label = ctk.CTkLabel(pag_frame, text="Page 1")
        self.prev_btn.pack(side="left", padx=5)
        self.page_label.pack(side="left", padx=5)
        self.next_btn.pack(side="left", padx=5)

        # Configuration de redimensionnement
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Chargement initial
        self.load_data()

    def _apply_filters(self):
        all_params = self.controller.list_params()
        term = self.search_var.get().strip().lower()
        cat = self.cat_var.get()

        def match(p):
            ok_term = term in p['nom_parametre'].lower() if term else True
            ok_cat = (cat == "Tous" or p['examen']['categorie'] == cat)
            return ok_term and ok_cat

        self.filtered = [p for p in all_params if match(p)]
        self.page = 0
        self._populate_tree()

    def load_data(self):
        self.filtered = None
        self.page = 0
        self._populate_tree()

    def _populate_tree(self):
        data = self.filtered if self.filtered is not None else self.controller.list_params()
        start = self.page * self.page_size
        end = start + self.page_size
        page_data = data[start:end]

        total = len(data)
        total_pages = max(1, (total + self.page_size -1)//self.page_size)
        self.page_label.configure(text=f"Page {self.page+1} / {total_pages}")
        self.prev_btn.configure(state="normal" if self.page>0 else "disabled")
        self.next_btn.configure(state="normal" if self.page<total_pages-1 else "disabled")

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for idx, p in enumerate(page_data):
            tag = 'even' if idx%2==0 else 'odd'
            self.tree.insert(
                "",
                "end",
                iid=p['id'],
                values=(p['id'], p['nom_parametre'], p['unite'], p['type_valeur'], p['examen']['nom']),
                tags=(tag,)
            )

    def _prev_page(self):
        if self.page>0:
            self.page -= 1
            self._populate_tree()

    def _next_page(self):
        data = self.filtered if self.filtered is not None else self.controller.list_params()
        if (self.page+1)*self.page_size < len(data):
            self.page += 1
            self._populate_tree()

    def _on_create(self):
        win = ParamFormView(
            master=self,
            controller=self.controller,
            exams=self.controller.list_examens(),
            param=None,
            on_save=lambda: (self.load_data(), win.destroy())
        )

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Erreur", "Aucun paramètre sélectionné.")
            return
        param_id = int(sel[0])
        param = self.controller.get_param(param_id)
        win = ParamFormView(
            master=self,
            controller=self.controller,
            exams=self.controller.list_examens(),
            param=param,
            on_save=lambda: (self.load_data(), win.destroy())
        )

    def _export_pdf(self):
        data = self.filtered if self.filtered is not None else self.controller.list_params()
        out = export_params_to_pdf(data, title="Paramètres_Labo")
        messagebox.showinfo("Export PDF", f"Fichier généré : {out}")
