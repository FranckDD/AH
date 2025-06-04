# view/secretaire/caisse_list.py

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, date
from view.secretaire.caisse_form import CaisseFormView

class CaisseListView(ctk.CTkFrame):
    def __init__(self, parent, controller, locale: str = "fr", **kwargs):
        """
        - controller : instance de CaisseController
        - locale     : "fr" ou "en" (pour les étiquettes)
        """
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.locale     = locale
        self.filtered   = None

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # --- Titre ---
        lbl_title = ctk.CTkLabel(
            self,
            text={"fr": "Liste des Transactions", "en": "Transaction List"}[self.locale],
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_title.pack(pady=(10,5))

        # --- Cadre des filtres ---
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=10, pady=(5,10))
        for col in range(6):
            filter_frame.grid_columnconfigure(col, weight=1)

        # Recherche (par type ou created_by_name)
        ctk.CTkLabel(filter_frame, text={"fr": "Rechercher :", "en": "Search:"}[self.locale]) \
            .grid(row=0, column=0, sticky="e", **pad)
        self.var_search = tk.StringVar()
        entry_search = ctk.CTkEntry(
            filter_frame,
            textvariable=self.var_search,
            placeholder_text={"fr": "Type ou utilisateur…", "en": "Type or user…"}[self.locale]
        )
        entry_search.grid(row=0, column=1, **pad)
        entry_search.bind("<Return>", lambda e: self.apply_filters())

        # Mode de paiement
        ctk.CTkLabel(filter_frame, text={"fr": "Mode paiement :", "en": "Payment method:"}[self.locale]) \
            .grid(row=0, column=2, sticky="e", **pad)
        self.var_payment = tk.StringVar(value={"fr": "Tous", "en": "All"}[self.locale])
        cb_payment = ctk.CTkComboBox(
            filter_frame,
            variable=self.var_payment,
            values=(["Tous", "Espèces", "Carte", "Chèque", "Virement"]
                    if self.locale == "fr" else
                    ["All", "Cash", "Card", "Check", "Transfer"])
        )
        cb_payment.grid(row=0, column=3, **pad)
        cb_payment.configure(command=lambda _: self.apply_filters())

        # Plage de dates
        ctk.CTkLabel(filter_frame, text={"fr": "Du :", "en": "From:"}[self.locale]) \
            .grid(row=1, column=0, sticky="e", **pad)
        self.date_from = DateEntry(filter_frame, date_pattern="yyyy-mm-dd")
        self.date_from.grid(row=1, column=1, **pad)

        ctk.CTkLabel(filter_frame, text={"fr": "Au :", "en": "To:"}[self.locale]) \
            .grid(row=1, column=2, sticky="e", **pad)
        self.date_to = DateEntry(filter_frame, date_pattern="yyyy-mm-dd")
        self.date_to.grid(row=1, column=3, **pad)

        ctk.CTkButton(
            filter_frame,
            text={"fr": "Appliquer filtres", "en": "Apply filters"}[self.locale],
            command=self.apply_filters
        ).grid(row=1, column=4, **pad)

        ctk.CTkButton(
            filter_frame,
            text={"fr": "Réinitialiser", "en": "Reset"}[self.locale],
            command=self._reset_filters
        ).grid(row=1, column=5, **pad)

        # --- Treeview des transactions ---
        cols = ("ID", "Patient", "Type", "Paiement", "Montant", "Date", "Statut")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree.heading(c, text=c, anchor="center")
            self.tree.column(c, anchor="center", width=100)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Styles de coloration selon le statut
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        # 'active' = blanc, 'cancelled' = rouge pâle
        self.tree.tag_configure('active', background='white')
        self.tree.tag_configure('cancelled', background='#F8D7DA')

        # --- Cadre des boutons d’actions ---
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=(0,10))

        ctk.CTkButton(
            action_frame,
            text={"fr": "Nouveau", "en": "New"}[self.locale],
            command=self._new_transaction
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            action_frame,
            text={"fr": "Éditer", "en": "Edit"}[self.locale],
            command=self._edit_selected
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            action_frame,
            text={"fr": "Annuler Tx", "en": "Cancel Tx"}[self.locale],
            fg_color="#D32F2F",
            command=self._cancel_selected
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            action_frame,
            text={"fr": "Supprimer Tx", "en": "Delete Tx"}[self.locale],
            fg_color="#D32F2F",
            command=self._delete_selected
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            action_frame,
            text={"fr": "Rafraîchir", "en": "Refresh"}[self.locale],
            command=self.load_data
        ).pack(side="left", padx=5)

    def _reset_filters(self):
        self.var_search.set("")
        self.var_payment.set({"fr": "Tous", "en": "All"}[self.locale])
        today = date.today().strftime("%Y-%m-%d")
        self.date_from.set_date(today)
        self.date_to.set_date(today)
        self.filtered = None
        self.load_data()

    def apply_filters(self):
        """
        Applique recherche + filtres sur date et mode paiement.
        """
        all_tx = self.controller.list_transactions()
        term = self.var_search.get().strip().lower()
        pay = self.var_payment.get()
        if pay and pay in (["Tous"] if self.locale=="fr" else ["All"]):
            pay = None

        # Conversion dates
        d_from = self.date_from.get_date()
        d_to   = self.date_to.get_date()

        filtered = all_tx

        # Filtre recherche sur transaction_type ou created_by_name
        if term:
            filt = []
            for tx in filtered:
                ty = tx.transaction_type.lower() if tx.transaction_type else ""
                cb = tx.created_by_name.lower() if tx.created_by_name else ""
                if term in ty or term in cb:
                    filt.append(tx)
            filtered = filt

        # Filtre mode paiement
        if pay:
            # Adapter les labels FR/EN en valeur interne
            filtered = [tx for tx in filtered if tx.payment_method == pay]

        # Filtre plage de dates (inclus)
        def in_date_range(tx_date):
            d = tx_date.date()
            return (d_from <= d <= d_to)

        filtered = [tx for tx in filtered if in_date_range(tx.paid_at)]

        self.filtered = filtered
        self._populate_tree()

    def load_data(self):
        """
        Charge toutes les transactions (sans filtre).
        """
        self.filtered = None
        self._populate_tree()

    def _populate_tree(self):
        # Vide le Treeview
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        data = self.filtered if self.filtered is not None else self.controller.list_transactions()
        for tx in data:
            # Affichage du patient (code_patient ou vide)
            if tx.patient_id:
                # Supposons que controller.get_patient(id) retourne un objet ou None
                patient = self.controller.get_patient(tx.patient_id)
                code = getattr(patient, "code_patient", "") if patient else ""
                patient_display = code
            else:
                patient_display = ""

            vals = (
                tx.transaction_id,
                patient_display,
                tx.transaction_type,
                tx.payment_method,
                f"{tx.amount:.2f}",
                tx.paid_at.strftime("%Y-%m-%d %H:%M"),
                tx.status
            )
            tag = tx.status  # 'active' ou 'cancelled'
            self.tree.insert("", "end", iid=str(tx.transaction_id), values=vals, tags=(tag,))

    def _new_transaction(self):
        def on_refresh():
            self.load_data()
        CaisseFormView(self, controller=self.controller, on_save=on_refresh, locale=self.locale)

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Aucune transaction sélectionnée.", "en": "No transaction selected."}[self.locale]
            )
            return
        tx_id = int(sel[0])
        tx = self.controller.get_transaction(tx_id)
        if tx.status == 'cancelled':
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Impossible d’éditer une transaction annulée.", "en": "Cannot edit a cancelled transaction."}[self.locale]
            )
            return

        def on_refresh():
            self.load_data()
        CaisseFormView(self, controller=self.controller, on_save=on_refresh, transaction=tx, locale=self.locale)

    def _cancel_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Aucune transaction sélectionnée.", "en": "No transaction selected."}[self.locale]
            )
            return
        tx_id = int(sel[0])
        try:
            self.controller.cancel_transaction(tx_id)
            messagebox.showinfo(
                {"fr": "Succès", "en": "Success"}[self.locale],
                {"fr": "Transaction annulée.", "en": "Transaction cancelled."}[self.locale]
            )
            self.load_data()
        except Exception as e:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                str(e)
            )

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Aucune transaction sélectionnée.", "en": "No transaction selected."}[self.locale]
            )
            return
        tx_id = int(sel[0])
        if messagebox.askyesno(
            {"fr": "Attention", "en": "Warning"}[self.locale],
            {"fr": "Supprimer définitivement cette transaction ?", "en": "Delete this transaction permanently?"}[self.locale]
        ):
            try:
                self.controller.delete_transaction(tx_id)
                messagebox.showinfo(
                    {"fr": "Succès", "en": "Success"}[self.locale],
                    {"fr": "Transaction supprimée.", "en": "Transaction deleted."}[self.locale]
                )
                self.load_data()
            except Exception as e:
                messagebox.showerror(
                    {"fr": "Erreur", "en": "Error"}[self.locale],
                    str(e)
                )
