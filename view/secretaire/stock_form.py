# view/secretaire/stock_form.py

import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox
from datetime import datetime

class StockFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, on_save=None):
        """
        Formulaire d'enregistrement d'un produit (médicament).
        - master     : fenêtre parente
        - controller : contrôleur métier avec méthode create_product(data)
        - on_save    : callback à exécuter après un enregistrement réussi
        """
        super().__init__(master)
        self.title("Enregistrer Produit")
        self.controller = controller
        self.on_save = on_save

        # ----------------------------------------
        # Cadre principal pour les champs communs
        # ----------------------------------------
        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="x")

        # 1) Nom du produit (StringVar)
        ctk.CTkLabel(frame, text="Nom du produit :").grid(row=0, column=0, sticky="w", pady=(0,5))
        self.var_name = tk.StringVar()
        ctk.CTkEntry(frame, textvariable=self.var_name).grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0,5))

        # 2) Quantité (StringVar, conversion en int plus tard)
        ctk.CTkLabel(frame, text="Quantité :").grid(row=1, column=0, sticky="w", pady=(0,5))
        self.var_qty = tk.StringVar(value="0")
        ctk.CTkEntry(frame, textvariable=self.var_qty).grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0,5))

        # 3) Seuil critique (StringVar, conversion en int plus tard)
        ctk.CTkLabel(frame, text="Seuil critique :").grid(row=2, column=0, sticky="w", pady=(0,5))
        self.var_threshold = tk.StringVar(value="0")
        ctk.CTkEntry(frame, textvariable=self.var_threshold).grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0,5))

        # 4) Type (Naturel / Pharmaceutique)
        ctk.CTkLabel(frame, text="Type de produit :").grid(row=3, column=0, sticky="w", pady=(0,5))
        self.var_type = tk.StringVar(value="Naturel")
        type_menu = ctk.CTkComboBox(
            frame,
            variable=self.var_type,
            values=["Naturel", "Pharmaceutique"],
            width=200,
            command=lambda _: self._render_dynamic_fields()
        )
        type_menu.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(0,5))

        # 5) Cadre pour les champs dynamiques selon le type
        self.dynamic_frame = ctk.CTkFrame(self)
        self.dynamic_frame.pack(padx=20, pady=(10, 0), fill="both", expand=True)
        self._render_dynamic_fields()  # Affichage initial

        # 6) Bouton “Enregistrer”
        ctk.CTkButton(self, text="Enregistrer", command=self._save).pack(pady=15)

        # Ajuster la grille interne pour qu’elle s’étende correctement
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)

    def _render_dynamic_fields(self):
        """
        Reconstruit self.dynamic_frame selon self.var_type.
        - Naturel : aucun champ supplémentaire (tout est déjà nom/quantité/seuil).
        - Pharmaceutique : ajoute Dosage (StringVar → float) et Date d'expiration.
        """
        for w in self.dynamic_frame.winfo_children():
            w.destroy()

        if self.var_type.get() == "Naturel":
            # Optionnel : un petit label pour dire qu'il n'y a rien de plus à remplir
            ctk.CTkLabel(
                self.dynamic_frame,
                text="(Aucun champ supplémentaire pour un produit naturel)"
            ).grid(row=0, column=0, sticky="w")
        else:
            # -- Champ "Dosage (mg)" (StringVar + conversion ultérieure) --
            ctk.CTkLabel(self.dynamic_frame, text="Dosage (mg) :").grid(row=0, column=0, sticky="w", pady=(0,5))
            self.var_dosage = tk.StringVar(value="0.0")
            ctk.CTkEntry(self.dynamic_frame, textvariable=self.var_dosage).grid(
                row=0, column=1, columnspan=2, sticky="ew", pady=(0,5)
            )

            # -- Champ "Date d'expiration" --
            ctk.CTkLabel(self.dynamic_frame, text="Date d'expiration :").grid(row=1, column=0, sticky="w", pady=(0,5))
            self.date_entry = DateEntry(self.dynamic_frame, date_pattern='yyyy-mm-dd')
            self.date_entry.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0,5))

        # Ajuster les colonnes pour qu'elles prennent toute la largeur
        self.dynamic_frame.grid_columnconfigure(1, weight=1)
        self.dynamic_frame.grid_columnconfigure(2, weight=1)

    def _save(self):
        """
        Récupère les valeurs depuis les StringVar, fait la conversion en int/float,
        affiche l’alerte si qty <= seuil, puis appelle controller.create_product(data).
        """
        name = self.var_name.get().strip()

        # Conversion de la quantité
        try:
            qty = int(self.var_qty.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Erreur", "La quantité doit être un entier.")
            return

        # Conversion du seuil critique
        try:
            threshold = int(self.var_threshold.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Erreur", "Le seuil critique doit être un entier.")
            return

        med_type = self.var_type.get()

        # Vérifications de base
        if not name:
            messagebox.showerror("Erreur", "Le nom du produit est requis.")
            return
        if qty < 0:
            messagebox.showerror("Erreur", "La quantité ne peut pas être négative.")
            return
        if threshold < 0:
            messagebox.showerror("Erreur", "Le seuil critique ne peut pas être négatif.")
            return

        # Construction de base du dictionnaire
        data = {
            'drug_name':       name,
            'quantity':        qty,
            'threshold':       threshold,
            'medication_type': med_type
        }

        # Si Pharmaceutique, on convertit dosage et date d'expiration
        if med_type == "Pharmaceutique":
            # Conversion du dosage
            try:
                dosage = float(self.var_dosage.get().strip() or 0.0)
            except ValueError:
                messagebox.showerror("Erreur", "Le dosage doit être un nombre.")
                return
            if dosage <= 0:
                messagebox.showerror("Erreur", "Le dosage doit être strictement positif.")
                return

            expiry_str = self.date_entry.get()
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
            except Exception as e:
                messagebox.showerror("Erreur", f"Date d'expiration invalide :\n{e}")
                return

            data['dosage_mg'] = dosage
            data['expiry_date'] = expiry_date

        # Alerte si qty <= seuil critique
        if qty <= threshold:
            messagebox.showwarning(
                "Alerte stock critique",
                f"La quantité ({qty}) est inférieure ou égale au seuil critique ({threshold})."
            )

        # Appel au contrôleur pour enregistrer en base
        try:
            self.controller.create_product(data)
            messagebox.showinfo("Succès", "Produit enregistré dans le stock.")
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as ex:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer :\n{ex}")
