import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from view.laboviews.form_reference_view import ReferenceRangeFormView

class ReferenceRangesView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.filtered = None
        self.page = 0
        self.page_size = 50

        # Titre
        ctk.CTkLabel(
            self,
            text="Liste des Plages de Référence",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=7, pady=(10,5), sticky="w")

        # Cadre de filtres
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=1, column=0, columnspan=7, sticky="ew", padx=10)
        filter_frame.grid_columnconfigure(0, weight=1)

        # Recherche par paramètre
        self.param_var = tk.StringVar()
        ctk.CTkLabel(filter_frame, text="Paramètre:").grid(row=0, column=0, padx=(0,5))
        ctk.CTkEntry(
            filter_frame,
            placeholder_text="Nom paramètre...",
            textvariable=self.param_var,
            width=200
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkButton(
            filter_frame, text="Filtrer", command=self._apply_filters
        ).grid(row=0, column=2, padx=5)

        # Treeview
        cols = ("ID","Paramètre","Sexe","Age_min","Age_max","Min","Max")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for col in cols:
            self.tree.heading(col, text=col.replace("_", " "), anchor="center")
            self.tree.column(col, anchor="center")
        self.tree.tag_configure('odd', background='white')
        self.tree.tag_configure('even', background='#f0f0f0')
        self.tree.grid(row=2, column=0, columnspan=7, sticky="nsew", padx=10, pady=5)

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.grid(row=2, column=7, sticky='ns', pady=5)
        h_scroll.grid(row=3, column=0, columnspan=7, sticky='ew', padx=10)

        # Boutons d'action
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=4, column=0, columnspan=7, pady=(5,0))
        ctk.CTkButton(action_frame, text="Nouvelle Plage", fg_color="green", command=self._on_create).pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text="Éditer", command=self._edit_selected).pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text="Supprimer", fg_color="red", command=self._delete_selected).pack(side="left", padx=10)

        # Pagination
        pag_frame = ctk.CTkFrame(self)
        pag_frame.grid(row=5, column=0, columnspan=7, pady=(5,10))
        self.prev_btn = ctk.CTkButton(pag_frame, text="Précédent", command=self._prev_page)
        self.next_btn = ctk.CTkButton(pag_frame, text="Suivant", command=self._next_page)
        self.page_label = ctk.CTkLabel(pag_frame, text="Page 1")
        self.prev_btn.pack(side="left", padx=5)
        self.page_label.pack(side="left", padx=5)
        self.next_btn.pack(side="left", padx=5)

        # Configuration redimensionnement
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Chargement initial
        self.load_data()

    def _apply_filters(self):
        all_ranges = self.controller.list_reference_ranges(self._get_selected_param_id())
        term = self.param_var.get().strip().lower()
        if term:
            self.filtered = [r for r in all_ranges if term in r['parametre_id'].__str__() or term in r['sexe'].lower()]
        else:
            self.filtered = None
        self.page = 0
        self._populate_tree()

    def _get_selected_param_id(self):
        # Retourne None ou filtrage par parametre
        return None  # TODO: étendre avec dropdown de paramètres

    def load_data(self):
        self.filtered = None
        self.page = 0
        self._populate_tree()

    def _populate_tree(self):
        data = self.filtered if self.filtered is not None else self.controller.list_reference_ranges(None)
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

        for idx, r in enumerate(page_data):
            tag = 'even' if idx%2==0 else 'odd'
            self.tree.insert(
                "",
                "end",
                iid=r['id'],
                values=(r['id'], r['parametre_id'], r['sexe'], r['age_min'], r['age_max'], r['valeur_min'], r['valeur_max']),
                tags=(tag,)
            )

    def _prev_page(self):
        if self.page>0:
            self.page -= 1
            self._populate_tree()

    def _next_page(self):
        data = self.filtered if self.filtered is not None else self.controller.list_reference_ranges(None)
        if (self.page+1)*self.page_size < len(data):
            self.page += 1
            self._populate_tree()

    def _on_create(self):
        win = ReferenceRangeFormView(
            master=self,
            controller=self.controller,
            reference=None,
            on_save=lambda: (self.load_data(), win.destroy())
        )

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Erreur", "Aucune plage sélectionnée.")
            return
        range_id = int(sel[0])
        reference = self.controller.get_reference_range(range_id)
        win = ReferenceRangeFormView(
            master=self,
            controller=self.controller,
            reference=reference,
            on_save=lambda: (self.load_data(), win.destroy())
        )

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Erreur", "Aucune plage sélectionnée.")
            return
        range_id = int(sel[0])
        if messagebox.askyesno("Confirmation", "Supprimer cette plage ?"):
            self.controller.delete_reference_range(range_id)
            self.load_data()
