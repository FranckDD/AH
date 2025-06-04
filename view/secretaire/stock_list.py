import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from view.secretaire.stock_form import StockFormView  # vue d’édition/création

class StockListView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.filtered = None

        # Titre
        ctk.CTkLabel(
            self,
            text="Liste des Produits / Product List",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(10, 5))

        # --- Filtres et recherche ---
        filter_frame = ctk.CTkFrame(self, corner_radius=10)
        filter_frame.pack(fill="x", padx=10, pady=(5, 10))
        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)

        # Recherche par nom ou type ou forme
        ctk.CTkLabel(filter_frame, text="Rechercher / Search :").grid(
            row=0, column=0, sticky="e", padx=(0, 5)
        )
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=self.search_var,
            placeholder_text="Nom, type ou forme… / Name, type or form…",
            width=200
        )
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self.apply_filters())

        ctk.CTkButton(
            filter_frame,
            text="🔍",
            width=30,
            command=self.apply_filters
        ).grid(row=0, column=2, padx=(0, 15))

        # Filtre par type
        ctk.CTkLabel(filter_frame, text="Type / Type :").grid(
            row=0, column=3, sticky="e", padx=(0, 5)
        )
        self.type_var = tk.StringVar(value="Tous / All")
        type_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.type_var,
            values=["Tous / All", "Naturel / Natural", "Pharmaceutique / Pharmaceutical"],
            width=150,
            command=lambda _: self.apply_filters()
        )
        type_combo.grid(row=0, column=4, sticky="ew", padx=(0, 15))

        # Filtre par statut
        ctk.CTkLabel(filter_frame, text="Statut / Status :").grid(
            row=0, column=5, sticky="e", padx=(0, 5)
        )
        self.status_var = tk.StringVar(value="Tous / All")
        status_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.status_var,
            values=["Tous / All", "normal / normal", "critique / critical", "épuisé / out_of_stock"],
            width=150,
            command=lambda _: self.apply_filters()
        )
        status_combo.grid(row=0, column=6, sticky="ew")

        # --- Treeview des produits ---
        cols = (
            "Nom / Name",
            "Type / Type",
            "Forme / Form",
            "Quantité / Quantity",
            "Seuil / Threshold",
            "Statut / Status",
            "Dosage (mg)",
            "Expiration"
        )
        self.tree = ttk.Treeview(
            self,
            columns=cols,
            show="headings",
            height=15
        )
        for col in cols:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(col, anchor="center", width=100)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Styles de ligne (coloration selon stock_status)
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree.tag_configure('normal', background='white')
        self.tree.tag_configure('critique', background='#FFF3CD')  # jaune pâle
        self.tree.tag_configure('épuisé', background='#F8D7DA')    # rose pâle

        # --- Boutons d’action ---
        action_frame = ctk.CTkFrame(self, corner_radius=10)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(action_frame, text="Nouveau / New", command=self._on_create).pack(side="left", padx=(0, 10))
        ctk.CTkButton(action_frame, text="Éditer / Edit", command=self._on_edit).pack(side="left", padx=(0, 10))
        ctk.CTkButton(action_frame, text="Rafraîchir / Refresh", command=self.load_data).pack(side="left")

        # Chargement initial
        self.load_data()

    def apply_filters(self):
        """
        Combine recherche (nom/type/forme), filtre type et filtre statut.
        """
        all_products = self.controller.list_products()
        term = self.search_var.get().strip().lower()
        t_full = self.type_var.get()
        s_full = self.status_var.get()

        # Extraction des parties françaises avant le slash
        t = t_full.split(" / ")[0].strip()       # ex. "Naturel" ou "Tous"
        s = s_full.split(" / ")[0].strip()       # ex. "normal" ou "Tous"

        filtered = all_products

        # 1) Recherche : nom OU type OU forme
        if term:
            filtered = [
                p for p in filtered
                if term in p.drug_name.lower()
                or term in p.medication_type.lower()
                or term in p.forme.lower()
            ]

        # 2) Filtre par type
        if t != "Tous":
            filtered = [p for p in filtered if p.medication_type == t]

        # 3) Filtre par statut
        if s != "Tous":
            filtered = [p for p in filtered if p.stock_status == s]

        self.filtered = filtered
        self._populate_tree()

    def load_data(self):
        """
        Réinitialise recherche + filtres, puis affiche tous les produits.
        """
        self.search_var.set("")
        self.type_var.set("Tous / All")
        self.status_var.set("Tous / All")
        self.filtered = None
        self._populate_tree()

    def _populate_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        data = self.filtered if self.filtered is not None else self.controller.list_products()

        for p in data:
            dosage_str = f"{float(p.dosage_mg):.2f}" if p.dosage_mg is not None else ""
            expiry_str = p.expiry_date.strftime("%Y-%m-%d") if p.expiry_date else ""
            tag = p.stock_status

            values = (
                p.drug_name,
                p.medication_type,
                p.forme,
                p.quantity,
                p.threshold,
                p.stock_status,
                dosage_str,
                expiry_str
            )
            self.tree.insert(
                "",
                "end",
                iid=p.medication_id,
                values=values,
                tags=(tag,)
            )

    def _on_create(self):
        """
        Ouvre le formulaire en création / open form in “create” mode
        """
        win = StockFormView(
            master=self,
            controller=self.controller,
            on_save=lambda: (self.load_data(), win.destroy()),
            product=None
        )

    def _on_edit(self):
        """
        Ouvre le formulaire pour éditer le produit sélectionné / open form in “edit” mode
        """
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Erreur / Error", "Aucun produit sélectionné / No product selected.")
            return
        try:
            product_id = int(sel[0])
        except ValueError:
            messagebox.showerror("Erreur / Error", f"ID invalide / Invalid ID : {sel[0]}")
            return

        product = self.controller.get_product(product_id)
        if not product:
            messagebox.showerror("Erreur / Error", f"Produit introuvable pour ID / Product not found for ID {product_id}")
            return

        win = StockFormView(
            master=self,
            controller=self.controller,
            on_save=lambda: (self.load_data(), win.destroy()),
            product=product
        )
