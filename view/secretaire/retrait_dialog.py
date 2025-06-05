import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox


class RetraitDialog(ctk.CTkToplevel):
    def __init__(self, master, on_confirm, locale: str = "fr"):
        """
        - master     : fenêtre parente dashboard secretaire 
        - on_confirm : callback(amount: float, justification: str) quand on valide
        - locale     : "fr" ou "en"
        """
        super().__init__(master)
        self.title({"fr": "Effectuer un retrait", "en": "Perform Withdrawal"}[locale])
        self.on_confirm = on_confirm
        self.locale = locale

        self.var_amount = tk.StringVar(value="0.00")
        self.var_justif = tk.StringVar(value="")

        self._build_ui()
        self.grab_set()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # 1) Montant du retrait
        ctk.CTkLabel(self, text={"fr": "Montant (CFA) :", "en": "Amount (CFA):"}[self.locale]) \
            .grid(row=0, column=0, sticky="w", **pad)
        self.ent_amount = ctk.CTkEntry(self, textvariable=self.var_amount)
        self.ent_amount.grid(row=0, column=1, **pad)

        # 2) Justification
        ctk.CTkLabel(self, text={"fr": "Justification :", "en": "Justification:"}[self.locale]) \
            .grid(row=1, column=0, sticky="w", **pad)
        self.ent_justif = ctk.CTkEntry(self, textvariable=self.var_justif, width=300)
        self.ent_justif.grid(row=1, column=1, **pad)

        # 3) Boutons Valider / Annuler
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 5))
        ctk.CTkButton(
            btn_frame,
            text={"fr": "Valider", "en": "Confirm"}[self.locale],
            command=self._on_confirm
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_frame,
            text={"fr": "Annuler", "en": "Cancel"}[self.locale],
            fg_color="#D32F2F",
            command=self.destroy
        ).pack(side="left", padx=10)

    def _on_confirm(self):
        # Validation des champs
        try:
            amt_raw = self.var_amount.get().strip().replace(",", ".")
            if not amt_raw:
                raise ValueError("Montant vide.")
            amount = float(amt_raw)
        except ValueError:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Montant invalide.", "en": "Invalid amount."}[self.locale]
            )
            return

        if amount <= 0:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Le montant doit être strictement positif.", 
                 "en": "Amount must be strictly positive."}[self.locale]
            )
            return

        justification = self.var_justif.get().strip()
        # On peut décider que justification est facultative

        # Appel du callback fourni par la vue
        self.on_confirm(amount, justification)
        self.destroy()
