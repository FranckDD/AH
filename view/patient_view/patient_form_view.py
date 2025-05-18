# views/patient_view/patient_form_view.py
import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import datetime
from tkinter import messagebox
from controller.patient_controller import PatientController

class PatientFormView(ctk.CTkFrame):
    def __init__(self, parent, controller, current_user, patient_id=None):
        super().__init__(parent, fg_color="white")
        self.controller   = controller
        self.current_user = current_user
        # Flag pour distinguer création vs mise à jour
        self.is_new = patient_id is None
        self.patient_id   = patient_id
        self.patient_id   = patient_id
        # dictionnaires pour widgets et variables
        self.field_widgets = {}
        self.vars = {}
        self.error_label = None
        # configuration colonne
        self.grid_columnconfigure(1, weight=1)

        # définition des champs
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

        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(self, text=label).grid(row=i+1, column=0, sticky='e', padx=5, pady=5)
            if key == "gender":
                var = tk.StringVar(value="Autre")
                widget = ctk.CTkOptionMenu(self, values=["Homme","Femme","Autre"], variable=var)
                widget.grid(row=i+1, column=1, sticky='ew', padx=5, pady=5)
                self.vars[key] = var
                self.field_widgets[key] = widget

            elif key == "birth_date":
                # Utilisation d'un DateEntry pour sélectionner la date
                widget = DateEntry(self,
                                   date_pattern='yyyy-mm-dd',
                                   background='white',
                                   foreground='black',
                                   borderwidth=1,
                                   year=2000)
                widget.grid(row=i+1, column=1, sticky='w', padx=5, pady=5)
                self.vars[key] = widget
                self.field_widgets[key] = widget

            else:
                e = ctk.CTkEntry(self)
                e.grid(row=i+1, column=1, sticky='ew', padx=5, pady=5)
                self.vars[key] = e
                self.field_widgets[key] = e

        # bouton enregistrement
        btn = ctk.CTkButton(self, text="Enregistrer", command=self._save)
        btn.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)

        # chargement si édition
        if self.patient_id:
            self._load()

    def _show_error(self, msg, invalid_fields=None):
        # supprime ancien message
        if self.error_label:
            self.error_label.destroy()
        # affiche nouveau message
        self.error_label = ctk.CTkLabel(self, text=msg, text_color="red")
        self.error_label.grid(row=0, column=0, columnspan=2, pady=(5,10))
        # réinitialise bordures
        for w in self.field_widgets.values():
            w.configure(borderwidth=0)
        # surligne champs manquants
        if invalid_fields:
            for key in invalid_fields:
                widget = self.field_widgets.get(key)
                if widget:
                    widget.configure(borderwidth=1, bordercolor="red")
                    widget.focus()

    def _load(self):
        p = self.controller.get_patient(self.patient_id)
        if not p:
            return
        for key, widget in self.vars.items():
            val = p.get(key)
            if key == "birth_date" and val:
                widget.set_date(val)
            elif isinstance(widget, tk.StringVar):
                widget.set(val or "Autre")
            else:
                widget.delete(0, tk.END)
                widget.insert(0, val or "")

    def _save(self):
        # collecte des données
        data = {}
        for key, widget in self.vars.items():
            if key == "birth_date":
                try:
                    data[key] = datetime.strptime(widget.get(), "%Y-%m-%d").date()
                except ValueError:
                    data[key] = None
            elif isinstance(widget, tk.StringVar):
                data[key] = widget.get().strip() or None
            else:
                data[key] = widget.get().strip() or None

        # validation des champs obligatoires
        required = ['first_name', 'last_name', 'birth_date']
        missing = [f for f in required if not data.get(f)]
        if missing:
            self._show_error("Champs obligatoires manquants", invalid_fields=missing)
            return

        # appel unique au controller + gestion message + redirection
        try:
            if self.patient_id:
                self.controller.update_patient(self.patient_id, data)
                title, msg = "Patient mis à jour", "Les modifications ont bien été prises en compte."
            else:
                # choisissez A ou B pour récupérer new_id et éventuellement code
                new_id, code = self.controller.create_patient(data)
                self.patient_id = new_id
                title = "Patient créé"
                msg = f"Patient enregistré avec succès.\nCode patient : {code}"
            
            # après avoir préparé title et msg
            messagebox.showinfo(title, msg)
            self._redirect_to_dashboard()
        except Exception as e:
            self._show_error("Erreur : " + str(e))


    def _show_error(self, message, invalid_fields=None):
        messagebox.showerror("Erreur", message)
        if invalid_fields:
            for field in invalid_fields:
                w = self.vars[field]
                # CustomTkinter accepte border_width, pas borderwidth
                try:
                    w.configure(border_width=2, border_color="red")
                except Exception:
                    pass


    def _redirect_to_dashboard(self):
        # remonte la hiérarchie des widgets jusqu'à trouver show_doctors_dashboard
        widget = self
        while widget is not None:
            if hasattr(widget, 'show_doctors_dashboard'):
                widget.show_doctors_dashboard()
                return
            widget = getattr(widget, 'master', None)
        # pas trouvé ? on peut loguer ou fallback
        print("⚠️ show_doctors_dashboard introuvable dans les parents.")
