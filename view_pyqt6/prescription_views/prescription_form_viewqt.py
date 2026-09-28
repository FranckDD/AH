from typing import Any, Dict, Optional, Callable
from datetime import date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QDateEdit, QMessageBox, QFormLayout, QSizePolicy, QSpacerItem,
    QGroupBox, QGridLayout, QFrame, QCheckBox, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon, QAction

from view_pyqt6.controller_resolver import ControllerResolver

# --- Styles CSS pour uniformiser l'apparence ---
STYLES = """
    QGroupBox {
        font-weight: bold;
        border: 1px solid #dcdcdc;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 10px;
        color: #34495e;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
    }
    QLineEdit, QDateEdit, QTextEdit, QListWidget {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 5px;
        background-color: #ffffff;
        selection-background-color: #3498db;
    }
    QLineEdit:focus, QDateEdit:focus, QTextEdit:focus, QListWidget:focus {
        border: 1px solid #3498db;
        background-color: #f0f8ff;
    }
    QListWidget::item {
        padding: 4px;
    }
    QListWidget::item:selected {
        background-color: #3498db;
        color: white;
    }
    QLabel {
        color: #2c3e50;
    }
"""

class PrescriptionFormView(QWidget):
    """
    Formulaire hybride pour création / édition de Prescriptions (Médicaments)
    OU de Bons d'examens (Laboratoire).
    """

    def __init__(
        self,
        parent,
        controllers: Any,
        current_user: Any,
        prescription_id: Optional[int] = None,
        patient_id: Optional[int] = None,
        medical_record_id: Optional[int] = None,
        on_save: Optional[Callable] = None
    ):
        super().__init__(parent)
        self.resolver = ControllerResolver(controllers)
        self.controller = self.resolver.prescription_controller()
        
        # Récupération optionnelle du contrôleur labo pour la liste des examens
        self.lab_ctrl = None
        try:
            self.lab_ctrl = self.resolver.lab_controller()
        except Exception:
            pass

        self.pat_ctrl = None
        try:
            self.pat_ctrl = self.resolver.patient_controller()
        except Exception:
            pass

        self.current_user = current_user
        self.prescription_id = prescription_id
        self.patient_id = patient_id
        self.medical_record_id = medical_record_id
        self.on_save = on_save
        self.is_new = prescription_id is None

        # --- Initialisation des Widgets ---
        self.code_edit = QLineEdit()
        self.patient_name_label = QLabel("Aucun patient sélectionné")
        self.medrec_edit = QLineEdit()
        
        # Switch Mode
        self.is_lab_check = QCheckBox("Ceci est un Bon d'Examen (Laboratoire)")
        
        # Mode Médicament
        self.medication_edit = QLineEdit()
        self.dosage_edit = QLineEdit()
        self.frequency_edit = QLineEdit()
        self.duration_edit = QLineEdit()
        
        # Mode Examen (Nouveau)
        self.exam_search = QLineEdit()
        self.exam_list = QListWidget()
        self.exam_summary = QTextEdit()

        # Commun
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.notes_text = QTextEdit()
        self.status_label = QLabel("")

        self._build_ui()
        self._setup_connections()

        # Logique de chargement
        self._load_exam_types() # Charger la liste des examens possibles (NFS, etc.)

        if not self.is_new:
            self._load()
        elif self.patient_id:
            self._prefill_patient_by_id(self.patient_id)
        
        # Initialiser l'état visuel (Médicament par défaut)
        self._on_mode_changed(self.is_lab_check.isChecked())

    def _build_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(STYLES)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- En-tête ---
        header_layout = QHBoxLayout()
        title_text = "Prescription / Bon d'Examen"
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        if not self.is_new:
            header_layout.addWidget(QLabel(f"#{self.prescription_id}"))
        main_layout.addLayout(header_layout)

        # --- Section 1 : Contexte Patient ---
        grp_patient = QGroupBox("Identification Patient")
        pat_layout = QGridLayout(grp_patient)
        
        self.code_edit.setPlaceholderText("Code...")
        self.medrec_edit.setPlaceholderText("ID Dossier (Optionnel)")
        
        # --- LOGIQUE REF DOSSIER ---
        if self.medical_record_id:
            self.medrec_edit.setText(str(self.medical_record_id))
            # On laisse activé au cas où l'utilisateur voudrait corriger manuellement,
            # ou vous pouvez mettre setEnabled(False) si c'est strict.
            # self.medrec_edit.setEnabled(False) 

        self.patient_name_label.setStyleSheet("color: #7f8c8d; font-style: italic;")

        pat_layout.addWidget(QLabel("Code Patient :"), 0, 0)
        pat_layout.addWidget(self.code_edit, 0, 1)
        pat_layout.addWidget(self.patient_name_label, 0, 2, 1, 2)
        pat_layout.addWidget(QLabel("Réf. Dossier :"), 1, 0)
        pat_layout.addWidget(self.medrec_edit, 1, 1)

        main_layout.addWidget(grp_patient)

        # --- Section 2 : Type de demande ---
        self.is_lab_check.setStyleSheet("font-weight: bold; color: #d35400; margin-left: 5px;")
        main_layout.addWidget(self.is_lab_check)

        # --- Section 3A : Mode Médicament (Group Box) ---
        self.grp_drugs = QGroupBox("Détails Médicament")
        drug_layout = QGridLayout(self.grp_drugs)
        
        self.medication_edit.setPlaceholderText("Nom du médicament (ex: Paracétamol)")
        drug_layout.addWidget(QLabel("Médicament* :"), 0, 0)
        drug_layout.addWidget(self.medication_edit, 0, 1, 1, 3)

        self.dosage_edit.setPlaceholderText("ex: 1000mg")
        self.frequency_edit.setPlaceholderText("ex: 3x / jour")
        
        drug_layout.addWidget(QLabel("Dosage :"), 1, 0)
        drug_layout.addWidget(self.dosage_edit, 1, 1)
        drug_layout.addWidget(QLabel("Fréquence :"), 1, 2)
        drug_layout.addWidget(self.frequency_edit, 1, 3)

        main_layout.addWidget(self.grp_drugs)

        # --- Section 3B : Mode Examen Labo (Group Box) ---
        self.grp_exams = QGroupBox("Sélection des Examens")
        self.grp_exams.setVisible(False) # Caché par défaut
        exam_layout = QVBoxLayout(self.grp_exams)

        # Recherche
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filtrer :"))
        self.exam_search.setPlaceholderText("Rechercher un examen...")
        search_layout.addWidget(self.exam_search)
        exam_layout.addLayout(search_layout)

        # Liste selection multiple
        self.exam_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.exam_list.setMaximumHeight(150)
        exam_layout.addWidget(self.exam_list)

        # Résumé textuel (Lecture seule pour vérification)
        exam_layout.addWidget(QLabel("Examens sélectionnés :"))
        self.exam_summary.setPlaceholderText("Les examens sélectionnés s'afficheront ici...")
        self.exam_summary.setMaximumHeight(50)
        self.exam_summary.setReadOnly(True)
        self.exam_summary.setStyleSheet("background-color: #ecf0f1; color: #2c3e50;")
        exam_layout.addWidget(self.exam_summary)

        main_layout.addWidget(self.grp_exams)

        # --- Section 4 : Planification ---
        grp_time = QGroupBox("Planification & Instructions")
        time_layout = QGridLayout(grp_time)

        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate())
        
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        
        self.duration_edit.setPlaceholderText("ex: 7 jours (Optionnel)")

        time_layout.addWidget(QLabel("Date :"), 0, 0)
        time_layout.addWidget(self.start_date, 0, 1)
        
        # Le champ date fin n'est pertinent que pour les médicaments, on peut le garder ou le cacher
        self.lbl_end_date = QLabel("Date Fin :")
        time_layout.addWidget(self.lbl_end_date, 0, 2)
        time_layout.addWidget(self.end_date, 0, 3)

        self.lbl_duration = QLabel("Durée :")
        time_layout.addWidget(self.lbl_duration, 1, 0)
        time_layout.addWidget(self.duration_edit, 1, 1)

        self.notes_text.setPlaceholderText("Instructions cliniques, contexte, renseignements cliniques...")
        self.notes_text.setMaximumHeight(60)
        time_layout.addWidget(QLabel("Notes :"), 2, 0)
        time_layout.addWidget(self.notes_text, 2, 1, 1, 3)

        main_layout.addWidget(grp_time)

        # --- Footer ---
        footer_layout = QHBoxLayout()
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self._close_form)
        
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px 15px; border-radius: 4px;")
        save_btn.setShortcut("Ctrl+S")

        footer_layout.addWidget(cancel_btn)
        footer_layout.addWidget(save_btn)
        main_layout.addLayout(footer_layout)

    def _setup_connections(self):
        # Toggle Mode
        self.is_lab_check.toggled.connect(self._on_mode_changed)
        
        # Patient Search
        self.code_edit.editingFinished.connect(self._on_code_focus_out)
        
        # Exam Filters
        self.exam_search.textChanged.connect(self._filter_exams)
        
        # Exam Selection Sync
        self.exam_list.itemSelectionChanged.connect(self._sync_exam_summary)

    # ---------------- Logique UI Dynamique ----------------

    def _on_mode_changed(self, is_lab: bool):
        """Affiche/Cache les sections selon le mode."""
        self.grp_drugs.setVisible(not is_lab)
        self.grp_exams.setVisible(is_lab)
        
        # On cache aussi la durée/date fin si c'est un examen (généralement one-shot)
        self.end_date.setVisible(not is_lab)
        self.lbl_end_date.setVisible(not is_lab)
        self.duration_edit.setVisible(not is_lab)
        self.lbl_duration.setVisible(not is_lab)

    def _load_exam_types(self):
        """
        Charge les types d'examens.
        Compatible avec votre LabController (clé='nom') et la liste de secours (str).
        """
        self.exam_list.clear()
        exams = []

        # ---------------------------------------------------------
        # 1. TENTATIVE DE RÉCUPÉRATION (Controller / Proxy)
        # ---------------------------------------------------------
        try:
            if self.lab_ctrl:
                # On essaie la méthode exacte de votre controller : list_examens
                if hasattr(self.lab_ctrl, 'list_examens'):
                    exams = self.lab_ctrl.list_examens()
                # Fallback sur d'autres noms courants
                elif hasattr(self.lab_ctrl, 'get_exam_types'):
                    exams = self.lab_ctrl.get_exam_types()
            else:
                pass

        except Exception as e:
            print(f"ERREUR CRITIQUE lors de la récupération : {e}")
            exams = [] # On force vide pour déclencher le plan B

        # ---------------------------------------------------------
        # 2. NORMALISATION (Gestion des formats API bizarres)
        # ---------------------------------------------------------
        # Si l'API renvoie { "data": [...] } au lieu de [...]
        if isinstance(exams, dict):
            if "data" in exams and isinstance(exams["data"], list):
                exams = exams["data"]
            elif "items" in exams and isinstance(exams["items"], list):
                exams = exams["items"]
            else:
                exams = [] # Format inconnu, on invalide

        if not isinstance(exams, list):
            exams = []

        # ---------------------------------------------------------
        # 3. LISTE DE SECOURS (Si vide ou erreur)
        # ---------------------------------------------------------
        if not exams:
            # print("⚠️ Liste vide ou erreur -> Utilisation de la liste de secours (Hardcoded)")
            exams = [
                "NFS (Numération Formule Sanguine)", 
                "Groupe Sanguin / Rhésus", 
                "Glycémie à jeun",
                "Hémoglobine Glyquée (HbA1c)", 
                "Créatinine", 
                "Urée", 
                "Widal et Félix", 
                "Goutte Epaisse (Palu)", 
                "CRP", 
                "Test de Grossesse (B-HCG)",
                "ECBU (Urines)",
                "Selles (Kyste et Oeufs)",
                "Prélèvement Vaginal (PV)"
            ]

        # ---------------------------------------------------------
        # 4. AFFICHAGE (Compatible Dict ET String)
        # ---------------------------------------------------------
        
        for item in exams:
            display_text = "Inconnu"
            user_data = None # Pour stocker l'objet complet si besoin

            try:
                # CAS A : C'est une simple chaîne (liste de secours)
                if isinstance(item, str):
                    display_text = item
                
                # CAS B : C'est un dictionnaire (venant de votre LabController)
                elif isinstance(item, dict):
                    # VOTRE CONTROLLER UTILISE LA CLÉ "nom"
                    display_text = item.get('nom') or item.get('name') or item.get('libelle') or "Examen sans nom"
                    user_data = item # On garde le dict complet (avec ID, prix...)

                # CAS C : Autre chose
                else:
                    display_text = str(item)

                # Création de l'item graphique
                list_item = QListWidgetItem(display_text)
                
                # (Optionnel) On cache les données brutes dans l'item pour usage futur
                if user_data:
                    list_item.setData(Qt.ItemDataRole.UserRole, user_data)

                self.exam_list.addItem(list_item)

            except Exception as loop_err:
                print(f"Erreur sur l'item {item} : {loop_err}")
                continue

    def _filter_exams(self, text):
        """Filtre la liste des examens."""
        for i in range(self.exam_list.count()):
            item = self.exam_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _sync_exam_summary(self):
        """Met à jour le champ texte résumé avec les sélections."""
        items = self.exam_list.selectedItems()
        txt = ", ".join([i.text() for i in items])
        self.exam_summary.setText(txt)

    # ---------------- Logique Patient (CORRECTION ID) ----------------

    def _on_code_focus_out(self):
        code = self.code_edit.text().strip()
        if not code: return

        self.status_label.setText("Recherche patient...")
        self.repaint()

        patient = None
        try:
            if self.pat_ctrl:
                if hasattr(self.pat_ctrl, "find_by_code"):
                    patient = self.pat_ctrl.find_by_code(code)
                elif hasattr(self.pat_ctrl, "get_patient_by_code"):
                    patient = self.pat_ctrl.get_patient_by_code(code)
        except Exception as e:
            print(f"Error finding patient: {e}")

        # --- CORRECTION MAJEURE ICI ---
        # Si le controller renvoie une liste (ex: [Patient]), on prend le premier
        if isinstance(patient, list):
            if len(patient) > 0:
                patient = patient[0]
            else:
                patient = None

        if patient:
            self._fill_patient_ui(patient)
            self.status_label.setText("")
        else:
            self.patient_id = None
            self.patient_name_label.setText("⚠️ Patient Introuvable")
            self.patient_name_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def _prefill_patient_by_id(self, pid: int):
        if not self.pat_ctrl: return
        try:
            p = self.pat_ctrl.get_patient(pid)
            if p: self._fill_patient_ui(p)
        except: pass

    def _fill_patient_ui(self, p):
        """
        Rplit les champs et SURTOUT récupère l'ID proprement.
        """
        # --- 1. Récupération robuste de l'ID ---
        extracted_id = None
        if isinstance(p, dict):
            extracted_id = p.get('id') or p.get('patient_id') or p.get('_id')
        else:
            # Si c'est un objet SQLAlchemy ou autre
            extracted_id = getattr(p, 'id', None) or getattr(p, 'patient_id', None)

        self.patient_id = extracted_id
        
        # Debug pour vérifier
        print(f"DEBUG: Patient chargé. ID trouvé = {self.patient_id}")

        # --- 2. Récupération des infos UI ---
        lname = p.get('last_name', '') if isinstance(p, dict) else getattr(p, 'last_name', '')
        fname = p.get('first_name', '') if isinstance(p, dict) else getattr(p, 'first_name', '')
        code = p.get('code_patient', '') if isinstance(p, dict) else getattr(p, 'code_patient', '')

        # Mise à jour UI
        self.code_edit.setText(str(code)) # Force string au cas où
        self.patient_name_label.setText(f"{lname} {fname}".upper())
        self.patient_name_label.setStyleSheet("color: #27ae60; font-weight: bold;")

    # ---------------- Sauvegarde (Create / Update) ----------------

    def _on_save(self):
        # Validation de base
        if not self.patient_id:
            self.status_label.setText("❌ Erreur: ID Patient manquant. Réessayez de saisir le code.")
            print("ERREUR: self.patient_id est None au moment du save.")
            return

        is_lab = self.is_lab_check.isChecked()
        
        # Validation spécifique
        if is_lab:
            if not self.exam_summary.toPlainText().strip():
                self.status_label.setText("❌ Aucun examen sélectionné.")
                return
        else:
            if not self.medication_edit.text().strip():
                self.status_label.setText("❌ Nom du médicament requis.")
                self.medication_edit.setFocus()
                return

        # Construction du payload
        # On utilise self.medrec_edit.text() pour respecter la logique du dossier
        ref_dossier = self.medrec_edit.text().strip()
        
        data = {
            "patient_id": int(self.patient_id), # On force le int par sécurité
            "medical_record_id": ref_dossier if ref_dossier else None,
            "start_date": self.start_date.date().toPyDate().isoformat(),
            "notes": self.notes_text.toPlainText().strip(),
            "is_lab_order": is_lab
        }

        if is_lab:
            # Mode Examen
            data["medication"] = "BON D'EXAMEN"
            data["dosage"] = "N/A"
            data["frequency"] = "N/A"
            data["duration"] = None
            data["end_date"] = None
            data["lab_exams"] = self.exam_summary.toPlainText().strip()
        else:
            # Mode Prescription
            data["medication"] = self.medication_edit.text().strip()
            data["dosage"] = self.dosage_edit.text().strip()
            data["frequency"] = self.frequency_edit.text().strip()
            data["duration"] = self.duration_edit.text().strip()
            ed = self.end_date.date()
            data["end_date"] = ed.toPyDate().isoformat() if ed.isValid() else None
            data["lab_exams"] = None

        try:
            self.status_label.setText("Enregistrement...")
            self.repaint()

            if self.is_new:
                res = self.controller.create_prescription(data)
            else:
                res = self.controller.update_prescription(self.prescription_id, data)

            # Gestion basique des erreurs retournées par l'API
            if res and isinstance(res, dict) and res.get("error"):
                self.status_label.setText(f"❌ Erreur: {res.get('message')}")
            else:
                # Succès
                msg = "Bon d'examen enregistré !" if is_lab else "Prescription enregistrée !"
                QMessageBox.information(self, "Succès", msg)
                if self.on_save: self.on_save()
                
                if self.is_new:
                    self._reset_form()
                else:
                    self._close_form()

        except Exception as e:
            QMessageBox.critical(self, "Erreur Technique", str(e))
            self.status_label.setText("❌ Erreur technique.")
            print(f"EXCEPTION SAVE: {e}")

    # ---------------- Chargement (Edit Mode) ----------------

    def _load(self):
        try:
            rec = self.controller.get_prescription(self.prescription_id)
            if not rec:
                self.status_label.setText("Impossible de charger la prescription.")
                return

            def _get(k): return rec.get(k) if isinstance(rec, dict) else getattr(rec, k, None)

            # Patient
            pat_data = _get("patient")
            if pat_data:
                self._fill_patient_ui(pat_data)
            else:
                pid = _get("patient_id")
                if pid: self._prefill_patient_by_id(pid)
            
            # --- LOGIQUE REF DOSSIER (Chargement) ---
            m_id = _get("medical_record_id")
            if m_id:
                self.medrec_edit.setText(str(m_id))

            # Mode (Labo vs Médicament)
            is_lab = bool(_get("is_lab_order"))
            self.is_lab_check.setChecked(is_lab)
            self._on_mode_changed(is_lab)

            # Dates & Notes
            self.notes_text.setPlainText(str(_get("notes") or ""))
            sd = str(_get("start_date"))[:10]
            if sd: self.start_date.setDate(QDate.fromString(sd, "yyyy-MM-dd"))
            
            if is_lab:
                # Charger les examens sélectionnés
                saved_exams_str = str(_get("lab_exams") or "")
                selected_labels = [s.strip() for s in saved_exams_str.split(',') if s.strip()]
                
                self.exam_list.blockSignals(True)
                for i in range(self.exam_list.count()):
                    item = self.exam_list.item(i)
                    if item.text() in selected_labels:
                        item.setSelected(True)
                self.exam_list.blockSignals(False)
                
                self.exam_summary.setText(saved_exams_str)

            else:
                # Charger les médicaments
                self.medication_edit.setText(str(_get("medication") or ""))
                self.dosage_edit.setText(str(_get("dosage") or ""))
                self.frequency_edit.setText(str(_get("frequency") or ""))
                self.duration_edit.setText(str(_get("duration") or ""))
                ed = str(_get("end_date"))[:10]
                if ed: self.end_date.setDate(QDate.fromString(ed, "yyyy-MM-dd"))

        except Exception as e:
            print(f"Erreur chargement prescription: {e}")
            QMessageBox.warning(self, "Erreur", "Données corrompues ou illisibles.")

    def _reset_form(self):
        self.medication_edit.clear()
        self.dosage_edit.clear()
        self.frequency_edit.clear()
        self.notes_text.clear()
        self.exam_list.clearSelection()
        self.exam_summary.clear()
        # On ne reset pas le patient ni le dossier si on enchaine les prescriptions pour le même patient
        # Si vous voulez reset le patient aussi, décommentez :
        # self.code_edit.clear()
        # self.patient_id = None
        # self.patient_name_label.setText("Aucun patient sélectionné")
        self.status_label.setText("✅ Prêt pour le suivant.")

    def _close_form(self):
        parent = self.parent()
        while parent and not hasattr(parent, "close"):
            parent = parent.parent()
        if parent: parent.close()
        else: self.close()