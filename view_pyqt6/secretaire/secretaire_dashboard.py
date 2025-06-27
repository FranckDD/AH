# view_pyqt6/secretaire/secretaire_dashboard.py

import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame,
    QStackedLayout, QSizePolicy, QMenu
)
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

# sous-vues PyQt6
from view_pyqt6.patient_view.patient_form import PatientFormView
from view_pyqt6.patient_view.patient_list import PatientListView
from view_pyqt6.secretaire.cs_form import CSFormDialog
from view_pyqt6.secretaire.cs_list import CSListView
from view_pyqt6.secretaire.stock_form import StockFormDialog
from view_pyqt6.secretaire.stock_list import StockListView
from view_pyqt6.secretaire.caisse_form import CaisseFormDialog
from view_pyqt6.secretaire.caisse_list import CaisseListView


class SecretaireDashboardView(QWidget):
    def __init__(self, parent, user, controllers, on_logout=None):
        super().__init__(parent)
        self.user = user
        self.controllers = controllers
        self.on_logout = on_logout

        # controllers
        self.patient_ctrl = controllers.patient_controller
        self.cs_ctrl = controllers.consultation_spirituel_controller
        self.stock_ctrl = controllers.stock_controller
        self.tx_ctrl = controllers.caisse_controller
        self.pharmacy_ctrl = controllers.pharmacy_controller
        self.retrait_ctrl = controllers.caisse_retrait_controller

        # layout principal : sidebar + contenu
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)

        # --- Sidebar ---
        self.sidebar = QFrame(self)
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background:#F8F9FA; border-right:1px solid #E0E0E0;")
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10,10,10,10)
        side_layout.setSpacing(10)

        # toggle
        self.toggle_btn = QPushButton("<")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        side_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # logo + titre
        logo = QPixmap(os.path.join("assets","logo_light.png")).scaled(32,32,Qt.AspectRatioMode.KeepAspectRatio)
        lbl_logo = QLabel(" Secrétariat")
        lbl_logo.setPixmap(logo)
        lbl_logo.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        side_layout.addWidget(lbl_logo)

        # menu buttons
        self.menu_buttons = {}
        def add_btn(key, text, handler):
            btn = QPushButton(text)
            btn.setStyleSheet("text-align:left; background:transparent; padding:6px; color:#333;")
            btn.clicked.connect(lambda _, k=key, h=handler: (self._activate(k), h()))
            side_layout.addWidget(btn)
            self.menu_buttons[key] = btn

        add_btn("dash",        "Tableau de bord",  self.show_dashboard)
        add_btn("patient_add", "Enr. patient",     self.show_patient_add)
        add_btn("patient_list","Liste patients",   self.show_patient_list)
        add_btn("cs_add",      "Nouvelle CS",      self.show_cs_form)
        add_btn("cs_list",     "Liste CS",         self.show_cs_list)
        add_btn("stock_add",   "Stock: enr.",      self.show_stock_form)
        add_btn("stock_list",  "Stock: liste",     self.show_stock_list)
        add_btn("tx_add",      "Caisse: vente",    self.show_tx_form)
        add_btn("tx_list",     "Caisse: liste",    self.show_tx_list)

        side_layout.addStretch()
        main_layout.addWidget(self.sidebar)

        # --- Contenu empilé ---
        container = QWidget()
        self.stack = QStackedLayout(container)

        # pages embarquées
        self.pages = {
            "dash": QLabel("Dashboard Secrétaire", alignment=Qt.AlignmentFlag.AlignCenter),
            "patient_list": PatientListView(container, self.patient_ctrl),
            "cs_list": CSListView(container, self.cs_ctrl),
            "stock_list": StockListView(container, self.stock_ctrl),
            "tx_list": CaisseListView(container,
                                      self.tx_ctrl,
                                      self.retrait_ctrl,
                                      self.patient_ctrl,
                                      self.pharmacy_ctrl)
        }
        # ajouter les widgets
        for key, w in self.pages.items():
            # pour QLabel, on embed dans un widget
            if isinstance(w, QLabel):
                tmp = QWidget()
                lay = QVBoxLayout(tmp)
                lay.addWidget(w)
                w = tmp
                self.pages[key] = w
            self.stack.addWidget(w)

        main_layout.addWidget(container)

        # --- Animation de sidebar ---
        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.sidebar_expanded = True

        # topbar (avatar + logout)
        top = QFrame(self)
        top.setStyleSheet("background:#007bff; color:white;")
        top.setFixedHeight(50)
        top_layout = QHBoxLayout(top)
        top_layout.addWidget(QLabel(f"Bienvenue {self.user.full_name}", styleSheet="color:white;font-size:16px;"))
        top_layout.addStretch()
        prof_btn = QPushButton(self.user.full_name+" ▼")
        prof_btn.setStyleSheet("background:transparent;color:white;")
        prof_btn.clicked.connect(self._open_profile_menu)
        top_layout.addWidget(prof_btn)
        main_layout.setMenuBar(top)

        # menu contextuel profil
        self.profile_menu = QMenu(self)
        for label, cmd in [
            ("Paramètres", lambda: None),
            ("Éditer Profil", lambda: None),
            ("Changer MDP", lambda: None)
        ]:
            self.profile_menu.addAction(label, cmd)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction("Déconnexion", self._logout)

        # afficher la page par défaut
        self._activate("dash")
        self.stack.setCurrentIndex(list(self.pages).index("dash"))


    def toggle_sidebar(self):
        start, end = (200, 60) if self.sidebar_expanded else (60, 200)
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()
        self.sidebar_expanded = not self.sidebar_expanded


    def _activate(self, key):
        # style des boutons
        for k, btn in self.menu_buttons.items():
            btn.setStyleSheet("text-align:left; background:transparent; padding:6px; color:#333;")
        self.menu_buttons[key].setStyleSheet("text-align:left; background:#4caf50; padding:6px; color:white;")
        # page
        idx = list(self.pages).index(key)
        self.stack.setCurrentIndex(idx)


    def _open_profile_menu(self):
        btn = self.sender()
        self.profile_menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))


    def _logout(self):
        if callable(self.on_logout):
            self.on_logout()


    # — Handlers pour les vues modales —
    def show_dashboard(self):
        self._activate("dash")

    def show_patient_add(self):
        dlg = PatientFormView(self, controller=self.patient_ctrl, current_user=self.user,
                              on_save=lambda: None)
        dlg.exec()

    def show_patient_list(self):
        self._activate("patient_list")

    def show_cs_form(self):
        dlg = CSFormDialog(self, controller=self.cs_ctrl,
                           patient_ctrl=self.patient_ctrl,
                           on_save=lambda: None)
        dlg.exec()

    def show_cs_list(self):
        self._activate("cs_list")

    def show_stock_form(self):
        dlg = StockFormDialog(self, controller=self.stock_ctrl,
                              on_save=lambda: None)
        dlg.exec()

    def show_stock_list(self):
        self._activate("stock_list")

    def show_tx_form(self):
        dlg = CaisseFormDialog(self,
            controller=self.tx_ctrl,
            patient_ctrl=self.patient_ctrl,
            pharmacy_ctrl=self.pharmacy_ctrl,
            on_save=lambda: None)
        dlg.exec()

    def show_tx_list(self):
        self._activate("tx_list")
