import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from view.secretaire.transaction_view import AddItemDialog
import traceback


class CaisseFormView(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        controller,
        patient_ctrl=None,
        pharmacy_ctrl=None,
        consultation_spirituel_ctrl=None,
        medical_record_ctrl=None,
        on_save=None,
        transaction=None,
        locale: str = "fr"
    ):
        """
        - master                       : fenêtre parente
        - controller                   : instance de CaisseController
        - patient_ctrl                 : instance de PatientController
        - pharmacy_ctrl                : instance de PharmacyController
        - consultation_spirituel_ctrl  : instance de ConsultationSpirituelController
        - medical_record_ctrl          : instance de MedicalRecordController
        - on_save                      : callback à exécuter après création/mise à jour
        - transaction                  : objet Caisse SQLAlchemy si édition, sinon None
        - locale                       : "fr" ou "en"
        """
        super().__init__(master)
        self.controller = controller
        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.consultation_spirituel_ctrl = consultation_spirituel_ctrl
        self.medical_record_ctrl = medical_record_ctrl
        self.on_save = on_save
        self.transaction = transaction
        self.locale = locale
        self.patient_id = None
        self.items = []  # liste des lignes (dict)

        self._init_vars()
        self._build_ui()

        if self.transaction:
            self._load_transaction_into_form()

        self.grab_set()
        self.after(50, lambda: self.focus_force())


    def _init_vars(self):
        # Code patient
        self.var_code = ctk.StringVar(value="")

        # Avance de paiement
        self.var_advance_amount = tk.StringVar(value="0.00")

        # Cases à cocher pour type de transaction
        self.var_trans_consult = tk.BooleanVar(value=False)
        self.var_trans_med     = tk.BooleanVar(value=False)
        self.var_trans_booklet = tk.BooleanVar(value=False)
        self.var_trans_hosp    = tk.BooleanVar(value=False)
        self.var_trans_exam    = tk.BooleanVar(value=False)

        # Mode paiement
        self.var_payment = ctk.StringVar(value=("Espèces" if self.locale == "fr" else "Cash"))
        # Note libre
        self.var_note = ctk.StringVar(value="")
        # Date/heure (readonly)
        self.var_date = ctk.StringVar(value=datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
        # Montant total des lignes
        self.var_amount = tk.StringVar(value="0.00")

    def _build_ui(self):
        pad_label = {"padx": 10, "pady": 5}
        pad_entry = {"padx": 10, "pady": 5}

        # Titre
        title = {"fr": "Transaction Caisse", "en": "Cash Transaction"}[self.locale]
        title += {True: {"fr": " [Édition]", "en": " [Edit]"}[self.locale],
                  False: {"fr": " [Nouveau]", "en": " [New]"}[self.locale]}[bool(self.transaction)]
        self.title(title)

        # Cadre supérieur
        frm_top = ctk.CTkFrame(self)
        frm_top.pack(fill="x", padx=10, pady=(10, 5))

        # Code patient
        ctk.CTkLabel(frm_top, text={"fr": "Code patient :", "en": "Patient code:"}[self.locale])\
            .grid(row=0, column=0, sticky="w", **pad_label)
        ctk.CTkEntry(frm_top, textvariable=self.var_code).grid(row=0, column=1, **pad_entry)
        ctk.CTkButton(frm_top, text={"fr": "Charger", "en": "Load"}[self.locale], command=self._load_patient)\
            .grid(row=0, column=2, **pad_entry)

        self.lbl_patient_info = ctk.CTkLabel(frm_top, text="", justify="left")
        self.lbl_patient_info.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 5))

        # Date/Heure
        ctk.CTkLabel(frm_top, text={"fr": "Date/Heure :", "en": "Date/Time:"}[self.locale])\
            .grid(row=2, column=0, sticky="w", **pad_label)
        ctk.CTkEntry(frm_top, textvariable=self.var_date, state="disabled").grid(
            row=2, column=1, columnspan=2, sticky="ew", **pad_entry)

        # Avance
        ctk.CTkLabel(frm_top, text={"fr": "Avance (CFA) :", "en": "Advance (CFA):"}[self.locale])\
            .grid(row=3, column=0, sticky="w", **pad_label)
        ctk.CTkEntry(frm_top, textvariable=self.var_advance_amount).grid(
            row=3, column=1, columnspan=2, sticky="ew", **pad_entry)

        # Type transaction
        ctk.CTkLabel(frm_top, text={"fr": "Type transac. :", "en": "Trans. type:"}[self.locale])\
            .grid(row=4, column=0, sticky="nw", **pad_label)
        box_frame = ctk.CTkFrame(frm_top)
        box_frame.grid(row=4, column=1, columnspan=2, sticky="w", **pad_entry)

        for var, text in [
            (self.var_trans_consult, {"fr": "Consultation", "en": "Consultation"}[self.locale]),
            (self.var_trans_med,     {"fr": "Vente Médicament", "en": "Sale Medication"}[self.locale]),
            (self.var_trans_booklet, {"fr": "Vente Carnet", "en": "Sale Booklet"}[self.locale]),
            (self.var_trans_hosp,    {"fr": "Hospitalisation", "en": "Hospitalization"}[self.locale]),
            (self.var_trans_exam,    {"fr": "Examens", "en": "Exams"}[self.locale])
        ]:
            ctk.CTkCheckBox(box_frame, text=text, variable=var, command=self._on_type_change)\
                .pack(side="left", padx=(0, 10))

        # Mode paiement
        ctk.CTkLabel(frm_top, text={"fr": "Mode paiement :", "en": "Payment method:"}[self.locale])\
            .grid(row=5, column=0, sticky="w", **pad_label)
        self.cb_pay = ctk.CTkComboBox(
            frm_top,
            variable=self.var_payment,
            values=(
                ["Espèces","Carte","Chèque","Virement","Orange Money","MTN Money"]
                if self.locale=="fr"
                else ["Cash","Card","Check","Transfer","Orange Money","MTN Money"]
            ),
            width=200
        )
        self.cb_pay.grid(row=5, column=1, columnspan=2, sticky="ew", **pad_entry)

        # Note
        ctk.CTkLabel(self, text={"fr": "Note :", "en": "Note:"}[self.locale])\
            .pack(anchor="w", padx=10, pady=(10, 0))
        self.txt_note = ctk.CTkTextbox(self, height=60)
        self.txt_note.pack(fill="x", padx=10, pady=(0, 5))
        if self.transaction and self.transaction.note:
            self.txt_note.insert("0.0", self.transaction.note)

        # Lignes
        ctk.CTkLabel(self, text={"fr": "Lignes :", "en": "Lines:"}[self.locale])\
            .pack(anchor="w", padx=10, pady=(10, 0))
        frm_items = ctk.CTkFrame(self)
        frm_items.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        cols = ("Type","Réf. ID","Quantité","Prix unitaire","Total","Note")
        self.tree_items = ttk.Treeview(frm_items, columns=cols, show="headings", height=5)
        for c in cols:
            self.tree_items.heading(c, text=c, anchor="center")
            self.tree_items.column(c, anchor="center", width=100)
        self.tree_items.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frm_items, orient="vertical", command=self.tree_items.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree_items.configure(yscrollcommand=scrollbar.set)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkButton(btn_frame, text={"fr": "Ajouter ligne", "en": "Add Line"}[self.locale], command=self._add_line)\
            .pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text={"fr": "Supprimer ligne", "en": "Remove Line"}[self.locale], fg_color="#D32F2F", command=self._remove_selected_line)\
            .pack(side="left")

        # Total
        frm_total = ctk.CTkFrame(self)
        frm_total.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(frm_total, text={"fr": "Montant total :", "en": "Total amount:"}[self.locale])\
            .grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkEntry(frm_total, textvariable=self.var_amount, state="disabled").grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        frm_total.grid_columnconfigure(1, weight=1)

        # Enregistrer / Annuler
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(pady=(0, 15))
        ctk.CTkButton(action_frame, text={"fr": "Enregistrer", "en": "Save"}[self.locale], command=self._on_save)\
            .pack(side="left", padx=10)
        ctk.CTkButton(action_frame, text={"fr": "Annuler", "en": "Cancel"}[self.locale], fg_color="#D32F2F", command=self.destroy)\
            .pack(side="left", padx=10)


    def _on_type_change(self):
        # Méthode vide, mais obligatoire pour éviter l’erreur d’attribut manquant
        pass


    def _load_patient(self):
        """
        Récupère le patient via patient_ctrl.find_by_code / get_by_id, et affiche 
        nom + ID de la dernière consultation (spirituel ou médical) sous le bouton.
        """
        code = self.var_code.get().strip()
        try:
            if hasattr(self.patient_ctrl, 'find_by_code'):
                patient = self.patient_ctrl.find_by_code(code)
            else:
                patient = self.patient_ctrl.find_patient_by_code(code)
        except Exception:
            patient = None

        if not patient:
            # Aucun patient trouvé : on vide le label et on affiche une erreur
            self.lbl_patient_info.configure(text="")
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Patient introuvable.", "en": "Patient not found."}[self.locale]
            )
            return

        # Récupération de l'ID patient
        pid = patient.get("patient_id") if isinstance(patient, dict) else patient.patient_id
        self.patient_id = pid

        # Chargement complet du patient pour récupérer first_name/last_name
        try:
            full_patient = self.patient_ctrl.get_by_id(pid)
        except Exception:
            full_patient = patient

        # Extraction du nom (first_name + last_name)
        if isinstance(full_patient, dict):
            patient_name = f"{full_patient.get('first_name','')} {full_patient.get('last_name','')}".strip()
        else:
            patient_name = (getattr(full_patient, 'first_name', '') + " " +
                            getattr(full_patient, 'last_name', '')).strip()

        # Récupérer la dernière consultation (spirituel OU médical) la plus récente
        last_consult_id = "0"
        last_consult_date = None

        # 1) Consultation Spirituelle
        if self.consultation_spirituel_ctrl:
            try:
                cs = self.consultation_spirituel_ctrl.get_last_for_patient(pid)
                if cs:
                    last_consult_id = cs.consultation_id
                    last_consult_date = cs.date
            except Exception:
                last_consult_id = "0"

        # 2) Consultation Médicale
        if self.medical_record_ctrl:
            try:
                mr = self.medical_record_ctrl.get_last_for_patient(pid)
                if mr:
                    # Si aucune date précédente ou date médicale plus récente
                    if last_consult_date is None or (mr.date and mr.date > last_consult_date):
                        last_consult_id = mr.consultation_id
                        last_consult_date = mr.date
            except Exception:
                last_consult_id = "0"

        # Mise à jour du label sous le bouton “Charger”
        if self.locale == 'fr':
            info_text = f"Nom patient : {patient_name}    |    Dernière consultation : {last_consult_id}"
        else:
            info_text = f"Patient name: {patient_name}    |    Last consult ID: {last_consult_id}"
        self.lbl_patient_info.configure(text=info_text)


    def _add_line(self):
        allowed = []
        if self.var_trans_consult.get():
            allowed += [ {"fr":"Consultation Spirituel","en":"Spiritual Consultation"}[self.locale],
                         {"fr":"Consultation Médical","en":"Medical Consultation"}[self.locale] ]
        if self.var_trans_med.get():
            allowed.append({"fr":"Médicament","en":"Medication"}[self.locale])
        if self.var_trans_booklet.get():
            allowed.append({"fr":"Carnet","en":"Booklet"}[self.locale])
        if self.var_trans_hosp.get():
            allowed += [ {"fr":"Hospitalisation","en":"Hospitalization"}[self.locale],
                         {"fr":"Désintox","en":"Detox"}[self.locale] ]
        if self.var_trans_exam.get():
            allowed.append({"fr":"Examens","en":"Exams"}[self.locale])
        if not allowed:
            messagebox.showerror(
                {"fr":"Erreur","en":"Error"}[self.locale],
                {"fr":"Cochez au moins un type...","en":"Please check at least one type..."}[self.locale]
            )
            return
        def on_item_confirm(item_dict):
            self.items.append(item_dict)
            self._refresh_items()
            self._update_total()
        AddItemDialog(
            master=self,
            on_confirm=on_item_confirm,
            pharmacy_ctrl=self.pharmacy_ctrl,
            patient_ctrl=self.patient_ctrl,
            consultation_spirituel_ctrl=self.consultation_spirituel_ctrl,
            medical_record_ctrl=self.medical_record_ctrl,
            allowed_types=allowed,
            patient_id=self.patient_id,
            locale=self.locale
        )


    def _remove_selected_line(self):
        sel = self.tree_items.selection()
        if not sel:
            return
        idx = int(sel[0])
        del self.items[idx]
        self._refresh_items()
        self._update_total()


    def _refresh_items(self):
        # Vide le Treeview
        for iid in self.tree_items.get_children():
            self.tree_items.delete(iid)
        # Remplit chaque ligne
        for idx, item in enumerate(self.items):
            vals = (
                item["item_type"],
                item["item_ref_id"],
                item["quantity"],
                f"{item['unit_price']:.2f}",
                f"{item['line_total']:.2f}",
                item["note"] or ""
            )
            self.tree_items.insert("", "end", iid=str(idx), values=vals)


    def _update_total(self):
        total = sum(item["line_total"] for item in self.items)
        self.var_amount.set(f"{total:.2f}")


    def _load_transaction_into_form(self):
        """
        Préremplit les champs d'une transaction existante (en mode Édition) :
         - Charge le patient + affiche nom et dernière consultation.
         - Charge date/heure, avance, note, paiement, types cochés.
         - Charge les lignes existantes dans le Treeview.
        """
        tx = self.transaction

        # 1) Code patient + affichage nom + dernière consultation
        if tx.patient_id:
            try:
                patient = self.patient_ctrl.get_by_id(tx.patient_id)
            except Exception:
                patient = None

            code = patient.get('code_patient') if isinstance(patient, dict) else getattr(patient, 'code_patient', '')
            self.var_code.set(code)
            self.patient_id = tx.patient_id

            # Nom patient
            if isinstance(patient, dict):
                patient_name = f"{patient.get('first_name','')} {patient.get('last_name','')}".strip()
            else:
                patient_name = (getattr(patient, 'first_name', '') + " " +
                                getattr(patient, 'last_name', '')).strip()

            # Récupérer dernière consultation globale
            last_consult_id = "0"
            last_consult_date = None

            if self.consultation_spirituel_ctrl:
                try:
                    cs = self.consultation_spirituel_ctrl.get_last_for_patient(tx.patient_id)
                    if cs:
                        last_consult_id = cs.consultation_id
                        last_consult_date = cs.date
                except Exception:
                    last_consult_id = "0"

            if self.medical_record_ctrl:
                try:
                    mr = self.medical_record_ctrl.get_last_for_patient(tx.patient_id)
                    if mr:
                        if last_consult_date is None or (mr.date and mr.date > last_consult_date):
                            last_consult_id = mr.consultation_id
                            last_consult_date = mr.date
                except Exception:
                    last_consult_id = "0"

            if self.locale == 'fr':
                info_text = f"Nom patient : {patient_name}    |    Dernière consultation : {last_consult_id}"
            else:
                info_text = f"Patient name: {patient_name}    |    Last consult ID: {last_consult_id}"
            self.lbl_patient_info.configure(text=info_text)

        # 2) Date/heure
        self.var_date.set(tx.paid_at.strftime("%Y-%m-%d %H:%M"))

        # 3) Avance, Note, Mode paiement
        if hasattr(tx, "advance_amount"):
            self.var_advance_amount.set(f"{float(tx.advance_amount):.2f}")
        self.var_payment.set(tx.payment_method or "")
        if tx.note:
            self.txt_note.delete("0.0", "end")
            self.txt_note.insert("0.0", tx.note)

        # 4) Type de transaction (cochage des cases)
        if tx.transaction_type:
            parts = [p.strip() for p in tx.transaction_type.split(",")]
            self.var_trans_consult.set("Consultation" in parts)
            self.var_trans_med.set(("Vente Médicament" in parts) or ("Sale Medication" in parts))
            self.var_trans_booklet.set(("Vente Carnet" in parts) or ("Sale Booklet" in parts))

        # 5) Chargement des lignes existantes
        for item in tx.items:
            line = {
                "item_type":   item.item_type,
                "item_ref_id": item.item_ref_id,
                "quantity":    item.quantity,
                "unit_price":  float(item.unit_price),
                "line_total":  float(item.line_total),
                "note":        item.note or ""
            }
            self.items.append(line)

        self._refresh_items()
        self._update_total()


    def _on_save(self):
        """
        Construction du dict `data` puis appel à `create_transaction` ou `update_transaction`.
        En cas d’erreur SQL, affichage de la trace dans la console et d’un pop‐up.
        """
        data = {}

        # a) Transaction types concaténés
        types_sel = []
        if self.var_trans_consult.get():
            types_sel.append("Consultation")
        if self.var_trans_med.get():
            types_sel.append("Vente Médicament" if self.locale == "fr" else "Sale Medication")
        if self.var_trans_booklet.get():
            types_sel.append("Vente Carnet" if self.locale == "fr" else "Sale Booklet")
        if self.var_trans_hosp.get():
            types_sel.append("Hospitalisation" if self.locale == "fr" else "Hospitalization")
        if self.var_trans_exam.get():
            types_sel.append("Examens" if self.locale == "fr" else "Exams")

        if not types_sel:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Sélectionnez au moins un type de transaction.",
                "en": "Select at least one transaction type."}[self.locale]
            )
            return

        data["transaction_type"] = ", ".join(types_sel)

        # b) Patient (optionnel, mais si avance > 0, alors obligatoire)
        try:
            advance_val = float(self.var_advance_amount.get())
        except ValueError:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Montant avance invalide.", "en": "Invalid advance amount."}[self.locale]
            )
            return

        if advance_val > 0 and not self.patient_id:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Vous devez renseigner un code patient si vous faites une avance.",
                "en": "You must provide a patient code if there is an advance."}[self.locale]
            )
            return

        data["advance_amount"] = advance_val
        data["patient_id"] = self.patient_id
        data["payment_method"] = self.var_payment.get().strip()
        data["note"] = self.txt_note.get("0.0", "end").strip() or None
        data["paid_at"] = datetime.strptime(self.var_date.get(), "%Y-%m-%d %H:%M")
        data["amount"] = float(self.var_amount.get())

        # c) Vérifier qu'il y a au moins une ligne
        if not self.items:
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                {"fr": "Ajoutez au moins une ligne.", "en": "Please add at least one line."}[self.locale]
            )
            return

        data["items"] = self.items.copy()

        try:
            if self.transaction:
                self.controller.update_transaction(self.transaction.transaction_id, data)
                messagebox.showinfo(
                    {"fr": "Succès", "en": "Success"}[self.locale],
                    {"fr": "Transaction mise à jour.", "en": "Transaction updated."}[self.locale]
                )
            else:
                self.controller.create_transaction(data)
                messagebox.showinfo(
                    {"fr": "Succès", "en": "Success"}[self.locale],
                    {"fr": "Transaction enregistrée.", "en": "Transaction saved."}[self.locale]
                )

            if self.on_save:
                self.on_save()
            self.destroy()

        except Exception as e:
            # Affiche la trace complète en console
            print("=== Exception levée lors de la sauvegarde de la transaction ===")
            traceback.print_exc()
            print("=== Fin de la trace d'exception ===\n")

            # Montre un message d’erreur
            messagebox.showerror(
                {"fr": "Erreur", "en": "Error"}[self.locale],
                str(e)
            )
            return
