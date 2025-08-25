import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, ttk

class PendingResultsView(ctk.CTkFrame):
    def __init__(self, parent, controller, on_complete=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller  = controller
        self.on_complete = on_complete
        self._build_ui()
        self.load_data()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Résultats en attente",
                     font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=10)

        self.tree = ttk.Treeview(
            self, columns=("code","patient","exam","date"), show="headings"
        )
        for col, txt in [("code","Code"),("patient","Patient"),
                         ("exam","Examen"),("date","Date")]:
            self.tree.heading(col, text=txt)
            self.tree.column(col, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=(0,10))

        ctk.CTkButton(self, text="Marquer comme complété",
                      command=self._mark_completed
        ).pack(pady=5)

    def load_data(self):
        for iid in self.tree.get_children(): 
            self.tree.delete(iid)
        raws = self.controller.list_results_by_status("pending")
        for r in raws:
            self.tree.insert(
                "", "end", iid=r["result_id"],
                values=(
                    r["code_lab_patient"],
                    r["patient_name"],
                    r["examen_name"],
                    r["test_date"]
                )
            )

    def _mark_completed(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sélection","Aucun résultat sélectionné")
            return
        rid = int(sel[0])
        # récupère âge et sexe depuis le controller
        age  = self.controller.get_patient_age(rid)
        sexe = self.controller.get_patient_sex(rid)
        self.controller.complete_result(rid, age, sexe)
        messagebox.showinfo("Terminé", "Le résultat est maintenant complété")
        self.load_data()
        if callable(self.on_complete):
            self.on_complete()
