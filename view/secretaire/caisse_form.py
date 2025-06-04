import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime
from typing import Optional
from view.secretaire.transaction_view import AddItemDialog

# --- Formulaire principal pour créer/éditer une transaction caisse ---
class CaisseFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, patient_ctrl=None, pharmacy_ctrl=None, on_save=None, transaction=None, locale: str = "fr"):
        """
        - controller    : instance de CaisseController, doit contenir un attribut `pharmacy_ctrl`
        - patient_ctrl  : instance de PatientController (pour find_patient_by_code)
        - on_save       : callback à exécuter après création/mise à jour réussie (p.ex. recharger la liste)
        - transaction   : objet Transaction SQLAlchemy si on édite, sinon None pour création
        - locale        : "fr" ou "en"
        """
        super().__init__(master)
        self.controller   = controller
        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.on_save      = on_save
        self.transaction  = transaction
        self.locale       = locale  # "fr" ou "en"
        self.patient_id   = None    # chargé si on renseigne un code patient
        self.items        = []      # liste locale des lignes (dict)

        self._init_vars()
        self._build_ui()

        # Si on édite : préremplir les champs
        if self.transaction:
            self._load_transaction_into_form()

        self.grab_set()

    def _init_vars(self):
        # Variables communes
        self.var_code       = ctk.StringVar(value="")
        self.var_payment    = ctk.StringVar(value=("Espèces" if self.locale == "fr" else "Cash"))
        self.var_type_trans = ctk.StringVar(value=("Consultation" if self.locale == "fr" else "Consultation"))
        self.var_note       = tk.StringVar(value="")
        # Date/heure par défaut = UTC now
        self.var_date       = ctk.StringVar(value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
        # Montant total calculé dynamiquement
        self.var_amount     = tk.StringVar(value="0.00")

    def _build_ui(self):
        pad_label = {"padx": 10, "pady": 5}
        pad_entry = {"padx": 10, "pady": 5}

        # Titre de la fenêtre
        title = {"fr": "Transaction Caisse", "en": "Cash Transaction"}[self.locale]
        if self.transaction:
            title += {"fr": " [Édition]", "en": " [Edit]"}[self.locale]
        else:
            title += {"fr": " [Nouveau]", "en": " [New]"}[self.locale]
        self.title(title)

        # -- Cadre supérieur : Patient, Date, Type, Payment Method --
        frm_top = ctk.CTkFrame(self)
        frm_top.pack(fill="x", padx=10, pady=(10, 5))

        # Patient code (optionnel)
        ctk.CTkLabel(frm_top, text={"fr": "Code patient :", "en": "Patient code:"}[self.locale]) \
            .grid(row=0, column=0, sticky="w", **pad_label)
        ctk.CTkEntry(frm_top, textvariable=self.var_code).grid(row=0, column=1, **pad_entry)
        ctk.CTkButton(
            frm_top,
            text={"fr": "Charger", "en": "Load"}[self.locale],
            command=self._load_patient
        ).grid(row=0, column=2, **pad_entry)

        # Date (readonly)
        ctk.CTkLabel(frm_top, text={"fr": "Date/Heure :", "en": "Date/Time:"}[self.locale]) \
            .grid(row=1, column=0, sticky="w", **pad_label)
        ent_date = ctk.CTkEntry(frm_top, textvariable=self.var_date, state="disabled")
        ent_date.grid(row=1, column=1, columnspan=2, sticky="ew", **pad_entry)

        # --- Type de transaction (Consultation / Vente Médicament / Vente Carnet) ---
        ctk.CTkLabel(frm_top, text={"fr": "Type transac. :", "en": "Trans. type:"}[self.locale]) \
            .grid(row=2, column=0, sticky="w", **pad_label)
        cb_type = ctk.CTkComboBox(
            frm_top,
            variable=self.var_type_trans,
            values=(
                ["Consultation", "Vente Médicament", "Vente Carnet"]
                if self.locale == "fr"
                else ["Consultation", "Sale Medication", "Sale Booklet"]
            ),
            width=200
        )
        cb_type.grid(row=2, column=1, columnspan=2, sticky="ew", **pad_entry)

        # --- Mode de paiement (ajout "Orange Money", "MTN Money") ---
        ctk.CTkLabel(frm_top, text={"fr": "Mode paiement :", "en": "Payment method:"}[self.locale]) \
            .grid(row=3, column=0, sticky="w", **pad_label)
        cb_pay = ctk.CTkComboBox(
            frm_top,
            variable=self.var_payment,
            values=(
                ["Espèces", "Carte", "Chèque", "Virement", "Orange Money", "MTN Money"]
                if self.locale == "fr"
                else ["Cash", "Card", "Check", "Transfer", "Orange Money", "MTN Money"]
            ),
            width=200
        )
        cb_pay.grid(row=3, column=1, columnspan=2, sticky="ew", **pad_entry)

        # Note (facultative)
        ctk.CTkLabel(self, text={"fr": "Note :", "en": "Note:"}[self.locale]) \
            .pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_note = ctk.CTkTextbox(self, height=60)
        self.txt_note.pack(fill="x", padx=10, pady=(0, 5))
        if self.transaction and self.transaction.note:
            self.txt_note.insert("0.0", self.transaction.note)

        # -- Cadre “Lignes” : tableau + boutons Ajouter/Supprimer --
        lbl_items = ctk.CTkLabel(self, text={"fr": "Lignes :", "en": "Lines:"}[self.locale])
        lbl_items.pack(anchor="w", padx=10, pady=(10, 0))

        frm_items = ctk.CTkFrame(self)
        frm_items.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        cols = ("Type", "Réf. ID", "Quantité", "Prix unitaire", "Total", "Note")
        self.tree_items = ttk.Treeview(frm_items, columns=cols, show="headings", height=5)
        for c in cols:
            self.tree_items.heading(c, text=c, anchor="center")
            self.tree_items.column(c, anchor="center", width=100)
        self.tree_items.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frm_items, orient="vertical", command=self.tree_items.yview)
        self.tree_items.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Frame boutons ligne
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkButton(
            btn_frame,
            text={"fr": "Ajouter ligne", "en": "Add Line"}[self.locale],
            command=self._add_line
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_frame,
            text={"fr": "Supprimer ligne", "en": "Remove Line"}[self.locale],
            command=self._remove_selected_line,
            fg_color="#D32F2F"
        ).pack(side="left")

        # -- Montant total (readonly) --
        frm_total = ctk.CTkFrame(self)
        frm_total.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(frm_total, text={"fr": "Montant total :", "en": "Total amount:"}[self.locale]) \
            .grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ent_total = ctk.CTkEntry(frm_total, textvariable=self.var_amount, state="disabled")
        ent_total.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        frm_total.grid_columnconfigure(1, weight=1)

        # -- Boutons Enregistrer / Annuler --
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(pady=(0, 15))
        ctk.CTkButton(
            action_frame,
            text={"fr": "Enregistrer", "en": "Save"}[self.locale],
            command=self._on_save
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            action_frame,
            text={"fr": "Annuler", "en": "Cancel"}[self.locale],
            fg_color="#D32F2F",
            command=self.destroy
        ).pack(side="left", padx=10)

    def _load_patient(self):
        code = self.var_code.get().strip()
        try:
            patient = self.patient_ctrl.find_patient_by_code(code)
        except Exception:
            patient = None

        if not patient:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Patient introuvable.", "en": "Patient not found."}[self.locale]
            )
            return

        pid = patient.get("patient_id") if isinstance(patient, dict) else patient.patient_id
        self.patient_id = pid
        messagebox.showinfo(
            {"fr": "OK", "en": "OK"}[self.locale],
            {"fr": f"Patient chargé (ID={pid}).", "en": f"Patient loaded (ID={pid})."}[self.locale]
        )

    def _add_line(self):
        """
        Ouvre le AddItemDialog en lui passant `pharmacy_ctrl` (depuis self.controller.pharmacy_ctrl).
        """
        def on_item_confirm(item_dict):
            # Ajoute la ligne à self.items, rafraîchit Treeview et total
            self.items.append(item_dict)
            self._refresh_items()
            self._update_total()

        AddItemDialog(
            master=self,
            on_confirm=on_item_confirm,
            pharmacy_ctrl=self.pharmacy_ctrl,
            locale=self.locale
        )

    def _remove_selected_line(self):
        sel = self.tree_items.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self.items[idx]
        self._refresh_items()
        self._update_total()

    def _refresh_items(self):
        # Vide le Treeview
        for iid in self.tree_items.get_children():
            self.tree_items.delete(iid)
        # Remplit chaque ligne et crée un tag = index
        for idx, item in enumerate(self.items):
            vals = (
                item["item_type"],
                item["item_ref_id"],
                item["quantity"],
                f"{item['unit_price']:.2f}",
                f"{item['line_total']:.2f}",
                item["note"] or ""
            )
            self.tree_items.insert("", "end", iid=str(idx), values=vals)

    def _update_total(self):
        total = sum(item["line_total"] for item in self.items)
        self.var_amount.set(f"{total:.2f}")

    def _load_transaction_into_form(self):
        """
        Préremplit les champs d'une transaction existante.
        """
        tx = self.transaction
        # 1) Code patient
        if tx.patient_id:
            patient = self.controller.get_patient(tx.patient_id)
            if patient:
                code = getattr(patient, "code_patient", "")
                self.var_code.set(code)
                self.patient_id = tx.patient_id

        # 2) Date/heure
        self.var_date.set(tx.paid_at.strftime("%Y-%m-%d %H:%M"))

        # 3) Mode paiement, type transac, note
        self.var_payment.set(tx.payment_method or "")
        self.var_type_trans.set(tx.transaction_type or "")
        if tx.note:
            self.txt_note.delete("0.0", "end")
            self.txt_note.insert("0.0", tx.note)

        # 4) Lignes existantes
        for item in tx.items:
            line = {
                "item_type":   item.item_type,
                "item_ref_id": item.item_ref_id,
                "quantity":    item.quantity,
                "unit_price":  float(item.unit_price),
                "line_total":  float(item.line_total),
                "note":        item.note or ""
            }
            self.items.append(line)

        self._refresh_items()
        self._update_total()

    def _on_save(self):
        # 1) Conversion / validations de base
        data = {}
        data["patient_id"]      = self.patient_id  # peut être None
        data["payment_method"]  = self.var_payment.get().strip()
        data["transaction_type"]= self.var_type_trans.get().strip()
        data["note"]            = self.txt_note.get("0.0", "end").strip() or None
        data["paid_at"]         = datetime.strptime(self.var_date.get(), "%Y-%m-%d %H:%M")
        data["amount"]          = float(self.var_amount.get())

        # 2) Vérifier qu'il y a au moins une ligne
        if not self.items:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Ajoutez au moins une ligne.", "en": "Please add at least one line."}[self.locale]
            )
            return

        data["items"] = self.items.copy()

        try:
            if self.transaction:
                # Édition
                self.controller.update_transaction(self.transaction.transaction_id, data)
                messagebox.showinfo(
                    {"fr": "Succès", "en": "Success"}[self.locale],
                    {"fr": "Transaction mise à jour.", "en": "Transaction updated."}[self.locale]
                )
            else:
                # Création
                self.controller.create_transaction(data)
                messagebox.showinfo(
                    {"fr": "Succès", "en": "Success"}[self.locale],
                    {"fr": "Transaction enregistrée.", "en": "Transaction saved."}[self.locale]
                )
        except Exception as e:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                str(e)
            )
            return

        if self.on_save:
            self.on_save()
        self.destroy()
