# view/secretaire/stock_list.py

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from view.secretaire.renew_stock import RenewStockDialog


class StockListView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.filtered = None

        # Titre
        ctk.CTkLabel(
            self,
            text="Liste des Produits",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(10, 5))

        # --- Filtres et recherche ---
        filter_frame = ctk.CTkFrame(self, corner_radius=10)
        filter_frame.pack(fill="x", padx=10, pady=(5, 10))
        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)
        filter_frame.grid_columnconfigure(5, weight=1)

        # Recherche par nom ou type
        ctk.CTkLabel(filter_frame, text="Rechercher :").grid(
            row=0, column=0, sticky="e", padx=(0, 5)
        )
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=self.search_var,
            placeholder_text="Nom ou type...",
            width=200
        )
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self.apply_filters())

        search_btn = ctk.CTkButton(
            filter_frame,
            text="🔍",
            width=30,
            command=self.apply_filters
        )
        search_btn.grid(row=0, column=2, padx=(0, 15))

        # Filtre par type
        ctk.CTkLabel(filter_frame, text="Type :").grid(
            row=0, column=3, sticky="e", padx=(0, 5)
        )
        self.type_var = tk.StringVar(value="Tous")
        type_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.type_var,
            values=["Tous", "Naturel", "Pharmaceutique"],
            width=150,
            command=lambda _: self.apply_filters()
        )
        type_combo.grid(row=0, column=4, sticky="ew", padx=(0, 15))

        # Filtre par statut
        ctk.CTkLabel(filter_frame, text="Statut :").grid(
            row=0, column=5, sticky="e", padx=(0, 5)
        )
        self.status_var = tk.StringVar(value="Tous")
        status_combo = ctk.CTkComboBox(
            filter_frame,
            variable=self.status_var,
            values=["Tous", "normal", "critique", "épuisé"],
            width=150,
            command=lambda _: self.apply_filters()
        )
        status_combo.grid(row=0, column=6, sticky="ew")

        # --- Treeview des produits ---
        cols = (
            "Nom", "Type", "Quantité", "Seuil", "Statut",
            "Dosage (mg)", "Expiration"
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

        # Styles des lignes
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree.tag_configure('normal', background='white')
        self.tree.tag_configure('critique', background='#FFF3CD')  # jaune pâle
        self.tree.tag_configure('épuisé', background='#F8D7DA')    # rose pâle

        # --- Boutons d'action ---
        action_frame = ctk.CTkFrame(self, corner_radius=10)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.renew_btn = ctk.CTkButton(
            action_frame,
            text="Réapprovisionner",
            command=self.renew_selected
        )
        self.renew_btn.pack(side="left")
        self.refresh_btn = ctk.CTkButton(
            action_frame,
            text="Rafraîchir",
            command=self.load_data
        )
        self.refresh_btn.pack(side="left", padx=(10, 0))

        # Initialisation
        self.load_data()

    def apply_filters(self):
        """
        Combine recherche (nom ou type), filtre type et filtre statut.
        """
        all_products = self.controller.list_products()
        term = self.search_var.get().strip().lower()
        t = self.type_var.get()
        s = self.status_var.get()

        filtered = all_products

        # Filtre par recherche sur nom OU type
        if term:
            filtered = [
                p for p in filtered
                if term in p.drug_name.lower()
                or term in p.medication_type.lower()
            ]

        # Filtre par type
        if t != "Tous":
            filtered = [p for p in filtered if p.medication_type == t]

        # Filtre par statut
        if s != "Tous":
            filtered = [p for p in filtered if p.stock_status == s]

        self.filtered = filtered
        self._populate_tree()

    def load_data(self):
        """
        Réinitialise la recherche et les filtres, puis recharge tous les produits.
        """
        self.search_var.set("")
        self.type_var.set("Tous")
        self.status_var.set("Tous")
        self.filtered = None
        self._populate_tree()

    def _populate_tree(self):
        """
        Remplit le Treeview avec la liste appropriée (filtrée ou complète).
        """
        # Effacer l’ancien contenu
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        data = self.filtered if self.filtered is not None else self.controller.list_products()

        for p in data:
            dosage_str = f"{float(p.dosage_mg):.2f}" if p.dosage_mg is not None else ""
            expiry_str = p.expiry_date.strftime("%Y-%m-%d") if p.expiry_date else ""
            tag = p.stock_status  # 'normal', 'critique' ou 'épuisé'

            values = (
                p.drug_name,
                p.medication_type,
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

    def renew_selected(self):
        """
        Ouvre le dialog pour réapprovisionner le stock du produit sélectionné.
        """
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Erreur", "Aucun produit sélectionné.")
            return

        product_id = int(sel[0])
        product = self.controller.get_product(product_id)
        product_name = product.drug_name

        def on_confirm(added_qty):
            try:
                updated = self.controller.renew_stock(product_id, added_qty)
                messagebox.showinfo(
                    "Succès",
                    f"Produit '{updated.drug_name}' réapprovisionné.\n"
                    f"Nouvelle quantité = {updated.quantity}."
                )
                self.load_data()
            except Exception as ex:
                messagebox.showerror("Erreur", str(ex))

        RenewStockDialog(self, product_name, on_confirm)
