import logging
from datetime import date, datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTreeWidget, 
    QTreeWidgetItem, QMessageBox, QDateEdit, QFrame, QGroupBox, 
    QHeaderView, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QColor, QBrush, QIcon

# Assurez-vous que ces imports pointent vers vos fichiers corrects
try:
    from view_pyqt6.secretaire.caisse_form import CaisseFormView 
    from view_pyqt6.secretaire.retraitList import RetraitListView
    from view_pyqt6.secretaire.retraitDialog import RetraitDialog
    from view_pyqt6.secretaire.transaction_details_dialog import TransactionDetailsDialog
except ImportError:
    # Fallback pour éviter le crash si les fichiers n'existent pas encore
    CaisseFormView = None
    RetraitListView = None
    RetraitDialog = None
    TransactionDetailsDialog = None

logger = logging.getLogger(__name__)

class CaisseWorker(QThread):
    """
    Thread dédié au chargement des données (Transactions + Totaux)
    pour ne pas bloquer l'interface graphique.
    """
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, controller, caisse_retrait_controller, filters):
        super().__init__()
        self.controller = controller
        self.caisse_retrait_controller = caisse_retrait_controller
        self.filters = filters

    def run(self):
        try:
            # 1. Liste des transactions
            response = self.controller.search_transactions(**self.filters)
            
            transactions = []
            total_items = 0
            
            if isinstance(response, list):
                transactions = response
                total_items = len(response) 
            elif isinstance(response, dict):
                transactions = response.get("data", []) or response.get("items", [])
                total_items = response.get("total", len(transactions))

            # 2. Calcul des Totaux Financiers
            d_from = self.filters.get('date_from')
            d_to = self.filters.get('date_to')
            
            dt_from = None
            dt_to = None

            if isinstance(d_from, date):
                dt_from = datetime.combine(d_from, datetime.min.time())
            if isinstance(d_to, date):
                dt_to = datetime.combine(d_to, datetime.max.time())

            # A. Total Encaissé (Paiements réels)
            total_tx = 0.0
            if hasattr(self.controller, "get_total_payments"):
                total_tx = self.controller.get_total_payments(
                    status="active", 
                    date_from=dt_from, 
                    date_to=dt_to
                )
            else:
                # Fallback
                total_tx = self.controller.get_total_transactions(
                    status="active", date_from=dt_from, date_to=dt_to
                )
            
            # B. Total Retraits
            total_rt = 0.0
            if self.caisse_retrait_controller:
                total_rt = self.caisse_retrait_controller.get_total_retraits(
                    status="active", 
                    date_from=dt_from, 
                    date_to=dt_to
                )

            # C. Total Restant Dû (AJOUTÉ)
            total_due = 0.0
            if hasattr(self.controller, "get_total_remaining_due"):
                total_due = self.controller.get_total_remaining_due(
                    status="active", 
                    date_from=dt_from, 
                    date_to=dt_to
                )

            self.data_loaded.emit({
                "transactions": transactions,
                "total_items": total_items,
                "total_tx": float(total_tx or 0.0),
                "total_rt": float(total_rt or 0.0),
                "total_due": float(total_due or 0.0) # <--- Nouvelle donnée
            })

        except Exception as e:
            logger.exception("Error in CaisseWorker")
            self.error_occurred.emit(str(e))


class CaisseListView(QWidget):
    def __init__(
        self, 
        parent, 
        controller, 
        caisse_retrait_controller, 
        patient_ctrl, 
        pharmacy_ctrl, 
        locale: str = "fr"
    ):
        super().__init__(parent)
        self.controller = controller
        self.caisse_retrait_controller = caisse_retrait_controller
        self.patient_ctrl = patient_ctrl
        self.pharmacy_ctrl = pharmacy_ctrl
        self.locale = locale

        # Pagination
        self.current_page = 1
        self.per_page = 50
        self.total_items = 0

        self.texts = {
            "fr": {
                "title": "Liste des Transactions",
                "search": "Rechercher :",
                "search_placeholder": "Type, utilisateur...",
                "payment": "Mode paiement :",
                "from": "Du :",
                "to": "Au :",
                "apply": "Filtrer",
                "reset": "Réinitialiser",
                "all": "Tous",
                "cols": ["ID", "Patient", "Type", "Paiement", "Montant", "Date", "Statut"],
                "total_tx": "Total Entrées :",
                "total_rt": "Total Sorties :",
                "net": "Solde Net :",
                "new": "Nouveau",
                "edit": "Éditer",
                "cancel": "Annuler Tx",
                "delete": "Supprimer Tx",
                "withdraw": "Effectuer retrait",
                "refresh": "Rafraîchir",
                "prev": "Précédent",
                "next": "Suivant",
                "loading": "Chargement...",
                "error": "Erreur",
                "confirm_del": "Supprimer définitivement cette transaction ?",
                "success_del": "Transaction supprimée.",
                "success_cancel": "Transaction annulée.",
                "err_sel": "Aucune transaction sélectionnée.",
                "err_cancelled": "Impossible d'éditer une transaction annulée.",
                "net": "Solde Net :",
                "total_due": "Reste à Percevoir :", # <--- AJOUTER CECI
                "new": "Nouveau"
            },
            "en": {
                "title": "Transaction List",
                "search": "Search:",
                "search_placeholder": "Type, user...",
                "payment": "Payment method:",
                "from": "From:",
                "to": "To:",
                "apply": "Filter",
                "reset": "Reset",
                "all": "All",
                "cols": ["ID", "Patient", "Type", "Payment", "Amount", "Date", "Status"],
                "total_tx": "Total In:",
                "total_rt": "Total Out:",
                "net": "Net Balance:",
                "new": "New",
                "edit": "Edit",
                "cancel": "Cancel Tx",
                "delete": "Delete Tx",
                "withdraw": "Withdraw",
                "refresh": "Refresh",
                "prev": "Previous",
                "next": "Next",
                "loading": "Loading...",
                "error": "Error",
                "confirm_del": "Permanently delete this transaction?",
                "success_del": "Transaction deleted.",
                "success_cancel": "Transaction cancelled.",
                "err_sel": "No transaction selected.",
                "err_cancelled": "Cannot edit a cancelled transaction.",
                "net": "Net Balance:",
                "total_due": "Remaining Due:"
            }
        }

        self._setup_ui()
        self.load_data()

    def _setup_ui(self):
        # --- Scroll Area Globale ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Widget Conteneur qui sera scrollable
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # 1. Titre
        lbl_title = QLabel(self.texts[self.locale]["title"])
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(lbl_title)

        # 2. Filtres (QGroupBox)
        filter_group = QGroupBox("Filtres")
        filter_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        filter_layout = QGridLayout(filter_group)
        filter_layout.setContentsMargins(10, 15, 10, 10)
        filter_layout.setSpacing(10)

        # Search
        filter_layout.addWidget(QLabel(self.texts[self.locale]["search"]), 0, 0)
        self.entry_search = QLineEdit()
        self.entry_search.setPlaceholderText(self.texts[self.locale]["search_placeholder"])
        self.entry_search.returnPressed.connect(self.apply_filters)
        filter_layout.addWidget(self.entry_search, 0, 1)

        # Payment
        filter_layout.addWidget(QLabel(self.texts[self.locale]["payment"]), 0, 2)
        self.combo_payment = QComboBox()
        modes = ["Tous", "Espèces", "Carte", "Chèque", "Virement", "Orange Money", "MTN Money"] if self.locale == "fr" else ["All", "Cash", "Card", "Check", "Transfer", "Orange Money", "MTN Money"]
        self.combo_payment.addItems(modes)
        self.combo_payment.currentTextChanged.connect(lambda _: self.apply_filters())
        filter_layout.addWidget(self.combo_payment, 0, 3)

        filter_layout.addWidget(QLabel("Statut :"), 0, 4) 
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Tous", "active", "cancelled"])
        self.combo_status.currentTextChanged.connect(lambda _: self.apply_filters())
        filter_layout.addWidget(self.combo_status, 0, 5)

        # Dates
        today = QDate.currentDate()
        filter_layout.addWidget(QLabel(self.texts[self.locale]["from"]), 1, 0)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(today)
        filter_layout.addWidget(self.date_from, 1, 1)

        filter_layout.addWidget(QLabel(self.texts[self.locale]["to"]), 1, 2)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(today)
        filter_layout.addWidget(self.date_to, 1, 3)

        # Buttons Filter
        btn_apply = QPushButton(self.texts[self.locale]["apply"])
        btn_apply.setStyleSheet("background-color: #007bff; color: white; font-weight: bold;")
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self.apply_filters)
        filter_layout.addWidget(btn_apply, 1, 4)

        btn_reset = QPushButton(self.texts[self.locale]["reset"])
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._reset_filters)
        filter_layout.addWidget(btn_reset, 1, 5)

        content_layout.addWidget(filter_group)

        # 3. TreeWidget (Liste Transactions)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(self.texts[self.locale]["cols"])
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Patient
        self.tree.setAlternatingRowColors(True)
        self.tree.setMinimumHeight(300)
        self.tree.itemDoubleClicked.connect(self._open_transaction_details)
        content_layout.addWidget(self.tree)

        # 4. Pagination Controls
        page_layout = QHBoxLayout()
        self.btn_prev = QPushButton(self.texts[self.locale]["prev"])
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_prev.setEnabled(False)
        
        self.lbl_page = QLabel("Page 1")
        
        self.btn_next = QPushButton(self.texts[self.locale]["next"])
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setEnabled(False)

        page_layout.addStretch()
        page_layout.addWidget(self.btn_prev)
        page_layout.addWidget(self.lbl_page)
        page_layout.addWidget(self.btn_next)
        page_layout.addStretch()
        content_layout.addLayout(page_layout)

        # 5. Actions
        action_layout = QHBoxLayout()
        
        btn_new = QPushButton(self.texts[self.locale]["new"])
        btn_new.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 5px 10px;")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self._new_transaction)
        action_layout.addWidget(btn_new)

        btn_edit = QPushButton(self.texts[self.locale]["edit"])
        btn_edit.setStyleSheet("padding: 5px 10px;")
        btn_edit.clicked.connect(self._edit_selected)
        action_layout.addWidget(btn_edit)

        btn_cancel = QPushButton(self.texts[self.locale]["cancel"])
        btn_cancel.setStyleSheet("background-color: #ffc107; color: black; padding: 5px 10px;")
        btn_cancel.clicked.connect(self._cancel_selected)
        action_layout.addWidget(btn_cancel)

        btn_del = QPushButton(self.texts[self.locale]["delete"])
        btn_del.setStyleSheet("background-color: #dc3545; color: white; padding: 5px 10px;")
        btn_del.clicked.connect(self._delete_selected)
        action_layout.addWidget(btn_del)

        action_layout.addSpacing(20)

        btn_withdraw = QPushButton(self.texts[self.locale]["withdraw"])
        btn_withdraw.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 5px 10px;")
        btn_withdraw.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_withdraw.clicked.connect(self._on_effectuer_retrait)
        action_layout.addWidget(btn_withdraw)

        btn_refresh = QPushButton(self.texts[self.locale]["refresh"])
        btn_refresh.setStyleSheet("padding: 5px 10px;")
        btn_refresh.clicked.connect(self.load_data)
        action_layout.addWidget(btn_refresh)

        content_layout.addLayout(action_layout)

        # 6. Totaux
        total_frame = QFrame()
        total_frame.setStyleSheet("background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; padding: 10px;")
        total_layout = QHBoxLayout(total_frame)

        self.lbl_total_tx = QLabel("0.00")
        self.lbl_total_rt = QLabel("0.00")
        self.lbl_net = QLabel("0.00")
        self.lbl_total_due = QLabel("0.00")
        
        
        style_num = "font-weight: bold; font-size: 16px;"
        self.lbl_total_tx.setStyleSheet(style_num + "color: #28a745;")
        self.lbl_total_rt.setStyleSheet(style_num + "color: #dc3545;")
        self.lbl_net.setStyleSheet(style_num + "color: #007bff;")
        self.lbl_total_due.setStyleSheet(style_num + "color: #fd7e14;")

        total_layout.addWidget(QLabel(self.texts[self.locale]["total_tx"]))
        total_layout.addWidget(self.lbl_total_tx)
        total_layout.addStretch()
        total_layout.addWidget(QLabel(self.texts[self.locale]["total_rt"]))
        total_layout.addWidget(self.lbl_total_rt)
        total_layout.addStretch()
        total_layout.addWidget(QLabel(self.texts[self.locale]["net"]))
        total_layout.addWidget(self.lbl_net)
        total_layout.addStretch()

        # --- AJOUTER CETTE SECTION ---
        total_layout.addWidget(QLabel(self.texts[self.locale]["total_due"]))
        total_layout.addWidget(self.lbl_total_due)
        # -----------------------------
        
        content_layout.addWidget(total_frame)

        # 7. Liste des Retraits (Section séparée)
        content_layout.addWidget(QLabel("--- Gestion des Retraits ---"))
        if RetraitListView and self.caisse_retrait_controller:
            self.retrait_view = RetraitListView(
                parent=self,
                retrait_ctrl=self.caisse_retrait_controller,
                on_retraits_changed=lambda: self.load_data(),
                locale=self.locale
            )
            self.retrait_view.setMinimumHeight(350)
            content_layout.addWidget(self.retrait_view)
        else:
            content_layout.addWidget(QLabel("Module de retraits indisponible."))

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def apply_filters(self):
        self.current_page = 1 
        self.load_data()

    def _reset_filters(self):
        self.entry_search.clear()
        self.combo_payment.setCurrentIndex(0)
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)
        self.apply_filters()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()

    def _next_page(self):
        self.current_page += 1
        self.load_data()

    def load_data(self):
        self.tree.setEnabled(False)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        
        d1 = self.date_from.date().toPyDate()
        d2 = self.date_to.date().toPyDate()
        if d1 > d2: d_from, d_to = d2, d1
        else: d_from, d_to = d1, d2

        filters = {
            "page": self.current_page,
            "per_page": self.per_page,
            "term": self.entry_search.text().strip() or None,
            "date_from": d_from,
            "date_to": d_to,
            "status": self.combo_status.currentText() if self.combo_status.currentText() != "Tous" else None
        }

        payment_raw = self.combo_payment.currentText()
        if payment_raw not in [self.texts[self.locale]["all"], "All", "Tous"]:
            filters["payment_method"] = payment_raw

        # Refresh Retraits view si elle existe
        if hasattr(self, "retrait_view"):
            self.retrait_view.load_data()

        self.worker = CaisseWorker(self.controller, self.caisse_retrait_controller, filters)
        self.worker.data_loaded.connect(self._on_data_loaded)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_data_loaded(self, results):
        self.tree.clear()
        self.tree.setEnabled(True)
        
        txs = results.get("transactions", [])
        
        for tx in txs:
            if isinstance(tx, dict):
                tid = tx.get("transaction_id") or tx.get("caisse_id")
                pid = tx.get("patient_id")
                p_label = tx.get("patient_name") or tx.get("patient_label")
                t_type = tx.get("transaction_type")
                pay_meth = tx.get("payment_method")
                amt = tx.get("amount", 0.0)
                date_str = tx.get("paid_at")
                status = tx.get("status")
            else:
                tid = getattr(tx, "transaction_id", None)
                pid = getattr(tx, "patient_id", None)
                p_label = getattr(tx, "patient_label", None)
                t_type = getattr(tx, "transaction_type", "")
                pay_meth = getattr(tx, "payment_method", "")
                amt = getattr(tx, "amount", 0.0)
                date_str = getattr(tx, "paid_at", None)
                status = getattr(tx, "status", "")

            # --- CORRECTION NOM PATIENT ---
            if pid and not p_label:
                try:
                    if self.patient_ctrl:
                        p = self.patient_ctrl.get_patient(pid)
                        if p:
                            if isinstance(p, dict):
                                nom = p.get("last_name", "") or p.get("nom", "")
                                prenom = p.get("first_name", "") or p.get("prenom", "")
                            else:
                                nom = getattr(p, "last_name", "") or getattr(p, "nom", "")
                                prenom = getattr(p, "first_name", "") or getattr(p, "prenom", "")
                            
                            full_name = f"{nom} {prenom}".strip()
                            p_label = full_name if full_name else "Inconnu"
                        else:
                            p_label = f"Patient {pid}"
                except Exception:
                    p_label = "Erreur récup."
            
            if not p_label: p_label = "Client de passage"

            # Format Date
            display_date = str(date_str)
            if isinstance(date_str, datetime):
                display_date = date_str.strftime("%d/%m/%Y %H:%M")
            elif isinstance(date_str, str) and "T" in date_str:
                 display_date = date_str.replace("T", " ")[:16]

            item = QTreeWidgetItem([
                str(tid),
                str(p_label),
                str(t_type),
                str(pay_meth),
                f"{float(amt):,.0f} F",
                display_date,
                str(status)
            ])
            
            if status == "cancelled":
                for c in range(7):
                    item.setBackground(c, QBrush(QColor("#f8d7da")))
                    item.setForeground(c, QBrush(QColor("#721c24")))
            
            self.tree.addTopLevelItem(item)

        # --- MISE À JOUR DES TOTAUX ---
        tx_val = results.get("total_tx", 0.0)   # Encaissé
        rt_val = results.get("total_rt", 0.0)   # Retraits
        due_val = results.get("total_due", 0.0) # Impayé (AJOUTÉ)
        net_val = tx_val - rt_val               # Solde Net
        
        self.lbl_total_tx.setText(f"{tx_val:,.0f} F")
        self.lbl_total_rt.setText(f"{rt_val:,.0f} F")
        self.lbl_net.setText(f"{net_val:,.0f} F")
        
        # Si vous avez ajouté ce label dans setup_ui
        if hasattr(self, "lbl_total_due"):
            self.lbl_total_due.setText(f"{due_val:,.0f} F")

        # Pagination
        self.total_items = results["total_items"]
        total_pages = (self.total_items + self.per_page - 1) // self.per_page if self.per_page else 1
        self.lbl_page.setText(f"Page {self.current_page} / {total_pages or 1}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

    def _on_error(self, error_msg):
        self.tree.setEnabled(True)
        self.btn_prev.setEnabled(True)
        self.btn_next.setEnabled(True)
        QMessageBox.critical(self, self.texts[self.locale]["error"], error_msg)

    def _get_selected_id(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_sel"])
            return None
        return int(item.text(0))

    def _new_transaction(self):
        if CaisseFormView is None: return
        try:
            dlg = CaisseFormView(
                parent=self, 
                controllers=self.controller, # Attention: vérifier si c'est le resolver ou le ctrl direct
                pharmacy_ctrl=self.pharmacy_ctrl,
                patient_ctrl=self.patient_ctrl,
                medical_record_ctrl=None, # ou self.controller.medical_record_controller() si dispo
                on_save=self.load_data,
                locale=self.locale
            )
            dlg.exec()
        except Exception as e:
            logger.error(f"Erreur ouverture CaisseFormView: {e}")
            QMessageBox.warning(self, "Info", f"Erreur ouverture formulaire: {e}")

    def _open_transaction_details(self, item, column):
        if not item or TransactionDetailsDialog is None: return
        try:
            tid = int(item.text(0))
        except ValueError: return

        try:
            # Récupération robuste de la transaction
            tx_data = self.controller.get_transaction(tid)
            if not isinstance(tx_data, dict):
                # Si c'est un objet (Offline), convertir en dict pour le Dialog si nécessaire
                # Mais TransactionDetailsDialog gère souvent les deux
                pass

            # Identifier le controller réel (pas le Resolver)
            caisse_ctrl_to_pass = self.controller 
            if hasattr(caisse_ctrl_to_pass, "caisse_controller"):
                 caisse_ctrl_to_pass = caisse_ctrl_to_pass.caisse_controller

            dlg = TransactionDetailsDialog(
                parent=self, 
                transaction_data=tx_data, 
                controller=caisse_ctrl_to_pass,
                on_change=self.load_data,
                locale=self.locale
            )
            dlg.exec()

        except Exception as e:
            logger.exception("Erreur ouverture détails")
            QMessageBox.critical(self, self.texts[self.locale]["error"], f"Impossible de charger les détails : {str(e)}")

    def _edit_selected(self):
        if CaisseFormView is None: return
        tid = self._get_selected_id()
        if not tid: return
        try:
            tx = self.controller.get_transaction(tid)
            status = tx.get("status") if isinstance(tx, dict) else getattr(tx, "status", "")
            if status == 'cancelled':
                QMessageBox.warning(self, self.texts[self.locale]["error"], self.texts[self.locale]["err_cancelled"])
                return

            dlg = CaisseFormView(
                parent=self,
                controllers=self.controller, 
                transaction=tx,
                patient_ctrl=self.patient_ctrl,
                pharmacy_ctrl=self.pharmacy_ctrl,
                medical_record_ctrl=None,
                on_save=self.load_data,
                locale=self.locale
            )
            dlg.exec()
        except Exception as e:
            logger.exception("Edit error")
            QMessageBox.critical(self, self.texts[self.locale]["error"], str(e))

    def _cancel_selected(self):
        tid = self._get_selected_id()
        if not tid: return
        if QMessageBox.question(self, "Confirmation", "Annuler cette transaction ?") == QMessageBox.StandardButton.Yes:
            try:
                self.controller.cancel_transaction(tid)
                QMessageBox.information(self, "Succès", self.texts[self.locale]["success_cancel"])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _delete_selected(self):
        tid = self._get_selected_id()
        if not tid: return
        if QMessageBox.question(self, "Attention", self.texts[self.locale]["confirm_del"]) == QMessageBox.StandardButton.Yes:
            try:
                self.controller.delete_transaction(tid)
                QMessageBox.information(self, "Succès", self.texts[self.locale]["success_del"])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _on_effectuer_retrait(self):
        if RetraitDialog is None: return
        def on_confirm(amount, justif):
            try:
                self.caisse_retrait_controller.effectuer_retrait(amount, justif)
                QMessageBox.information(self, "Succès", "Retrait enregistré.")
                self.load_data()
                if hasattr(self, "retrait_view"):
                    self.retrait_view.load_data() 
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

        dlg = RetraitDialog(self, on_confirm, locale=self.locale)
        dlg.exec()