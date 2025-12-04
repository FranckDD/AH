import logging
import traceback
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QCheckBox, QTextEdit, 
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFrame, QGroupBox,
    QHeaderView, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QCursor 

from view_pyqt6.controller_resolver import ControllerResolver
# Assurez-vous que ce chemin est correct pour votre projet
# from view_pyqt6.secretaire.transaction_viewpyqt6 import AddItemDialog 

logger = logging.getLogger(__name__)

# --- CLASSE UTILITAIRE POUR LE PAIEMENT (Unique définition) ---
# Cette classe sera importée par transaction_details_dialog.py
class PaymentDialog(QDialog):
    def __init__(self, parent=None, remaining_amount=0.0):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un Paiement")
        self.resize(350, 200)
        layout = QVBoxLayout(self)

        # Info Reste à payer
        layout.addWidget(QLabel(f"<b>Reste à payer actuel : {remaining_amount:,.2f} CFA</b>"))
        
        layout.addSpacing(10)

        # Champ Montant
        layout.addWidget(QLabel("Montant versé :"))
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Ex: 5000")
        # On valide pour que ce soit un float positif, max le reste à payer (avec une marge float)
        self.amount_input.setValidator(QDoubleValidator(0.0, remaining_amount + 1.0, 2))
        self.amount_input.setText(str(remaining_amount)) # Par défaut, on propose de solder
        layout.addWidget(self.amount_input)

        # Champ Méthode
        layout.addWidget(QLabel("Mode de paiement :"))
        self.combo_method = QComboBox()
        self.combo_method.addItems(["Espèces", "Orange Money", "MTN Money", "Carte", "Chèque", "Virement"])
        layout.addWidget(self.combo_method)

        # Boutons
        layout.addSpacing(10)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Valider le paiement")
        btn_ok.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        try:
            val = float(self.amount_input.text().replace(',', '.') or 0)
        except ValueError:
            val = 0.0
        return {
            "paid_amount": val,
            "payment_method": self.combo_method.currentText()
        }

# --- VUE PRINCIPALE ---
class CaisseFormView(QDialog):
    def __init__(
        self,
        parent,
        controllers, 
        patient_ctrl=None,
        pharmacy_ctrl=None,
        consultation_spirituel_ctrl=None,
        medical_record_ctrl=None,
        on_save=None,
        transaction=None,
        locale: str = "fr"
    ):
        super().__init__(parent)

        self.resolver = ControllerResolver(controllers)
        
        # Résolution du contrôleur principal (Caisse)
        if hasattr(controllers, "create_transaction"): 
            self.controller = controllers
        else:
            self.controller = getattr(controllers, "caisse_controller", None) or controllers

        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl
        self.on_save = on_save
        self.transaction = transaction
        self.locale = locale
        
        self.patient_id = None
        self.items = []  # Liste de dicts

        self.texts = {
            "fr": {
                "title_new": "Transaction Caisse [Nouveau]",
                "title_edit": "Transaction Caisse [Édition & Paiement]",
                "patient_code": "Code patient :",
                "load": "Charger",
                "date": "Date/Heure :",
                "advance": "Total Payé (CFA) :", 
                "type": "Type transac. :",
                "payment": "Mode paiement (Initial) :",
                "note": "Note :",
                "lines": "Lignes :",
                "add_line": "Ajouter ligne",
                "del_line": "Supprimer ligne",
                "total": "Montant total :",
                "remaining": "Reste à payer :",
                "save": "Enregistrer",
                "cancel": "Fermer",
                "add_payment": "Ajouter un Paiement",
                "err_patient": "Patient introuvable.",
                "err_no_type": "Sélectionnez au moins un type de transaction.",
                "err_advance": "Montant invalide.",
                "err_advance_req": "Vous devez renseigner un code patient si vous faites une avance.",
                "err_no_lines": "Ajoutez au moins une ligne.",
                "success_save": "Transaction enregistrée avec succès.",
                "success_update": "Transaction mise à jour.",
                "error": "Erreur",
                "types": {
                    "cons": "Consultation", "med": "Vente Médicament", "book": "Vente Carnet", 
                    "hosp": "Hospitalisation", "exam": "Examens"
                },
                "pay_methods": ["Espèces", "Carte", "Chèque", "Virement", "Orange Money", "MTN Money"]
            },
            "en": {
                "title_new": "Cash Transaction [New]",
                "title_edit": "Cash Transaction [Edit & Payment]",
                "patient_code": "Patient code:",
                "load": "Load",
                "date": "Date/Time:",
                "advance": "Total Paid (CFA):",
                "type": "Trans. type:",
                "payment": "Payment method (Initial):",
                "note": "Note:",
                "lines": "Lines:",
                "add_line": "Add Line",
                "del_line": "Remove Line",
                "total": "Total amount:",
                "remaining": "Remaining Due:",
                "save": "Save",
                "cancel": "Close",
                "add_payment": "Add Payment",
                "err_patient": "Patient not found.",
                "err_no_type": "Select at least one transaction type.",
                "err_advance": "Invalid amount.",
                "err_advance_req": "You must provide a patient code if there is an advance.",
                "err_no_lines": "Please add at least one line.",
                "success_save": "Transaction saved.",
                "success_update": "Transaction updated.",
                "error": "Error",
                "types": {
                    "cons": "Consultation", "med": "Sale Medication", "book": "Sale Booklet", 
                    "hosp": "Hospitalization", "exam": "Exams"
                },
                "pay_methods": ["Cash", "Card", "Check", "Transfer", "Orange Money", "MTN Money"]
            }
        }

        self.setWindowTitle(self.texts[self.locale]["title_edit"] if self.transaction else self.texts[self.locale]["title_new"])
        self.resize(950, 750)
        self._setup_ui()
        
        if self.transaction:
            self._load_transaction_into_form()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- 1. Top Frame (Patient info & Meta) ---
        top_group = QGroupBox("Informations Générales")
        top_layout = QGridLayout(top_group)
        top_layout.setSpacing(10)
        
        # Code Patient
        top_layout.addWidget(QLabel(self.texts[self.locale]["patient_code"]), 0, 0)
        self.entry_code = QLineEdit()
        self.entry_code.setPlaceholderText("ex: P-12345")
        self.entry_code.returnPressed.connect(self._load_patient)
        top_layout.addWidget(self.entry_code, 0, 1)
        
        btn_load = QPushButton(self.texts[self.locale]["load"])
        btn_load.clicked.connect(self._load_patient)
        top_layout.addWidget(btn_load, 0, 2)
        
        # Label Info Patient
        self.lbl_patient_info = QLabel("")
        self.lbl_patient_info.setStyleSheet("color: #2e7d32; font-weight: bold;")
        top_layout.addWidget(self.lbl_patient_info, 1, 0, 1, 3)
        
        # Date (Readonly)
        top_layout.addWidget(QLabel(self.texts[self.locale]["date"]), 2, 0)
        self.entry_date = QLineEdit(datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.entry_date.setReadOnly(True)
        self.entry_date.setStyleSheet("background-color: #f0f0f0; color: #555;")
        top_layout.addWidget(self.entry_date, 2, 1, 1, 2)
        
        # Avance / Total Payé
        top_layout.addWidget(QLabel(self.texts[self.locale]["advance"]), 3, 0)
        self.entry_advance = QLineEdit("0.00")
        self.entry_advance.setValidator(QDoubleValidator(0.0, 999999999.0, 2))
        
        # CONNEXION SIGNAL POUR MAJ DYNAMIQUE DU RESTE A PAYER
        self.entry_advance.textChanged.connect(self._on_advance_changed)
        
        # En mode édition, ce champ sera désactivé par _load_transaction_into_form
        top_layout.addWidget(self.entry_advance, 3, 1, 1, 2)
        
        layout.addWidget(top_group)
        
        # --- 2. Types de transaction ---
        type_group = QGroupBox(self.texts[self.locale]["type"])
        type_layout = QHBoxLayout(type_group)
        
        self.chk_consult = QCheckBox(self.texts[self.locale]["types"]["cons"])
        self.chk_med = QCheckBox(self.texts[self.locale]["types"]["med"])
        self.chk_booklet = QCheckBox(self.texts[self.locale]["types"]["book"])
        self.chk_hosp = QCheckBox(self.texts[self.locale]["types"]["hosp"])
        self.chk_exam = QCheckBox(self.texts[self.locale]["types"]["exam"])
        
        for chk in [self.chk_consult, self.chk_med, self.chk_booklet, self.chk_hosp, self.chk_exam]:
            type_layout.addWidget(chk)
            
        layout.addWidget(type_group)
        
        # --- 3. Paiement & Note ---
        mid_layout = QHBoxLayout()
        
        # Paiement
        pay_layout = QVBoxLayout()
        pay_layout.addWidget(QLabel(self.texts[self.locale]["payment"]))
        self.combo_payment = QComboBox()
        self.combo_payment.addItems(self.texts[self.locale]["pay_methods"])
        pay_layout.addWidget(self.combo_payment)
        mid_layout.addLayout(pay_layout)
        
        # Note
        note_layout = QVBoxLayout()
        note_layout.addWidget(QLabel(self.texts[self.locale]["note"]))
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(60)
        note_layout.addWidget(self.txt_note)
        mid_layout.addLayout(note_layout, stretch=2)
        
        layout.addLayout(mid_layout)
        
        # --- 4. Lignes (TreeWidget) ---
        layout.addWidget(QLabel(self.texts[self.locale]["lines"]))
        
        self.tree_items = QTreeWidget()
        cols = ["Type", "Réf. ID", "Quantité", "Prix Unitaire", "Total", "Note"]
        self.tree_items.setHeaderLabels(cols)
        self.tree_items.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tree_items.header().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree_items)
        
        # Boutons Lignes
        line_btn_layout = QHBoxLayout()
        btn_add_line = QPushButton(self.texts[self.locale]["add_line"])
        btn_add_line.clicked.connect(self._add_line)
        line_btn_layout.addWidget(btn_add_line)
        
        btn_del_line = QPushButton(self.texts[self.locale]["del_line"])
        btn_del_line.setStyleSheet("background-color: #d32f2f; color: white;")
        btn_del_line.clicked.connect(self._remove_selected_line)
        line_btn_layout.addWidget(btn_del_line)
        line_btn_layout.addStretch()
        
        layout.addLayout(line_btn_layout)
        
        # --- 5. Footer (Total, Reste & Actions) ---
        footer_frame = QFrame()
        footer_frame.setStyleSheet("background-color: #e9ecef; border-radius: 5px; padding: 5px;")
        footer_layout = QHBoxLayout(footer_frame)
        
        # Total Facture
        footer_layout.addWidget(QLabel(self.texts[self.locale]["total"]))
        self.lbl_total_amount = QLabel("0.00")
        self.lbl_total_amount.setStyleSheet("font-size: 16px; font-weight: bold; color: #2e7d32;")
        footer_layout.addWidget(self.lbl_total_amount)
        
        # Espacement
        footer_layout.addSpacing(20)

        # Reste à payer (Nouveau)
        footer_layout.addWidget(QLabel(self.texts[self.locale]["remaining"]))
        self.lbl_remaining = QLabel("0.00")
        self.lbl_remaining.setStyleSheet("font-size: 16px; font-weight: bold; color: #d32f2f;")
        footer_layout.addWidget(self.lbl_remaining)

        footer_layout.addStretch()
        
        layout.addWidget(footer_frame)
        
        action_layout = QHBoxLayout()

        # Bouton Ajouter un paiement (Visible seulement en mode édition)
        self.btn_add_payment = QPushButton(self.texts[self.locale]["add_payment"])
        self.btn_add_payment.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 8px;")
        self.btn_add_payment.clicked.connect(self._open_payment_dialog)
        self.btn_add_payment.setVisible(False) # Caché par défaut
        action_layout.addWidget(self.btn_add_payment)

        action_layout.addStretch()

        btn_save = QPushButton(self.texts[self.locale]["save"])
        btn_save.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        btn_save.clicked.connect(self._on_save)
        
        btn_cancel = QPushButton(self.texts[self.locale]["cancel"])
        btn_cancel.setStyleSheet("background-color: #6c757d; color: white; padding: 8px;")
        btn_cancel.clicked.connect(self.reject)
        
        action_layout.addWidget(btn_save)
        action_layout.addWidget(btn_cancel)
        
        layout.addLayout(action_layout)

    def _load_patient(self):
        code = self.entry_code.text().strip()
        if not code:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # Recherche Patient
            if hasattr(self.patient_ctrl, 'find_by_code'):
                patient = self.patient_ctrl.find_by_code(code)
            elif hasattr(self.patient_ctrl, 'find_patient_by_code'):
                patient = self.patient_ctrl.find_patient_by_code(code)
            else:
                patient = None

            if not patient:
                self.lbl_patient_info.setText("")
                self.lbl_patient_info.setStyleSheet("color: red;")
                QMessageBox.critical(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_patient"])
                return

            # Récup ID et Nom
            if isinstance(patient, dict):
                self.patient_id = patient.get("patient_id")
                fname = patient.get("first_name", "")
                lname = patient.get("last_name", "")
            else:
                self.patient_id = getattr(patient, "patient_id", None)
                fname = getattr(patient, "first_name", "")
                lname = getattr(patient, "last_name", "")
            
            patient_name = f"{fname} {lname}".strip()

            # Recherche Dernière Consultation (Logique existante)
            last_consult_id = "0"
            last_consult_date = None

            if self.consultation_spirituel_ctrl:
                try:
                    cs = self.consultation_spirituel_ctrl.get_last_for_patient(self.patient_id)
                    if cs:
                        cid = cs.get("consultation_id") if isinstance(cs, dict) else cs.consultation_id
                        cdate = cs.get("date") if isinstance(cs, dict) else cs.date
                        last_consult_id = cid
                        last_consult_date = cdate
                except Exception:
                    pass

            if self.medical_record_ctrl:
                try:
                    mr = self.medical_record_ctrl.get_last_for_patient(self.patient_id)
                    if mr:
                        mid = mr.get("consultation_id") if isinstance(mr, dict) else mr.consultation_id
                        mdate = mr.get("date") if isinstance(mr, dict) else mr.date
                        
                        use_med = False
                        if last_consult_date is None:
                            use_med = True
                        elif mdate and str(mdate) > str(last_consult_date):
                            use_med = True
                            
                        if use_med:
                            last_consult_id = mid
                except Exception:
                    pass

            lbl_text = f"Patient : {patient_name}  |  Dernière Consultation : {last_consult_id}"
            self.lbl_patient_info.setText(lbl_text)
            self.lbl_patient_info.setStyleSheet("color: #2e7d32; font-weight: bold;")
            
        except Exception as e:
            logger.error(f"Erreur load patient: {e}")
            QMessageBox.warning(self, "Erreur", str(e))
        finally:
            QApplication.restoreOverrideCursor()

    def _add_line(self):
        types_map = self.texts[self.locale]["types"]
        allowed = []

        if self.chk_consult.isChecked(): allowed.append(types_map["cons"])
        if self.chk_med.isChecked(): allowed.append(types_map["med"])
        if self.chk_booklet.isChecked(): allowed.append(types_map["book"])
        if self.chk_hosp.isChecked(): allowed.append(types_map["hosp"])
        if self.chk_exam.isChecked(): allowed.append(types_map["exam"])

        if not allowed:
            QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_no_type"])
            return

        def on_item_confirm(item_dict):
            self.items.append(item_dict)
            self._refresh_items()
            self._update_total()

        # Résolution du lab controller
        lab_ctrl = None
        try:
            lab_ctrl = self.resolver.lab_controller()
        except Exception:
            if hasattr(self.controller, "gateway"):
                 from view_pyqt6.api_controller import ApiControllerProxy
                 lab_ctrl = ApiControllerProxy(self.controller.gateway)

        from view_pyqt6.secretaire.transaction_viewpyqt6 import AddItemDialog
        
        dlg = AddItemDialog(
            parent=self,
            on_confirm=on_item_confirm,
            allowed_types=allowed,
            patient_id=self.patient_id,
            pharmacy_ctrl=self.pharmacy_ctrl or self.resolver.pharmacy_controller(),
            medical_record_ctrl=self.medical_record_ctrl or self.resolver.medical_record_controller(),
            consultation_spirituel_ctrl=self.consultation_spirituel_ctrl or self.resolver.consultation_spirituel_controller(),
            lab_controller=lab_ctrl,
            locale=self.locale
        )
        dlg.exec()

    def _remove_selected_line(self):
        item = self.tree_items.currentItem()
        if not item: return
        idx = self.tree_items.indexOfTopLevelItem(item)
        if idx >= 0:
            del self.items[idx]
            self._refresh_items()
            self._update_total()

    def _refresh_items(self):
        self.tree_items.clear()
        for item in self.items:
            row = QTreeWidgetItem([
                str(item.get("item_type", "")),
                str(item.get("item_ref_id", "")),
                str(item.get("quantity", 0)),
                f"{float(item.get('unit_price', 0)):.2f}",
                f"{float(item.get('line_total', 0)):.2f}",
                str(item.get("note", ""))
            ])
            self.tree_items.addTopLevelItem(row)

    def _on_advance_changed(self, text):
        """Met à jour le reste à payer quand on modifie le montant versé"""
        try:
            # On récupère le total (label)
            total_text = self.lbl_total_amount.text().replace(',', '.')
            if not total_text: total = 0.0
            else: total = float(total_text)
            
            # On parse ce que l'utilisateur tape
            val_text = text.replace(',', '.')
            if not val_text: val_text = "0"
            paid = float(val_text)
        except ValueError:
            paid = 0.0
            total = 0.0
            
        remaining = max(0, total - paid)
        
        # Affichage visuel : Si reste > 0, on met en rouge pour alerter
        self.lbl_remaining.setText(f"{remaining:.2f}")
        if remaining > 0:
            self.lbl_remaining.setStyleSheet("font-size: 16px; font-weight: bold; color: #d32f2f;") # Rouge
        else:
            self.lbl_remaining.setStyleSheet("font-size: 16px; font-weight: bold; color: #2e7d32;") # Vert

    def _update_total(self):
        # 1. Calcul du total des lignes
        total = sum(float(i.get("line_total", 0)) for i in self.items)
        self.lbl_total_amount.setText(f"{total:.2f}")

        # --- LOGIQUE PRÉ-REMPLISSAGE ---
        # Si on est en CREATION (pas de transaction existante chargée)
        if not self.transaction:
            # Par défaut, on suppose que le patient paie tout (comptant)
            # On met à jour le champ "Avance" avec le montant total
            # Ceci déclenchera _on_advance_changed qui mettra le reste à 0
            self.entry_advance.setText(f"{total:.2f}")
        else:
            # En mode édition (lecture seule sur l'avance), on calcule juste le reste
            try:
                paid = float(self.entry_advance.text().replace(',', '.') or 0)
            except ValueError:
                paid = 0.0
            
            # On appelle explicitement la mise à jour visuelle du reste
            # (car setText sur un champ ReadOnly ne déclenche pas toujours l'event utilisateur)
            self._on_advance_changed(str(paid))

    def _load_transaction_into_form(self):
        tx = self.transaction
        if not tx: return

        if isinstance(tx, dict):
            pid = tx.get("patient_id")
            d_raw = tx.get("paid_at") or tx.get("payment_date")
            if isinstance(d_raw, str):
                try:
                    d_obj = datetime.fromisoformat(d_raw) if "T" in d_raw else datetime.strptime(d_raw, "%Y-%m-%d %H:%M:%S")
                    date_str = d_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = str(d_raw)
            else:
                date_str = d_raw.strftime("%Y-%m-%d %H:%M") if d_raw else ""
            
            adv = tx.get("advance_amount", 0)
            pay_method = tx.get("payment_method", "")
            note = tx.get("note", "")
            t_types = tx.get("transaction_type", "")
            raw_items = tx.get("items", [])
        else:
            # Objet SQLAlchemy
            pid = getattr(tx, "patient_id", None)
            d_raw = getattr(tx, "paid_at", None)
            date_str = d_raw.strftime("%Y-%m-%d %H:%M") if d_raw else ""
            adv = getattr(tx, "advance_amount", 0)
            pay_method = getattr(tx, "payment_method", "")
            note = getattr(tx, "note", "")
            t_types = getattr(tx, "transaction_type", "")
            raw_items = getattr(tx, "items", [])

        # Remplissage UI
        if pid:
            try:
                p = self.patient_ctrl.get_by_id(pid)
                if p:
                    code = p.get("code_patient") if isinstance(p, dict) else getattr(p, "code_patient", "")
                    self.entry_code.setText(code)
                    self._load_patient() 
            except: pass

        self.entry_date.setText(date_str)
        self.entry_advance.setText(f"{float(adv):.2f}")
        
        idx = self.combo_payment.findText(pay_method)
        if idx >= 0: self.combo_payment.setCurrentIndex(idx)
        
        self.txt_note.clear()
        self.txt_note.insert("0.0", note or "")

        # Types
        if t_types:
            if "Consultation" in t_types: self.chk_consult.setChecked(True)
            if "Médicament" in t_types or "Medication" in t_types: self.chk_med.setChecked(True)
            if "Carnet" in t_types or "Booklet" in t_types: self.chk_booklet.setChecked(True)
            if "Hospitalisation" in t_types: self.chk_hosp.setChecked(True)
            if "Examen" in t_types: self.chk_exam.setChecked(True)

        # Items
        self.items = []
        for i in raw_items:
            if isinstance(i, dict):
                item_data = i
            else:
                item_data = {
                    "item_type": i.item_type,
                    "item_ref_id": i.item_ref_id,
                    "quantity": i.quantity,
                    "unit_price": i.unit_price,
                    "line_total": i.line_total,
                    "note": i.note
                }
            item_data["unit_price"] = float(item_data["unit_price"])
            item_data["line_total"] = float(item_data["line_total"])
            self.items.append(item_data)

        self._refresh_items()
        self._update_total()

        # --- LOGIQUE PAIEMENT ECHELONNÉ EN EDITION ---
        # 1. On désactive le champ avance pour ne pas créer de conflit
        self.entry_advance.setReadOnly(True)
        self.entry_advance.setStyleSheet("background-color: #f0f0f0; color: #777;")
        self.entry_advance.setToolTip("Pour ajouter de l'argent, utilisez le bouton 'Ajouter un Paiement'")
        
        # 2. On affiche le bouton d'ajout de paiement
        self.btn_add_payment.setVisible(True)

    def _open_payment_dialog(self):
        """Ouvre la popup pour ajouter un versement."""
        try:
            total = float(self.lbl_total_amount.text())
            paid = float(self.entry_advance.text()) 
            remaining = max(0, total - paid)
        except:
            remaining = 0

        if remaining <= 0.01:
            QMessageBox.information(self, "Info", "Cette transaction est déjà soldée.")
            return

        dlg = PaymentDialog(self, remaining_amount=remaining)
        if dlg.exec():
            data = dlg.get_data()
            if data["paid_amount"] <= 0: return

            try:
                # Récupérer ID transaction
                tid = self.transaction.get("transaction_id") if isinstance(self.transaction, dict) else self.transaction.transaction_id
                
                # Appel Backend
                # La méthode add_installment_payment doit exister sur le controller ou gateway
                if hasattr(self.controller, 'add_installment_payment'):
                    self.controller.add_installment_payment(tid, data)
                elif hasattr(self.controller, 'gateway'):
                    # Fallback si méthode non exposée directement sur controller
                    self.controller.gateway.add_installment_payment(tid, data)
                else:
                    raise AttributeError("Impossible de trouver la méthode 'add_installment_payment'")
                
                QMessageBox.information(self, "Succès", "Paiement ajouté avec succès !")
                
                # Mise à jour locale
                new_total_paid = paid + data["paid_amount"]
                self.entry_advance.setText(f"{new_total_paid:.2f}")
                self._update_total() # Met à jour le reste à payer

                if self.on_save: self.on_save()
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors du paiement : {str(e)}")

    def _on_save(self):
        try:
            # 1. Construction des types de transaction
            types_sel = []
            if self.chk_consult.isChecked(): types_sel.append("Consultation")
            if self.chk_med.isChecked(): types_sel.append("Vente Médicament" if self.locale=="fr" else "Sale Medication")
            if self.chk_booklet.isChecked(): types_sel.append("Vente Carnet" if self.locale=="fr" else "Sale Booklet")
            if self.chk_hosp.isChecked(): types_sel.append("Hospitalisation" if self.locale=="fr" else "Hospitalization")
            if self.chk_exam.isChecked(): types_sel.append("Examens" if self.locale=="fr" else "Exams")

            if not types_sel:
                QMessageBox.warning(self, "Attention", self.texts[self.locale]["err_no_type"])
                return
            
            # 2. Vérification des lignes
            if not self.items:
                QMessageBox.warning(self, "Attention", self.texts[self.locale]["err_no_lines"])
                return

            # 3. Récupération des montants
            try:
                # Montant versé (Avance)
                adv = float(self.entry_advance.text().replace(",", "."))
                # Montant total de la facture
                total_amount = float(self.lbl_total_amount.text().replace(",", "."))
            except:
                QMessageBox.warning(self, "Attention", self.texts[self.locale]["err_advance"])
                return

            # 4. --- NOUVELLE LOGIQUE DE VALIDATION (Dette vs Patient) ---
            
            remaining_due = total_amount - adv

            # Règle : Si il reste de l'argent à payer (Dette > 0), il faut OBLIGATOIREMENT un patient.
            # On utilise 0.01 pour gérer les approximations de nombres flottants.
            if remaining_due > 0.01 and not self.patient_id:
                msg_fr = "Impossible de laisser une dette (reste à payer) à un client anonyme.\n\nPour un paiement partiel, veuillez charger un dossier Patient.\nPour un client anonyme, encaissez la totalité."
                msg_en = "Cannot leave a debt to an anonymous client.\nPlease register the patient or collect the full amount."
                
                QMessageBox.warning(self, "Attention", msg_fr if self.locale == "fr" else msg_en)
                return

            # Sécurité : Empêcher de payer plus que le total (Trop perçu)
            if remaining_due < -0.01:
                 QMessageBox.warning(self, "Erreur", "Le montant versé est supérieur au total de la facture.")
                 return
            
            # -------------------------------------------------------------

            # 5. Préparation des données
            data = {
                "transaction_type": ", ".join(types_sel),
                "advance_amount": adv,
                "patient_id": self.patient_id,
                "payment_method": self.combo_payment.currentText(),
                "note": self.txt_note.toPlainText(),
                "paid_at": datetime.now(), 
                "amount": total_amount,
                "items": self.items
            }

            # 6. Appel Controller
            if self.transaction:
                tid = getattr(self.transaction, "transaction_id", None) or self.transaction.get("transaction_id")
                self.controller.update_transaction(tid, data)
                msg = self.texts[self.locale]["success_update"]
            else:
                self.controller.create_transaction(data)
                msg = self.texts[self.locale]["success_save"]
            
            QMessageBox.information(self, "Succès", msg)
            
            if self.on_save:
                self.on_save()
            self.accept()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, self.texts[self.locale]["error"], str(e))