import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, ttk

class CompletedResultsView(ctk.CTkFrame):
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        ctk.CTkLabel(self, text="Résultats interprétés", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=10)
        self.tree = ttk.Treeview(self, columns=("code","patient","exam","status"), show="headings")
        for c,h in [("code","Code"),("patient","Patient"),("exam","Examen"),("status","Interprétation")]:
            self.tree.heading(c, text=h)
            self.tree.column(c, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.load_data()

    def load_data(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        raws = self.controller.list_results_by_status('completed')
        for r in raws:
            self.tree.insert('',"end", values=(r['code_lab_patient'], r['patient_name'], r['examen_name'], r['status']))
