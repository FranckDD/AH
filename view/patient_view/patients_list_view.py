import customtkinter as ctk
from tkinter import ttk
from tkinter import messagebox
from utils.pdf_export import export_patients_to_pdf

# Assuming these view classes exist for editing and viewing profiles
from view.patient_view.patients_edit_view import PatientsEditView
from view.patient_view.patient_profile_view import PatientProfileView

class PatientListView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        # Allow frame to expand and fill when resized
        self.pack(expand=True, fill='both')

        # Determine patient controller
        if hasattr(controller, 'list_patients'):
            self.controller = controller
        elif hasattr(controller, 'patient_controller'):
            self.controller = controller.patient_controller
        else:
            raise AttributeError(f"No patient controller available on {controller}")

        # Top bar with search and action buttons
        top = ctk.CTkFrame(self)
        top.pack(fill='x', pady=5, padx=5)
        top.grid_columnconfigure(0, weight=1)
        for col in range(1, 5):
            top.grid_columnconfigure(col, weight=0)

        self.search_entry = ctk.CTkEntry(top, placeholder_text="Recherche...")
        self.search_entry.grid(row=0, column=0, sticky='ew', padx=(0,5))
        ctk.CTkButton(top, text="🔍", command=self.refresh).grid(row=0, column=1, padx=5)

        # View Profile button
        self.view_btn = ctk.CTkButton(top, text="Voir Profil", command=self.view_profile, state='disabled')
        self.view_btn.grid(row=0, column=2, padx=5)
        # Edit Patient button
        self.edit_btn = ctk.CTkButton(top, text="Éditer", command=self.edit_patient, state='disabled')
        self.edit_btn.grid(row=0, column=3, padx=5)
        # Export PDF button
        ctk.CTkButton(top, text="Export PDF", command=self.export_pdf).grid(row=0, column=4, padx=(5,0))

        # Table container
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill='both', expand=True, padx=5, pady=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("ID","Code","Nom","Prénom","Naissance","Téléphone")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor='center')

        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Pagination bar
        nav = ctk.CTkFrame(self)
        nav.pack(fill='x', pady=5)
        self.page = 1
        ctk.CTkButton(nav, text="←", width=30, command=self.prev_page).pack(side='left', padx=5)
        ctk.CTkButton(nav, text="→", width=30, command=self.next_page).pack(side='right', padx=5)

        # Load initial data
        self.refresh()

    def refresh(self):
        # Clear selection and disable action buttons
        self.selected_patient = None
        self.view_btn.configure(state='disabled')
        self.edit_btn.configure(state='disabled')

        search = self.search_entry.get().strip() or None
        data = self.controller.list_patients(page=self.page, per_page=15, search=search)

        # Clear existing rows
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        # Insert new data
        for p in data:
            self.tree.insert('', 'end', iid=p.patient_id, values=(
                p.patient_id, p.code_patient, p.last_name, p.first_name,
                p.birth_date, p.contact_phone
            ))

    def on_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.selected_patient = int(sel[0])
            # Enable action buttons
            self.view_btn.configure(state='normal')
            self.edit_btn.configure(state='normal')
        else:
            self.selected_patient = None
            self.view_btn.configure(state='disabled')
            self.edit_btn.configure(state='disabled')

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        self.page += 1
        self.refresh()

    def export_pdf(self):
            search = self.search_entry.get().strip() or None
            data = self.controller.list_patients(
                page=self.page, per_page=1000, search=search
            )
            try:
                out_path = export_patients_to_pdf(data, title="Liste des Patients")
                messagebox.showinfo(
                    "Export PDF terminé",
                    f"Le fichier a été généré ici :\n{out_path}"
                )
            except Exception as e:
                messagebox.showerror(
                    "Erreur lors de l'export PDF",
                    f"Une erreur est survenue :\n{e}"
                )

    def view_profile(self):
        if self.selected_patient is None:
            return
        # Open profile in a popup with patient_id
        popup = ctk.CTkToplevel(self)
        popup.title("Profil Patient")
        popup.geometry("600x400")
        PatientProfileView(popup, self.controller, patient_id=self.selected_patient).pack(expand=True, fill='both')

    def edit_patient(self):
        if self.selected_patient is None:
            return
        # Open edit form in a popup with patient_id only
        popup = ctk.CTkToplevel(self)
        popup.title("Éditer Patient")
        popup.geometry("600x400")
        PatientsEditView(
            popup,
            self.controller,
            patient_id=self.selected_patient      # plus de current_user ici
        ).pack(expand=True, fill='both')
        # After edit, refresh list on close
        popup.protocol("WM_DELETE_WINDOW", lambda: (popup.destroy(), self.refresh()))


