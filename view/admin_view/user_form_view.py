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
        self.geometry("450x450")
        self.resizable(False, False)

        # Conteneurs pour validation
        self.containers = {}
        # Widgets pour mise à jour dynamique
        self.widgets    = {}
        # Variables
        self.vars       = {}

        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=20, pady=20)
        frm.grid_columnconfigure(1, weight=1)

        # 1) Username *
        self._add_row(frm, 0, "Username *", "username",
                      widget_type="entry",
                      initial=(user.username if user else ""))

        # 2) Mot de passe *
        self._add_row(frm, 1, "Mot de passe *", "password",
                      widget_type="entry", show="*")

        # 3) Nom complet *
        self._add_row(frm, 2, "Nom complet *", "full_name",
                      widget_type="entry",
                      initial=(user.full_name if user else ""))

        # 4) Rôle PG *
        pg_roles = ["app_admin","app_medical","app_secretaire","app_laborantin"]
        self._add_row(frm, 3, "Rôle PG *", "postgres_role",
                      widget_type="optionmenu",
                      values=pg_roles,
                      initial=(user.postgres_role if user else pg_roles[0]),
                      command=self._on_pg_change)

        # 5) Actif
        self._add_row(frm, 4, "Actif", "is_active",
                      widget_type="checkbox",
                      initial=(user.is_active if user else True))

        # 6) Rôle appli. *
        self._add_row(frm, 5, "Rôle appli. *", "role_id",
                      widget_type="optionmenu",
                      values=[])

        # 7) Spécialité (optionnelle)
        specs = [s.name for s in controller.list_specialties()]
        self._add_row(frm, 6, "Spécialité", "specialty_id",
                      widget_type="optionmenu",
                      values=specs)

        # Feedback & bouton
        self.lbl_fb = ctk.CTkLabel(frm, text="", text_color="green")
        self.lbl_fb.grid(row=7, column=0, columnspan=2, pady=(10,0))
        ctk.CTkButton(frm, text="Enregistrer", command=self._on_save)\
           .grid(row=8, column=0, columnspan=2, pady=20)

        # Pré-remplissage si édition
        if user:
            self.vars["role_id"].set(
                user.application_role.role_name
                if getattr(user, "application_role", None) else ""
            )
            if getattr(user, "specialty", None):
                self.vars["specialty_id"].set(user.specialty.name)

        # Initialisation du menu métier selon PG
        self._on_pg_change(self.vars["postgres_role"].get())

    def _add_row(self, frm, i, label, field, *,
                 widget_type, initial=None, values=None, show=None, command=None):
        # Label
        ctk.CTkLabel(frm, text=label).grid(row=i, column=0, sticky="w", pady=5)
        # Container transparent pour contour
        cont = ctk.CTkFrame(frm, fg_color="transparent", border_width=0)
        cont.grid(row=i, column=1, sticky="ew", padx=(10,0), pady=5)

        # Création du widget
        if widget_type == "entry":
            var = tk.StringVar(value=initial or "")
            w = ctk.CTkEntry(cont, textvariable=var, show=show or "")
        elif widget_type == "checkbox":
            var = tk.BooleanVar(value=initial)
            w = ctk.CTkCheckBox(cont, variable=var, text="")
        elif widget_type == "optionmenu":
            var = tk.StringVar(value=initial or "")
            w = ctk.CTkOptionMenu(
                cont,
                values=values or [],
                variable=var,
                command=command
            )
        else:
            raise ValueError(f"widget_type inconnu: {widget_type}")

        w.pack(fill="both", expand=True)

        # Mémorisation
        self.containers[field] = cont
        self.widgets[field]    = w
        self.vars[field]       = var

    def _on_pg_change(self, pg_role):
        # mapping postgres → métier
        mapping = {
            "app_admin":      ["admin"],
            "app_secretaire": ["secretaire"],
            "app_medical":    ["medecin", "nurse"],
            "app_laborantin": ["laborantin"]
        }
        choix = mapping.get(pg_role, [])
        om = self.widgets["role_id"]
        om.configure(values=choix)
        # si l'ancien n'existe plus, reset
        self.vars["role_id"].set(choix[0] if choix else "")

    def _on_save(self):
        # 1) Validation
        required = ["username","full_name","postgres_role","role_id"]
        missing = []
        for f in required:
            val = (self.vars[f].get().strip()
                   if isinstance(self.vars[f], tk.StringVar)
                   else self.vars[f].get())
            frm = self.containers[f]
            if not val:
                missing.append(f)
                frm.configure(border_width=2, border_color="red")
            else:
                frm.configure(border_width=0)

        # pwd obligatoire en création
        pwd = self.vars["password"].get().strip()
        frm_pwd = self.containers["password"]
        if not self.user and not pwd:
            missing.append("password")
            frm_pwd.configure(border_width=2, border_color="red")
        else:
            frm_pwd.configure(border_width=0)

        if missing:
            self.lbl_fb.configure(text="Veuillez remplir les champs *", text_color="red")
            return

        # 2) Prépare data
        data = {
            "username":      self.vars["username"].get().strip(),
            "full_name":     self.vars["full_name"].get().strip(),
            "postgres_role": self.vars["postgres_role"].get(),
            "is_active":     self.vars["is_active"].get(),
        }
        if pwd:
            data["password"] = pwd

        # rôle appli → lookup objet
        rn = self.vars["role_id"].get()
        role = next(r for r in self.controller.list_roles() if r.role_name==rn)
        data["role_id"] = role.role_id

        # spécialité
        if spec := self.vars["specialty_id"].get():
            s = next(s for s in self.controller.list_specialties() if s.name==spec)
            data["specialty_id"] = s.specialty_id

        # 3) Save
        if self.user:
            self.controller.update_user(self.user.user_id, data)
            msg = "Utilisateur mis à jour ✔️"
        else:
            self.controller.create_user(data)
            msg = "Utilisateur créé ✔️"

        self.lbl_fb.configure(text=msg, text_color="green")
        if callable(self.on_save):
            self.on_save()
        self.after(1500, self.destroy)