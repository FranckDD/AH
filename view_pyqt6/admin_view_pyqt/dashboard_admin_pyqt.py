from PyQt6 import QtWidgets, QtCore, QtGui
from datetime import date
import typing
import logging
from .user_form_pyqt import UserFormDialog  # Import corrigé

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class KpiCard(QtWidgets.QFrame):
    def __init__(self, title: str, value: typing.Any, note: str | None = None, enabled: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("kpi_card")
        self.setStyleSheet("""
            QFrame#kpi_card {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E7FF;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
        """)
        self.setMinimumWidth(220)
        self.setMaximumHeight(160)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        header = QtWidgets.QHBoxLayout()
        lbl_title = QtWidgets.QLabel(title)
        lbl_title.setStyleSheet("font-size:14pt; color:#6B7280; font-family: Roboto, Arial, sans-serif;")
        lbl_title.setAccessibleName(title)
        header.addWidget(lbl_title)
        header.addStretch()
        if not enabled:
            badge = QtWidgets.QLabel("Non implémenté")
            badge.setStyleSheet("font-size:10pt; color:#9CA3AF; background-color: #F3F4F6; border-radius: 4px; padding: 4px 8px;")
            header.addWidget(badge)
        layout.addLayout(header)

        lbl_value = QtWidgets.QLabel(str(value))
        lbl_value.setStyleSheet("font-size:26pt; font-weight:600; color:#1F2937; font-family: Roboto, Arial, sans-serif;")
        layout.addWidget(lbl_value, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        if note:
            lbl_note = QtWidgets.QLabel(note)
            lbl_note.setStyleSheet("font-size:11pt; color:#9CA3AF; font-family: Roboto, Arial, sans-serif;")
            layout.addWidget(lbl_note, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

class DashboardAdminView(QtWidgets.QWidget):
    def __init__(self, controller, current_user=None, on_logout: typing.Callable[..., typing.Any] | None = None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_user = current_user
        self.on_logout = on_logout
        self.user_controller = controller.user_controller() if hasattr(controller, "user_controller") else None
        self.specialty_map = {}  # Cache pour spécialités

        self.setWindowTitle("A.H.2 — Administration")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #F9FAFB; font-family: Roboto, Arial, sans-serif;")

        # Persistance sidebar
        from PyQt6.QtCore import QSettings
        settings = QSettings("MyApp", "AdminDashboard")
        self.sidebar_expanded = settings.value("sidebar_expanded", True, type=bool)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Topbar avec logo
        topbar = QtWidgets.QFrame()
        topbar.setStyleSheet("background:#059669; padding:12px;")
        topbar.setFixedHeight(64)
        t_layout = QtWidgets.QHBoxLayout(topbar)
        t_layout.setContentsMargins(12, 0, 12, 0)
        self.toggle_btn = QtWidgets.QPushButton("⮜" if self.sidebar_expanded else "⮞")
        self.toggle_btn.setToolTip("Réduire le menu" if self.sidebar_expanded else "Étendre le menu")
        self.toggle_btn.setStyleSheet("background: transparent; color: white; border: none; font-size: 18pt;")
        self.toggle_btn.setFixedWidth(40)
        self.toggle_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.toggle_btn.setAccessibleName("Basculer menu")
        self.toggle_btn.clicked.connect(self._toggle_sidebar)
        t_layout.addWidget(self.toggle_btn)

        # Logo et titre
        logo_label = QtWidgets.QLabel()
        logo_pixmap = QtGui.QPixmap("assets/ahlogo.png")  
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(40, 40, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
        else:
            logo_label.setText("Logo")  # Fallback si le logo n'est pas trouvé
        logo_label.setStyleSheet("margin-right: 8px;")
        logo_label.setAccessibleName("Logo application")
        t_layout.addWidget(logo_label)

        app_lbl = QtWidgets.QLabel("A.H.2 — Administration")
        app_lbl.setStyleSheet("font-weight:700; color:white; font-size:15pt;")
        app_lbl.setAccessibleName("Titre application")
        t_layout.addWidget(app_lbl)
        t_layout.addStretch()
        user_lbl = QtWidgets.QLabel(f"Connecté comme: {current_user.get('username', 'Admin')}" if current_user else "")
        user_lbl.setStyleSheet("color: white; font-size: 12pt;")
        user_lbl.setAccessibleName("Utilisateur connecté")
        t_layout.addWidget(user_lbl)
        btn_logout = QtWidgets.QPushButton("🚪 Déconnexion")
        btn_logout.setStyleSheet("background: transparent; color: white; border: none; font-size: 12pt; padding: 8px 16px;")
        btn_logout.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_logout.setAccessibleName("Déconnexion")
        btn_logout.clicked.connect(self._logout)
        t_layout.addWidget(btn_logout)
        main_layout.addWidget(topbar)

        # Body
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        body_widget = QtWidgets.QWidget()
        body = QtWidgets.QHBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        scroll.setWidget(body_widget)
        main_layout.addWidget(scroll)

        # Sidebar (déroulante et réductible)
        self.expanded_width = 240
        self.collapsed_width = 80
        self.sidebar = QtWidgets.QFrame()
        self.sidebar.setStyleSheet("background: #FFFFFF; border-right: 1px solid #E0E7FF;")
        self.sidebar.setFixedWidth(self.expanded_width if self.sidebar_expanded else self.collapsed_width)
        s_scroll = QtWidgets.QScrollArea()  # Sidebar déroulante
        s_scroll.setWidgetResizable(True)
        s_scroll.setStyleSheet("border: none; background: #FFFFFF;")
        s_widget = QtWidgets.QWidget()
        s_layout = QtWidgets.QVBoxLayout(s_widget)
        s_layout.setContentsMargins(12, 20, 12, 12)
        s_layout.setSpacing(6)
        s_scroll.setWidget(s_widget)
        self.sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar)
        self.sidebar_layout.addWidget(s_scroll)
        self.menu_buttons = {}

        self.menu_map = {
            "Synthèses": (self.show_overview, "📈"),
            "Statistiques": (self.show_statistics, "📊"),
            "Utilisateurs": (self.show_user_management, "👤"),
        }

        for name, (fn, icon) in self.menu_map.items():
            b = QtWidgets.QPushButton(f"{icon}  {name}" if self.sidebar_expanded else icon)
            b.setCheckable(True)
            b.setFlat(True)
            b.setToolTip(name)
            b.setAccessibleName(name)
            b.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 14px 16px;
                    border-radius: 8px;
                    color: #1F2937;
                    font-size: 14pt;
                    font-weight: 500;
                    background: transparent;
                }
                QPushButton:hover {
                    background: #F0FDF4;
                }
                QPushButton:checked {
                    background: #D1FAE5;
                    color: #059669;
                }
                QPushButton[collapsed="true"] {
                    font-size: 18pt;
                    text-align: center;
                    padding: 14px;
                    border-radius: 8px;
                    background: transparent;
                }
                QPushButton[collapsed="true"]:hover {
                    background: #F0FDF4;
                }
                QPushButton[collapsed="true"]:checked {
                    background: #D1FAE5;
                    color: #059669;
                }
            """)
            b.setProperty("collapsed", not self.sidebar_expanded)
            b.clicked.connect(lambda _, f=fn: self._switch(f))
            s_layout.addWidget(b)
            self.menu_buttons[name] = b
        s_layout.addStretch()
        body.addWidget(self.sidebar)

        # Content area
        self.stack = QtWidgets.QStackedWidget()
        body.addWidget(self.stack, stretch=1)

        # Pages
        self.page_overview = QtWidgets.QWidget()
        self.page_stats = QtWidgets.QWidget()
        self.page_users = QtWidgets.QWidget()

        for p in (self.page_overview, self.page_stats, self.page_users):
            self.stack.addWidget(p)

        self._build_overview_page()
        self._build_stats_page()
        self._build_users_page()

        # Default
        self._switch(self.show_user_management)
        self._load_specialties_map()

    def _toggle_sidebar(self):
        self.sidebar_expanded = not self.sidebar_expanded
        target_width = self.expanded_width if self.sidebar_expanded else self.collapsed_width

        animation = QtCore.QPropertyAnimation(self.sidebar, b"minimumWidth")
        animation.setDuration(300)
        animation.setStartValue(self.sidebar.width())
        animation.setEndValue(target_width)
        animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutQuad)
        animation.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

        self.toggle_btn.setText("⮜" if self.sidebar_expanded else "⮞")
        self.toggle_btn.setToolTip("Réduire le menu" if self.sidebar_expanded else "Étendre le menu")
        for name, b in self.menu_buttons.items():
            icon = self.menu_map[name][1]
            text = f"{icon}  {name}" if self.sidebar_expanded else icon
            b.setText(text)
            b.setProperty("collapsed", not self.sidebar_expanded)
            b.style().unpolish(b)
            b.style().polish(b)
        from PyQt6.QtCore import QSettings
        settings = QSettings("MyApp", "AdminDashboard")
        settings.setValue("sidebar_expanded", self.sidebar_expanded)

    def _try_call(self, name: str, *args, default=None, **kwargs):
        targets = []
        if self.user_controller:
            targets.append(self.user_controller)
        if getattr(self.controller, "admin_controller", None):
            targets.append(self.controller.admin_controller)
        if getattr(self.controller, "api_proxy", None):
            targets.append(self.controller.api_proxy)
        if getattr(self.controller, "remote_gateway", None):
            targets.append(self.controller.remote_gateway)
        if getattr(self.controller, "gateway", None):
            targets.append(self.controller.gateway)
        for attr in ("activity_controller", "prescription_controller", "medical_record_controller"):
            t = getattr(self.controller, attr, None)
            if t:
                targets.append(t)
        targets.append(self.controller)

        for t in targets:
            fn = getattr(t, name, None)
            if callable(fn):
                try:
                    result = fn(*args, **kwargs)
                    #logger.debug(f"Successfully called {name} on {t.__class__.__name__}: {result}")
                    return result
                except Exception as e:
                    logger.error(f"Error calling {name} on {t.__class__.__name__}: {e}")
                    continue
        logger.warning(f"No valid target found for {name}")
        return default

    def _get_attr(self, obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _logout(self):
        if callable(self.on_logout):
            self.on_logout()

    def _switch(self, fn):
        for b in self.menu_buttons.values():
            b.setChecked(False)
        self.menu_buttons[[name for name, (f, _) in self.menu_map.items() if f == fn][0]].setChecked(True)
        fn()

    def _build_overview_page(self):
        l = QtWidgets.QVBoxLayout(self.page_overview)
        l.setContentsMargins(24, 24, 24, 24)
        hdr = QtWidgets.QLabel("Synthèse du Jour")
        hdr.setStyleSheet("font-size:22pt; font-weight:700; color: #1F2937;")
        hdr.setAccessibleName("Synthèse du Jour")
        l.addWidget(hdr)

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(20)
        cards.addWidget(KpiCard("Utilisateurs actifs", 0, "Total aujourd'hui", enabled=False))
        cards.addWidget(KpiCard("Rendez-vous", 0, "Planifiés aujourd'hui", enabled=False))
        cards.addWidget(KpiCard("Activité système", 0, "Actions récentes", enabled=False))
        l.addLayout(cards)
        l.addStretch()

    def show_overview(self):
        self.stack.setCurrentWidget(self.page_overview)

    def _build_stats_page(self):
        l = QtWidgets.QVBoxLayout(self.page_stats)
        l.setContentsMargins(24, 24, 24, 24)
        hdr = QtWidgets.QLabel("Statistiques")
        hdr.setStyleSheet("font-size:22pt; font-weight:700; color: #1F2937;")
        hdr.setAccessibleName("Statistiques")
        l.addWidget(hdr)
        l.addWidget(QtWidgets.QLabel("Statistiques non implémentées"))
        l.addStretch()

    def show_statistics(self):
        self.stack.setCurrentWidget(self.page_stats)

    def _load_specialties_map(self):
        try:
            specs = self._try_call("list_speciality", default=[]) or []
            if isinstance(specs, dict):
                for k in ("specialties", "data", "items", "results"):
                    if k in specs and isinstance(specs[k], list):
                        specs = specs[k]
                        break
                else:
                    found = []
                    for v in specs.values():
                        if isinstance(v, list):
                            found = v
                            break
                    specs = found or []

            if not isinstance(specs, (list, tuple)):
                logger.error(f"list_speciality returned non-iterable response: {specs!r}")
                specs = []

            self.specialty_map = {}
            for s in specs:
                spec_id = self._get_attr(s, "specialty_id", None)
                name = (self._get_attr(s, "name", None)
                        or self._get_attr(s, "specialty_name", None)
                        or str(s))
                if spec_id:
                    self.specialty_map[spec_id] = name
        except Exception as e:
            logger.exception(f"Error loading specialties map: {e}")
            self.specialty_map = {}

    def _build_users_page(self):
        l = QtWidgets.QVBoxLayout(self.page_users)
        l.setContentsMargins(24, 24, 24, 24)
        hdr = QtWidgets.QLabel("Gestion des Utilisateurs")
        hdr.setStyleSheet("font-size:22pt; font-weight:700; color: #1F2937;")
        hdr.setAccessibleName("Gestion des Utilisateurs")
        l.addWidget(hdr)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(10)
        self.input_search = QtWidgets.QLineEdit()
        self.input_search.setPlaceholderText("Rechercher… (id, username, nom, rôle)")
        self.input_search.setStyleSheet("""
            QLineEdit {
                border-radius: 8px; 
                padding: 10px; 
                border: 1px solid #D1D5DB; 
                font-size: 13pt;
                color: #1F2937;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 1px solid #059669;
                box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.2);
            }
            QLineEdit::placeholder {
                color: #6B7280;
            }
        """)
        self.input_search.setAccessibleName("Rechercher un utilisateur")
        self.input_search.returnPressed.connect(self._load_users)
        toolbar.addWidget(self.input_search)
        btn_search = QtWidgets.QPushButton("🔍 Rechercher")
        btn_search.setStyleSheet("""
            QPushButton {
                background: #059669; 
                color: white; 
                border-radius: 8px; 
                padding: 10px 16px; 
                font-size: 13pt;
            }
            QPushButton:hover {
                background: #047857;
            }
        """)
        btn_search.setAccessibleName("Lancer la recherche")
        btn_search.clicked.connect(self._load_users)
        toolbar.addWidget(btn_search)
        btn_create = QtWidgets.QPushButton("➕ Créer")
        btn_create.setStyleSheet(btn_search.styleSheet())
        btn_create.setAccessibleName("Créer un nouvel utilisateur")
        btn_create.clicked.connect(self._create_user)
        toolbar.addWidget(btn_create)
        self.btn_edit = QtWidgets.QPushButton("✏️ Éditer")
        self.btn_edit.setStyleSheet(btn_search.styleSheet())
        self.btn_edit.setAccessibleName("Éditer l'utilisateur sélectionné")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._edit_user)
        toolbar.addWidget(self.btn_edit)
        self.btn_delete = QtWidgets.QPushButton("🗑️ Supprimer")
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: #DC2626; 
                color: white; 
                border-radius: 8px; 
                padding: 10px 16px; 
                font-size: 13pt;
            }
            QPushButton:hover {
                background: #B91C1C;
            }
        """)
        self.btn_delete.setAccessibleName("Supprimer l'utilisateur sélectionné")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_user)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        l.addLayout(toolbar)

        l.addSpacing(20)

        self.table_users = QtWidgets.QTableWidget(0, 5)
        self.table_users.setHorizontalHeaderLabels(["ID", "Username", "Rôle", "Spécialité", "Actif"])
        self.table_users.setAccessibleName("Tableau des utilisateurs")
        header = self.table_users.horizontalHeader()
        if header is not None:
            header.setStyleSheet("QHeaderView::section { background-color: #F3F4F6; font-weight: bold; color: #1F2937; padding: 10px; font-size: 13pt; }")
            header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table_users.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_users.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table_users.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E0E7FF;
                gridline-color: #E0E7FF;
                selection-background-color: #D1FAE5;
                font-size: 13pt;
                color: #1F2937;
                background-color: #FFFFFF;
            }
            QTableWidget::item {
                padding: 12px;
            }
            QTableWidget::item:selected {
                background-color: #D1FAE5;
                color: #1F2937;
            }
        """)
        self.table_users.setAlternatingRowColors(True)
        self.table_users.setShowGrid(False)
        v_header = self.table_users.verticalHeader()
        if v_header is not None:
            v_header.setVisible(False)
        self.table_users.itemSelectionChanged.connect(self._on_user_select)
        l.addWidget(self.table_users)
        l.addStretch()
        self._load_users()

    def show_user_management(self):
        self.stack.setCurrentWidget(self.page_users)
        self._load_users()

    def _load_users(self):
        term = self.input_search.text().strip()
        try:
            if self.user_controller:
                users = self.user_controller.search_users(term) if term else self.user_controller.list_users()
            else:
                users = self._try_call("search_users", term, default=[]) if term else self._try_call("list_users", default=[])
            #logger.debug(f"Loaded users: {users}")
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Erreur")
            msg_box.setText("Impossible de charger les utilisateurs.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    font-size: 13pt;
                }
                QLabel {
                    color: #1F2937;
                }
                QPushButton {
                    background: #059669;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13pt;
                }
                QPushButton:hover {
                    background: #047857;
                }
            """)
            msg_box.exec()
            users = []

        if not isinstance(users, typing.Iterable):
            users = []
            logger.warning("Users response is not iterable")

        self.table_users.setRowCount(0)
        for i, u in enumerate(users):
            self.table_users.insertRow(i)
            user_id = str(self._get_attr(u, "user_id", ""))
            self.table_users.setItem(i, 0, QtWidgets.QTableWidgetItem(user_id))
            self.table_users.setItem(i, 1, QtWidgets.QTableWidgetItem(self._get_attr(u, "username", "")))
            role = self._get_attr(self._get_attr(u, "application_role", {}), "role_name", "") or self._get_attr(u, "role_name", "")
            self.table_users.setItem(i, 2, QtWidgets.QTableWidgetItem(role))
            spec_id = self._get_attr(u, "specialty_id", None)
            spec = (self.specialty_map.get(spec_id, "N/A")
                    if spec_id and self.specialty_map
                    else self._get_attr(self._get_attr(u, "specialty", {}), "name", "")
                    or self._get_attr(u, "specialty_name", "")
                    or self._get_attr(self._get_attr(u, "specialty", {}), "specialty_name", "")
                    or "N/A")
            self.table_users.setItem(i, 3, QtWidgets.QTableWidgetItem(spec))
            is_active = self._get_attr(u, "is_active", False)
            active_text = "Oui" if is_active is True else "Non"
            self.table_users.setItem(i, 4, QtWidgets.QTableWidgetItem(active_text))

        self.table_users.resizeColumnsToContents()
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)

    def _on_user_select(self):
        selected = self.table_users.selectedItems()
        self.btn_edit.setEnabled(len(selected) > 0)
        self.btn_delete.setEnabled(len(selected) > 0)

    def _create_user(self):
        dialog = UserFormDialog(self, self.controller, on_save_callback=self._load_users)
        dialog.exec()

    def _edit_user(self):
        sel = self.table_users.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        user_id_item = self.table_users.item(row, 0)
        user_id = user_id_item.text() if user_id_item else ""
        if not user_id:
            logger.warning("No user_id found for selected row")
            return
        try:
            user = self._try_call("get_user", user_id, default=None)
            if user:
                dialog = UserFormDialog(self, self.controller, user=user, on_save_callback=self._load_users)
                dialog.exec()
            else:
                msg_box = QtWidgets.QMessageBox(self)
                msg_box.setWindowTitle("Erreur")
                msg_box.setText("Utilisateur non trouvé.")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #FFFFFF;
                        color: #1F2937;
                        font-size: 13pt;
                    }
                    QLabel {
                        color: #1F2937;
                    }
                    QPushButton {
                        background: #059669;
                        color: white;
                        border-radius: 8px;
                        padding: 8px 16px;
                        font-size: 13pt;
                    }
                    QPushButton:hover {
                        background: #047857;
                    }
                """)
                msg_box.exec()
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {e}")
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Erreur")
            msg_box.setText(f"Erreur lors du chargement: {str(e)}")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    font-size: 13pt;
                }
                QLabel {
                    color: #1F2937;
                }
                QPushButton {
                    background: #059669;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13pt;
                }
                QPushButton:hover {
                    background: #047857;
                }
            """)
            msg_box.exec()

    def _delete_user(self):
        sel = self.table_users.selectedItems()
        if not sel:
            return
        row = sel[0].row()
        user_id_item = self.table_users.item(row, 0)
        username_item = self.table_users.item(row, 1)
        user_id = user_id_item.text() if user_id_item else ""
        username = username_item.text() if username_item else "Utilisateur inconnu"
        if not user_id:
            logger.warning("No user_id found for selected row")
            return
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText(f"Supprimer l'utilisateur '{username}' ?")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #FFFFFF;
                color: #1F2937;
                font-size: 13pt;
            }
            QLabel {
                color: #1F2937;
            }
            QPushButton {
                background: #059669;
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13pt;
            }
            QPushButton:hover {
                background: #047857;
            }
            QPushButton[text="Non"] {
                background: #E5E7EB;
                color: #1F2937;
            }
            QPushButton[text="Non"]:hover {
                background: #D1D5DB;
            }
        """)
        ok = msg_box.exec()
        if ok != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            self._try_call("delete_user", user_id)
            self._load_users()
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Succès")
            msg_box.setText("Utilisateur supprimé.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    font-size: 13pt;
                }
                QLabel {
                    color: #1F2937;
                }
                QPushButton {
                    background: #059669;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13pt;
                }
                QPushButton:hover {
                    background: #047857;
                }
            """)
            msg_box.exec()
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Erreur")
            msg_box.setText(f"Erreur lors de la suppression: {str(e)}")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    font-size: 13pt;
                }
                QLabel {
                    color: #1F2937;
                }
                QPushButton {
                    background: #059669;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 13pt;
                }
                QPushButton:hover {
                    background: #047857;
                }
            """)
            msg_box.exec()