import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

class ReferenceRangeFormView(ctk.CTkToplevel):
    def __init__(self, master, controller, reference=None, on_save=None):
        super().__init__(master)
        self.controller = controller
        self.reference = reference
        self.on_save = on_save
        self.title("Plage de Référence")
        self.geometry("400x400")
        self.resizable(False, False)

        # Paramètres disponibles (liste de dicts via controller)
        params = self.controller.list_params()
        # Map "id - nom" pour affichage et recherche
        self.param_map = {f"{p['id']} - {p['nom_parametre']}": p['id'] for p in params}
        param_keys = list(self.param_map.keys())

        # Variables en StringVar pour éviter TclError
        self.param_var = tk.StringVar(value=param_keys[0] if param_keys else "")
        self.sexe_var = tk.StringVar(value="M")
        self.age_min_var = tk.StringVar()
        self.age_max_var = tk.StringVar()
        self.val_min_var = tk.StringVar()
        self.val_max_var = tk.StringVar()

        # Pré-remplir si édition
        if reference:
            # selection du paramètre
            for key, pid in self.param_map.items():
                if pid == reference.get('parametre_id'):
                    self.param_var.set(key)
                    break
            self.sexe_var.set(reference.get('sexe', 'M'))
            self.age_min_var.set(str(reference.get('age_min', '')))
            self.age_max_var.set(str(reference.get('age_max', '')))
            self.val_min_var.set(str(reference.get('valeur_min', '')))
            self.val_max_var.set(str(reference.get('valeur_max', '')))

        # Construction UI
        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        # Ligne: Paramètre
        ctk.CTkLabel(frm, text="Paramètre:").grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkOptionMenu(frm, values=param_keys, variable=self.param_var).grid(row=0, column=1, pady=5)

        # Ligne: Sexe
        ctk.CTkLabel(frm, text="Sexe:").grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkOptionMenu(frm, values=["M","F","X"], variable=self.sexe_var).grid(row=1, column=1, pady=5)

        # Ligne: Age min
        ctk.CTkLabel(frm, text="Âge min:").grid(row=2, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frm, textvariable=self.age_min_var).grid(row=2, column=1, pady=5)

        # Ligne: Age max
        ctk.CTkLabel(frm, text="Âge max:").grid(row=3, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frm, textvariable=self.age_max_var).grid(row=3, column=1, pady=5)

        # Ligne: Valeur min
        ctk.CTkLabel(frm, text="Valeur min:").grid(row=4, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frm, textvariable=self.val_min_var).grid(row=4, column=1, pady=5)

        # Ligne: Valeur max
        ctk.CTkLabel(frm, text="Valeur max:").grid(row=5, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frm, textvariable=self.val_max_var).grid(row=5, column=1, pady=5)

        # Buttons en pied
        btn_frame = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(20,0))
        ctk.CTkButton(btn_frame, text="Enregistrer", fg_color="green", command=self._save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="red", command=self.destroy).pack(side="left", padx=10)

        self.grab_set()

    def _save(self):
        # Récupération et conversion
        try:
            pid = self.param_map[self.param_var.get()]
            sexe = self.sexe_var.get()
            age_min = int(self.age_min_var.get())
            age_max = int(self.age_max_var.get())
            val_min = float(self.val_min_var.get())
            val_max = float(self.val_max_var.get())
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir des valeurs numériques valides.")
            return

        # Validation métier
        if age_min < 0 or age_max < age_min:
            messagebox.showerror("Erreur", "Âge invalide : min ≤ max requis et positif.")
            return
        if val_min < 0 or val_max < val_min:
            messagebox.showerror("Erreur", "Valeurs invalides : min ≤ max requis et positif.")
            return

        payload = {
            'parametre_id': pid,
            'sexe': sexe,
            'age_min': age_min,
            'age_max': age_max,
            'valeur_min': val_min,
            'valeur_max': val_max
        }

        if self.reference:
            # Édition existante
            self.controller.update_reference_range(self.reference['id'], payload)
        else:
            # Création
            self.controller.create_reference_range(payload)

        if callable(self.on_save):
            self.on_save()
        self.destroy()
