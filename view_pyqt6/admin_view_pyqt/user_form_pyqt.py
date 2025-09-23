from PyQt6 import QtWidgets, QtCore, QtGui
import typing
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class UserFormDialog(QtWidgets.QDialog):
    def __init__(self, parent, controller, user=None, on_save_callback=None):
        super().__init__(parent)
        self.controller = controller
        self.user = user
        self.on_save_callback = on_save_callback

        # Window setup
        self.setWindowTitle("Ajouter un utilisateur" if not user else f"Éditer {self._get_attr(user, 'username', '') if user else ''}")
        self.setModal(True)
        self.setMinimumSize(500, 500)
        self.resize(600, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #F9FAFB;
                font-family: Roboto, Arial, sans-serif;
            }
            QFrame#form_card {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E7FF;
            }
        """)

        # Main layout
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        scroll.setWidget(main_widget)
        dialog_layout = QtWidgets.QVBoxLayout(self)
        dialog_layout.addWidget(scroll)

        # Form card
        form_card = QtWidgets.QFrame()
        form_card.setObjectName("form_card")
        form_layout = QtWidgets.QVBoxLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)

        # Shadow effect
        shadow = QtWidgets.QGraphicsDropShadowEffect(form_card)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 6)
        shadow.setColor(QtGui.QColor(0, 0, 0, 40))
        form_card.setGraphicsEffect(shadow)

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel("👤")
        icon.setStyleSheet("font-size: 18pt; color: #1F2937;")
        header_layout.addWidget(icon)
        header = QtWidgets.QLabel("Informations de l'utilisateur" if not user else "Modifier l'utilisateur")
        header.setStyleSheet("font-size: 18pt; font-weight: 600; color: #1F2937; margin-bottom: 10px;")
        header.setAccessibleName("Formulaire utilisateur")
        header_layout.addWidget(header)
        form_layout.addLayout(header_layout)

        # Form grid
        grid_layout = QtWidgets.QFormLayout()
        grid_layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        grid_layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Username
        self.username_edit = QtWidgets.QLineEdit()
        self.username_edit.setPlaceholderText("Entrez le nom d'utilisateur")
        self.username_edit.setToolTip("Nom d'utilisateur unique (requis)")
        self.username_edit.setAccessibleName("Nom d'utilisateur")
        self.username_edit.setStyleSheet("""
            QLineEdit {
                border-radius: 6px; 
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
            QLineEdit[invalid="true"] {
                border: 1px solid #DC2626;
            }
            QLineEdit::placeholder {
                color: #6B7280;
            }
        """)
        self.username_edit.setProperty("invalid", False)
        if user:
            self.username_edit.setText(self._get_attr(user, "username", ""))
        grid_layout.addRow("Nom d'utilisateur *", self.username_edit)

        # Password
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Entrez le mot de passe" if not user else "Laissez vide pour ne pas modifier")
        self.password_edit.setToolTip("Mot de passe (requis pour création)")
        self.password_edit.setAccessibleName("Mot de passe")
        self.password_edit.setStyleSheet(self.username_edit.styleSheet())
        self.password_edit.setProperty("invalid", False)
        grid_layout.addRow("Mot de passe *", self.password_edit)

        # Full name
        self.full_name_edit = QtWidgets.QLineEdit()
        self.full_name_edit.setPlaceholderText("Entrez le nom complet")
        self.full_name_edit.setToolTip("Nom complet (requis)")
        self.full_name_edit.setAccessibleName("Nom complet")
        self.full_name_edit.setStyleSheet(self.username_edit.styleSheet())
        self.full_name_edit.setProperty("invalid", False)
        if user:
            self.full_name_edit.setText(self._get_attr(user, "full_name", ""))
        grid_layout.addRow("Nom complet *", self.full_name_edit)

        # Postgres role
        self.pg_role_combo = QtWidgets.QComboBox()
        self.pg_role_combo.setToolTip("Rôle database (requis)")
        self.pg_role_combo.setAccessibleName("Rôle PostgreSQL")
        self.pg_role_combo.setStyleSheet("""
            QComboBox {
                border-radius: 6px; 
                padding: 10px; 
                border: 1px solid #D1D5DB; 
                font-size: 13pt;
                color: #1F2937;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #059669;
                box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.2);
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #D1D5DB;
                border-left-style: solid;
            }
            QComboBox QAbstractItemView {
                color: #1F2937;
                background-color: #FFFFFF;
                selection-background-color: #D1FAE5;
                selection-color: #1F2937;
            }
        """)
        pg_roles = ["app_admin", "app_medical", "app_secretaire", "app_laborantin"]
        self.pg_role_combo.addItems(pg_roles)
        if user:
            self.pg_role_combo.setCurrentText(self._get_attr(user, "postgres_role", pg_roles[0]))
        else:
            self.pg_role_combo.setCurrentText(pg_roles[0])
        self.pg_role_combo.currentTextChanged.connect(self._on_pg_change)
        grid_layout.addRow("Rôle PostgreSQL *", self.pg_role_combo)

        # Application role
        self.role_combo = QtWidgets.QComboBox()
        self.role_combo.setToolTip("Rôle dans l'application (requis)")
        self.role_combo.setAccessibleName("Rôle applicatif")
        self.role_combo.setStyleSheet(self.pg_role_combo.styleSheet())
        grid_layout.addRow("Rôle applicatif *", self.role_combo)

        # Specialty
        self.specialty_combo = QtWidgets.QComboBox()
        self.specialty_combo.setToolTip("Spécialité (optionnel, pour médecins)")
        self.specialty_combo.setAccessibleName("Spécialité")
        self.specialty_combo.setStyleSheet(self.pg_role_combo.styleSheet())
        grid_layout.addRow("Spécialité", self.specialty_combo)

        # Is active
        self.is_active_check = QtWidgets.QCheckBox("Compte actif")
        self.is_active_check.setStyleSheet("""
            QCheckBox {
                font-size: 13pt;
                color: #1F2937;
                margin-left: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #059669;
                border: 1px solid #059669;
                image: url(:/icons/check.png); /* Optionnel : icône de coche */
            }
            QCheckBox::indicator:unchecked {
                background-color: #E5E7EB;
            }
        """)
        self.is_active_check.setToolTip("Activer/désactiver le compte")
        self.is_active_check.setAccessibleName("Compte actif")
        if user:
            is_active = self._get_attr(user, "is_active", True)
            self.is_active_check.setChecked(bool(is_active))
        else:
            self.is_active_check.setChecked(True)
        grid_layout.addRow("", self.is_active_check)

        form_layout.addLayout(grid_layout)
        main_layout.addWidget(form_card)

        # Feedback label
        self.feedback_lbl = QtWidgets.QLabel("")
        self.feedback_lbl.setStyleSheet("""
            QLabel {
                font-size: 13pt;
                color: #1F2937;
                margin-top: 10px;
            }
            QLabel[status="error"] {
                color: #DC2626;
            }
            QLabel[status="success"] {
                color: #059669;
            }
            QLabel[status="warning"] {
                color: #D97706;
            }
        """)
        self.feedback_lbl.setAccessibleName("Messages de feedback")
        main_layout.addWidget(self.feedback_lbl)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        save_btn = QtWidgets.QPushButton("💾 Enregistrer")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #059669; 
                color: white; 
                border-radius: 8px; 
                padding: 12px 24px; 
                font-size: 13pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #047857;
            }
            QPushButton:pressed {
                background: #065F46;
            }
            QPushButton:disabled {
                background: #D1D5DB;
                color: #6B7280;
            }
        """)
        save_btn.setAccessibleName("Enregistrer utilisateur")
        save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(save_btn)

        cancel_btn = QtWidgets.QPushButton("❌ Annuler")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #E5E7EB; 
                color: #1F2937; 
                border-radius: 8px; 
                padding: 12px 24px; 
                font-size: 13pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #D1D5DB;
            }
            QPushButton:pressed {
                background: #B0B7C0;
            }
        """)
        cancel_btn.setAccessibleName("Annuler")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        # Init role combo
        self._on_pg_change(self.pg_role_combo.currentText())

        # Set initial app role if editing
        if user and self._get_attr(user, "application_role", None):
            self.role_combo.setCurrentText(self._get_attr(self._get_attr(user, "application_role", {}), "role_name", ""))

        # Populate roles and specialties
        self._populate_roles()
        self._load_specialties()

    def _get_attr(self, obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if obj is not None else default

    def _try_call(self, name: str, *args, default=None, **kwargs):
        targets = []
        if name.startswith("list_special"):
            user_ctrl = getattr(self.controller, "user_controller", None)
            if user_ctrl:
                targets.insert(0, user_ctrl)
        if self.controller:
            targets.append(self.controller)
        if getattr(self.controller, "api_proxy", None):
            targets.append(self.controller.api_proxy)
        if getattr(self.controller, "remote_gateway", None):
            targets.append(self.controller.remote_gateway)
        if getattr(self.controller, "gateway", None):
            targets.append(self.controller.gateway)
        if getattr(self.controller, "admin_controller", None):
            targets.append(self.controller.admin_controller)

        for attr in ("activity_controller", "prescription_controller", "medical_record_controller"):
            t = getattr(self.controller, attr, None)
            if t and t not in targets:
                targets.append(t)

        for t in targets:
            fn = getattr(t, name, None)
            if callable(fn):
                try:
                    result = fn(*args, **kwargs)
                    #logger.debug(f"Successfully called {name} on {t.__class__.__name__}: {result}")
                    return result
                except Exception as e:
                    logger.debug(f"call {name} on {t.__class__.__name__} failed: {e}")
                    continue
        logger.warning(f"No valid target found for {name}")
        return default

    def _populate_roles(self):
        candidates = ["list_roles", "get_all_roles", "roles", "list_role", "get_roles"]
        roles = []
        for name in candidates:
            roles = self._try_call(name, default=None)
            if roles:
                break
        roles = roles or []

        if isinstance(roles, dict) and "roles" in roles and isinstance(roles["roles"], list):
            roles = roles["roles"]
        if not isinstance(roles, (list, tuple)):
            logger.error("list_roles returned non-iterable response: %r", roles)
            roles = []

        role_names = []
        self._roles_normalized = []
        for r in roles:
            if isinstance(r, str):
                role_names.append(r)
                self._roles_normalized.append({"role_name": r, "role_id": None})
            elif isinstance(r, dict):
                rn = r.get("role_name") or r.get("name") or r.get("role")
                role_names.append(rn or str(r))
                self._roles_normalized.append(r)
            else:
                rn = getattr(r, "role_name", None) or getattr(r, "name", None) or getattr(r, "role_name", None)
                role_names.append(str(rn) if rn is not None else str(r))
                self._roles_normalized.append(r)

        self.role_combo.clear()
        if role_names:
            self.role_combo.addItems(role_names)
            if self.user:
                current_role = self._get_attr(self._get_attr(self.user, "application_role", {}), "role_name", "")
                if current_role:
                    self.role_combo.setCurrentText(current_role)
        else:
            self._on_pg_change(self.pg_role_combo.currentText())
            if self.feedback_lbl:
                self.feedback_lbl.setText("⚠️ Aucun rôle chargé.")
                self.feedback_lbl.setProperty("status", "warning")
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore

    def _load_specialties(self):
        try:
            specs = None
            user_ctrl = getattr(self.controller, "user_controller", None)
            if user_ctrl:
                try:
                    specs = user_ctrl.list_speciality()
                    #logger.debug(f"Loaded specialties from user_controller: {specs}")
                except Exception as e:
                    logger.debug(f"user_controller.list_speciality failed: {e}")

            if specs is None:
                candidates = ["list_speciality", "list_specialties", "get_all_specialties", "get_all_speciality", "list_specialty"]
                for name in candidates:
                    specs = self._try_call(name, default=None)
                    if specs is not None:
                        #logger.debug(f"Loaded specialties from {name}: {specs}")
                        break

            specs = specs or []

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

            spec_names = []
            self._specs_normalized = []
            for s in specs:
                if isinstance(s, str):
                    spec_names.append(s)
                    self._specs_normalized.append({"name": s, "specialty_id": None})
                elif isinstance(s, dict):
                    name = s.get("name") or s.get("specialty_name") or s.get("label") or None
                    spec_names.append(name or str(s))
                    self._specs_normalized.append(s)
                else:
                    name = getattr(s, "name", None) or getattr(s, "specialty_name", None)
                    spec_names.append(str(name) if name is not None else str(s))
                    self._specs_normalized.append(s)

            self.specialty_combo.clear()
            if not spec_names:
                self.specialty_combo.addItem("(Aucune spécialité disponible)")
                if self.feedback_lbl:
                    self.feedback_lbl.setText("⚠️ Impossible de charger les spécialités.")
                    self.feedback_lbl.setProperty("status", "warning")
                    if self.feedback_lbl.style():
                        self.feedback_lbl.style().unpolish(self.feedback_lbl) # pyright: ignore[reportOptionalMemberAccess]
                        self.feedback_lbl.style().polish(self.feedback_lbl) # pyright: ignore[reportOptionalMemberAccess]
            else:
                self.specialty_combo.addItems([""] + spec_names)

            if self.user:
                current_spec = (self._get_attr(self.user, "specialty_name", None)
                               or self._get_attr(self._get_attr(self.user, "specialty", {}), "name", None)
                               or self._get_attr(self.user, "specialty", None))
                if current_spec:
                    self.specialty_combo.setCurrentText(str(current_spec))
        except Exception as e:
            logger.exception(f"Error loading specialties: {e}")
            self.specialty_combo.clear()
            self.specialty_combo.addItem("(Erreur de chargement)")
            if self.feedback_lbl:
                self.feedback_lbl.setText(f"❌ Erreur chargement spécialités: {str(e)}")
                self.feedback_lbl.setProperty("status", "error")
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore

    def _on_pg_change(self, pg_role):
        mapping = {
            "app_admin": ["admin"],
            "app_secretaire": ["secretaire"],
            "app_medical": ["medecin", "nurse"],
            "app_laborantin": ["laborantin"]
        }
        choices = mapping.get(pg_role, [])
        self.role_combo.clear()
        if choices:
            self.role_combo.addItems(choices)
            self.role_combo.setCurrentIndex(0)

    def _on_save(self):
        invalid = False
        username = self.username_edit.text().strip()
        self.username_edit.setProperty("invalid", not username)
        if self.username_edit.style():
            self.username_edit.style().unpolish(self.username_edit) # type: ignore
            self.username_edit.style().polish(self.username_edit) # type: ignore
        if not username:
            invalid = True

        password = self.password_edit.text().strip()
        if not self.user and not password:
            self.password_edit.setProperty("invalid", True)
            if self.password_edit.style():
                self.password_edit.style().unpolish(self.password_edit) # type: ignore
                self.password_edit.style().polish(self.password_edit) # type: ignore
            invalid = True
        else:
            self.password_edit.setProperty("invalid", False)
            if self.password_edit.style():
                self.password_edit.style().unpolish(self.password_edit) # type: ignore
                self.password_edit.style().polish(self.password_edit) # type: ignore

        full_name = self.full_name_edit.text().strip()
        self.full_name_edit.setProperty("invalid", not full_name)
        if self.full_name_edit.style():
            self.full_name_edit.style().unpolish(self.full_name_edit) # type: ignore
            self.full_name_edit.style().polish(self.full_name_edit) # type: ignore
        if not full_name:
            invalid = True

        pg_role = self.pg_role_combo.currentText()
        role_name = self.role_combo.currentText()
        spec_name = self.specialty_combo.currentText()

        if invalid or not pg_role or not role_name:
            if self.feedback_lbl:
                self.feedback_lbl.setText("❌ Veuillez remplir tous les champs obligatoires (*).")
                self.feedback_lbl.setProperty("status", "error")
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore
            return

        roles = self._try_call("list_roles", default=[]) or []
        if not isinstance(roles, (list, tuple)):
            logger.error("list_roles returned non-iterable response")
            if self.feedback_lbl:
                self.feedback_lbl.setText("❌ Erreur : Impossible de charger les rôles.")
                self.feedback_lbl.setProperty("status", "error")
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore
            return

        normalized_roles = getattr(self, "_roles_normalized", [])
        role_obj = next((r for r in normalized_roles if self._get_attr(r, "role_name", "") == role_name), None)
        if not role_obj:
            if self.feedback_lbl:
                self.feedback_lbl.setText("❌ Rôle non trouvé.")
                self.feedback_lbl.setProperty("status", "error")
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore
            return

        data = {
            "username": username,
            "full_name": full_name,
            "postgres_role": pg_role,
            "is_active": self.is_active_check.isChecked(),
            "role_id": self._get_attr(role_obj, "role_id", None)
        }
        if password:
            data["password"] = password

        if spec_name and spec_name not in ("(Aucune spécialité disponible)", "(Erreur de chargement)"):
            specs = self._try_call("list_speciality", default=[]) or []
            if not isinstance(specs, (list, tuple)):
                logger.error("list_speciality returned non-iterable response")
                if self.feedback_lbl:
                    self.feedback_lbl.setText("❌ Erreur : Impossible de charger les spécialités.")
                    self.feedback_lbl.setProperty("status", "error")
                    if self.feedback_lbl.style():
                        self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                        self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore
                return

            normalized_specs = getattr(self, "_specs_normalized", [])
            spec_obj = next((s for s in normalized_specs if self._get_attr(s, "name", "") == spec_name or self._get_attr(s, "specialty_name", "") == spec_name), None)
            if spec_obj:
                data["specialty_id"] = self._get_attr(spec_obj, "specialty_id", None)

        try:
            if self.user:
                user_id = self._get_attr(self.user, "user_id", None)
                if user_id is None:
                    raise ValueError("ID utilisateur manquant pour la mise à jour.")
                self._try_call("update_user", user_id, data)
                msg = "✅ Utilisateur mis à jour avec succès."
                status = "success"
            else:
                self._try_call("create_user", data)
                msg = "✅ Utilisateur créé avec succès."
                status = "success"
            if self.feedback_lbl:
                self.feedback_lbl.setText(msg)
                self.feedback_lbl.setProperty("status", status)
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore
            if callable(self.on_save_callback):
                self.on_save_callback()
            QtCore.QTimer.singleShot(1500, self.accept)
        except Exception as e:
            logger.exception("Error saving user")
            if self.feedback_lbl:
                self.feedback_lbl.setText(f"❌ Erreur: {str(e)}")
                self.feedback_lbl.setProperty("status", "error")
                if self.feedback_lbl.style():
                    self.feedback_lbl.style().unpolish(self.feedback_lbl) # type: ignore
                    self.feedback_lbl.style().polish(self.feedback_lbl) # type: ignore