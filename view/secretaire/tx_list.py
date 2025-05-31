# view/secretaire/tx_list.py
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk

class TxListView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller

        # Title
        ctk.CTkLabel(self, text="Liste des Transactions", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        # Treeview
        cols = ("ID", "Patient", "Montant", "Date", "Handled By")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Load data
        self.load_data()

    def load_data(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        transactions = self.controller.list_transactions()
        for tx in transactions:
            patient_code = tx.patient.code_patient if tx.patient else ""
            handler = tx.handler.username if hasattr(tx, 'handler') and tx.handler else ""
            self.tree.insert("", "end", iid=tx.transaction_id, values=(
                tx.transaction_id,
                patient_code,
                f"{tx.amount:.2f}",
                tx.date.strftime("%Y-%m-%d"),
                handler
            ))
