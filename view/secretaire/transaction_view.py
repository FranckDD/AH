# add_item_dialog.py
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional

# Liste des 30 examens médicaux
EXAMENS_LIST = [
    "Numération formule sanguine (NFS)",
    "Ionogramme sanguin",
    "Bilan rénal",
    "Bilan hépatique",
    "Glycémie à jeun",
    "Hémoglobine glyquée (HbA1c)",
    "Cholestérol total",
    "HDL cholestérol",
    "LDL cholestérol",
    "Triglycérides",
    "TSH (thyroïde)",
    "T4 libre",
    "T3 libre",
    "CRP (C-réactive protéine)",
    "Vitesse de sédimentation (VS)",
    "Protéines totales",
    "Phosphatases alcalines",
    "Gamma-GT",
    "Bilirubine totale",
    "Bilirubine conjuguée",
    "Amylase",
    "Lipase",
    "Ferritine",
    "Fer sérique",
    "Vitamine D (25-OH)",
    "Vitamine B12",
    "Acide folique",
    "Sérologie VIH",
    "Sérologie Hépatite B",
    "Sérologie Hépatite C"
]

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
        super().__init__(master)
        self.locale = locale
        self.on_confirm = on_confirm
        self.allowed_types = allowed_types[:]
        self.patient_id = patient_id
        self.pharmacy_ctrl = pharmacy_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl

        # Forcer type unique
        forced = self.allowed_types[0] if len(self.allowed_types) == 1 else None

        # Variables
        self.var_item_type = tk.StringVar(
            value=(initial_data.get("item_type") if initial_data else forced or self.allowed_types[0])
        )
        self.var_med_category = tk.StringVar(value="")
        self.var_med_sel = tk.StringVar(value="")
        # Réf. ID = patient_id si présent, sinon "0"
        self.var_ref_id = tk.StringVar(value=str(patient_id) if patient_id else "0")
        self.var_qty = tk.StringVar(value=(str(initial_data.get("quantity")) if initial_data else "1"))
        self.var_unit = tk.StringVar(value=(f"{initial_data.get('unit_price'):.2f}" if initial_data else "0.00"))
        self.var_note = tk.StringVar(value=(initial_data.get("note") or "" if initial_data else ""))

        self._build_ui()
        self._bind_events()
        if forced:
            self.cb_item_type.configure(state="disabled")
        self._update_visibility()
        self.grab_set()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # 1) Type de ligne
        ctk.CTkLabel(self, text={"fr":"Type de ligne :","en":"Line type:"}[self.locale])\
            .grid(row=0, column=0, sticky="w", **pad)
        self.cb_item_type = ctk.CTkComboBox(
            self,
            variable=self.var_item_type,
            values=self.allowed_types,
            command=self._on_item_type_change
        )
        self.cb_item_type.grid(row=0, column=1, **pad)

        # 2) Catégorie Médicament
        ctk.CTkLabel(self, text={"fr":"Catégorie Méd. :","en":"Med Category:"}[self.locale])\
            .grid(row=1, column=0, sticky="w", **pad)
        self.cb_med_category = ctk.CTkComboBox(
            self,
            variable=self.var_med_category,
            values=("Naturel","Pharmaceutique") if self.locale=="fr" else ("Natural","Pharmaceutical"),
            command=self._on_med_category_change
        )
        self.cb_med_category.grid(row=1, column=1, **pad)

        # 3) Produit
        ctk.CTkLabel(self, text={"fr":"Produit :","en":"Product:"}[self.locale])\
            .grid(row=2, column=0, sticky="w", **pad)
        self.cb_med_sel = ctk.CTkComboBox(
            self,
            variable=self.var_med_sel,
            values=[],
            command=self._on_med_sel_change
        )
        self.cb_med_sel.grid(row=2, column=1, **pad)

        # 4) Réf. ID
        ctk.CTkLabel(self, text={"fr":"Réf. ID :","en":"Ref. ID:"}[self.locale])\
            .grid(row=3, column=0, sticky="w", **pad)
        self.ent_ref_id = ctk.CTkEntry(self, textvariable=self.var_ref_id)
        self.ent_ref_id.grid(row=3, column=1, **pad)

        # 5) Quantité
        ctk.CTkLabel(self, text={"fr":"Quantité :","en":"Quantity:"}[self.locale])\
            .grid(row=4, column=0, sticky="w", **pad)
        self.ent_qty = ctk.CTkEntry(self, textvariable=self.var_qty)
        self.ent_qty.grid(row=4, column=1, **pad)

        # 6) Prix unitaire
        ctk.CTkLabel(self, text={"fr":"Prix unitaire :","en":"Unit price:"}[self.locale])\
            .grid(row=5, column=0, sticky="w", **pad)
        self.ent_unit = ctk.CTkEntry(self, textvariable=self.var_unit)
        self.ent_unit.grid(row=5, column=1, **pad)

        # 7) Note
        ctk.CTkLabel(self, text={"fr":"Note :","en":"Note:"}[self.locale])\
            .grid(row=6, column=0, sticky="w", **pad)
        self.ent_note = ctk.CTkEntry(self, textvariable=self.var_note)
        self.ent_note.grid(row=6, column=1, **pad)

        # 8) Examens (checkbox scrollable)
        self.lbl_exam = ctk.CTkLabel(self, text={"fr":"Examens :","en":"Exams:"}[self.locale])
        self.frm_exam = ctk.CTkFrame(self)
        self.canvas = tk.Canvas(self.frm_exam, height=150)
        self.scroll = ttk.Scrollbar(self.frm_exam, orient="vertical", command=self.canvas.yview)
        self.inner = ctk.CTkFrame(self.canvas)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.grid(row=7, column=1, sticky="nsew", padx=pad['padx'], pady=pad['pady'])
        self.scroll.grid(row=7, column=2, sticky="ns", pady=pad['pady'])

        self.exam_vars = {}
        for idx, ex in enumerate(EXAMENS_LIST):
            var_chk = tk.BooleanVar(value=False)
            var_price = tk.StringVar(value="0.00")

            cb = ctk.CTkCheckBox(self.inner, text=ex, variable=var_chk)
            cb.grid(row=idx, column=0, sticky="w", padx=5, pady=2)

            entry = ctk.CTkEntry(self.inner, textvariable=var_price, width=80)
            entry.grid(row=idx, column=1, padx=5, pady=2)

            self.exam_vars[ex] = (var_chk, var_price)


        # 9) Boutons Valider / Annuler
        btn = ctk.CTkFrame(self)
        btn.grid(row=8, column=0, columnspan=3, pady=(10,5))
        ctk.CTkButton(btn, text={"fr":"Valider","en":"Confirm"}[self.locale], command=self._on_confirm)\
            .pack(side="left", padx=10)
        ctk.CTkButton(btn, text={"fr":"Annuler","en":"Cancel"}[self.locale], fg_color="#D32F2F", command=self.destroy)\
            .pack(side="left", padx=10)

    def _bind_events(self):
        self.cb_item_type.configure(command=self._on_item_type_change)
        self.cb_med_category.configure(command=self._on_med_category_change)
        self.cb_med_sel.configure(command=self._on_med_sel_change)

    def _update_visibility(self):
        pad = {"padx":10,"pady":5}
        itype = self.var_item_type.get()

        # 1) forcer ref_id selon patient_id
        if self.patient_id:
            self.var_ref_id.set(str(self.patient_id))
        else:
            self.var_ref_id.set("0")

        # masquer tous les widgets spécifiques
        for w in (self.cb_med_category, self.cb_med_sel, self.lbl_exam, self.frm_exam):
            try: w.grid_remove()
            except: pass

        # afficher/ref selon type
        if itype in ("Médicament","Medication"):
            self.cb_med_category.grid(row=1, column=1, **pad)
            self.cb_med_sel.grid(row=2, column=1, **pad)
            self.ent_ref_id.configure(state="disabled")
        elif itype in ("Carnet","Booklet"):
            self.cb_med_sel.grid(row=2, column=1, **pad)
            self._load_carnets()
            self.var_unit.set("500.00")
            self.ent_ref_id.configure(state="disabled")
        elif itype in ("Consultation Spirituel","Spiritual Consultation"):
            self.ent_ref_id.configure(state="normal")
            self._prefill_last_consultation_spirituel()
        elif itype in ("Consultation Médical","Medical Consultation"):
            self.ent_ref_id.configure(state="normal")
            self._prefill_last_consultation_medical()
        elif itype in ("Examens","Exams"):
            # afficher examens + laisser ref & price éditables
            self.lbl_exam.grid(row=7, column=0, sticky="nw", **pad)
            self.frm_exam.grid(row=7, column=1, columnspan=2, sticky="nsew", **pad)
            self.ent_ref_id.configure(state="normal")
            self.ent_unit.configure(state="normal")

    def _load_carnets(self):
        terme = "carnet" if self.locale=="fr" else "book"
        try:
            produits = self.pharmacy_ctrl.search_products(term=terme, type_filter=None, status_filter=None)
        except:
            produits = []
        self._med_mapping = {}
        labels = []
        for p in produits:
            if terme in p.drug_name.lower():
                label = f"{p.drug_name} (ID {p.medication_id})"
                labels.append(label)
                self._med_mapping[label] = p
        self.cb_med_sel.configure(values=labels)

    def _on_item_type_change(self, *args):
        self._update_visibility()

    def _on_med_category_change(self, *args):
        cat = self.var_med_category.get()
        try:
            meds = self.pharmacy_ctrl.search_products(term=None, type_filter=cat, status_filter=None)
        except:
            meds = []
        self._med_mapping = {f"{m.drug_name} (ID {m.medication_id})": m for m in meds}
        labels = list(self._med_mapping.keys())
        self.cb_med_sel.configure(values=labels)
        if labels:
            self.var_med_sel.set(labels[0])
            self._on_med_sel_change()

    def _on_med_sel_change(self, *args):
        sel = self.var_med_sel.get()
        if sel in getattr(self, '_med_mapping', {}):
            obj = self._med_mapping[sel]
            self.var_ref_id.set(str(obj.medication_id))

    def _prefill_last_consultation_spirituel(self):
        if not self.patient_id or not self.consultation_spirituel_ctrl:
            return
        try:
            cs = self.consultation_spirituel_ctrl.get_last_for_patient(self.patient_id)
            self.var_ref_id.set(str(cs.consultation_id) if cs else "0")
        except:
            self.var_ref_id.set("0")

    def _prefill_last_consultation_medical(self):
        if not self.patient_id or not self.medical_record_ctrl:
            return
        try:
            mr = self.medical_record_ctrl.get_last_for_patient(self.patient_id)
            self.var_ref_id.set(str(mr.consultation_id) if mr else "0")
        except:
            self.var_ref_id.set("0")

    def _on_confirm(self):
        itype = self.var_item_type.get()

        # Examens avec prix individuel
        if itype in ("Examens", "Exams"):
            # Récupérer la Réf. ID
            try:
                ref = int(self.var_ref_id.get().strip())
            except ValueError:
                messagebox.showerror(
                    {"fr":"Erreur","en":"Error"}[self.locale],
                    {"fr":"Réf. ID invalide.","en":"Invalid Ref. ID."}[self.locale]
                )
                return

            any_selected = False
            for ex, (var_chk, var_price) in self.exam_vars.items():
                if not var_chk.get():
                    continue
                any_selected = True
                # Lecture et validation du prix pour cet examen
                try:
                    price = float(var_price.get().strip())
                except ValueError:
                    messagebox.showerror(
                        {"fr":"Erreur","en":"Error"}[self.locale],
                        {"fr":f"Prix invalide pour « {ex} ».","en":f"Invalid price for “{ex}”."}[self.locale]
                    )
                    return

                # Créer la ligne pour chaque examen sélectionné
                self.on_confirm({
                    "item_type":   itype,
                    "item_ref_id": ref,
                    "quantity":    1,
                    "unit_price":  price,
                    "line_total":  round(price, 2),
                    "note":        ex
                })

            if not any_selected:
                messagebox.showerror(
                    {"fr":"Erreur","en":"Error"}[self.locale],
                    {"fr":"Sélectionnez au moins un examen.","en":"Select at least one exam."}[self.locale]
                )
                return

            self.destroy()
            return

        # *** Sinon : logique existante pour Médicament, Carnet, Consultation, Hospitalisation ***
        try:
            ref = int(self.var_ref_id.get().strip())
            qty = int(self.var_qty.get().strip())
            unit = float(self.var_unit.get().strip())
        except ValueError as ve:
            messagebox.showerror(
                {"fr":"Erreur","en":"Error"}[self.locale],
                str(ve)
            )
            return

        if qty <= 0 or unit < 0:
            messagebox.showerror(
                {"fr":"Erreur","en":"Error"}[self.locale],
                {"fr":"Quantité > 0 et Prix ≥ 0.","en":"Quantity > 0 and Price ≥ 0."}[self.locale]
            )
            return

        total = round(qty * unit, 2)
        self.on_confirm({
            "item_type":   itype,
            "item_ref_id": ref,
            "quantity":    qty,
            "unit_price":  unit,
            "line_total":  total,
            "note":        self.var_note.get().strip()
        })
        self.destroy()
