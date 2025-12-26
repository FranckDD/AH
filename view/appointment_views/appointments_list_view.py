import customtkinter as ctk
from tkinter import ttk
from datetime import date

class AppointmentsList(ctk.CTkFrame):
    def __init__(self, master, controller, *, on_book, on_edit, per_page=20, target_date=None):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        target_date = target_date
        self.on_book = on_book
        self.on_edit = on_edit
        self.page = 1
        self.per_page = per_page
        

        # Barre de contrôle
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", pady=(10,5), padx=10)
        self.search_var = ctk.StringVar()
        ctk.CTkEntry(ctrl, placeholder_text="Rechercher nom ou code",
                     textvariable=self.search_var, width=200).pack(side="left", padx=(0,5))
        ctk.CTkButton(ctrl, text="🔍", width=30, command=self.refresh).pack(side="left", padx=(0,10))
        self.status_filter = ctk.StringVar(value="Tous")
        ctk.CTkOptionMenu(ctrl, variable=self.status_filter,
                          values=["Tous","pending","completed","cancelled"], width=120,
                          command=lambda _: self.refresh()).pack(side="left", padx=(0,10))
        self.date_filter = ttk.Combobox(ctrl, values=["Toutes","Aujourd'hui"],
                                        width=12, state="readonly")
        self.date_filter.set("Toutes")
        self.date_filter.pack(side="left", padx=(0,10))
        self.date_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ctk.CTkButton(ctrl, text="Book Appointment", command=self.on_book).pack(side="right")

        # Tableau
        cols = ("id","patient","code","phone","doctor",
                "date","time","reason","status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        headers = {"id":"ID","patient":"Patient","code":"Code Patient",
                   "phone":"Téléphone","doctor":"Médecin","date":"Date",
                   "time":"Heure","reason":"Raison","status":"Statut"}
        widths = {c:w for c,w in zip(cols, [50,150,100,100,150,90,70,200,90])}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,5))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)
        style.map("Treeview",
                  background=[("selected", "#338cff")],
                  foreground=[("selected", "white")])
        self.tree.tag_configure("pending",   background="#fffbea")
        self.tree.tag_configure("completed", background="#e6ffec")  # vert clair
        self.tree.tag_configure("cancelled", background="#ffecec")

        # Actions & pagination
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(0,10))
        self.btn_accept = ctk.CTkButton(bottom, text="Accepter", state="disabled",
                                         fg_color="grey", hover_color="#ccffcc",
                                         command=self.accept)
        self.btn_accept.pack(side="left", padx=5)
        self.btn_reject = ctk.CTkButton(bottom, text="Refuser", state="disabled",
                                         fg_color="grey", hover_color="#ffcccc",
                                         command=self.reject)
        self.btn_reject.pack(side="left", padx=5)
        self.btn_complete = ctk.CTkButton(bottom, text="Compléter", state="disabled",
                                  fg_color="grey", hover_color="#99ffcc",
                                  command=self.complete)
        self.btn_complete.pack(side="left", padx=5)
        self.btn_edit = ctk.CTkButton(bottom, text="Éditer", state="disabled",
                                       fg_color="grey", hover_color="#cce0ff",
                                       command=lambda: self.on_edit(self.selected_id))
        self.btn_edit.pack(side="left", padx=5)
        ctk.CTkButton(bottom, text="← Précédent", command=self.prev_page).pack(side="right", padx=5)
        ctk.CTkButton(bottom, text="Suivant →", command=self.next_page).pack(side="right", padx=5)

        self.refresh()

    def refresh(self):
        for iid in self.tree.get_children(): self.tree.delete(iid)
        rdvs = self.controller.repo.list_all()
        # filtres
        st = self.status_filter.get()
        if st != "Tous": rdvs = [r for r in rdvs if r.status==st]
        if self.date_filter.get()=="Aujourd'hui":
            today = date.today(); rdvs=[r for r in rdvs if r.appointment_date==today]
        term = self.search_var.get().lower().strip()
        if term:
            rdvs=[r for r in rdvs if term in getattr(r.patient,"code_patient","").lower()
                   or term in getattr(r.patient,"full_name",f"{r.patient.first_name} {r.patient.last_name}").lower()]
        start=(self.page-1)*self.per_page; end=start+self.per_page
        for appt in rdvs[start:end]:
            p=appt.patient; name=getattr(p,"full_name",f"{p.first_name} {p.last_name}")
            code=getattr(p,"code_patient","")
            phone=getattr(p,"contact_phone","")
            doc=getattr(appt.doctor,"full_name",appt.doctor.username)
            self.tree.insert("","end",iid=str(appt.id),
                              values=(appt.id,name,code,phone,doc,
                                      appt.appointment_date.strftime("%Y-%m-%d"),
                                      appt.appointment_time.strftime("%H:%M"),
                                      appt.reason,appt.status),
                              tags=(appt.status,))
        self.on_select()

    def on_select(self, event=None):
        sel = self.tree.selection(); has=bool(sel)
        self.selected_id=int(sel[0]) if has else None
        for btn in (self.btn_accept, self.btn_reject, self.btn_edit, self.btn_complete):
            btn.configure(state="normal" if has else "disabled")

    def accept(self):
        if self.selected_id:
            self.controller.modify_appointment(self.selected_id, status="pending")
            self.refresh()

    def reject(self):
        if self.selected_id:
            self.controller.cancel_appointment(self.selected_id)
            self.refresh()

    def complete(self):
        if self.selected_id:
            self.controller.complete_appointment(self.selected_id)
            self.refresh()


    def prev_page(self):
        if self.page>1:
            self.page-=1; self.refresh()

    def next_page(self):
        total=len(self.controller.repo.list_all())
        maxp=(total-1)//self.per_page+1
        if self.page<maxp:
            self.page+=1; self.refresh()