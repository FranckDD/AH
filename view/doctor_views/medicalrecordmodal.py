import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class MedicalRecordModal(ctk.CTkToplevel):
    def __init__(self, master, records=None, medrec_ctrl=None, patient_id=None, presc_ctrl=None, on_prescribe=None):
        super().__init__(master)
        self.title(f"Dossiers médicaux - Patient {patient_id}")
        self.geometry("1000x700")
        self.resizable(True, True)
        
        self.medrec_ctrl = medrec_ctrl
        self.presc_ctrl = presc_ctrl
        self.patient_id = patient_id
        self.on_prescribe = on_prescribe  # Fonction de callback pour prescription
        self.current_record = None
        
        # Configuration des polices
        self.title_font = ctk.CTkFont(size=16, weight="bold")
        self.label_font = ctk.CTkFont(size=12, weight="bold")
        self.text_font = ctk.CTkFont(size=12)
        
        # Centrer la fenêtre
        self.transient(master)
        self.grab_set()
        
        self._build_ui()
        self._load_records(records)
        
    def _build_ui(self):
        # Main container with two panels
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Records list
        left_frame = ctk.CTkFrame(main_paned)
        main_paned.add(left_frame, width=300)
        
        # Title for records list
        ctk.CTkLabel(left_frame, text="Historique des consultations", font=self.title_font).pack(pady=(10, 5))
        
        # Listbox for records
        list_frame = ctk.CTkFrame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.lst = tk.Listbox(list_frame, font=self.text_font)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.lst.yview)
        self.lst.configure(yscrollcommand=scrollbar.set)
        
        self.lst.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lst.bind("<<ListboxSelect>>", self.on_select_record)
        
        # Right panel - Details and actions
        right_frame = ctk.CTkFrame(main_paned)
        main_paned.add(right_frame, width=700)
        
        # Details section
        details_frame = ctk.CTkFrame(right_frame)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a notebook for tabs
        self.notebook = ttk.Notebook(details_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # View tab
        self.view_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.view_frame, text="Détails")
        
        # Text widget for details (read-only)
        self.txt = tk.Text(self.view_frame, wrap="word", state="disabled", font=self.text_font)
        scrollbar_txt = tk.Scrollbar(self.view_frame, orient=tk.VERTICAL, command=self.txt.yview)
        self.txt.configure(yscrollcommand=scrollbar_txt.set)
        
        self.txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_txt.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Edit tab
        self.edit_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.edit_frame, text="Modifier")
        
        # Form for editing
        form_frame = ctk.CTkScrollableFrame(self.edit_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Diagnosis field
        ctk.CTkLabel(form_frame, text="Diagnostic:", font=self.label_font).pack(anchor="w", pady=(10, 5))
        self.diagnosis_text = ctk.CTkTextbox(form_frame, height=100, font=self.text_font)
        self.diagnosis_text.pack(fill=tk.X, pady=(0, 10))
        
        # Notes field
        ctk.CTkLabel(form_frame, text="Notes:", font=self.label_font).pack(anchor="w", pady=(10, 5))
        self.notes_text = ctk.CTkTextbox(form_frame, height=150, font=self.text_font)
        self.notes_text.pack(fill=tk.X, pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(form_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ctk.CTkButton(buttons_frame, text="Mettre à jour", command=self.update_record).pack(side=tk.LEFT, padx=5)
        ctk.CTkButton(buttons_frame, text="Nouvelle prescription", command=self.create_prescription).pack(side=tk.LEFT, padx=5)
        
        # Bottom buttons
        bottom_frame = ctk.CTkFrame(right_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkButton(bottom_frame, text="Fermer", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def _load_records(self, records):
        self._records = []
        if records:
            self._records = records
            for r in records:
                label = self._rec_label(r)
                self.lst.insert(tk.END, label)
        else:
            # Try to load via medrec_ctrl if provided
            try:
                if self.medrec_ctrl and hasattr(self.medrec_ctrl, "list_records_for_patient"):
                    recs = self.medrec_ctrl.list_records_for_patient(self.patient_id) or []
                elif self.medrec_ctrl and hasattr(self.medrec_ctrl, "list_records"):
                    recs = self.medrec_ctrl.list_records(patient_id=self.patient_id, page=1, per_page=50) or []
                else:
                    recs = []
                self._records = recs
                for r in recs:
                    self.lst.insert(tk.END, self._rec_label(r))
            except Exception as e:
                self.lst.insert(tk.END, f"Erreur chargement dossiers: {e}")

    def _rec_label(self, r):
        if isinstance(r, dict):
            date_str = r.get('consultation_date', '')
            # Vérifier si c'est un objet datetime avant d'appeler strftime
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%d/%m/%Y %H:%M")
            elif not isinstance(date_str, str):
                date_str = str(date_str)
            return f"{date_str} — {r.get('diagnosis','') or r.get('motif_code','')}"
        else:
            date_ = getattr(r, "consultation_date", "") or getattr(r, "date", "")
            # Vérifier si c'est un objet datetime avant d'appeler strftime
            if isinstance(date_, datetime):
                date_ = date_.strftime("%d/%m/%Y %H:%M")
            diag = getattr(r, "diagnosis", "") or getattr(r, "motif_code", "")
            return f"{date_} — {diag}"

    def on_select_record(self, ev=None):
        sel = self.lst.curselection()
        if not sel:
            return
        
        self.current_record = self._records[sel[0]]
        
        # Enable text widget for editing
        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        
        # Display a clean summary (dict or ORM)
        if isinstance(self.current_record, dict):
            # Organize fields in a more readable way
            display_fields = [
                ("ID Dossier", "record_id"),
                ("Date Consultation", "consultation_date"),
                ("Code Patient", "patient_code"),
                ("ID Patient", "patient_id"),
                ("Nom Patient", "patient_name", lambda r: f"{r.get('first_name', '')} {r.get('last_name', '')}"),
                ("Statut Marital", "marital_status"),
                ("Tension", "bp"),
                ("Température", "temperature"),
                ("Poids", "weight"),
                ("Taille", "height"),
                ("Motif", "motif_code"),
                ("Antécédents", "medical_history"),
                ("Allergies", "allergies"),
                ("Symptômes", "symptoms"),
                ("Diagnostic", "diagnosis"),
                ("Traitement", "treatment"),
                ("Gravité", "severity"),
                ("Notes", "notes")
            ]
            
            for label, field, *transform in display_fields:
                if field in self.current_record:
                    value = self.current_record[field]
                    if transform:
                        value = transform[0](self.current_record)
                    
                    if value is not None:
                        if field == 'consultation_date' and isinstance(value, datetime):
                            value = value.strftime("%d/%m/%Y %H:%M")
                        self.txt.insert(tk.END, f"{label}: {value}\n\n")
        else:
            # Display useful attributes for ORM object
            fields = [
                ("ID Dossier", "record_id"),
                ("Date Consultation", "consultation_date"),
                ("Code Patient", "patient_code"),
                ("Nom Patient", "patient_name", lambda r: f"{getattr(r, 'first_name', '')} {getattr(r, 'last_name', '')}"),
                ("Statut Marital", "marital_status"),
                ("Tension", "bp"),
                ("Température", "temperature"),
                ("Poids", "weight"),
                ("Taille", "height"),
                ("Motif", "motif_code"),
                ("Antécédents", "medical_history"),
                ("Allergies", "allergies"),
                ("Symptômes", "symptoms"),
                ("Diagnostic", "diagnosis"),
                ("Traitement", "treatment"),
                ("Gravité", "severity"),
                ("Notes", "notes")
            ]
            
            for label, field, *transform in fields:
                if hasattr(self.current_record, field):
                    value = getattr(self.current_record, field, None)
                    if transform:
                        value = transform[0](self.current_record)
                    
                    if value is not None:
                        if field == "consultation_date" and isinstance(value, datetime):
                            value = value.strftime("%d/%m/%Y %H:%M")
                        self.txt.insert(tk.END, f"{label}: {value}\n\n")
        
        # Disable text widget for viewing
        self.txt.config(state="disabled")
        
        # Load data into edit fields
        if isinstance(self.current_record, dict):
            diagnosis = self.current_record.get('diagnosis', '')
            notes = self.current_record.get('notes', '')
        else:
            diagnosis = getattr(self.current_record, 'diagnosis', '')
            notes = getattr(self.current_record, 'notes', '')
            
        self.diagnosis_text.delete("1.0", tk.END)
        self.diagnosis_text.insert("1.0", diagnosis if diagnosis else "")
        
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", notes if notes else "")
        
        # Switch to view tab
        self.notebook.select(0)

    def update_record(self):
        if not self.current_record:
            messagebox.showwarning("Avertissement", "Veuillez sélectionner un dossier à modifier.")
            return
        
        new_diagnosis = self.diagnosis_text.get("1.0", tk.END).strip()
        new_notes = self.notes_text.get("1.0", tk.END).strip()
        
        try:
            if isinstance(self.current_record, dict):
                record_id = self.current_record.get('record_id')
                # Récupérer toutes les valeurs nécessaires pour éviter l'erreur
                update_data = {
                    'diagnosis': new_diagnosis,
                    'notes': new_notes,
                    'marital_status': self.current_record.get('marital_status'),
                    'bp': self.current_record.get('bp'),
                    'temperature': self.current_record.get('temperature'),
                    'weight': self.current_record.get('weight'),
                    'height': self.current_record.get('height'),
                    'medical_history': self.current_record.get('medical_history'),
                    'allergies': self.current_record.get('allergies'),
                    'symptoms': self.current_record.get('symptoms'),
                    'treatment': self.current_record.get('treatment'),
                    'severity': self.current_record.get('severity'),
                    'motif_code': self.current_record.get('motif_code')
                }
            else:
                record_id = getattr(self.current_record, 'record_id', None)
                # Récupérer toutes les valeurs nécessaires pour éviter l'erreur
                update_data = {
                    'diagnosis': new_diagnosis,
                    'notes': new_notes,
                    'marital_status': getattr(self.current_record, 'marital_status', None),
                    'bp': getattr(self.current_record, 'bp', None),
                    'temperature': getattr(self.current_record, 'temperature', None),
                    'weight': getattr(self.current_record, 'weight', None),
                    'height': getattr(self.current_record, 'height', None),
                    'medical_history': getattr(self.current_record, 'medical_history', None),
                    'allergies': getattr(self.current_record, 'allergies', None),
                    'symptoms': getattr(self.current_record, 'symptoms', None),
                    'treatment': getattr(self.current_record, 'treatment', None),
                    'severity': getattr(self.current_record, 'severity', None),
                    'motif_code': getattr(self.current_record, 'motif_code', None)
                }
            
            if record_id and self.medrec_ctrl and hasattr(self.medrec_ctrl, 'update_record'):
                success = self.medrec_ctrl.update_record(record_id, update_data)
                if success:
                    messagebox.showinfo("Succès", "Dossier médical mis à jour avec succès.")
                    
                    # Update the current record
                    if isinstance(self.current_record, dict):
                        self.current_record['diagnosis'] = new_diagnosis
                        self.current_record['notes'] = new_notes
                    else:
                        setattr(self.current_record, 'diagnosis', new_diagnosis)
                        setattr(self.current_record, 'notes', new_notes)
                        
                    # Refresh the view
                    self.on_select_record()
                else:
                    messagebox.showerror("Erreur", "Échec de la mise à jour du dossier.")
            else:
                messagebox.showerror("Erreur", "Impossible de mettre à jour le dossier.")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur s'est produite: {str(e)}")

    def create_prescription(self):
        if not self.current_record:
            messagebox.showwarning("Avertissement", "Veuillez sélectionner un dossier patient.")
            return
        
        # Get patient info for prescription
        patient_id = None
        medical_record_id = None
        
        if isinstance(self.current_record, dict):
            patient_id = self.current_record.get('patient_id', self.patient_id)
            medical_record_id = self.current_record.get('record_id')
        else:
            patient_id = getattr(self.current_record, 'patient_id', self.patient_id)
            medical_record_id = getattr(self.current_record, 'record_id', None)
        
        # Vérifier que les IDs nécessaires sont disponibles
        if not patient_id:
            messagebox.showerror("Erreur", "Impossible de déterminer l'ID du patient.")
            return
            
        if not medical_record_id:
            # Demander confirmation si pas d'ID de dossier médical
            if not messagebox.askyesno("Confirmation", 
                                    "Aucun dossier médical sélectionné. Voulez-vous quand même créer une prescription?"):
                return
        
        # Utiliser le callback pour ouvrir le formulaire de prescription existant
        if self.on_prescribe and callable(self.on_prescribe):
            self.on_prescribe(patient_id, medical_record_id)
        else:
            messagebox.showerror("Erreur", "Fonctionnalité de prescription non disponible.")