# view/laboviews/form_param_view.py

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import traceback

class ParamFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, exams: list, param: dict=None, on_save=None):
        super().__init__(master)
        self.title("Paramètre de Laboratoire" + (" [Édition]" if param else " [Nouveau]"))
        self.controller = controller
        self.on_save = on_save
        self.param = param
        self.exams = exams  # list of dicts {'id', 'nom', 'categorie'}

        frm = ctk.CTkFrame(self)
        frm.pack(padx=20, pady=20, fill="x")

        # Examen
        ctk.CTkLabel(frm, text="Examen:").grid(row=0, column=0, sticky="w")
        self.var_exam = tk.StringVar()
        self.mnu_exam = ctk.CTkOptionMenu(
            frm,
            values=[e['nom'] for e in exams],
            variable=self.var_exam
        )
        self.mnu_exam.grid(row=0, column=1, pady=5, sticky="ew")

        # Nom Paramètre
        ctk.CTkLabel(frm, text="Nom Paramètre:").grid(row=1, column=0, sticky="w")
        self.var_name = tk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.var_name).grid(row=1, column=1, pady=5, sticky="ew")

        # Unité
        ctk.CTkLabel(frm, text="Unité:").grid(row=2, column=0, sticky="w")
        self.var_unit = tk.StringVar()
        ctk.CTkEntry(frm, textvariable=self.var_unit).grid(row=2, column=1, pady=5, sticky="ew")

        # Type de valeur
        ctk.CTkLabel(frm, text="Type de valeur:").grid(row=3, column=0, sticky="w")
        self.var_type = tk.StringVar()
        ctk.CTkOptionMenu(
            frm,
            values=["numeric", "text", "boolean", "qualitatif"],
            variable=self.var_type
        ).grid(row=3, column=1, pady=5, sticky="ew")

        # Boutons
        btns = ctk.CTkFrame(self)
        btns.pack(fill="x", pady=(10,10))
        ctk.CTkButton(btns, text="Enregistrer", fg_color="green", command=self._save).pack(side="right", padx=5)
        ctk.CTkButton(btns, text="Annuler", fg_color="gray", command=self.destroy).pack(side="right")

        if param:
            self._load_param()

    def _load_param(self):
        # Remplir les champs à partir de self.param dict
        self.var_name.set(self.param.get('nom_parametre', ''))
        self.var_unit.set(self.param.get('unite', ''))
        self.var_type.set(self.param.get('type_valeur', ''))
        # Sélectionner l'examen correspondant
        for e in self.exams:
            if e['id'] == self.param.get('examen_id'):
                self.var_exam.set(e['nom'])
                break

    def _save(self):
        try:
            # Préparer les données à envoyer au controller
            selected_nom = self.var_exam.get()
            examen_id = next((e['id'] for e in self.exams if e['nom'] == selected_nom), None)
            data = {
                'examen_id': examen_id,
                'nom_parametre': self.var_name.get().strip(),
                'unite': self.var_unit.get().strip(),
                'type_valeur': self.var_type.get()
            }
            if self.param:
                # Mise à jour
                self.controller.update_param(self.param.get('id'), data)
                messagebox.showinfo("Succès", "Paramètre mis à jour")
            else:
                # Création
                self.controller.create_param(data)
                messagebox.showinfo("Succès", "Paramètre créé")
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erreur", str(e))
