import customtkinter as ctk
from tkcalendar import DateEntry

class AppointmentsBook(ctk.CTkToplevel):
    def __init__(self, master, controller, appointment=None, on_save=None):
        super().__init__(master)
        self.controller = controller
        self.appointment = appointment
        self.on_save     = on_save

        self.title("Prendre un RDV" if not appointment else "Éditer un RDV")
        self.geometry("400x500")
        self.resizable(False, False)

        # Construire le formulaire
        self._build_form()

        # Pré-remplir si édition
        if self.appointment:
            self._prefill_fields()

    def _build_form(self):
        # Code patient
        ctk.CTkLabel(self, text="Code Patient").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.code_var = ctk.StringVar()
        self.entry_code = ctk.CTkEntry(self, textvariable=self.code_var)
        self.entry_code.grid(row=0, column=1, padx=10, pady=5)
        self.entry_code.bind("<Return>", self.on_code_enter)

        # Lecture seule patient
        self.lbl_name = ctk.CTkLabel(self, text="Prénom Nom : –")
        self.lbl_name.grid(row=1, column=0, columnspan=2, padx=10)
        self.lbl_phone = ctk.CTkLabel(self, text="Téléphone : –")
        self.lbl_phone.grid(row=2, column=0, columnspan=2, padx=10, pady=(0,10))

        # Spécialité
        ctk.CTkLabel(self, text="Spécialité").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.specialty_var = ctk.StringVar()
        specs = self.controller.get_all_specialties()
        self.specialty_menu = ctk.CTkOptionMenu(self, variable=self.specialty_var, values=specs)
        self.specialty_menu.grid(row=3, column=1, padx=10, pady=5)

        # Date
        ctk.CTkLabel(self, text="Date").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.date_entry = DateEntry(self, date_pattern='yyyy-MM-dd')
        self.date_entry.grid(row=4, column=1, padx=10, pady=5)

        # Heure
        ctk.CTkLabel(self, text="Heure").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        times = [f"{h:02d}:{m:02d}" for h in range(8,19) for m in (0,30)]
        self.time_entry = ctk.CTkComboBox(self, values=times)
        self.time_entry.grid(row=5, column=1, padx=10, pady=5)

        # Raison
        ctk.CTkLabel(self, text="Raison").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.reason_var = ctk.StringVar()
        self.entry_reason = ctk.CTkEntry(self, textvariable=self.reason_var)
        self.entry_reason.grid(row=6, column=1, padx=10, pady=5)

        # Bouton Enregistrer
        self.btn_save = ctk.CTkButton(self, text="Enregistrer", command=self.save_appointment)
        self.btn_save.grid(row=7, column=0, columnspan=2, pady=20)

    def on_code_enter(self, event):
        raw   = self.code_var.get().strip()            # ce que l'utilisateur a tapé
        if not raw:
            return

        # Normalise tout en majuscules pour la recherche
        norm = raw.upper()

        # Ajoute le préfixe si besoin
        if not norm.startswith("AH2-"):
            code = f"AH2-{norm}"
        else:
            code = norm

        # Écrase la saisie pour afficher la version normalisée
        self.code_var.set(code)

        # Recherche le patient
        patient = self.controller.patient_ctrl.find_by_code(code)
        if not patient:
            ctk.CTkLabel(self, text="Code inconnu !", text_color="red")\
            .grid(row=0, column=2, padx=5)
            return

        # Affiche les infos et conserve l'ID
        name = f"{patient['first_name']} {patient['last_name']}"
        self.lbl_name.configure(text=f"Prénom Nom : {name}")
        self.lbl_phone.configure(text=f"Téléphone : {patient['contact_phone']}")
        self.patient_id = patient['patient_id']


    def _prefill_fields(self):
        appt = self.appointment
        # Debug : imprime en console les valeurs
        print(">>> _prefill_fields called with appointment:", appt)
        print("    patient.code_patient:", appt.patient.code_patient)
        print("    specialty:", appt.specialty)
        print("    date:", appt.appointment_date)
        print("    time:", appt.appointment_time)
        print("    reason:", appt.reason)

        # Maintenant on remplit
        self.code_var.set(appt.patient.code_patient)
        self.on_code_enter(None)

        self.specialty_var.set(appt.specialty or "")
        self.date_entry.set_date(appt.appointment_date)
        self.time_entry.set(appt.appointment_time.strftime("%H:%M"))
        self.reason_var.set(appt.reason or "")

    def save_appointment(self):
        # si on n'a pas de patient_id, on bloque directement
        if not hasattr(self, 'patient_id') or self.patient_id is None:
            ctk.CTkLabel(self, text="Veuillez saisir un code patient valide.", text_color="red")\
               .grid(row=8, column=0, columnspan=2, pady=(5,10))
            return

        data = {
            'patient_id':       self.patient_id,
            'specialty':        self.specialty_var.get(),
            'appointment_date': self.date_entry.get_date(),
            'appointment_time': self.time_entry.get(),
            'reason':           self.reason_var.get().strip()
        }
        try:
            if self.appointment:
                self.controller.modify_appointment(self.appointment.id, **data)
                msg = f"RDV #{self.appointment.id} modifié avec succès"
            else:
                appt = self.controller.book_appointment(data)
                msg = f"RDV créé (ID {appt.id})"

            # Affiche le message vert
            self.lbl_feedback = ctk.CTkLabel(self, text=msg, text_color="green")
            self.lbl_feedback.grid(row=8, column=0, columnspan=2, pady=(5,10))

            # Appelle le callback pour rafraîchir la liste
            if self.on_save:
                self.on_save()

            # Ferme après 1.5 s
            self.after(1500, self.destroy)

        except Exception as e:
            self.lbl_feedback = ctk.CTkLabel(self, text=f"Erreur : {e}", text_color="red")
            self.lbl_feedback.grid(row=8, column=0, columnspan=2, pady=(5,10))
