# view/secretaire/stock_list.py
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk

class StockListView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller

        # Title
        ctk.CTkLabel(self, text="Liste des Produits", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        # Treeview
        cols = ("ID", "Nom", "Type", "Quantité", "Patient", "Prescripteur")
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
        products = self.controller.list_all() if hasattr(self.controller, 'list_all') else self.controller.list_products()
        for p in products:
            patient_code = p.patient.code_patient if p.patient else ""
            prescriber = p.prescriber.username if hasattr(p, 'prescriber') and p.prescriber else ""
            self.tree.insert("", "end", iid=p.medication_id, values=(
                p.medication_id,
                p.drug_name,
                p.medication_type,
                p.quantity,
                patient_code,
                prescriber
            ))