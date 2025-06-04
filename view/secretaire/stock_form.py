import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox
from datetime import datetime

class StockFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, on_save=None, product=None):
        """
        Si product (instance SQLAlchemy) est fourni, on est en édition / edit, sinon création / create.
        on_save : callback après succès.
        """
        super().__init__(master)
        self.title(
            "Enregistrer Produit / Register Product" +
            (" [Éditer / Edit]" if product else " [Nouveau / New]")
        )
        self.controller = controller
        self.on_save = on_save
        self.product = product

        # --- Cadre principal / Main frame ---
        frame = ctk.CTkFrame(self)
        frame.pack(padx=20, pady=20, fill="x")

        # 1) Nom du produit / Product Name
        ctk.CTkLabel(frame, text="Nom du produit / Product Name :").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self.var_name = tk.StringVar(
            value=product.drug_name if product else ""
        )
        ctk.CTkEntry(frame, textvariable=self.var_name).grid(
            row=0, column=1, columnspan=2, sticky="ew", pady=(0, 5)
        )

        # 2) Quantité / Quantity
        ctk.CTkLabel(frame, text="Quantité / Quantity :").grid(
            row=1, column=0, sticky="w", pady=(0, 5)
        )
        self.var_qty = tk.StringVar(
            value=str(product.quantity) if product else "0"
        )
        ctk.CTkEntry(frame, textvariable=self.var_qty).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(0, 5)
        )

        # 3) Seuil critique / Threshold
        ctk.CTkLabel(frame, text="Seuil critique / Threshold :").grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )
        self.var_threshold = tk.StringVar(
            value=str(product.threshold) if product else "0"
        )
        ctk.CTkEntry(frame, textvariable=self.var_threshold).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=(0, 5)
        )

        # 4) Type (Naturel / Pharmaceutique) / Type (Natural / Pharmaceutical)
        ctk.CTkLabel(frame, text="Type du produit / Product Type :").grid(
            row=3, column=0, sticky="w", pady=(0, 5)
        )
        self.var_type = tk.StringVar(
            value=product.medication_type if product else "Naturel"
        )
        type_menu = ctk.CTkComboBox(
            frame,
            variable=self.var_type,
            values=["Tous / All", "Naturel / Natural", "Pharmaceutique / Pharmaceutical"],
            width=200,
            command=lambda _: self._render_dynamic_fields()
        )
        # Note : "Tous / All" ne sera utilisé que si l'on veut un filtre maître ailleurs. Ici on se limite à "Naturel" ou "Pharmaceutique".
        # Mais on laisse la valeur initiale prise dans product.medication_type (en français) ou "Naturel" par défaut.
        type_menu.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(0, 5))

        # 5) Cadre pour champs dynamiques (forme, dosage, expiration) / Dynamic sub-frame
        self.dynamic_frame = ctk.CTkFrame(self)
        self.dynamic_frame.pack(padx=20, pady=(10, 0), fill="both", expand=True)
        self._render_dynamic_fields()

        # 6) Bouton Enregistrer / Save
        ctk.CTkButton(
            self,
            text="Enregistrer / Save",
            command=self._save
        ).pack(pady=15)

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)

    def _render_dynamic_fields(self):
        """
        Reconstruit self.dynamic_frame selon self.var_type (en français).
        """
        for w in self.dynamic_frame.winfo_children():
            w.destroy()

        chosen_type = self.var_type.get()
        # On recherche la partie française avant le slash (si l’affichage est "Pharmaceutique / Pharmaceutical").
        french_part = chosen_type.split(" / ")[0].strip()

        if french_part == "Naturel":
            # Aucun champ supplémentaire
            ctk.CTkLabel(
                self.dynamic_frame,
                text="(Pas de forme à saisir pour un produit Naturel / No form needed for a Natural product)"
            ).grid(row=0, column=0, sticky="w")
            self.var_forme = tk.StringVar(value="Autre")  # Forcer "Autre" si jamais utilisé en base

        else:
            # Pharmaceutique => Forme, Dosage, Expiration
            # 1) Forme / Form
            ctk.CTkLabel(self.dynamic_frame, text="Forme / Form :").grid(
                row=0, column=0, sticky="w", pady=(0, 5)
            )
            existing_forme = self.product.forme if self.product else ""
            self.var_forme = tk.StringVar(value=existing_forme or "")
            ctk.CTkEntry(
                self.dynamic_frame,
                textvariable=self.var_forme
            ).grid(row=0, column=1, columnspan=2, sticky="ew", pady=(0, 5))

            # 2) Dosage (mg) / Dosage (mg)
            ctk.CTkLabel(self.dynamic_frame, text="Dosage (mg) :").grid(
                row=1, column=0, sticky="w", pady=(0, 5)
            )
            existing_dosage = (
                str(self.product.dosage_mg) if (self.product and self.product.dosage_mg) else "0.0"
            )
            self.var_dosage = tk.StringVar(value=existing_dosage)
            ctk.CTkEntry(
                self.dynamic_frame,
                textvariable=self.var_dosage
            ).grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 5))

            # 3) Date d’expiration / Expiry Date
            ctk.CTkLabel(self.dynamic_frame, text="Date d'expiration / Expiry Date :").grid(
                row=2, column=0, sticky="w", pady=(0, 5)
            )
            self.date_entry = DateEntry(self.dynamic_frame, date_pattern='yyyy-MM-dd')
            if self.product and self.product.expiry_date:
                self.date_entry.set_date(self.product.expiry_date.strftime("%Y-%m-%d"))
            else:
                # Valeur par défaut : aujourd'hui
                self.date_entry.set_date(datetime.utcnow().strftime("%Y-%m-%d"))
            self.date_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(0, 5))

        self.dynamic_frame.grid_columnconfigure(1, weight=1)
        self.dynamic_frame.grid_columnconfigure(2, weight=1)

    def _save(self):
        # 1) Nom du produit / Product name
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Erreur / Error", "Le nom du produit est requis / Product name is required.")
            return

        # 2) Quantité / Quantity
        try:
            qty = int(self.var_qty.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Erreur / Error", "La quantité doit être un entier / Quantity must be an integer.")
            return
        if qty < 0:
            messagebox.showerror("Erreur / Error", "La quantité ne peut pas être négative / Quantity cannot be negative.")
            return

        # 3) Seuil / Threshold
        try:
            threshold = int(self.var_threshold.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Erreur / Error", "Le seuil doit être un entier / Threshold must be an integer.")
            return
        if threshold < 0:
            messagebox.showerror("Erreur / Error", "Le seuil ne peut pas être négatif / Threshold cannot be negative.")
            return

        # 4) Type choisi (on récupère la partie française avant " / ")
        full_type = self.var_type.get()
        med_type = full_type.split(" / ")[0].strip()  # => "Naturel" ou "Pharmaceutique"

        data = {
            'drug_name':       name,
            'quantity':        qty,
            'threshold':       threshold,
            'medication_type': med_type,
        }

        if med_type == "Pharmaceutique":
            # Forme / Form
            forme = self.var_forme.get().strip()
            if not forme:
                messagebox.showerror("Erreur / Error", "La forme est requise / Form is required for pharmaceutical.")
                return
            data['forme'] = forme

            # Dosage / Dosage
            try:
                dosage = float(self.var_dosage.get().strip() or 0.0)
            except ValueError:
                messagebox.showerror("Erreur / Error", "Le dosage doit être un nombre / Dosage must be a number.")
                return
            if dosage <= 0:
                messagebox.showerror("Erreur / Error", "Le dosage doit être strictement positif / Dosage must be positive.")
                return
            data['dosage_mg'] = dosage

            # Expiration / Expiry date
            expiry_str = self.date_entry.get()
            try:
                data['expiry_date'] = datetime.strptime(expiry_str, "%Y-%m-%d")
            except Exception as e:
                messagebox.showerror("Erreur / Error", f"Date invalide / Invalid date :\n{e}")
                return

        else:
            # Naturel => Forme = "Autre" (obligatoire en base)
            data['forme'] = "Autre"
            data['dosage_mg'] = None
            data['expiry_date'] = None

        # 5) Appel create ou update
        try:
            if self.product:
                self.controller.update_product(self.product.medication_id, data)
                messagebox.showinfo("Succès / Success", "Produit mis à jour / Product updated.")
            else:
                self.controller.create_product(data)
                messagebox.showinfo("Succès / Success", "Produit créé / Product created.")
        except Exception as e:
            messagebox.showerror("Erreur SQL / SQL Error", str(e))
            return

        # 6) Callback + fermeture
        if self.on_save:
            self.on_save()
        self.destroy()
