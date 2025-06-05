import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional


class AddItemDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        on_confirm,
        pharmacy_ctrl,
        patient_ctrl,
        consultation_spirituel_ctrl,
        medical_record_ctrl,
        allowed_types: list,
        patient_id: Optional[int] = None,
        initial_data: dict = None,
        locale: str = "fr"
    ):
        """
        - master                     : fenêtre parente
        - on_confirm                 : callback(item_dict) quand l’utilisateur valide
        - pharmacy_ctrl              : instance de PharmacyController (ou obj ayant .search_products())
        - patient_ctrl               : instance de PatientController
        - consultation_spirituel_ctrl: instance de ConsultationSpirituelController
        - medical_record_ctrl        : instance de MedicalRecordController
        - allowed_types              : liste de chaînes parmi 
                                      ["Consultation Spirituel","Consultation Médical","Médicament","Carnet"]
        - patient_id                 : ID du patient courant
        - initial_data               : dict facultatif pour éditer une ligne existante
        - locale                     : "fr" ou "en"
        """
        super().__init__(master)
        self.title({"fr": "Ajouter/Éditer une ligne", "en": "Add/Edit Line"}[locale])

        self.pharmacy_ctrl = pharmacy_ctrl
        self.patient_ctrl = patient_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl
        self.on_confirm = on_confirm
        self.locale = locale
        self.allowed_types = allowed_types[:]
        self.patient_id = patient_id

        # Si une seule option, on la force
        forced = None
        if len(self.allowed_types) == 1:
            forced = self.allowed_types[0]

        # Variables
        self.var_item_type = tk.StringVar(
            value=(initial_data.get("item_type") if initial_data else forced or self.allowed_types[0])
        )
        self.var_med_category = tk.StringVar(value="")    # “Naturel” / “Pharmaceutique”
        self.var_med_sel = tk.StringVar(value="")         # label “Nom (ID X)”
        self.var_ref_id = tk.StringVar(value="")
        self.var_qty = tk.StringVar(
            value=(str(initial_data.get("quantity")) if initial_data else "1")
        )
        self.var_unit = tk.StringVar(
            value=(f"{initial_data.get('unit_price'):.2f}" if initial_data else "0.00")
        )
        self.var_note = tk.StringVar(value=(initial_data.get("note") or "" if initial_data else ""))

        self._build_ui()
        self._bind_events()

        # Si forced_type est défini, on désactive la combobox :
        if forced is not None:
            self.cb_item_type.configure(state="disabled")

        # Mise à jour de la visibilité des champs
        self._update_visibility()

        # Si on démarre en consultation, on préremplit via les méthodes des controllers
        itype0 = self.var_item_type.get()
        cs_fr = "Consultation Spirituel"; cm_fr = "Consultation Médical"
        cs_en = "Spiritual Consultation"; cm_en = "Medical Consultation"
        if itype0 == cs_fr or itype0 == cs_en:
            self._prefill_last_consultation_spirituel()
        if itype0 == cm_fr or itype0 == cm_en:
            self._prefill_last_consultation_medical()

        self.grab_set()


    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # 1) Type de ligne
        ctk.CTkLabel(self, text={"fr": "Type de ligne :", "en": "Line type:"}[self.locale]) \
            .grid(row=0, column=0, sticky="w", **pad)
        self.cb_item_type = ctk.CTkComboBox(
            self,
            variable=self.var_item_type,
            values=self.allowed_types
        )
        self.cb_item_type.grid(row=0, column=1, **pad)

        # 2) Catégorie Médicament
        ctk.CTkLabel(self, text={"fr": "Catégorie Méd. :", "en": "Med Category:"}[self.locale]) \
            .grid(row=1, column=0, sticky="w", **pad)
        self.cb_med_category = ctk.CTkComboBox(
            self,
            variable=self.var_med_category,
            values=["Naturel", "Pharmaceutique"] if self.locale == "fr" else ["Natural", "Pharmaceutical"]
        )
        self.cb_med_category.grid(row=1, column=1, **pad)

        # 3) Sélection du Médicament ou Carnet
        ctk.CTkLabel(self, text={"fr": "Produit :", "en": "Product:"}[self.locale]) \
            .grid(row=2, column=0, sticky="w", **pad)
        self.cb_med_sel = ctk.CTkComboBox(self, variable=self.var_med_sel, values=[])
        self.cb_med_sel.grid(row=2, column=1, **pad)

        # 4) Réf. ID
        ctk.CTkLabel(self, text={"fr": "Réf. ID :", "en": "Ref. ID:"}[self.locale]) \
            .grid(row=3, column=0, sticky="w", **pad)
        self.ent_ref_id = ctk.CTkEntry(self, textvariable=self.var_ref_id)
        self.ent_ref_id.grid(row=3, column=1, **pad)

        # 5) Quantité
        ctk.CTkLabel(self, text={"fr": "Quantité :", "en": "Quantity:"}[self.locale]) \
            .grid(row=4, column=0, sticky="w", **pad)
        self.ent_qty = ctk.CTkEntry(self, textvariable=self.var_qty)
        self.ent_qty.grid(row=4, column=1, **pad)

        # 6) Prix unitaire
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
        # Quand on sélectionne un produit
        self.cb_med_sel.configure(command=self._on_med_sel_change)


    def _update_visibility(self):
        """
        Affiche/masque les champs selon self.var_item_type :
        - “Consultation Spirituel”  : masque “Produit” / “Catégorie Méd.”, Ref ID rempli via controller,
                                     Prix unitaire libre.
        - “Consultation Médical”    : même principe que spirituel.
        - “Médicament”              : affiche “Catégorie Méd.” + “Produit”; Ref ID bloqué.
        - “Carnet”                  : affiche “Produit” (liste de carnets); Ref ID bloqué; Prix unitaire = 500 (bloqué).
        """
        itype = self.var_item_type.get()
        cs_fr = "Consultation Spirituel"; cm_fr = "Consultation Médical"
        cs_en = "Spiritual Consultation"; cm_en = "Medical Consultation"

        if itype in ("Médicament", "Medication"):
            # -> on montre catégorie + médocs, on bloque Ref ID
            self.cb_med_category.grid()
            self.cb_med_sel.grid()
            self.ent_ref_id.configure(state="disabled")
            self.ent_unit.configure(state="normal")

        elif itype in ("Carnet", "Booklet"):
            # -> on cache catégorie, on affiche la liste des carnets
            self.cb_med_category.grid_remove()
            self.cb_med_sel.grid()
            self.ent_ref_id.configure(state="disabled")
            self.var_unit.set("500.00")
            self.ent_unit.configure(state="disabled")
            self._load_carnets()

        elif itype == cs_fr or itype == cs_en:
            # -> Consultation spirituel : aucun champ médoc, on libère Ref ID pour préremplissage
            self.cb_med_category.grid_remove()
            self.cb_med_sel.grid_remove()
            self.ent_ref_id.configure(state="normal")
            self.ent_unit.configure(state="normal")
            self._prefill_last_consultation_spirituel()

        elif itype == cm_fr or itype == cm_en:
            # -> Consultation médical
            self.cb_med_category.grid_remove()
            self.cb_med_sel.grid_remove()
            self.ent_ref_id.configure(state="normal")
            self.ent_unit.configure(state="normal")
            self._prefill_last_consultation_medical()

        else:
            # Au cas où (ne devrait pas arriver)
            self.cb_med_category.grid_remove()
            self.cb_med_sel.grid_remove()
            self.ent_ref_id.configure(state="normal")
            self.ent_unit.configure(state="normal")


    def _prefill_last_consultation_spirituel(self):
        """
        Si patient_id est défini, appelle consultation_spirituel_ctrl.get_last_for_patient(...)
        pour récupérer la dernière consultation spirituelle.
        Sinon, met “0”.
        """
        if not self.patient_id or not self.consultation_spirituel_ctrl:
            self.var_ref_id.set("0")
            return

        try:
            cs = self.consultation_spirituel_ctrl.get_last_for_patient(self.patient_id)
            if cs:
                self.var_ref_id.set(str(cs.consultation_id))
            else:
                self.var_ref_id.set("0")
        except Exception:
            self.var_ref_id.set("0")


    def _prefill_last_consultation_medical(self):
        """
        Même principe que pour spirituel, mais via medical_record_ctrl.
        """
        if not self.patient_id or not self.medical_record_ctrl:
            self.var_ref_id.set("0")
            return

        try:
            mr = self.medical_record_ctrl.get_last_for_patient(self.patient_id)
            if mr:
                self.var_ref_id.set(str(mr.consultation_id))
            else:
                self.var_ref_id.set("0")
        except Exception:
            self.var_ref_id.set("0")


    def _on_item_type_change(self, *args):
        self._update_visibility()
        # Si on passe à autre chose que Médicament/Carnet/Consultation, on remet prix à 0.00.
        itype = self.var_item_type.get()
        cs_fr = "Consultation Spirituel"; cm_fr = "Consultation Médical"
        cs_en = "Spiritual Consultation"; cm_en = "Medical Consultation"
        if itype not in (
            "Médicament", "Medication", "Carnet", "Booklet",
            cs_fr, cm_fr, cs_en, cm_en
        ):
            self.var_med_category.set("")
            self.var_med_sel.set("")
            if not self.var_unit.get().replace('.', '', 1).isdigit():
                self.var_unit.set("0.00")


    def _on_med_category_change(self, *args):
        """
        Chargement dynamique des médicaments selon la catégorie.
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

        self._med_mapping = {}
        labels = []
        for m in meds:
            label = f"{m.drug_name} (ID {m.medication_id})"
            labels.append(label)
            self._med_mapping[label] = m

        self.cb_med_sel.configure(values=labels)
        if labels:
            self.var_med_sel.set(labels[0])
            self._on_med_sel_change()


    def _load_carnets(self):
        """
        Récupère tous les produits dont le nom contient “carnet” (FR) ou “book” (EN).
        """
        try:
            critere = "carnet" if self.locale == "fr" else "book"
            carnets = self.pharmacy_ctrl.search_products(
                term=critere,
                type_filter=None,
                status_filter=None
            )
        except Exception:
            carnets = []

        self._med_mapping = {}
        labels = []
        for prod in carnets:
            name_lower = prod.drug_name.lower()
            if critere in name_lower:
                label = f"{prod.drug_name} (ID {prod.medication_id})"
                labels.append(label)
                self._med_mapping[label] = prod

        self.cb_med_sel.configure(values=labels)


    def _on_med_sel_change(self, *args):
        """
        Quand on sélectionne un Médicament OU un Carnet, on remplit automatiquement Ref ID.
        """
        selection = self.var_med_sel.get()
        if not selection:
            return

        obj = self._med_mapping.get(selection)
        if not obj:
            return

        # 1) Remplir l’ID
        self.var_ref_id.set(str(obj.medication_id))

        # 2) Si c’est un Carnet, on fixe le prix unitaire à 500.00
        if self.var_item_type.get() in ("Carnet", "Booklet"):
            self.var_unit.set("500.00")
        else:
            # Si Médicament, on vide le prix unitaire pour forcer saisie
            if self.var_unit.get().strip() in ("", "0.00"):
                self.var_unit.set("")


    def _on_confirm(self):
        # Validation des champs
        try:
            ref_id_raw = self.var_ref_id.get().strip()
            if not ref_id_raw:
                raise ValueError("Réf. ID vide.")
            if not ref_id_raw.isdigit():
                raise ValueError("Réf. ID doit être un entier.")
            ref_id = int(ref_id_raw)

            qty = int(self.var_qty.get().strip())
            unit = float(self.var_unit.get().strip())
        except ValueError as ve:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": str(ve), "en": str(ve)}[self.locale]
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
