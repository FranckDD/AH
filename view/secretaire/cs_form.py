# view/secretaire/cs_form.py
import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox
import traceback

class CSFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, patient_ctrl, on_save=None):
        super().__init__(master)
        self.title("Nouvelle Consultation Spirituelle")
        self.controller = controller
        self.patient_ctrl = patient_ctrl
        self.on_save = on_save
        self.patient_id = None

        # --- Code patient ---
        self.var_code = ctk.StringVar()
        frm_top = ctk.CTkFrame(self)
        frm_top.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(frm_top, text="Code patient:").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(frm_top, textvariable=self.var_code).grid(row=0, column=1, pady=5)
        ctk.CTkButton(frm_top, text="Charger", command=self.load_patient).grid(row=0, column=2, padx=5)

        # --- Choix du type de consultation ---
        self.var_type = ctk.StringVar(value="Spiritual")
        ctk.CTkLabel(frm_top, text="Type:").grid(row=1, column=0, sticky="w")

        cb_type = ctk.CTkComboBox(
            frm_top,
            variable=self.var_type,
            values=["Spiritual", "FamilyRestoration"],
            width=200,
            command=lambda v: self.render_fields()
        )
        cb_type.grid(row=1, column=1, columnspan=2, pady=5)

        # --- Frame dynamique ---
        self.dynamic_frame = ctk.CTkFrame(self)
        self.dynamic_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # --- Notes ---
        ctk.CTkLabel(self, text="Notes:").pack(anchor="w", padx=20, pady=(5, 0))
        self.txt_notes = ctk.CTkTextbox(self, height=80)
        self.txt_notes.pack(padx=20, fill="x")

        # --- Bouton Enregistrer ---
        btn_save = ctk.CTkButton(self, text="Enregistrer", command=self.save)
        btn_save.pack(pady=10)

        # Affiche les champs initiaux “Spiritual”
        self.render_fields()


    def load_patient(self):
        code = self.var_code.get().strip()
        p = self.patient_ctrl.find_by_code(code)
        if not p:
            messagebox.showerror("Erreur", "Patient introuvable")
            return
        self.patient_id = p['patient_id']


    def render_fields(self):
        """
        Reconstruit self.dynamic_frame selon self.var_type.get()
        """
        #print(f"[DEBUG] render_fields() appelé -> var_type = '{self.var_type.get()}'")
        for w in self.dynamic_frame.winfo_children():
            w.destroy()

        if self.var_type.get() == "Spiritual":
            self._render_spiritual_fields()
        else:
            self._render_family_fields()


    def _render_spiritual_fields(self):
        # Prescription générale (CheckBoxes)
        ctk.CTkLabel(self.dynamic_frame, text="Prescription générale:").grid(row=0, column=0, sticky="w")
        self.chk_vars_generic = {
            'Hony': tk.BooleanVar(value=False),
            'Massage': tk.BooleanVar(value=False),
            'Prayer': tk.BooleanVar(value=False)
        }
        col = 1
        for key, var in self.chk_vars_generic.items():
            ctk.CTkCheckBox(
                self.dynamic_frame,
                text=key,
                variable=var
            ).grid(row=0, column=col, padx=(5, 10), pady=5, sticky="w")
            col += 1

        # Médicaments spirituels (CheckBoxes)
        ctk.CTkLabel(self.dynamic_frame, text="Méd. spirituel:").grid(row=1, column=0, sticky="w")
        self.chk_vars_med = {
            'SE': tk.BooleanVar(value=False),
            'TIS': tk.BooleanVar(value=False),
            'AE': tk.BooleanVar(value=False)
        }
        col = 1
        for key, var in self.chk_vars_med.items():
            ctk.CTkCheckBox(
                self.dynamic_frame,
                text=key,
                variable=var
            ).grid(row=1, column=col, padx=(5, 10), pady=5, sticky="w")
            col += 1

        # --- Combobox pour Prayer Book (possibilité de ne rien sélectionner) ---
        from models.prayer_book_type import PrayerBookType
        session = self.controller.repo.session
        prayer_types = session.query(PrayerBookType).all()
        values = ["" ] + [pt.type_code for pt in prayer_types]
        # => ajouter une valeur vide en tête pour autoriser null

        ctk.CTkLabel(self.dynamic_frame, text="Prayer Book:").grid(row=2, column=0, sticky="w")
        self.var_mp = tk.StringVar(value="")  # valeur initiale = vide
        self.combo_mp = ctk.CTkComboBox(
            self.dynamic_frame,
            variable=self.var_mp,
            values=values,
            width=200
        )
        self.combo_mp.grid(row=2, column=1, columnspan=2, pady=5, sticky="w")

        # Psaume (champ texte libre)
        last_row = 3
        self.var_ps = tk.StringVar()
        ctk.CTkLabel(self.dynamic_frame, text="Psaume:").grid(row=last_row, column=0, sticky="w")
        ctk.CTkEntry(
            self.dynamic_frame,
            textvariable=self.var_ps
        ).grid(row=last_row, column=1, columnspan=3, pady=5, sticky="ew")


    def _render_family_fields(self):
        row = 0
        self.var_fr_reg = tk.StringVar()
        self.var_fr_app = tk.StringVar()
        self.var_fr_amt = tk.DoubleVar()
        self.var_fr_obs = tk.StringVar()

        ctk.CTkLabel(self.dynamic_frame, text="Date enreg. (YYYY-MM-DD):").grid(row=row, column=0, sticky="w")
        ctk.CTkEntry(self.dynamic_frame, textvariable=self.var_fr_reg).grid(row=row, column=1, pady=5, sticky="ew")
        row += 1

        ctk.CTkLabel(self.dynamic_frame, text="Date RDV (YYYY-MM-DD):").grid(row=row, column=0, sticky="w")
        ctk.CTkEntry(self.dynamic_frame, textvariable=self.var_fr_app).grid(row=row, column=1, pady=5, sticky="ew")
        row += 1

        ctk.CTkLabel(self.dynamic_frame, text="Montant payé:").grid(row=row, column=0, sticky="w")
        ctk.CTkEntry(self.dynamic_frame, textvariable=self.var_fr_amt).grid(row=row, column=1, pady=5, sticky="ew")
        row += 1

        ctk.CTkLabel(self.dynamic_frame, text="Observation:").grid(row=row, column=0, sticky="w")
        ctk.CTkEntry(self.dynamic_frame, textvariable=self.var_fr_obs).grid(row=row, column=1, pady=5, sticky="ew")


    def save(self):
        if not self.patient_id:
            messagebox.showerror("Erreur", "Chargez d'abord un patient")
            return

        data = {
            'patient_id': self.patient_id,
            'type_consultation': self.var_type.get(),
            'notes': self.txt_notes.get("0.0", "end").strip()
        }

        if self.var_type.get() == 'Spiritual':
            sel_generic = [k for k, v in self.chk_vars_generic.items() if v.get()]
            sel_med     = [k for k, v in self.chk_vars_med.items() if v.get()]

            # Récupérer la valeur du combobox ; "" -> None
            mp_raw = self.var_mp.get().strip()
            mp_value = mp_raw if mp_raw else None

            data.update({
                'presc_generic':       sel_generic       if sel_generic else None,
                'presc_med_spirituel': sel_med           if sel_med else None,
                'mp_type':             mp_value,   # chaîne ou None
                'psaume':              self.var_ps.get().strip() or None
            })
        else:
            data.update({
                'fr_registered_at': self.var_fr_reg.get().strip()    or None,
                'fr_appointment_at': self.var_fr_app.get().strip()   or None,
                'fr_amount_paid':    self.var_fr_amt.get(),
                'fr_observation':    self.var_fr_obs.get().strip()   or None
            })

        try:
            self.controller.create_consultation(data)
            messagebox.showinfo("Succès", "Consultation enregistrée")
            self.destroy()
            if self.on_save:
                self.on_save()

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Une erreur s'est produite :\n{e}")
