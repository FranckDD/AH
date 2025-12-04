import os
import logging
from typing import Any, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame,
    QToolButton, QMenu, QComboBox, QStackedWidget, QMessageBox,QScrollArea
)
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt, QTimer

# Imports Architecture
from view_pyqt6.controller_resolver import ControllerResolver

# Gestion robuste des imports de vues
try:
    from view_pyqt6.secretaire.dashboard_home import SecretaireHomeWidget
except ImportError:
    SecretaireHomeWidget = None

PatientFormView = None
PatientListView = None
CSFormView = None
CSListView = None
StockFormView = None
StockListView = None
CaisseFormView = None
CaisseListView = None
try:
    from view_pyqt6.patient_view.patient_form import PatientFormView
    from view_pyqt6.patient_view.patient_list import PatientListView
    from view_pyqt6.secretaire.cs_form import CSFormView
    from view_pyqt6.secretaire.cs_list import CSListView
    from view_pyqt6.secretaire.stock_form import StockFormView
    from view_pyqt6.secretaire.stock_list import StockListView
    from view_pyqt6.secretaire.caisse_form import CaisseFormView
    from view_pyqt6.secretaire.caisse_list import CaisseListView
except ImportError:
    PatientListView = None
    # ... autres vues à None par défaut si import échoue ...
    pass

logger = logging.getLogger(__name__)

class SecretaireDashboardView(QWidget):
    def __init__(self, parent, user: Any, controllers: Any, on_logout: Optional[Callable] = None):
        super().__init__(parent)
        self.user = user
        self.controllers_obj = controllers
        self.on_logout = on_logout
        
        # 1. Initialisation du Resolver
        self.resolver = ControllerResolver(controllers)
        
        # CORRECTION : Renommé pour éviter conflit avec QWidget.locale()
        self.current_locale = "fr" 
        
        self.sidebar_expanded = True
        self.view_instances = {}
        self.page_placeholders = {} # Initialisation explicite
        
        # Initialisation des boutons pour éviter AttributeError
        self.dash_btn = None
        self.pats_btn = None
        self.cs_btn = None
        self.stock_btn = None
        self.caisse_btn = None

        # Textes pour les menus
        self.texts = {
            "fr": {
                "title": "Secrétariat", "welcome": "Bienvenue", "dashboard": "Tableau de bord",
                "patients": "Patients", "patient_add": "Ajout Patient", "patient_list": "Liste Patients",
                "cs": "Consultations", "cs_add": "Nouvelle CS", "cs_list": "Liste CS",
                "stock": "Stock", "stock_add": "Entrée Stock", "stock_list": "Inventaire",
                "caisse": "Caisse", "tx_add": "Nouvelle Trans.", "tx_list": "Historique",
                "settings": "Paramètres", "logout": "Déconnexion", "profile": "Mon Profil",
                "change_pwd": "Mot de passe", "settings_label": "Paramètres",
                "error_unexpected": "Une erreur inattendue est survenue.",
                "error_network": "Erreur réseau."
            },
            "en": {
                "title": "Secretary", "welcome": "Welcome", "dashboard": "Dashboard",
                "patients": "Patients", "patient_add": "Add Patient", "patient_list": "Patient List",
                "cs": "Consultations", "cs_add": "New CS", "cs_list": "CS List",
                "stock": "Stock", "stock_add": "Add Stock", "stock_list": "Inventory",
                "caisse": "Cashier", "tx_add": "New Trans.", "tx_list": "History",
                "settings": "Settings", "logout": "Logout", "profile": "My Profile",
                "change_pwd": "Password", "settings_label": "Settings",
                "error_unexpected": "An unexpected error occurred.",
                "error_network": "Network error."
            }
        }

        self._init_ui()
        QTimer.singleShot(50, self.show_dashboard)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("background-color: #2c3e50; color: white; border-right: 1px solid #34495e;")
        self._build_sidebar()
        main_layout.addWidget(self.sidebar)

        # Zone Centrale
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        
        # Topbar
        self._build_topbar()
        central_layout.addWidget(self.topbar)
        
        # Contenu
        self.content_area = QStackedWidget()
        central_layout.addWidget(self.content_area)
        
        # Initialiser les placeholders
        self._init_placeholders()
        
        main_layout.addWidget(central_widget)

    def _init_placeholders(self):
        """Initialise les placeholders pour chaque vue possible."""
        self.page_placeholders = {}
        for name in ("dashboard", "patient_add", "patient_list", "cs_form", "cs_list",
                     "stock_form", "stock_list", "tx_form", "tx_list"):
            w = QWidget()
            l = QVBoxLayout(w)
            l.addWidget(QLabel(f"Chargement... [{name}]"))
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            setattr(w, "_is_placeholder", True)
            self.page_placeholders[name] = w
            # On ne les ajoute pas tout de suite au StackedWidget pour éviter de l'encombrer,
            # ou on peut les ajouter si on veut préserver l'ordre.

    def _build_sidebar(self):
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. En-tête Sidebar
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_frame.setStyleSheet("background-color: #1abc9c;") 
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 0, 10, 0)

        self.logo_lbl = QLabel("🏥") 
        img_path = os.path.join("assets", "glostone-kare.png")
        if os.path.exists(img_path):
            pix = QPixmap(img_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_lbl.setPixmap(pix)
            self.logo_lbl.setText("")
        
        self.title_lbl = QLabel(self.texts[self.current_locale]["title"])
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 16px; border: none;")
        
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("☰")
        self.toggle_btn.setStyleSheet("border: none; color: white; font-size: 16px;")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        header_layout.addWidget(self.logo_lbl)
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_btn)
        
        layout.addWidget(header_frame)

        # 2. Menus
        self.scroll_menu = QScrollArea()
        self.scroll_menu.setWidgetResizable(True)
        self.scroll_menu.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_menu.setStyleSheet("background: transparent;")
        
        menu_content = QWidget()
        self.menu_layout = QVBoxLayout(menu_content)
        self.menu_layout.setContentsMargins(0, 10, 0, 10)
        self.menu_layout.setSpacing(5)
        
        self.menu_buttons = {}
        self.sub_menus = {}

        # Ajout des items et sauvegarde des références des boutons principaux
        self.dash_btn = self._add_menu_item("dashboard", "dashboard", [], self.show_dashboard, icon_path="assets/dashboard.png")
        
        self.pats_btn = self._add_menu_item("patients", "patients", [
            ("patient_add", "patient_add", self.show_patient_add),
            ("patient_list", "patient_list", self.show_patient_list)
        ], icon_path="assets/patient.png")
        
        self.cs_btn = self._add_menu_item("cs", "cs", [
            ("cs_add", "cs_add", lambda: self.show_cs_form(None)),
            ("cs_list", "cs_list", self.show_cs_list)
        ], icon_path="assets/cs.png")
        
        self.stock_btn = self._add_menu_item("stock", "stock", [
            ("stock_add", "stock_add", self.show_stock_form),
            ("stock_list", "stock_list", self.show_stock_list)
        ], icon_path="assets/stock.png")
        
        self.caisse_btn = self._add_menu_item("caisse", "caisse", [
            ("tx_add", "tx_add", self.show_tx_form),
            ("tx_list", "tx_list", self.show_tx_list)
        ], icon_path="assets/caisse.png")

        self.menu_layout.addStretch()
        self.scroll_menu.setWidget(menu_content)
        layout.addWidget(self.scroll_menu)

        # 3. Bas de Sidebar
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 10)
        
        self.settings_btn = QPushButton(self.texts[self.current_locale]["settings_label"])
        self.settings_btn.setStyleSheet("""
            QPushButton { text-align: left; padding: 12px 20px; border: none; color: #bdc3c7; background-color: transparent; }
            QPushButton:hover { color: white; background-color: #34495e; }
        """)
        self.settings_btn.clicked.connect(self._show_settings)
        bottom_layout.addWidget(self.settings_btn)
        
        layout.addWidget(bottom_frame)

    def _add_menu_item(self, key, label_key, sub_items, callback=None, icon_path=None):
        btn = QPushButton(self.texts[self.current_locale][label_key])
        if icon_path and os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            
        btn.setStyleSheet("""
            QPushButton { text-align: left; padding: 12px 15px; border: none; color: #ecf0f1; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #34495e; border-left: 4px solid #1abc9c; }
            QPushButton:checked { background-color: #2980b9; font-weight: bold; }
        """)
        btn.setCheckable(True)
        self.menu_buttons[key] = btn
        
        if sub_items:
            sub_container = QWidget()
            sub_layout = QVBoxLayout(sub_container)
            sub_layout.setContentsMargins(25, 0, 0, 0)
            sub_layout.setSpacing(2)
            sub_container.setVisible(False)
            
            for sub_key, sub_label_key, sub_cb in sub_items:
                sub_btn = QPushButton(self.texts[self.current_locale][sub_label_key])
                sub_btn.setStyleSheet("""
                    QPushButton { text-align: left; padding: 8px; border: none; color: #bdc3c7; font-size: 13px; }
                    QPushButton:hover { color: white; background-color: #34495e; }
                """)
                sub_btn.clicked.connect(sub_cb)
                sub_layout.addWidget(sub_btn)
            
            self.sub_menus[key] = sub_container
            btn.clicked.connect(lambda: self._toggle_submenu(key))
            
            self.menu_layout.addWidget(btn)
            self.menu_layout.addWidget(sub_container)
        else:
            if callback:
                btn.clicked.connect(callback)
            self.menu_layout.addWidget(btn)
            
        return btn

    def _toggle_submenu(self, key):
        container = self.sub_menus.get(key)
        if container:
            is_visible = container.isVisible()
            container.setVisible(not is_visible)
            for k, b in self.menu_buttons.items():
                b.setChecked(k == key)

    def _build_topbar(self):
        self.topbar = QFrame()
        self.topbar.setFixedHeight(60)
        self.topbar.setStyleSheet("background-color: white; border-bottom: 1px solid #e0e0e0;")
        layout = QHBoxLayout(self.topbar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        full_name = self._get_user_name()
        self.lbl_welcome = QLabel(f"{self.texts[self.current_locale]['welcome']}, {full_name}")
        self.lbl_welcome.setStyleSheet("font-size: 16px; color: #333;")
        layout.addWidget(self.lbl_welcome)
        
        layout.addStretch()
        
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["FR", "EN"])
        self.combo_lang.setCurrentIndex(0 if self.current_locale == "fr" else 1)
        self.combo_lang.currentIndexChanged.connect(self._change_language)
        layout.addWidget(self.combo_lang)
        
        self.btn_profile = QToolButton()
        self.btn_profile.setText("👤")
        self.btn_profile.setStyleSheet("border: none; font-size: 20px; padding: 5px;")
        self.btn_profile.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        profile_menu = QMenu(self.btn_profile)
        action_profile = QAction(self.texts[self.current_locale]["profile"], self)
        action_profile.triggered.connect(self._show_edit_profile)
        profile_menu.addAction(action_profile)
        
        action_pwd = QAction(self.texts[self.current_locale]["change_pwd"], self)
        action_pwd.triggered.connect(self._show_change_password)
        profile_menu.addAction(action_pwd)
        
        profile_menu.addSeparator()
        
        action_logout = QAction(self.texts[self.current_locale]["logout"], self)
        action_logout.triggered.connect(self._logout)
        profile_menu.addAction(action_logout)
        
        self.btn_profile.setMenu(profile_menu)
        layout.addWidget(self.btn_profile)

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.setFixedWidth(60)
            self.logo_lbl.hide()
            self.title_lbl.hide()
            for btn in self.menu_buttons.values():
                btn.setText("")
            for sub in self.sub_menus.values():
                sub.hide()
            self.settings_btn.setText("")
        else:
            self.sidebar.setFixedWidth(220)
            self.logo_lbl.show()
            self.title_lbl.show()
            self._update_ui_texts() 
        self.sidebar_expanded = not self.sidebar_expanded

    def _change_language(self, index):
        self.current_locale = "fr" if index == 0 else "en"
        self._update_ui_texts()
        
        # Update Dashboard Widget if active
        current = self.content_area.currentWidget()
        if isinstance(current, SecretaireHomeWidget):
            # Passer self.current_locale, qui est une string
            current.update_locale(self.current_locale)

    def _update_ui_texts(self):
        t = self.texts[self.current_locale]
        self.title_lbl.setText(t["title"])
        self.settings_btn.setText(t["settings_label"] if self.sidebar_expanded else "")
        self.lbl_welcome.setText(f"{t['welcome']}, {self._get_user_name()}")
        
        menu_keys = ["dashboard", "patients", "cs", "stock", "caisse"]
        for key in menu_keys:
            if self.sidebar_expanded:
                self.menu_buttons[key].setText(t[key])
            else:
                self.menu_buttons[key].setText("")

    # --- Gestion des Widgets / Navigation ---

    def _replace_page_widget(self, page_key: str, new_widget: QWidget):
        logger.debug("Replacing page widget for key: %s", page_key)
        
        # 1. Si un ancien widget existe pour cette clé, le retirer
        old_widget = self.page_placeholders.get(page_key)
        
        if old_widget is not None:
            try:
                if self.content_area.indexOf(old_widget) != -1:
                    self.content_area.removeWidget(old_widget)
                    # Si c'est un placeholder temporaire, on le supprime
                    if getattr(old_widget, "_is_placeholder", False):
                        old_widget.deleteLater()
            except Exception as e:
                logger.warning(f"Erreur lors du retrait de l'ancien widget: {e}")

        # 2. Ajouter le nouveau widget au StackedWidget
        self.content_area.addWidget(new_widget)
        
        # 3. Mettre à jour la référence
        self.page_placeholders[page_key] = new_widget
        
        # 4. Afficher le nouveau widget
        try:
            self.content_area.setCurrentWidget(new_widget)
        except Exception as e:
            logger.exception(f"Erreur lors de l'affichage du widget: {e}")

    def _is_widget_alive(self, widget):
        try:
            if widget is None: return False
            # Le test simple de parent() suffit souvent pour voir si l'objet C++ est vivant
            _ = widget.parent()
            return True
        except RuntimeError:
            return False
        except Exception:
            return False

    def show_dashboard(self):
        self._set_active("dashboard")
        view_key = "dashboard"
        
        if SecretaireHomeWidget:
            view = self.view_instances.get(view_key)
            # Si la vue n'existe pas ou est détruite
            if view is None or not self._is_widget_alive(view):
                # Correction: passer self.current_locale (str)
                view = SecretaireHomeWidget(self.content_area, self.resolver, self.current_locale)
                self.view_instances[view_key] = view
                self._replace_page_widget(view_key, view)
            else:
                # Si elle existe, juste rafraîchir
                if hasattr(view, "refresh_data"):
                    view.refresh_data()
                self.content_area.setCurrentWidget(view)
        else:
            QMessageBox.warning(self, "Erreur", "Module Dashboard non disponible.")

    def show_patient_list(self):
        self._set_active("patients")
        view_key = "patient_list"
        
        if PatientListView is None:
            QMessageBox.warning(self, "Erreur", "Module Patient non chargé.")
            return

        view = self.view_instances.get(view_key)
        if view is None or not self._is_widget_alive(view):
            try:
                # Utilisation du resolver pour obtenir le patient_controller
                ctrl = self.resolver.patient_controller()
                view = PatientListView(self.content_area, ctrl)
                self.view_instances[view_key] = view
                self._replace_page_widget(view_key, view)
            except Exception as e:
                logger.error(f"Erreur création PatientList: {e}")
                return
        
        self.content_area.setCurrentWidget(view)
        if hasattr(view, "refresh"): view.refresh()

    # ... (Ajouter show_cs_list, show_stock_list, show_tx_list sur le même modèle) ...
    def show_patient_add(self):
        self._set_active("patients")
        view_key = "patient_add"
        
        if PatientFormView is None: return

        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            try:
                form = PatientFormView(
                    parent=self.content_area,
                    controllers=self.controllers_obj, # On passe l'objet racine si nécessaire
                    current_user=self.user,
                    patient_id=None,
                    on_save=lambda code: self.show_cs_form(code) # Workflow: Patient -> CS
                )
                self.view_instances[view_key] = form
                self._replace_page_widget(view_key, form)
            except Exception as e:
                logger.error(f"Erreur creation PatientForm: {e}")
                return
        
        self.content_area.setCurrentWidget(self.view_instances[view_key])

    def show_cs_list(self):
        self._set_active("cs")
        view_key = "cs_list"
        
        if CSListView is None: return

        view = self.view_instances.get(view_key)
        if view is None or not self._is_widget_alive(view):
            try:
                ctrl = self.resolver.consultation_spirituel_controller()
                view = CSListView(self.content_area, ctrl)
                self.view_instances[view_key] = view
                self._replace_page_widget(view_key, view)
            except Exception as e:
                logger.error(f"Erreur creation CSListView: {e}")
                return
                
        self.content_area.setCurrentWidget(view)
        if hasattr(view, "refresh"): view.refresh()

    def show_cs_form(self, patient_code: Optional[str] = None):
        self._set_active("cs")
        view_key = f"cs_form_{patient_code or 'new'}"
        
        if CSFormView is None: return

        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            try:
                form = CSFormView(
                    parent=self,
                    controllers=self.controllers_obj,
                    consultation=None,
                    on_save=lambda: self.show_cs_list()
                )
                if patient_code:
                    # Logique pour pré-remplir si votre formulaire le supporte
                    if hasattr(form, "entry_code"):
                        form.entry_code.setText(patient_code)
                        if hasattr(form, "load_patient"): form.load_patient()
                        
                self.view_instances[view_key] = form
                self._replace_page_widget("cs_form", form) # On réutilise souvent un slot générique
            except Exception as e:
                logger.error(f"Erreur creation CSFormView: {e}")
                return
        
        # Attention: ici j'utilise une clé générique pour l'affichage simple
        view = self.view_instances.get(view_key) or self.page_placeholders.get("cs_form")
        if view: self.content_area.setCurrentWidget(view)

    def show_stock_list(self):
        self._set_active("stock")
        view_key = "stock_list"
        
        if StockListView is None: return

        view = self.view_instances.get(view_key)
        if view is None or not self._is_widget_alive(view):
            try:
                ctrl = self.resolver.stock_controller()
                view = StockListView(self.content_area, ctrl)
                self.view_instances[view_key] = view
                self._replace_page_widget(view_key, view)
            except Exception as e:
                logger.error(f"Erreur creation StockListView: {e}")
                return
        self.content_area.setCurrentWidget(view)
        if hasattr(view, "refresh"): view.refresh()

    def show_stock_form(self):
        self._set_active("stock")
        view_key = "stock_form"
        if StockFormView is None: return
        
        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            try:
                ctrl = self.resolver.stock_controller()
                form = StockFormView(self, ctrl, lambda: self.show_stock_list())
                self.view_instances[view_key] = form
                self._replace_page_widget(view_key, form)
            except Exception as e:
                logger.error(f"Erreur creation StockFormView: {e}")
                return
        self.content_area.setCurrentWidget(self.view_instances[view_key])

    def show_tx_list(self):
        self._set_active("caisse")
        view_key = "tx_list"
        if CaisseListView is None: return

        view = self.view_instances.get(view_key)
        if view is None or not self._is_widget_alive(view):
            try:
                # On passe les contrôleurs spécifiques requis par la vue Caisse
                view = CaisseListView(
                    self.content_area,
                    self.resolver.caisse_controller(),
                    self.resolver.caisse_retrait_controller(),
                    self.resolver.patient_controller(),
                    self.resolver.pharmacy_controller(),
                    self.current_locale
                )
                self.view_instances[view_key] = view
                self._replace_page_widget(view_key, view)
            except Exception as e:
                logger.error(f"Erreur creation CaisseListView: {e}")
                return
        self.content_area.setCurrentWidget(view)
        if hasattr(view, "refresh"): view.refresh()

    def show_tx_form(self):
        self._set_active("caisse")
        view_key = "tx_form"
        if CaisseFormView is None: return
        
        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            try:
                form = CaisseFormView(
                    self,
                    self.controllers_obj, # CaisseFormView a souvent besoin de l'objet controllers global
                    self.resolver.patient_controller(),
                    self.resolver.pharmacy_controller(),
                    self.resolver.medical_record_controller(),
                    lambda: self.show_tx_list()
                )
                self.view_instances[view_key] = form
                self._replace_page_widget(view_key, form)
            except Exception as e:
                logger.error(f"Erreur creation CaisseFormView: {e}")
                return
        self.content_area.setCurrentWidget(self.view_instances[view_key])

    def _set_active(self, key):
        if key in self.menu_buttons:
            for k, btn in self.menu_buttons.items():
                btn.setChecked(k == key)

    # --- Paramètres et Profil ---
    def _show_settings(self):
        QMessageBox.information(self, self.texts[self.current_locale]["settings"], "Module Paramètres à venir.")

    def _show_edit_profile(self):
        QMessageBox.information(self, "Profil", "Module Édition Profil à venir.")

    def _show_change_password(self):
        QMessageBox.information(self, "Sécurité", "Module Changement Mot de Passe à venir.")

    def _get_user_name(self):
        if isinstance(self.user, dict):
            return self.user.get("username", "User")
        return getattr(self.user, "username", "User")

    def _logout(self):
        if self.on_logout:
            self.on_logout()