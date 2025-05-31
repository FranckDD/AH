# view/patient_view/patient_form_view.py
import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime
from tkinter import messagebox
from controller.patient_controller import PatientController

class PatientFormView(ctk.CTkFrame):
    def __init__(self, parent, controller: PatientController, current_user, patient_id=None, on_save=None):
        """
        on_save : fonction callback à appeler après la création d'un patient.
                  Elle doit prendre en paramètre le code_patient généré (str).
        """
        super().__init__(parent, fg_color="white")
        self.controller   = controller
        self.current_user = current_user
        self.on_save      = on_save

        self.is_new       = (patient_id is None)
        self.patient_id   = patient_id

        self.field_widgets = {}
        self.vars = {}
        self.error_label = None

        # disposition
        self.grid_columnconfigure(1, weight=1)

        fields = [
            ("Prénom",      "first_name"),
            ("Nom",         "last_name"),
            ("Date Naiss.", "birth_date"),
            ("Genre",       "gender"),
            ("N° national", "national_id"),
            ("Téléphone",   "contact_phone"),
            ("Assurance",   "assurance"),
            ("Résidence",   "residence"),
            ("Nom Père",    "father_name"),
            ("Nom Mère",    "mother_name"),
        ]

        for i, (label_text, key) in enumerate(fields):
            ctk.CTkLabel(self, text=label_text).grid(row=i+1, column=0, sticky='e', padx=5, pady=5)

            if key == "gender":
                var = tk.StringVar(value="Autre")
                widget = ctk.CTkOptionMenu(self, values=["Homme","Femme","Autre"], variable=var)
                widget.grid(row=i+1, column=1, sticky='ew', padx=5, pady=5)
                self.vars[key] = var
                self.field_widgets[key] = widget

            elif key == "birth_date":
                widget = DateEntry(
                    self,
                    date_pattern='yyyy-mm-dd',
                    background='white',
                    foreground='black',
                    borderwidth=1,
                    year=2000
                )
                widget.grid(row=i+1, column=1, sticky='w', padx=5, pady=5)
                self.vars[key] = widget
                self.field_widgets[key] = widget

            else:
                entry = ctk.CTkEntry(self)
                entry.grid(row=i+1, column=1, sticky='ew', padx=5, pady=5)
                self.vars[key] = entry
                self.field_widgets[key] = entry

        # Bouton Enregistrer
        btn = ctk.CTkButton(self, text="Enregistrer", command=self._save)
        btn.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)

        if self.patient_id:
            self._load()

    def _show_error(self, message, invalid_fields=None):
        if self.error_label:
            self.error_label.destroy()
        self.error_label = ctk.CTkLabel(self, text=message, text_color="red")
        self.error_label.grid(row=0, column=0, columnspan=2, pady=(5,10))

        for w in self.field_widgets.values():
            w.configure(borderwidth=0)
        if invalid_fields:
            for key in invalid_fields:
                widget = self.field_widgets.get(key) or self.vars.get(key)
                if widget:
                    widget.configure(border_width=2, border_color="red")
                    widget.focus()

    def _load(self):
        p = self.controller.get_patient(self.patient_id)
        if not p:
            return
        for key, widget in self.vars.items():
            val = p.get(key) if isinstance(p, dict) else getattr(p, key, None)
            if key == "birth_date" and val:
                try:
                    widget.set_date(val)
                except:
                    pass
            elif isinstance(widget, tk.StringVar):
                widget.set(val or "Autre")
            else:
                widget.delete(0, tk.END)
                widget.insert(0, val or "")

    def _save(self):
        # 1. Collecte des données
        data = {}
        for key, widget in self.vars.items():
            if key == "birth_date":
                try:
                    data[key] = datetime.strptime(widget.get(), "%Y-%m-%d").date()
                except:
                    data[key] = None
            elif isinstance(widget, tk.StringVar):
                data[key] = widget.get().strip() or None
            else:
                data[key] = widget.get().strip() or None

        # 2. Validation
        required = ["first_name", "last_name", "birth_date"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return self._show_error("Champs obligatoires manquants", invalid_fields=missing)

        try:
            if self.patient_id:
                self.controller.update_patient(self.patient_id, data)
                messagebox.showinfo("Patient mis à jour", "Les modifications ont bien été prises en compte.")
                self._redirect_to_dashboard()
            else:
                new_id, code = self.controller.create_patient(data)
                self.patient_id = new_id
                messagebox.showinfo("Patient créé", f"Patient enregistré.\nCode : {code}")

                # Si on a passé un callback on_save, on l'appelle et on ferme ce formulaire
                if self.on_save:
                    self.destroy()
                    self.on_save(code)
                else:
                    self._redirect_to_dashboard()

        except Exception as e:
            return self._show_error("Erreur : " + str(e))

    def _redirect_to_dashboard(self):
        """
        Remonte la hiérarchie jusqu’à trouver show_doctors_dashboard()
        (dans le contexte médical). Si jamais on ne le trouve pas, ne fait rien.
        """
        widget = self
        while widget:
            if hasattr(widget, "show_doctors_dashboard"):
                widget.show_doctors_dashboard()
                return
            widget = getattr(widget, "master", None)
        print("⚠️ show_doctors_dashboard introuvable parmi les parents.")
