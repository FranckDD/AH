import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

class NewEntryView(ctk.CTkFrame):
    def __init__(self, parent, controller, on_saved=None, patient_code=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.on_saved = on_saved
        self.patient_code = patient_code  # Code externe préchargé
        
        # Initialiser les attributs nécessaires avant de construire l'UI
        self.categories = {}
        self.all_exams = []
        self.filtered_exams = []
        self.param_vars = {}
        
        # Charger les examens
        self._load_exams()
        
        # Construire l'interface utilisateur
        self._build_ui()

    def _load_exams(self):
        """Charge les examens et les organise par catégorie"""
        exams = self.controller.list_examens()
        self.all_exams = exams
        self.filtered_exams = exams
        
        # Organiser les examens par catégorie
        self.categories = {}
        for e in exams:
            cat = e['categorie']
            self.categories.setdefault(cat, []).append(e)

    def _build_ui(self):
        frm = ctk.CTkFrame(self)
        frm.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Ajouter un champ pour le code patient
        ctk.CTkLabel(frm, text="Code Patient:").grid(row=0, column=0, sticky="w")
        self.code_var = tk.StringVar(value=self.patient_code or "")
        code_entry = ctk.CTkEntry(frm, textvariable=self.code_var, state="readonly")
        code_entry.grid(row=0, column=1, pady=5, sticky="ew")
        
        # Recherche
        ctk.CTkLabel(frm, text="Recherche examen:").grid(row=1, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(frm, textvariable=self.search_var)
        search_entry.grid(row=1, column=1, pady=5, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda e: self._filter_exams())

        # Catégorie
        ctk.CTkLabel(frm, text="Catégorie:").grid(row=2, column=0, sticky="w")
        cats = list(self.categories.keys()) if self.categories else []
        self.cat_var = tk.StringVar(value=cats[0] if cats else "")
        self.cat_menu = ctk.CTkOptionMenu(frm, values=cats, variable=self.cat_var,
                          command=lambda _: self._populate_exams())
        self.cat_menu.grid(row=2, column=1, pady=5, sticky="ew")
        
        # Examen
        ctk.CTkLabel(frm, text="Examen:").grid(row=3, column=0, sticky="w")
        self.exam_var = tk.StringVar()
        self.exam_menu = ctk.CTkOptionMenu(frm, values=[], variable=self.exam_var,
                                           command=lambda _: self._on_exam_change())
        self.exam_menu.grid(row=3, column=1, pady=5, sticky="ew")
        
        # Params container
        self.params_frame = ctk.CTkScrollableFrame(frm)
        self.params_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="nsew")
        frm.grid_columnconfigure(1, weight=1)
        
        # Save button
        ctk.CTkButton(frm, text="Enregistrer", command=self._save).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Initialisation des menus
        self._populate_exams()

    def _filter_exams(self):
        term = self.search_var.get().strip().lower()
        if term:
            self.filtered_exams = [e for e in self.all_exams if term in e['nom'].lower()]
        else:
            self.filtered_exams = self.all_exams
        
        # Mise à jour des catégories
        cats = sorted({e['categorie'] for e in self.filtered_exams})
        self.cat_var.set(cats[0] if cats else "")
        self.categories = {cat: [e for e in self.filtered_exams if e['categorie']==cat] for cat in cats}
        
        # Mettre à jour le menu des catégories
        self.cat_menu.configure(values=cats)
        
        # Mettre à jour les examens
        self._populate_exams()

    def _populate_exams(self):
        cat = self.cat_var.get()
        exams = self.categories.get(cat, [])
        names = [e['nom'] for e in exams]
        
        # Mettre à jour le menu des examens
        self.exam_menu.configure(values=names)
        
        if names:
            self.exam_var.set(names[0])
            self._on_exam_change()
        else:
            # Effacer les paramètres s'il n'y a pas d'examens
            for w in self.params_frame.winfo_children():
                w.destroy()

    def _on_exam_change(self):
        # Effacer les paramètres précédents
        for w in self.params_frame.winfo_children():
            w.destroy()
        
        # Trouver l'examen sélectionné
        selected = next((e for e in self.filtered_exams if e['nom'] == self.exam_var.get()), None)
        if not selected:
            return
        
        exam_id = selected['id']
        
        # Cas spécial pour la coprologie
        if selected.get('code') == 'COPRO':
            txt = ctk.CTkTextbox(self.params_frame, height=200)
            txt.pack(fill="both", expand=True)
            return
        
        # Charger les paramètres de l'examen
        params = self.controller.list_parametres_for_examen(exam_id)
        if not params:
            ctk.CTkLabel(self.params_frame, text="Aucun paramètre pour cet examen").pack(pady=10)
            return
        
        # Afficher les paramètres
        self.param_vars = {}
        for idx, p in enumerate(params):
            row_frame = ctk.CTkFrame(self.params_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(row_frame, text=p['nom_parametre'], width=150).pack(side="left", padx=5)
            var = tk.StringVar()
            self.param_vars[p['id']] = var
            ctk.CTkEntry(row_frame, textvariable=var).pack(side="right", fill="x", expand=True, padx=5)

    def _save(self):
        # Récupérer l'examen sélectionné
        selected = next((e for e in self.filtered_exams if e['nom'] == self.exam_var.get()), None)
        if not selected:
            messagebox.showerror("Erreur", "Veuillez sélectionner un examen")
            return
        
        exam_id = selected['id']
        details = []
        
        # Vérifier et collecter les valeurs des paramètres
        for param_id, var in self.param_vars.items():
            val = var.get().strip()
            if not val:
                messagebox.showerror("Erreur", "Tous les paramètres doivent être saisis")
                return
            
            try:
                # Essayer de convertir en numérique si possible
                num = float(val)
                details.append({
                    'parametre_id': param_id,
                    'valeur_text': val,
                    'valeur_num': num
                })
            except ValueError:
                # Si conversion échoue, stocker comme texte
                details.append({
                    'parametre_id': param_id,
                    'valeur_text': val
                })
        
        # Créer le résultat
        try:
            res = self.controller.create_result(
                patient_id=None,  # Patient externe
                examen_id=exam_id,
                details=details
            )
            messagebox.showinfo("Succès", f"Résultat créé: {res['code_lab_patient']}")
            
            # Appeler le callback de sauvegarde si défini
            if callable(self.on_saved):
                self.on_saved()
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création: {str(e)}")