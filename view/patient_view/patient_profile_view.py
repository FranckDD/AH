import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from tkinter import ttk

class PatientProfileView(ctk.CTkFrame):
    def __init__(self, parent, controller, patient_id=None):
        super().__init__(parent)
        self.controller = controller
        self.patient_id = patient_id or getattr(controller, 'selected_patient', None)

        # Create tabs with display names as keys
        tab_names = ["Informations", "Rendez-vous", "Prescriptions", "Examens labo", "Consult. spirituelles"]
        self.tabview = ctk.CTkTabview(self)
        for name in tab_names:
            self.tabview.add(name)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Build tabs
        self._build_info_tab()
                # Resolve fetch functions (fall back to subcontrollers if needed)
        appt_fetch = getattr(self.controller, 'get_appointments', None) or getattr(getattr(self.controller, 'appointment_controller', None), 'get_appointments', None)
        presc_fetch = getattr(self.controller, 'get_prescriptions', None) or getattr(getattr(self.controller, 'prescription_controller', None), 'get_prescriptions', None)
        lab_fetch = getattr(self.controller, 'get_lab_results', None) or getattr(getattr(self.controller, 'lab_controller', None), 'get_lab_results', None)
        spirit_fetch = getattr(self.controller, 'get_spiritual_consultations', None) or getattr(getattr(self.controller, 'spiritual_controller', None), 'get_spiritual_consultations', None)

        # Build tabs
        self._build_info_tab()
        self._build_list_tab("Rendez-vous", appt_fetch,
                              ("appointment_date","doctor_name","reason"))
        self._build_list_tab("Prescriptions", presc_fetch,
                              ("medication","dosage","start_date","end_date"))
        self._build_list_tab("Examens labo", lab_fetch,
                              ("test_type","test_date","status"))
        self._build_list_tab("Consult. spirituelles", spirit_fetch,
                              ("notes","consultation_date"))("Rendez-vous", self.controller.get_appointments,
                              ("appointment_date","doctor_name","reason"))
        self._build_list_tab("Prescriptions", self.controller.get_prescriptions,
                              ("medication","dosage","start_date","end_date"))
        self._build_list_tab("Examens labo", self.controller.get_lab_results,
                              ("test_type","test_date","status"))
        self._build_list_tab("Consult. spirituelles", self.controller.get_spiritual_consultations,
                              ("notes","consultation_date"))

        # Load data
        if self.patient_id is not None:
            self.load_patient()
        else:
            placeholder = ctk.CTkLabel(self, text="Aucun patient sélectionné.")
            placeholder.pack(pady=20)

    def _build_info_tab(self):
        tab = self.tabview.tab("Informations")
        labels = [
            ("Code patient", "code_patient"),
            ("Prénom", "first_name"),
            ("Nom", "last_name"),
            ("Date Naiss.", "birth_date"),
            ("Genre", "gender"),
            ("Téléphone", "contact_phone"),
            ("Assurance", "assurance"),
            ("Résidence", "residence"),
            ("Nom Père", "father_name"),
            ("Nom Mère", "mother_name"),
            ("Créé le", "created_at"),
            ("Par", "created_by_name"),
        ]
        self.info_vars = {}
        for i, (label, key) in enumerate(labels):
            ctk.CTkLabel(tab, text=f"{label}:").grid(row=i, column=0, padx=5, pady=3, sticky="e")
            var = ctk.CTkLabel(tab, text="")
            var.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            self.info_vars[key] = var

    def _build_list_tab(self, tab_name, fetch_func, columns):
        tab = self.tabview.tab(tab_name)
        tree = ttk.Treeview(tab, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col.replace('_', ' ').title())
            tree.column(col, anchor='center')
        tree.pack(fill='both', expand=True, padx=5, pady=5)
        setattr(self, f"tree_{tab_name.replace(' ', '_')}", tree)
        setattr(self, f"fetch_{tab_name.replace(' ', '_')}", fetch_func)

    def load_patient(self):
        data = self.controller.get_patient(self.patient_id)
        if not data:
            return
        # Load info
        for key, var in self.info_vars.items():
            val = data.get(key)
            if hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d')
            var.configure(text=val)
        # Load lists
        for tab_name in ["Rendez-vous","Prescriptions","Examens labo","Consult. spirituelles"]:
            tree = getattr(self, f"tree_{tab_name.replace(' ', '_')}")
            fetch = getattr(self, f"fetch_{tab_name.replace(' ', '_')}")
            for iid in tree.get_children():
                tree.delete(iid)
            for row in fetch(self.patient_id):
                vals = []
                for col in tree['columns']:
                    v = row.get(col)
                    if hasattr(v, 'strftime'):
                        v = v.strftime('%Y-%m-%d')
                    vals.append(v)
                tree.insert('', 'end', values=tuple(vals))
