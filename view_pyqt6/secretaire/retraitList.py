from datetime import datetime, date
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox, 
    QDateEdit, QGroupBox, QHeaderView, QInputDialog, QFrame
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush

class RetraitListView(QWidget):
    def __init__(self, parent, retrait_ctrl, on_retraits_changed=None, locale="fr"):
        super().__init__(parent)
        self.retrait_ctrl = retrait_ctrl
        self.on_retraits_changed = on_retraits_changed
        self.locale = locale
        
        self.texts = {
            "fr": {
                "title": "Gestion des Retraits",
                "status": "Statut :",
                "from": "Du :",
                "to": "Au :",
                "btn_today": "Aujourd'hui",
                "btn_month": "Ce Mois",
                "cancel_btn": "✖ Annuler le Retrait sélectionné",
                "total_lbl": "Total Période :",
                "all": "Tous",
                "active": "Actif",
                "cancelled": "Annulé",
                "cols": ["ID", "Montant", "Date", "Auteur", "Justification", "Statut"],
                "err_sel": "Veuillez sélectionner un retrait à annuler.",
                "reason_title": "Annulation",
                "reason_msg": "Motif de l'annulation :",
                "success_cancel": "Le retrait a été annulé avec succès.",
                "error": "Erreur"
            },
            "en": {
                "title": "Withdrawal Management",
                "status": "Status:",
                "from": "From:",
                "to": "To:",
                "btn_today": "Today",
                "btn_month": "This Month",
                "cancel_btn": "✖ Cancel Selected Withdrawal",
                "total_lbl": "Total Period:",
                "all": "All",
                "active": "Active",
                "cancelled": "Cancelled",
                "cols": ["ID", "Amount", "Date", "Author", "Justification", "Status"],
                "err_sel": "Please select a withdrawal to cancel.",
                "reason_title": "Cancellation",
                "reason_msg": "Reason for cancellation:",
                "success_cancel": "Withdrawal cancelled successfully.",
                "error": "Error"
            }
        }

        self._setup_ui()
        # Charge les données d'aujourd'hui par défaut
        self.load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        
        # --- 1. Titre & Boutons Rapides ---
        top_layout = QHBoxLayout()
        lbl_title = QLabel(self.texts[self.locale]["title"])
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        top_layout.addWidget(lbl_title)
        
        top_layout.addStretch()
        
        # Boutons pour filtrer rapidement (Jour / Mois)
        btn_today = QPushButton(self.texts[self.locale]["btn_today"])
        btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_today.clicked.connect(self._set_filter_today)
        top_layout.addWidget(btn_today)
        
        btn_month = QPushButton(self.texts[self.locale]["btn_month"])
        btn_month.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_month.clicked.connect(self._set_filter_month)
        top_layout.addWidget(btn_month)
        
        layout.addLayout(top_layout)
        
        # --- 2. Filtres Manuels ---
        filter_box = QGroupBox()
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setContentsMargins(5, 5, 5, 5)
        
        # Statut
        filter_layout.addWidget(QLabel(self.texts[self.locale]["status"]))
        self.combo_status = QComboBox()
        self.combo_status.addItems([
            self.texts[self.locale]["all"],
            self.texts[self.locale]["active"],
            self.texts[self.locale]["cancelled"]
        ])
        self.combo_status.currentTextChanged.connect(lambda _: self.load_data())
        filter_layout.addWidget(self.combo_status)
        
        # Dates
        today = QDate.currentDate()
        filter_layout.addWidget(QLabel(self.texts[self.locale]["from"]))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(today)
        self.date_from.dateChanged.connect(lambda _: self.load_data())
        filter_layout.addWidget(self.date_from)
        
        filter_layout.addWidget(QLabel(self.texts[self.locale]["to"]))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(today)
        self.date_to.dateChanged.connect(lambda _: self.load_data())
        filter_layout.addWidget(self.date_to)
        
        layout.addWidget(filter_box)
        
        # --- 3. Liste (TreeWidget) ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(self.texts[self.locale]["cols"])
        
        # Ajustement des colonnes
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Montant
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # Justification prend la place
        
        self.tree.setAlternatingRowColors(True)
        self.tree.setFixedHeight(250)
        layout.addWidget(self.tree)
        
        # --- 4. Actions & Totaux (Bas de page) ---
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #f8f9fa; border-top: 1px solid #ddd;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        
        # Bouton Annuler (Rouge)
        self.btn_cancel = QPushButton(self.texts[self.locale]["cancel_btn"])
        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color: #dc3545; color: white; font-weight: bold; padding: 5px 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #c82333; }
        """)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._cancel_selected)
        bottom_layout.addWidget(self.btn_cancel)
        
        bottom_layout.addStretch()
        
        # Affichage Total
        bottom_layout.addWidget(QLabel(self.texts[self.locale]["total_lbl"]))
        self.lbl_total = QLabel("0.00")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: bold; color: #28a745;")
        bottom_layout.addWidget(self.lbl_total)
        
        layout.addWidget(bottom_frame)

    # --- Gestion des Filtres Rapides ---

    def _set_filter_today(self):
        """Met les dates à aujourd'hui -> Charge le total journalier"""
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)
        # load_data est appelé automatiquement grâce au signal dateChanged

    def _set_filter_month(self):
        """Met les dates du 1er au dernier jour du mois -> Charge le total mensuel"""
        today = QDate.currentDate()
        first_day = QDate(today.year(), today.month(), 1)
        last_day = first_day.addMonths(1).addDays(-1)
        
        # On bloque les signaux pour éviter de charger 2 fois
        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        
        self.date_from.setDate(first_day)
        self.date_to.setDate(last_day)
        
        self.date_from.blockSignals(False)
        self.date_to.blockSignals(False)
        
        self.load_data()

    # --- Chargement des Données ---

    def load_data(self):
        # 1. Dates (Inversion auto + Conversion)
        d1 = self.date_from.date().toPyDate()
        d2 = self.date_to.date().toPyDate()
        
        if d1 > d2:
            d_from, d_to = d2, d1
        else:
            d_from, d_to = d1, d2
        
        dt_from = datetime.combine(d_from, datetime.min.time())
        dt_to = datetime.combine(d_to, datetime.max.time())
        
        # 2. Statut
        status_txt = self.combo_status.currentText()
        s_map = {
            self.texts[self.locale]["active"]: "active",
            self.texts[self.locale]["cancelled"]: "cancelled",
            self.texts[self.locale]["all"]: None
        }
        status_filter = s_map.get(status_txt, None)

        try:
            # 3. Récupération Liste
            rets = self.retrait_ctrl.list_retraits(
                status=status_filter,
                date_from=dt_from,
                date_to=dt_to,
                page=1, per_page=100
            )
            
            # Parsing robuste
            items = []
            if isinstance(rets, dict) and "data" in rets:
                items = rets["data"]
            elif isinstance(rets, list):
                items = rets

            self.tree.clear()
            
            for r in items:
                # Gestion Dict/Objet
                if isinstance(r, dict):
                    rid = r.get("retrait_id")
                    amt = r.get("amount", 0)
                    dt_raw = r.get("retrait_at")
                    user = r.get("created_by_name", "N/A")
                    justif = r.get("cancel_justification") or r.get("justification", "")
                    stat = r.get("status")
                else:
                    rid = getattr(r, "retrait_id", None)
                    amt = getattr(r, "amount", 0)
                    dt_raw = getattr(r, "retrait_at", None)
                    user = getattr(r, "created_by_name", "N/A")
                    justif = getattr(r, "cancel_justification", "") or getattr(r, "justification", "")
                    stat = getattr(r, "status", "")

                # Format date
                date_str = str(dt_raw)
                if isinstance(dt_raw, datetime):
                    date_str = dt_raw.strftime("%d/%m/%Y %H:%M")
                elif isinstance(dt_raw, str) and "T" in dt_raw:
                    # ex: 2025-11-20T10:00:00 -> 20/11/2025 10:00
                    try:
                        d_obj = datetime.fromisoformat(dt_raw)
                        date_str = d_obj.strftime("%d/%m/%Y %H:%M")
                    except:
                        pass

                item = QTreeWidgetItem([
                    str(rid),
                    f"{float(amt):.2f}",
                    date_str,
                    str(user),
                    str(justif),
                    str(stat)
                ])
                
                if stat == "cancelled":
                    for c in range(6):
                        item.setBackground(c, QBrush(QColor("#f8d7da"))) # Rouge
                        item.setForeground(c, QBrush(QColor("#721c24")))
                
                self.tree.addTopLevelItem(item)

            # 4. Récupération Total
            # C'est ici que la magie opère : le backend calcule le total 
            # pour la plage de dates (dt_from -> dt_to)
            total = self.retrait_ctrl.get_total_retraits(
                status=status_filter,
                date_from=dt_from,
                date_to=dt_to
            )
            self.lbl_total.setText(f"{float(total):.2f} CFA")
            
        except Exception as e:
            print(f"Erreur load retraits: {e}")

    # --- Actions ---

    def _cancel_selected(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_sel"])
            return
        
        # Colonne 5 = Statut
        if item.text(5) == "cancelled":
            QMessageBox.warning(self, "Info", "Ce retrait est déjà annulé.")
            return

        rid = int(item.text(0)) # Colonne 0 = ID
        
        reason, ok = QInputDialog.getText(
            self, 
            self.texts[self.locale]["reason_title"], 
            self.texts[self.locale]["reason_msg"]
        )
        
        if ok and reason.strip():
            try:
                # Appel Controller
                if hasattr(self.retrait_ctrl, "annuler_retrait"):
                    self.retrait_ctrl.annuler_retrait(rid, reason)
                else:
                    self.retrait_ctrl.cancel_retrait(rid, reason)
                
                QMessageBox.information(self, "Succès", self.texts[self.locale]["success_cancel"])
                
                # Recharger
                self.load_data()
                
                # Prévenir la vue parente (CaisseListView) pour qu'elle mette à jour le Solde Net
                if self.on_retraits_changed:
                    self.on_retraits_changed()
                    
            except Exception as e:
                QMessageBox.critical(self, self.texts[self.locale]["error"], str(e))