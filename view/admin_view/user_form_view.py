import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

class UserFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, user=None, on_save=None):
        super().__init__(master)
        self.controller = controller
        self.user       = user
        self.on_save    = on_save

        self.title("Ajouter un utilisateur" if not user else f"Éditer {user.username}")
        self.geometry("450x400")
        self.resizable(False, False)

        # Frame interne
        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=20, pady=20)
        frm.grid_columnconfigure(1, weight=1)

        # Définition des champs
        labels = [
            ("Username *",      'username'),
            ("Mot de passe *",  'password'),
            ("Nom complet *",   'full_name'),
            ("Rôle PG",         'postgres_role'),
            ("Actif",           'is_active'),
            ("Rôle appli.",     'role_id'),
            ("Spécialité",      'specialty_id'),
        ]
        self.vars = {}
        for i, (text, field) in enumerate(labels):
            ctk.CTkLabel(frm, text=text).grid(row=i, column=0, sticky="w", pady=5)
            if field == 'is_active':
                v = tk.BooleanVar(value=(user.is_active if user else True))
                w = ctk.CTkCheckBox(frm, variable=v, text="")
            elif field in ('role_id', 'specialty_id'):
                # controller.list_roles/specialties retourne objets avec name
                items = controller.list_roles() if field=='role_id' else controller.list_specialties()
                names = [getattr(x, 'role_name', None) or x.name for x in items]
                v = tk.StringVar()
                w = ttk.Combobox(frm, values=names, textvariable=v, state="readonly")
            elif field == 'password':
                v = tk.StringVar()
                w = ctk.CTkEntry(frm, show="*", textvariable=v)
            else:
                init = getattr(user, field, "") if user else ""
                v = tk.StringVar(value=init)
                w = ctk.CTkEntry(frm, textvariable=v)
            w.grid(row=i, column=1, sticky="ew", padx=(10,0), pady=5)
            self.vars[field] = v

        # Feedback
        self.lbl_fb = ctk.CTkLabel(frm, text="", text_color="green")
        self.lbl_fb.grid(row=len(labels), column=0, columnspan=2, pady=(10,0))

        # Bouton Enregistrer
        btn = ctk.CTkButton(frm, text="Enregistrer", command=self._on_save)
        btn.grid(row=len(labels)+1, column=0, columnspan=2, pady=20)

        # Pré-remplissage si édition
        if user:
            if getattr(user, 'application_role', None):
                self.vars['role_id'].set(user.application_role.role_name)
            if getattr(user, 'specialty', None):
                self.vars['specialty_id'].set(user.specialty.name)

    def _on_save(self):
        data = {
            'username':      self.vars['username'].get().strip(),
            'full_name':     self.vars['full_name'].get().strip(),
            'postgres_role': self.vars['postgres_role'].get().strip(),
            'is_active':     self.vars['is_active'].get(),
        }
        pwd = self.vars['password'].get().strip()
        if pwd or not self.user:
            data['password'] = pwd

        # Rôle appli
        role_name = self.vars['role_id'].get()
        if role_name:
            role = next(r for r in self.controller.list_roles()
                if r.role_name == role_name)
            data['role_id'] = role.role_id
            

        # Spécialité
        spec_name = self.vars['specialty_id'].get()
        if spec_name:
            spec = next(s for s in self.controller.list_specialties() if s.name == spec_name)
            data['specialty_id'] = spec.specialty_id

        # Création ou mise à jour
        if self.user:
            self.controller.update_user(self.user.user_id, data)
            msg = "Utilisateur mis à jour ✔️"
        else:
            self.controller.create_user(data)
            msg = "Utilisateur créé ✔️"

        self.lbl_fb.configure(text=msg)
        if callable(self.on_save):
            self.on_save()
        self.after(1500, self.destroy)
