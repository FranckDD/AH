import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog
from datetime import datetime, timedelta
from tkcalendar import DateEntry
from utils.export_utils import export_medical_records_to_pdf, export_medical_records_to_excel
from view.medical_record.medical_record_form_view import MedicalRecordFormView

class MedicalRecordListView(ctk.CTkFrame):
    def __init__(self, parent, controller, on_prescribe):
        super().__init__(parent, fg_color="white")
        self.ctrl = controller
        self.on_prescribe = on_prescribe
        self.page = 1
        self.per_page = 20
        self.selected_record = None

        # Charger motifs pour mapping code ↔ label
        motifs = controller.list_motifs()
        self.code_to_label = {m['code']: m['label_fr'] for m in motifs}
        self.label_to_code = {m['label_fr']: m['code'] for m in motifs}

        # === Filters & Actions Bar ===
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill='x', pady=10, padx=10)
        filter_frame.grid_columnconfigure(3, weight=1)

        # Date range filters (dernier an par défaut)
        ctk.CTkLabel(filter_frame, text="Date from:").grid(row=0, column=0, padx=5)
        self.from_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.from_date.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(filter_frame, text="to:").grid(row=0, column=2, padx=5)
        self.to_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.to_date.grid(row=0, column=3, padx=5)
        self.from_date.set_date(datetime.today() - timedelta(days=365))
        self.to_date.set_date(datetime.today())

        # Motif filter
        labels = [m['label_fr'] for m in motifs]
        self.motif_var = tk.StringVar(value="Tous")
        self.motif_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["Tous"] + labels,
            variable=self.motif_var
        )
        self.motif_menu.grid(row=0, column=4, padx=5)

        # Severity filter
        self.severity_var = tk.StringVar(value="Toutes")
        self.severity_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=["Toutes", "low", "medium", "high"],
            variable=self.severity_var
        )
        self.severity_menu.grid(row=0, column=5, padx=5)

        # Recherche (code_patient ou nom)
        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Rechercher code/nom",
            textvariable=self.search_var
        )
        self.search_entry.grid(row=0, column=6, padx=5)
        ctk.CTkButton(filter_frame, text="Rechercher", command=self.refresh).grid(row=0, column=7, padx=5)

        # Boutons Filter / Export
        ctk.CTkButton(filter_frame, text="Filtrer", command=self.refresh).grid(row=0, column=8, padx=5)
        ctk.CTkButton(filter_frame, text="Export PDF", command=self.export_pdf).grid(row=0, column=9, padx=5)
        ctk.CTkButton(filter_frame, text="Export Excel", command=self.export_excel).grid(row=0, column=10, padx=5)

        # === Table ===
        table_container = ctk.CTkScrollableFrame(self)
        table_container.pack(fill='both', expand=True, padx=10, pady=(0,10))
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        cols = (
            "record_id","patient_code","patient_id","consultation_date","marital_status",
            "bp","temperature","weight","height","medical_history","allergies",
            "symptoms","diagnosis","treatment","severity","notes","motif_code"
        )
        headers = {
            "record_id":"ID", "patient_code":"Code Patient", "patient_id":"Pat. ID",
            "consultation_date":"Date", "marital_status":"Statut", "bp":"Tension",
            "temperature":"Temp.","weight":"Poids","height":"Taille",
            "medical_history":"Antécédents","allergies":"Allergies","symptoms":"Symptômes",
            "diagnosis":"Diagnostic","treatment":"Traitement","severity":"Gravité",
            "notes":"Notes","motif_code":"Motif code"
        }

        self.tree = ttk.Treeview(table_container, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=100, anchor='center')
        vsb = ttk.Scrollbar(table_container, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(table_container, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # === Actions ===
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill='x', padx=10, pady=(0,10))
        self.view_btn = ctk.CTkButton(action_frame, text="Voir/Éditer", command=self.view_record, state='disabled')
        self.view_btn.pack(side='left', padx=5)
        self.email_btn = ctk.CTkButton(action_frame, text="Envoyer Email", command=self.send_email, state='disabled')
        self.email_btn.pack(side='left', padx=5)
        self.prescribe_btn = ctk.CTkButton(action_frame, text="Prescription", command=self.prescribe_record, state='disabled')
        self.prescribe_btn.pack(side='left', padx=5)

        # === Pagination ===
        nav_frame = ctk.CTkFrame(self)
        nav_frame.pack(fill='x', padx=10, pady=(0,10))
        ctk.CTkButton(nav_frame, text="← Page précédente", command=self.prev_page).pack(side='left', padx=5)
        ctk.CTkButton(nav_frame, text="Page suivante →", command=self.next_page).pack(side='right', padx=5)

        # Initial load
        self.refresh()

    def on_select(self, event):
        sel = self.tree.selection()
        state = 'normal' if sel else 'disabled'
        self.selected_record = int(sel[0]) if sel else None
        self.view_btn.configure(state=state)
        self.email_btn.configure(state=state)
        self.prescribe_btn.configure(state=state)

    def refresh(self):
        recs = self._get_filtered_records()
        self.tree.delete(*self.tree.get_children())
        for r in recs:
            self.tree.insert('', 'end', iid=r.record_id, values=(
                r.record_id,
                r.patient.code_patient if r.patient else "",
                r.patient_id,
                r.consultation_date.strftime('%Y-%m-%d'),
                r.marital_status,
                r.bp,
                r.temperature,
                r.weight,
                r.height,
                (r.medical_history or "")[:15] + "...",
                (r.allergies or "")[:15] + "...",
                (r.symptoms or "")[:15] + "...",
                (r.diagnosis or "")[:15] + "...",
                (r.treatment or "")[:15] + "...",
                r.severity,
                (r.notes or "")[:15] + "...",
                r.motif_code
            ))

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        self.page += 1
        self.refresh()

    def export_pdf(self):
        file = filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('PDF','*.pdf')])
        if not file:
            return
        recs = self._get_filtered_records(for_export=True)
        data = [{
            'record_id': r.record_id,
            'consultation_date': r.consultation_date,
            'patient_name': f"{r.patient.last_name} {r.patient.first_name}" if r.patient else "",
            'motif_code': r.motif_code,
            'severity': r.severity,
            'bp': r.bp,
            'temperature': r.temperature,
            'weight': r.weight,
            'height': r.height,
            'diagnosis': r.diagnosis,
            'treatment': r.treatment
        } for r in recs]
        export_medical_records_to_pdf(data, file)
        self._flash_message(f"PDF enregistré : {file}")

    def export_excel(self):
        file = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel','*.xlsx')])
        if not file:
            return
        recs = self._get_filtered_records(for_export=True)
        data = [{
            'record_id': r.record_id,
            'consultation_date': r.consultation_date,
            'patient_name': f"{r.patient.last_name} {r.patient.first_name}" if r.patient else "",
            'motif_code': r.motif_code,
            'severity': r.severity,
            'bp': r.bp,
            'temperature': r.temperature,
            'weight': r.weight,
            'height': r.height,
            'diagnosis': r.diagnosis,
            'treatment': r.treatment
        } for r in recs]
        export_medical_records_to_excel(data, file)
        self._flash_message(f"Excel enregistré : {file}")

    def view_record(self):
        if not self.selected_record:
            return
        popup = ctk.CTkToplevel(self)
        popup.title("Éditer Dossier Médical")
        popup.geometry("700x500")
        scroll_frame = ctk.CTkScrollableFrame(popup)
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)
        MedicalRecordFormView(scroll_frame, self.ctrl, record_id=self.selected_record).pack(expand=True, fill='both')
        popup.bind("<Destroy>", lambda e: self.refresh())

    def send_email(self):
        self._flash_message("📧 Email envoyé !")

    def prescribe_record(self):
        if not self.selected_record:
            return
        recs = self._get_filtered_records()
        rec = next(r for r in recs if r.record_id == self.selected_record)
        if rec and rec.patient_id:
            self.on_prescribe(
                patient_id=rec.patient_id,
                medical_record_id=rec.record_id
            )

    def _flash_message(self, text, duration=2000):
        msg = ctk.CTkLabel(self, text=text, text_color="green")
        msg.place(relx=0.5, rely=0.5, anchor='center')
        self.after(duration, msg.destroy)

    def _get_filtered_records(self, for_export=False):
        # Pagination ou export
        if for_export:
            recs = self.ctrl.list_records(page=1, per_page=10_000)
        else:
            recs = self.ctrl.list_records(page=self.page, per_page=self.per_page)
        # Filtres date
        from_d = self.from_date.get_date()
        to_d = self.to_date.get_date()
        recs = [r for r in recs if from_d <= r.consultation_date.date() <= to_d]
        # Filtre motif
        if self.motif_var.get() != "Tous":
            code = self.label_to_code[self.motif_var.get()]
            recs = [r for r in recs if r.motif_code == code]
        # Filtre gravité
        if self.severity_var.get() != "Toutes":
            recs = [r for r in recs if r.severity == self.severity_var.get()]
        # Filtre recherche
        q = self.search_var.get().strip().lower()
        if q:
            recs = [r for r in recs if r.patient and (
                q in r.patient.code_patient.lower() or
                q in f"{r.patient.last_name} {r.patient.first_name}".lower()
            )]
        # Tri décroissant par date
        recs.sort(key=lambda r: r.consultation_date, reverse=True)
        return recs
