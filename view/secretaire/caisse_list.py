# view/secretaire/caisse_list.py

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import DateEntry
from datetime import date, datetime

from view.secretaire.caisse_form import CaisseFormView
from view.secretaire.retraitList import RetraitListView
from view.secretaire.retrait_dialog import RetraitDialog


class CaisseListView(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        controller,
        caisse_retrait_controller,
        patient_ctrl,
        pharmacy_ctrl,
        locale: str = "fr",
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.caisse_retrait_controller = caisse_retrait_controller
        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.locale = locale
        self.filtered = None

        # Variables pour afficher les totaux
        self.var_total_tx        = tk.StringVar(value="0.00")
        self.var_total_retraits  = tk.StringVar(value="0.00")
        self.var_net             = tk.StringVar(value="0.00")

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # — Transactions Title —
        lbl_title = ctk.CTkLabel(
            self,
            text={"fr": "Liste des Transactions", "en": "Transaction List"}[self.locale],
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_title.pack(pady=(10, 5))

        # — Transactions Filters —
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=10, pady=(5, 10))
        for col in range(6):
            filter_frame.grid_columnconfigure(col, weight=1)

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

        ctk.CTkLabel(filter_frame, text={"fr": "Mode paiement :", "en": "Payment method:"}[self.locale]) \
            .grid(row=0, column=2, sticky="e", **pad)
        self.var_payment = tk.StringVar(value={"fr": "Tous", "en": "All"}[self.locale])
        cb_payment = ctk.CTkComboBox(
            filter_frame,
            variable=self.var_payment,
            values=(
                ["Tous", "Espèces", "Carte", "Chèque", "Virement"] if self.locale == "fr"
                else ["All", "Cash", "Card", "Check", "Transfer"]
            )
        )
        cb_payment.grid(row=0, column=3, **pad)
        cb_payment.configure(command=lambda _: self.apply_filters())

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

        # — Transactions Treeview —
        cols = ("ID", "Patient", "Type", "Paiement", "Montant", "Date", "Statut")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for col_name in cols:
            self.tree.heading(col_name, text=col_name)
            self.tree.column(col_name, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree.tag_configure('active', background='white')
        self.tree.tag_configure('cancelled', background='#F8D7DA')

        # — Totals frame —
        totals_frame = ctk.CTkFrame(self)
        totals_frame.pack(fill="x", padx=10, pady=(0, 10))
        for col in range(4):
            totals_frame.grid_columnconfigure(col, weight=1)

        # Total des transactions
        ctk.CTkLabel(totals_frame, text={"fr": "Total Tx :", "en": "Total Tx:"}[self.locale]) \
            .grid(row=0, column=0, sticky="e", **pad)
        ctk.CTkEntry(
            totals_frame,
            textvariable=self.var_total_tx,
            state="disabled"
        ).grid(row=0, column=1, sticky="w", **pad)

        # Total des retraits
        ctk.CTkLabel(totals_frame, text={"fr": "Total Retraits :", "en": "Total withdrawals:"}[self.locale]) \
            .grid(row=0, column=2, sticky="e", **pad)
        ctk.CTkEntry(
            totals_frame,
            textvariable=self.var_total_retraits,
            state="disabled"
        ).grid(row=0, column=3, sticky="w", **pad)

        # Solde net (Tx - Retraits)
        ctk.CTkLabel(totals_frame, text={"fr": "Solde net :", "en": "Net balance:"}[self.locale]) \
            .grid(row=1, column=0, sticky="e", **pad)
        ctk.CTkEntry(
            totals_frame,
            textvariable=self.var_net,
            state="disabled"
        ).grid(row=1, column=1, sticky="w", **pad)

        # — Action buttons —
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        actions = [
            ({"fr": "Nouveau", "en": "New"}[self.locale], self._new_transaction, None),
            ({"fr": "Éditer", "en": "Edit"}[self.locale], self._edit_selected, None),
            ({"fr": "Annuler Tx", "en": "Cancel Tx"}[self.locale], self._cancel_selected, "#D32F2F"),
            ({"fr": "Supprimer Tx", "en": "Delete Tx"}[self.locale], self._delete_selected, "#D32F2F"),
            ({"fr": "Effectuer retrait", "en": "Make Withdrawal"}[self.locale], self._on_effectuer_retrait, None),
            ({"fr": "Rafraîchir", "en": "Refresh"}[self.locale], self.load_data, None),
        ]
        for txt, cmd, clr in actions:
            btn = ctk.CTkButton(action_frame, text=txt, command=cmd)
            if clr:
                btn.configure(fg_color=clr)
            btn.pack(side="left", padx=5)

        # — Embedded RetraitListView —
        self.retrait_list = RetraitListView(
        self,
        self.caisse_retrait_controller,
        on_retraits_changed=self._refresh_totals,  # ← appel du callback sur annulation
        locale=self.locale)
        self.retrait_list.pack(fill="x", pady=(20, 0))

    def _reset_filters(self):
        self.var_search.set("")
        self.var_payment.set({"fr": "Tous", "en": "All"}[self.locale])
        today = date.today().strftime("%Y-%m-%d")
        self.date_from.set_date(today)
        self.date_to.set_date(today)
        self.filtered = None
        self.load_data()

    def apply_filters(self):
        txs = self.controller.list_transactions()
        d1, d2 = self.date_from.get_date(), self.date_to.get_date()
        self.filtered = [tx for tx in txs if d1 <= tx.paid_at.date() <= d2]
        self._populate_tree()
        self._refresh_totals()

    def load_data(self):
        self.filtered = None
        self._populate_tree()
        self._refresh_totals()
        self.retrait_list.load_data()

    def _populate_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        data = self.filtered or self.controller.list_transactions()
        for tx in data:
            patient_display = ""
            if tx.patient_id:
                p = self.patient_ctrl.get_patient(tx.patient_id)
                patient_display = getattr(p, 'code_patient', '') if p else ''
            tag = tx.status
            self.tree.insert(
                "", "end", iid=str(tx.transaction_id),
                values=(
                    tx.transaction_id,
                    patient_display,
                    tx.transaction_type,
                    tx.payment_method,
                    f"{tx.amount:.2f}",
                    tx.paid_at.strftime("%Y-%m-%d %H:%M"),
                    tx.status
                ), tags=(tag,)
            )

    def _refresh_totals(self):
        """
        Calcule et met à jour :
         - total des transactions (Caisse)    → var_total_tx
         - total des retraits (CaisseRetrait) → var_total_retraits
         - net = total_tx - total_retraits    → var_net
        Le tout en tenant compte du filtre sur les dates.
        """
        # 1) Construire date_from / date_to en datetime complet
        d_from = self.date_from.get_date()
        d_to   = self.date_to.get_date()
        dt_start = datetime(d_from.year,  d_from.month,  d_from.day,  0,  0,  0)
        dt_end   = datetime(d_to.year,    d_to.month,    d_to.day,    23, 59, 59)

        # 2) Somme des transactions (Decimal)
        total_tx = self.controller.get_total_transactions(
            date_from=dt_start,
            date_to=dt_end
        )

        # 3) Somme des retraits (float)
        total_rt = self.caisse_retrait_controller.get_total_retraits(
            status=None,  # None = tous statuts
            date_from=dt_start,
            date_to=dt_end
        )

        # 4) Calcul du net en convertissant en float
        net_amount = float(total_tx) - float(total_rt)

        # 5) Mise à jour des StringVar
        self.var_total_tx.set(f"{float(total_tx):.2f}")
        self.var_total_retraits.set(f"{total_rt:.2f}")
        self.var_net.set(f"{net_amount:.2f}")

    def _new_transaction(self):
        def on_refresh():
            self.load_data()

        CaisseFormView(
            master=self,
            controller=self.controller,
            patient_ctrl=self.patient_ctrl,
            pharmacy_ctrl=self.pharmacy_ctrl,
            on_save=on_refresh,
            locale=self.locale
        )

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

        CaisseFormView(
            master=self,
            controller=self.controller,
            patient_ctrl=self.patient_ctrl,
            pharmacy_ctrl=self.pharmacy_ctrl,
            on_save=on_refresh,
            transaction=tx,
            locale=self.locale
        )

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

    def _on_effectuer_retrait(self):
        """
        Ouvre le RetraitDialog. Quand l’utilisateur confirme, on crée le retrait
        et on met uniquement à jour les totaux (sans recharger tout le tableau).
        """
        def on_retrait_confirm(amount, justification):
            try:
                self.caisse_retrait_controller.effectuer_retrait(amount, justification)
                # Mise à jour uniquement des totaux, pas besoin de recharger la liste entière
                self._refresh_totals()
                messagebox.showinfo(
                    {"fr": "Succès", "en": "Success"}[self.locale],
                    {"fr": f"Retrait enregistré ({amount:.2f}).", 
                     "en": f"Withdrawal recorded ({amount:.2f})."}[self.locale]
                )
            except Exception as e:
                messagebox.showerror(
                    {"fr": "Erreur", "en": "Error"}[self.locale],
                    str(e)
                )

        RetraitDialog(master=self, on_confirm=on_retrait_confirm, locale=self.locale)
