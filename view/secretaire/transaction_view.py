import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

class AddItemDialog(ctk.CTkToplevel):
    def __init__(self, master, on_confirm, pharmacy_ctrl, initial_data: dict = None, locale: str = "fr"):
        """
        - master         : fenêtre parente (parent)
        - on_confirm     : callback(item_dict) appelé quand l’utilisateur valide
        - pharmacy_ctrl  : instance de PharmacyController (ou repo) pour charger la table `pharmacy`
        - initial_data   : {'item_type','item_ref_id','unit_price','quantity','line_total','note'} (optionnel)
        - locale         : "fr" ou "en"
        """
        super().__init__(master)
        self.title({"fr": "Ajouter/Éditer une ligne", "en": "Add/Edit Line"}[locale])
        self.on_confirm    = on_confirm
        self.pharmacy_ctrl = pharmacy_ctrl
        self.locale        = locale

        # 1) Variables pour les champs
        self.var_item_type    = tk.StringVar(value="Consultation")
        self.var_med_category = tk.StringVar(value="")    # "Naturel" ou "Pharmaceutique"
        self.var_med_sel      = tk.StringVar(value="")    # label du médicament sélectionné
        self.var_ref_id       = tk.StringVar(value="")
        self.var_qty          = tk.StringVar(value="1")
        self.var_unit         = tk.StringVar(value="0.00")
        self.var_note         = tk.StringVar(value="")

        # 2) Si mode édition, préremplir
        if initial_data:
            self.var_item_type.set(initial_data.get("item_type", "Consultation"))
            self.var_ref_id.set(str(initial_data.get("item_ref_id", "")))
            self.var_qty.set(str(initial_data.get("quantity", "1")))
            self.var_unit.set(f"{initial_data.get('unit_price', 0):.2f}")
            self.var_note.set(initial_data.get("note", ""))

        self._build_ui()
        self._bind_events()
        self._update_visibility()
        self.grab_set()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # 1) Type de ligne (Consultation / Médicament / Carnet)
        ctk.CTkLabel(self, text={"fr": "Type de ligne :", "en": "Line type:"}[self.locale]) \
            .grid(row=0, column=0, sticky="w", **pad)
        self.cb_item_type = ctk.CTkComboBox(
            self,
            variable=self.var_item_type,
            values=(
                ["Consultation", "Médicament", "Carnet"]
                if self.locale == "fr"
                else ["Consultation", "Medication", "Booklet"]
            )
        )
        self.cb_item_type.grid(row=0, column=1, **pad)

        # 2) Catégorie Médicament (Naturel / Pharmaceutique)
        ctk.CTkLabel(self, text={"fr": "Catégorie Méd. :", "en": "Med Category:"}[self.locale]) \
            .grid(row=1, column=0, sticky="w", **pad)
        self.cb_med_category = ctk.CTkComboBox(
            self,
            variable=self.var_med_category,
            values=["Naturel", "Pharmaceutique"] if self.locale == "fr" else ["Natural", "Pharmaceutical"]
        )
        self.cb_med_category.grid(row=1, column=1, **pad)

        # 3) Sélection du Médicament (vide au départ)
        ctk.CTkLabel(self, text={"fr": "Médicament :", "en": "Medication:"}[self.locale]) \
            .grid(row=2, column=0, sticky="w", **pad)
        self.cb_med_sel = ctk.CTkComboBox(
            self,
            variable=self.var_med_sel,
            values=[]
        )
        self.cb_med_sel.grid(row=2, column=1, **pad)

        # 4) Réf. ID (sera rempli automatiquement si Médicament, blocage seulement pour Médicament)
        ctk.CTkLabel(self, text={"fr": "Réf. ID :", "en": "Ref. ID:"}[self.locale]) \
            .grid(row=3, column=0, sticky="w", **pad)
        self.ent_ref_id = ctk.CTkEntry(self, textvariable=self.var_ref_id)
        self.ent_ref_id.grid(row=3, column=1, **pad)

        # 5) Quantité
        ctk.CTkLabel(self, text={"fr": "Quantité :", "en": "Quantity:"}[self.locale]) \
            .grid(row=4, column=0, sticky="w", **pad)
        self.ent_qty = ctk.CTkEntry(self, textvariable=self.var_qty)
        self.ent_qty.grid(row=4, column=1, **pad)

        # 6) Prix unitaire (laissé éditable en toutes circonstances)
        ctk.CTkLabel(self, text={"fr": "Prix unitaire :", "en": "Unit price:"}[self.locale]) \
            .grid(row=5, column=0, sticky="w", **pad)
        self.ent_unit = ctk.CTkEntry(self, textvariable=self.var_unit)
        self.ent_unit.grid(row=5, column=1, **pad)

        # 7) Note (facultative)
        ctk.CTkLabel(self, text={"fr": "Note :", "en": "Note:"}[self.locale]) \
            .grid(row=6, column=0, sticky="w", **pad)
        self.ent_note = ctk.CTkEntry(self, textvariable=self.var_note)
        self.ent_note.grid(row=6, column=1, **pad)

        # 8) Boutons Valider / Annuler
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(10, 5))
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

    def _bind_events(self):
        # Quand on change le type de ligne
        self.cb_item_type.configure(command=self._on_item_type_change)
        # Quand on change la catégorie de médicament
        self.cb_med_category.configure(command=self._on_med_category_change)
        # Quand on sélectionne un médicament
        self.cb_med_sel.configure(command=self._on_med_sel_change)

    def _update_visibility(self):
        """
        Affiche/masque les champs selon la valeur de var_item_type :
        - Consultation   : on masque tout ce qui concerne Médicament / Carnet (champ Ref ID et Unit restent éditables)
        - Médicament     : on affiche caté & sélection + on bloque uniquement Ref ID (unit reste éditable)
        - Carnet         : on masque Médicament, on fixe Ref ID="CARNET", unit=500.00, puis on bloque les deux
        """
        itype = self.var_item_type.get()
        if itype in ("Médicament", "Medication"):
            # Montrer caté et sélection
            self.cb_med_category.grid()
            self.cb_med_sel.grid()
            # Bloquer uniquement l’entrée manuelle de Ref ID
            self.ent_ref_id.configure(state="disabled")
            # Laisser le prix unitaire éditable
            self.ent_unit.configure(state="normal")
        else:
            # Cacher les zones Médicament
            self.cb_med_category.grid_remove()
            self.cb_med_sel.grid_remove()
            # Réactiver Ref ID et Prix
            self.ent_ref_id.configure(state="normal")
            self.ent_unit.configure(state="normal")

            if itype in ("Carnet", "Booklet"):
                # Pour Carnet : pré-remplir Ref="CARNET", Prix=500.00
                self.var_ref_id.set("CARNET")
                self.var_unit.set("500.00")
                self.ent_ref_id.configure(state="disabled")
                self.ent_unit.configure(state="disabled")
            else:
                # Consultation : champs libres (on vide si nécessaire)
                if not self.var_ref_id.get().isdigit():
                    self.var_ref_id.set("")
                if not self.var_unit.get().replace('.', '', 1).isdigit():
                    self.var_unit.set("0.00")

    def _on_item_type_change(self, *args):
        self._update_visibility()
        # Si on passe à autre chose que Médicament, vider les valeurs liées
        if self.var_item_type.get() not in ("Médicament", "Medication"):
            self.var_med_category.set("")
            self.var_med_sel.set("")

    def _on_med_category_change(self, *args):
        """
        Chargement dynamique de la liste des médicaments selon la catégorie.
        On utilise self.pharmacy_ctrl.search_products(term=None, type_filter=cat, status_filter=None).
        """
        cat = self.var_med_category.get()
        if not cat:
            return

        try:
            meds = self.pharmacy_ctrl.search_products(
                term=None,
                type_filter=cat,
                status_filter=None
            )
        except Exception:
            meds = []

        # Construire un mapping label → objet Pharmacy
        self._med_mapping = {}
        values = []
        for m in meds:
            label = f"{m.drug_name} (ID {m.medication_id})"
            values.append(label)
            self._med_mapping[label] = m

        self.cb_med_sel.configure(values=values)
        if values:
            self.var_med_sel.set(values[0])
            self._on_med_sel_change()

    def _on_med_sel_change(self, *args):
        """
        Quand on sélectionne un médicament, on remplit seulement Ref ID = medication_id.
        On ne change PAS le prix unitaire (on laisse l’utilisateur saisir).
        """
        selection = self.var_med_sel.get()
        if not selection:
            return

        med_obj = self._med_mapping.get(selection)
        if not med_obj:
            return

        # 1) Mettre l’ID du médicament dans Ref ID
        self.var_ref_id.set(str(med_obj.medication_id))

        # 2) Ne rien toucher à prix unitaire pour permettre saisie manuelle
        #    (on pourrait placer "0.00" par défaut, mais on laisse tel quel)
        current_unit = self.var_unit.get().strip()
        # Si c’était à 0.00 avant, on peut le garder, ou simplement vider pour inciter la saisie :
        if current_unit == "" or current_unit == "0.00":
            self.var_unit.set("")  # on vide pour que l’utilisateur tape
        # Sinon on ne touche pas à var_unit

    def _on_confirm(self):
        # Validation des champs
        try:
            ref_id_raw = self.var_ref_id.get().strip()
            # Pour "CARNET", on garde le texte. Si c’est numérique, caster en int
            if ref_id_raw.isdigit():
                ref_id = int(ref_id_raw)
            else:
                ref_id = ref_id_raw

            qty = int(self.var_qty.get().strip())
            unit = float(self.var_unit.get().strip())
        except ValueError:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Veuillez saisir des nombres valides.", "en": "Please enter valid numbers."}[self.locale]
            )
            return

        if qty <= 0 or unit < 0:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Quantité > 0 et Prix ≥ 0.", "en": "Quantity > 0 and Price ≥ 0."}[self.locale]
            )
            return

        line_total = round(qty * unit, 2)
        item_dict = {
            "item_type":   self.var_item_type.get(),
            "item_ref_id": ref_id,
            "quantity":    qty,
            "unit_price":  unit,
            "line_total":  line_total,
            "note":        self.var_note.get().strip(),
        }
        self.on_confirm(item_dict)
        self.destroy()
