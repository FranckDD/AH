import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from tkinter import ttk

class PatientsEditView(ctk.CTkFrame):
    def __init__(self, parent, controller, patient_id=None, current_user=None):
        super().__init__(parent)
        # Determine current_user: explicit or via hierarchy
        self.current_user = current_user or self._find_current_user(parent)
        self.controller = controller
        self.patient_id = patient_id

        # Setup scrollable canvas
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        # Inner frame for content
        self.inner = ctk.CTkFrame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.inner_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.inner_window, width=e.width))

        # Layout in inner
        self.inner.grid_columnconfigure(1, weight=1)
        title = "Éditer un patient" if self.patient_id else "Ajouter un patient"
        ctk.CTkLabel(self.inner, text=title, font=(None, 20, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        labels = [
            ("Prénom", "first_name"), ("Nom", "last_name"),
            ("Date Naiss. (YYYY-MM-DD)", "birth_date"), ("Genre", "gender"),
            ("N° national", "national_id"), ("Téléphone", "contact_phone"),
            ("Assurance", "assurance"), ("Résidence", "residence"),
            ("Nom Père", "father_name"), ("Nom Mère", "mother_name"),
        ]
        self.entries = {}
        for idx, (lbl, key) in enumerate(labels, start=1):
            ctk.CTkLabel(self.inner, text=f"{lbl}:").grid(row=idx, column=0, padx=10, pady=5, sticky="e")
            if key == "gender":
                var = tk.StringVar(value="Autre")
                widget = ctk.CTkOptionMenu(self.inner, values=["Homme","Femme","Autre"], variable=var)
                widget.grid(row=idx, column=1, padx=10, pady=5, sticky="ew")
                self.entries[key] = var
            else:
                e = ctk.CTkEntry(self.inner, placeholder_text=lbl)
                e.grid(row=idx, column=1, padx=10, pady=5, sticky="ew")
                self.entries[key] = e

        # Buttons
        btn_frame = ctk.CTkFrame(self.inner)
        btn_frame.grid(row=len(labels)+1, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="Enregistrer", command=self._on_save).pack(side="left", padx=10)
        if self.patient_id:
            ctk.CTkButton(btn_frame, text="Supprimer", fg_color="#D32F2F", command=self._on_delete).pack(side="right", padx=10)

        # Load data if editing
        if self.patient_id:
            self._load_patient()

    def _find_current_user(self, widget):
        w = widget
        while w:
            cu = getattr(w, 'current_user', None)
            if cu:
                return cu
            w = getattr(w, 'master', None)
        return None

    def _load_patient(self):
        data = self.controller.get_patient(self.patient_id)
        if not data:
            return
        for key, widget in self.entries.items():
            val = data.get(key)
            if key == "birth_date" and val:
                val = val.strftime("%Y-%m-%d")
            if isinstance(widget, tk.StringVar):
                widget.set(val or "Autre")
            else:
                widget.delete(0, tk.END)
                widget.insert(0, val or "")

    def _collect_data(self):
        d = {}
        for key, widget in self.entries.items():
            d[key] = widget.get() if not isinstance(widget, tk.StringVar) else widget.get()
        try:
            d['birth_date'] = datetime.strptime(d['birth_date'], "%Y-%m-%d").date()
        except:
            d['birth_date'] = None
        return d

    def _on_save(self):
        data = self._collect_data()
        try:
            if self.patient_id:
                # update without passing current_user (controller handles user internally)
                self.controller.update_patient(self.patient_id, data)
            else:
                new = self.controller.create_patient(data)
                self.patient_id = getattr(new, 'patient_id', None) or new
        except Exception as e:
            print(f"Erreur lors de l'enregistrement : {e}")
            return
        # Fermer le popup et rafraîchir la liste
        popup = self.master
        try:
            popup.destroy()
            # rafraîchir la vue parente si possible
            parent_view = getattr(popup, 'master', None)
            if parent_view and hasattr(parent_view, 'refresh'):
                parent_view.refresh()
        except:
            pass

    def _on_delete(self):
        if self.patient_id:
            self.controller.delete_patient(self.patient_id)
        # Fermer le popup et rafraîchir la liste
        popup = self.master
        try:
            popup.destroy()
            parent_view = getattr(popup, 'master', None)
            if parent_view and hasattr(parent_view, 'refresh'):
                parent_view.refresh()
        except:
            pass
