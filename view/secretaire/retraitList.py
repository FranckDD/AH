# view/secretaire/retraitList.py

import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import DateEntry
from datetime import datetime


class RetraitListView(ctk.CTkFrame):
    """
    Frame dédiée à la liste des retraits (avec filtre statut/date, totaux, annulation).
    """

    def __init__(
        self,
        parent,
        retrait_ctrl,
        on_retraits_changed=None,   # <-- callback facultatif pour prévenir la vue parente
        locale="fr",
        **kwargs
    ):
        # NE PAS passer on_retraits_changed à super().__init__
        super().__init__(parent, **kwargs)
        self.retrait_ctrl = retrait_ctrl
        self.on_retraits_changed = on_retraits_changed
        self.locale = locale

        self._build_ui()
        self.load_data()


    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # — Titre —
        lbl = ctk.CTkLabel(
            self,
            text={"fr": "Liste des Retraits", "en": "Withdrawal List"}[self.locale],
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl.pack(pady=(10, 5))

        # — Filtres : statut + dates —
        filt = ctk.CTkFrame(self)
        filt.pack(fill="x", padx=10, pady=(0, 10))
        for col in range(7):
            filt.grid_columnconfigure(col, weight=1)

        # 1) Statut
        ctk.CTkLabel(filt, text={"fr": "Statut :", "en": "Status:"}[self.locale]) \
            .grid(row=0, column=0, sticky="e", **pad)

        self.var_status = tk.StringVar(value={"fr": "Tous", "en": "All"}[self.locale])
        cb_status = ctk.CTkComboBox(
            filt,
            variable=self.var_status,
            values=(
                ["Tous", "Actif", "Annulé"] if self.locale == "fr"
                else ["All", "Active", "Cancelled"]
            )
        )
        cb_status.grid(row=0, column=1, **pad)
        # Lorsque l'utilisateur change le statut, on recharge la liste
        cb_status.configure(command=lambda _: self.load_data())

        # 2) Date "Du"
        ctk.CTkLabel(filt, text={"fr": "Du :", "en": "From:"}[self.locale]) \
            .grid(row=0, column=2, sticky="e", **pad)
        self.ret_from = DateEntry(filt, date_pattern="yyyy-mm-dd")
        self.ret_from.grid(row=0, column=3, **pad)
        self.ret_from.bind("<<DateEntrySelected>>", lambda _: self.load_data())

        # 3) Date "Au"
        ctk.CTkLabel(filt, text={"fr": "Au :", "en": "To:"}[self.locale]) \
            .grid(row=0, column=4, sticky="e", **pad)
        self.ret_to = DateEntry(filt, date_pattern="yyyy-mm-dd")
        self.ret_to.grid(row=0, column=5, **pad)
        self.ret_to.bind("<<DateEntrySelected>>", lambda _: self.load_data())

        # 4) Bouton "Afficher totaux" (actualise la liste)
        ctk.CTkButton(
            filt,
            text={"fr": "Afficher totaux", "en": "Show totals"}[self.locale],
            command=self.load_data
        ).grid(row=0, column=6, **pad)

        # — Treeview des retraits —
        cols = ("ID", "Montant", "Date", "Auteur", "Justification", "Statut")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center", width=100)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # Coloration selon statut
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        self.tree.tag_configure('active', background='white')
        self.tree.tag_configure('cancelled', background='#F8D7DA')

        # — Bouton pour annuler le retrait sélectionné —
        btn = ctk.CTkButton(
            self,
            text={"fr": "Annuler Retrait", "en": "Cancel Withdrawal"}[self.locale],
            fg_color="#D32F2F",
            command=self._cancel_selected
        )
        btn.pack(pady=(0, 10))

        # — Affichage du total des retraits pour le filtre actuel —
        lbl_tot = ctk.CTkLabel(self, text={"fr": "Total Retraits :", "en": "Total Withdrawals:"}[self.locale])
        lbl_tot.pack()

        self.var_total = tk.StringVar(value="0.00")
        ctk.CTkEntry(self, textvariable=self.var_total, state="disabled") \
            .pack(padx=10, pady=(0, 10), fill="x")


    def load_data(self):
        """
        Recharge la liste des retraits en fonction :
         - statut choisi (Actif, Annulé, Tous),
         - plage de dates (Du … Au …).
        Puis met à jour le total correspondant.
        """
        # 1) Traduire status_choice en "active"/"cancelled"/None
        status_choice = self.var_status.get()
        if self.locale == "fr":
            if status_choice == "Actif":
                status_filter = "active"
            elif status_choice == "Annulé":
                status_filter = "cancelled"
            else:
                status_filter = None  # "Tous"
        else:
            if status_choice == "Active":
                status_filter = "active"
            elif status_choice == "Cancelled":
                status_filter = "cancelled"
            else:
                status_filter = None  # "All"

        # 2) Construire date_from / date_to en datetime complet (inclusif)
        d_from = self.ret_from.get_date()
        d_to   = self.ret_to.get_date()
        date_from_dt = datetime(d_from.year,   d_from.month,   d_from.day,   0,  0,  0)
        date_to_dt   = datetime(d_to.year,     d_to.month,     d_to.day,     23, 59, 59)

        # 3) Appeler le controller pour récupérer la liste filtrée
        rets = self.retrait_ctrl.list_retraits(
            status=status_filter,
            date_from=date_from_dt,
            date_to=date_to_dt
        )

        # 4) Remplir le Treeview
        self.tree.delete(*self.tree.get_children())
        for r in rets:
            utilisateur   = getattr(r.user, 'username', str(r.handled_by))
            justification = r.cancel_justification or r.justification or ""
            vals = (
                r.retrait_id,
                f"{float(r.amount):.2f}",
                r.retrait_at.strftime("%Y-%m-%d %H:%M"),
                utilisateur,
                justification,
                r.status
            )
            tag = r.status  # 'active' ou 'cancelled'
            self.tree.insert("", "end", iid=str(r.retrait_id), values=vals, tags=(tag,))

        # 5) Mettre à jour le total
        self._refresh_totals()


    def _refresh_totals(self):
        """
        Calcule la somme des montants des retraits selon le même filtre
        (statut, date_from, date_to) et l’affiche dans self.var_total.
        """
        status_choice = self.var_status.get()
        if self.locale == "fr":
            if status_choice == "Actif":
                status_filter = "active"
            elif status_choice == "Annulé":
                status_filter = "cancelled"
            else:
                status_filter = None
        else:
            if status_choice == "Active":
                status_filter = "active"
            elif status_choice == "Cancelled":
                status_filter = "cancelled"
            else:
                status_filter = None

        d_from = self.ret_from.get_date()
        d_to   = self.ret_to.get_date()
        date_from_dt = datetime(d_from.year,   d_from.month,   d_from.day,   0,  0,  0)
        date_to_dt   = datetime(d_to.year,     d_to.month,     d_to.day,     23, 59, 59)

        total = self.retrait_ctrl.get_total_retraits(
            status=status_filter,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        self.var_total.set(f"{total:.2f}")


    def _cancel_selected(self):
        """
        Demande une justification, puis annule le retrait sélectionné en appelant le controller.
        """
        sel = self.tree.selection()
        if not sel:
            return messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Aucun retrait sélectionné.", "en": "No withdrawal selected."}[self.locale]
            )
        rid = int(sel[0])

        # Demander la justification par pop-up
        justification = simpledialog.askstring(
            {"fr": "Justification", "en": "Justification"}[self.locale],
            {"fr": "Motif d'annulation :", "en": "Reason for cancellation:"}[self.locale]
        )
        if justification is None or justification.strip() == "":
            return  # L’utilisateur a annulé ou laissé vide

        try:
            # 1) Annuler dans le controller
            self.retrait_ctrl.annuler_retrait(rid, justification)

            # 2) Recharger la liste des retraits
            self.load_data()

            # 3) Prévenir la vue parente (callback) qu’un retrait a changé
            if callable(self.on_retraits_changed):
                self.on_retraits_changed()

            messagebox.showinfo(
                {"fr": "Succès", "en": "Success"}[self.locale],
                {"fr": "Retrait annulé.", "en": "Withdrawal cancelled."}[self.locale]
            )

        except Exception as e:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                str(e)
            )
