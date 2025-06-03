import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime


class RenewStockDialog(ctk.CTkToplevel):
    def __init__(self, parent, product_name, on_confirm):
        """
        Dialog moderne pour réapprovisionner un produit.
        - parent : fenêtre parente
        - product_name : nom du produit à réapprovisionner
        - on_confirm : callback (added_qty) à appeler si l'utilisateur valide
        """
        super().__init__(parent)
        self.title("Réapprovisionnement")
        self.geometry("400x200")
        self.resizable(False, False)
        self.configure(bg="transparent")
        self.on_confirm = on_confirm

        # Cadre principal
        container = ctk.CTkFrame(self, corner_radius=10)
        container.pack(expand=True, fill="both", padx=20, pady=20)

        # Titre du dialog
        ctk.CTkLabel(
            container,
            text=f"Réapprovisionner : {product_name}",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(10, 10))

        # Champ entrée quantité
        self.var_add = tk.StringVar(value="0")
        entry_frame = ctk.CTkFrame(container, corner_radius=5)
        entry_frame.pack(fill="x", padx=10, pady=(0, 15))
        ctk.CTkLabel(entry_frame, text="Quantité à ajouter :", anchor="w").pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkEntry(entry_frame, textvariable=self.var_add, placeholder_text="Entrez un entier").pack(fill="x", padx=10, pady=(0, 5))
        entry_frame.grid_columnconfigure(0, weight=1)

        # Boutons confirmer / annuler
        btn_frame = ctk.CTkFrame(container, corner_radius=5)
        btn_frame.pack(pady=(0, 10))
        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="Valider",
            width=100,
            command=self._on_confirm
        )
        confirm_btn.pack(side="left", padx=(0, 10))
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Annuler",
            width=100,
            fg_color="#D32F2F",
            hover_color="#E57373",
            command=self.destroy
        )
        cancel_btn.pack(side="left")

        self.bind("<Return>", lambda e: self._on_confirm())
        self.grab_set()

    def _on_confirm(self):
        try:
            added = int(self.var_add.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Erreur", "La quantité doit être un entier valide.", parent=self)
            return
        if added <= 0:
            messagebox.showerror("Erreur", "La quantité doit être strictement positive.", parent=self)
            return

        self.on_confirm(added)
        self.destroy()