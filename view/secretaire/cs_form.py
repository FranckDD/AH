# view/secretaire/cs_form.py

import tkinter as tk
import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import messagebox
from datetime import datetime
import traceback

class CSFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, patient_ctrl, consultation=None, on_save=None):
        """
        consultation : instance de ConsultationSpirituel (SQLAlchemy) si on édite, sinon None pour la création.
        on_save      : fonction callback à appeler après un create ou update réussi (généralement pour rafraîchir la liste).
        """
        super().__init__(master)
        self.title("Consultation Spirituelle" + (" [Édition]" if consultation else " [Nouveau]"))
        self.controller   = controller
        self.patient_ctrl = patient_ctrl
        self.on_save      = on_save
        self.patient_id   = None
        self.consultation = consultation

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

        # --- Frame dynamique (contiendra soit les champs Spiritual, soit les FamilyRestoration) ---
        self.dynamic_frame = ctk.CTkFrame(self)
        self.dynamic_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # --- Notes (communes aux deux types) ---
        ctk.CTkLabel(self, text="Notes:").pack(anchor="w", padx=20, pady=(5, 0))
        self.txt_notes = ctk.CTkTextbox(self, height=80)
        self.txt_notes.pack(padx=20, fill="x")

        # --- Bouton Enregistrer ---
        btn_save = ctk.CTkButton(self, text="Enregistrer", command=self.save)
        btn_save.pack(pady=10)

        # Initialisation de la partie dynamique selon le type actuel
        self.render_fields()

        # Si on édite, on préremplit tous les champs
        if self.consultation:
            self._load_consultation_into_form()

    def load_patient(self):
        """
        Charge le patient à partir du code saisi.
        Stocke l’ID dans self.patient_id pour l’inclure dans data au save().
        """
        code = self.var_code.get().strip()
        p = self.patient_ctrl.find_by_code(code)
        if not p:
            messagebox.showerror("Erreur", "Patient introuvable")
            return
        # p peut être un dict ou une instance SQLAlchemy; on récupère patient_id
        self.patient_id = p['patient_id'] if isinstance(p, dict) else p.patient_id

    def render_fields(self):
        """
        Reconstruit self.dynamic_frame en fonction du type de consultation sélectionné.
        """
        for w in self.dynamic_frame.winfo_children():
            w.destroy()

        if self.var_type.get() == "Spiritual":
            self._render_spiritual_fields()
        else:
            self._render_family_fields()

    def _render_spiritual_fields(self):
        # 1) Prescription générale (checkboxes)
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

        # 2) Médicaments spirituels (checkboxes)
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

        # 3) Combobox pour Prayer Book (on autorise une valeur vide)
        from models.prayer_book_type import PrayerBookType
        session = self.controller.repo.session
        prayer_types = session.query(PrayerBookType).all()
        values = [""] + [pt.type_code for pt in prayer_types]

        ctk.CTkLabel(self.dynamic_frame, text="Prayer Book:").grid(row=2, column=0, sticky="w")
        self.var_mp = tk.StringVar(value="")
        self.combo_mp = ctk.CTkComboBox(
            self.dynamic_frame,
            variable=self.var_mp,
            values=values,
            width=200
        )
        self.combo_mp.grid(row=2, column=1, columnspan=2, pady=5, sticky="w")

        # 4) Psaume (texte libre)
        last_row = 3
        self.var_ps = tk.StringVar()
        ctk.CTkLabel(self.dynamic_frame, text="Psaume:").grid(row=last_row, column=0, sticky="w")
        ctk.CTkEntry(
            self.dynamic_frame,
            textvariable=self.var_ps
        ).grid(row=last_row, column=1, columnspan=3, pady=5, sticky="ew")

    def _render_family_fields(self):
        # Champs pour FamilyRestoration : date inscription, date RDV, montant, observation
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

    def _load_consultation_into_form(self):
        """
        Préremplit tous les widgets à partir de self.consultation (instance SQLAlchemy).
        """
        cs = self.consultation

        # 1) Charger le code patient + patient_id
        if hasattr(cs, 'patient') and cs.patient:
            code = getattr(cs.patient, 'code_patient', "")
            self.var_code.set(code)
            self.patient_id = cs.patient_id

        # 2) Type de consultation -> re-render des champs
        if cs.type_consultation:
            self.var_type.set(cs.type_consultation)
            self.render_fields()
        else:
            self.var_type.set("Spiritual")
            self.render_fields()

        # 3) Notes
        self.txt_notes.delete("0.0", "end")
        if getattr(cs, 'notes', None):
            self.txt_notes.insert("0.0", cs.notes)

        # 4) Champs spécifiques
        if cs.type_consultation == "Spiritual":
            # presc_generic
            if cs.presc_generic:
                for label in cs.presc_generic:
                    if label in self.chk_vars_generic:
                        self.chk_vars_generic[label].set(True)
            # presc_med_spirituel
            if cs.presc_med_spirituel:
                for label in cs.presc_med_spirituel:
                    if label in self.chk_vars_med:
                        self.chk_vars_med[label].set(True)
            # mp_type
            if getattr(cs, 'mp_type', None):
                self.var_mp.set(cs.mp_type)
            else:
                self.var_mp.set("")
            # psaume
            if getattr(cs, 'psaume', None):
                self.var_ps.set(cs.psaume)
            else:
                self.var_ps.set("")
        else:
            # FamilyRestoration
            if getattr(cs, 'fr_registered_at', None):
                self.var_fr_reg.set(cs.fr_registered_at.strftime("%Y-%m-%d"))
            if getattr(cs, 'fr_appointment_at', None):
                self.var_fr_app.set(cs.fr_appointment_at.strftime("%Y-%m-%d"))
            if getattr(cs, 'fr_amount_paid', None) is not None:
                self.var_fr_amt.set(float(cs.fr_amount_paid))
            if getattr(cs, 'fr_observation', None):
                self.var_fr_obs.set(cs.fr_observation)

    def save(self):
        """
        Construit le dict data, puis appelle create_consultation ou update_consultation.
        Gère le rollback en cas d'exception, et ferme la fenêtre si tout est OK.
        """
        # 0) Vérifier que l’on a bien chargé un patient
        if not self.patient_id:
            messagebox.showerror("Erreur", "Chargez d'abord un patient")
            return

        # 1) Champs communs
        data = {
            'patient_id':        self.patient_id,
            'type_consultation': self.var_type.get(),
            'notes':             self.txt_notes.get("0.0", "end").strip() or None
        }

        # 2) Champs selon le type
        if self.var_type.get() == 'Spiritual':
            # 2.a) presc_generic
            sel_generic = [k for k, v in self.chk_vars_generic.items() if v.get()]
            data['presc_generic'] = sel_generic if sel_generic else None

            # 2.b) presc_med_spirituel
            sel_med = [k for k, v in self.chk_vars_med.items() if v.get()]
            data['presc_med_spirituel'] = sel_med if sel_med else None

            # 2.c) mp_type (combobox)
            mp_raw = self.var_mp.get().strip()
            data['mp_type'] = mp_raw if mp_raw else None

            # 2.d) psaume
            data['psaume'] = self.var_ps.get().strip() or None

        else:  # FamilyRestoration
            reg_str = self.var_fr_reg.get().strip()
            app_str = self.var_fr_app.get().strip()
            try:
                data['fr_registered_at']  = datetime.strptime(reg_str, "%Y-%m-%d") if reg_str else None
                data['fr_appointment_at'] = datetime.strptime(app_str, "%Y-%m-%d") if app_str else None
            except Exception as e:
                messagebox.showerror("Erreur", f"Format date invalide :\n{e}")
                return

            amt = self.var_fr_amt.get()
            data['fr_amount_paid'] = float(amt) if amt is not None else None
            data['fr_observation'] = self.var_fr_obs.get().strip() or None

        # 3) Appel create ou update en gérant rollback
        try:
            if self.consultation:
                # Édition
                self.controller.update_consultation(self.consultation.consultation_id, data)
                messagebox.showinfo("Succès", "Consultation mise à jour")
            else:
                # Création
                self.controller.create_consultation(data)
                messagebox.showinfo("Succès", "Consultation créée")

        except Exception as e:
            traceback.print_exc()
            try:
                self.controller.repo.session.rollback()
            except Exception:
                pass
            messagebox.showerror("Erreur SQL/BDD", str(e))
            return

        # 4) Callback on_save + fermeture
        if self.on_save:
            self.on_save()
        self.destroy()
