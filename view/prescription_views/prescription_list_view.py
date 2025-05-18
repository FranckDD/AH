import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog
from tkcalendar import DateEntry
from view.prescription_views.prescription_form import PrescriptionFormView

class PrescriptionListView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.ctrl = controller
        self.page, self.per_page = 1, 20
        self.selected = None

        # filtres
        frm = ctk.CTkFrame(self); frm.pack(fill='x', pady=5)
        ctk.CTkLabel(frm,text="Date from").grid(row=0,column=0)
        self.from_d = DateEntry(frm,date_pattern='yyyy-mm-dd'); self.from_d.grid(row=0,column=1)
        ctk.CTkLabel(frm,text="to").grid(row=0,column=2)
        self.to_d   = DateEntry(frm,date_pattern='yyyy-mm-dd'); self.to_d.grid(row=0,column=3)
        ctk.CTkButton(frm,text="Filtrer",command=self.refresh).grid(row=0,column=4,padx=10)

        # table
        cols = ("ID","Patient","Médoc","Dosage","Freq","Début","Fin")
        self.tree = ttk.Treeview(self,columns=cols,show='headings')
        for c in cols:
            self.tree.heading(c,text=c); self.tree.column(c,width=100)
        self.tree.pack(fill='both',expand=True)
        self.tree.bind("<<TreeviewSelect>>",self._on_select)

        # actions
        act = ctk.CTkFrame(self); act.pack(fill='x',pady=5)
        self.btn_edit  = ctk.CTkButton(act,text="Aff/Edit",state='disabled',command=self._edit); self.btn_edit.pack(side='left',padx=5)
        self.btn_del   = ctk.CTkButton(act,text="Supprimer",state='disabled',command=self._delete); self.btn_del.pack(side='left',padx=5)

        self.refresh()

    def _on_select(self,_):
        sel = self.tree.selection()
        ok = bool(sel)
        self.selected = int(sel[0]) if ok else None
        self.btn_edit.configure(state='normal' if ok else 'disabled')
        self.btn_del .configure(state='normal' if ok else 'disabled')

    def refresh(self):
        recs = self.ctrl.list_prescriptions(page=self.page, per_page=self.per_page)
        # date filter
        fd,td = self.from_d.get_date(), self.to_d.get_date()
        recs = [r for r in recs if fd <= r.start_date <= td]
        self.tree.delete(*self.tree.get_children())
        for r in recs:
            self.tree.insert('','end',iid=r.prescription_id,values=(
                r.prescription_id,
                getattr(r.patient,'code_patient',''),
                r.medication,
                r.dosage,
                r.frequency,
                r.start_date.strftime("%Y-%m-%d"),
                r.end_date.strftime("%Y-%m-%d") if r.end_date else ''
            ))

    def _edit(self):
        top = ctk.CTkToplevel(self)
        top.title("Éditer Prescription")
        PrescriptionFormView(top,self.ctrl,prescription_id=self.selected).pack(expand=True,fill='both')
        top.bind("<Destroy>",lambda e: self.refresh())

    def _delete(self):
        if not self.selected: return
        try:
            self.ctrl.delete_prescription(self.selected)
            self.refresh()
        except Exception as e:
            ctk.CTkMessagebox.showerror("Erreur",str(e))
