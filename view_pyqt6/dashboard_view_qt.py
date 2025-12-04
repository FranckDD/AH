# view_pyqt6/dashboard_view_qt.py
import os
from typing import Any, Optional, Callable
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame,
    QStackedWidget, QListWidget, QLineEdit, QToolButton, QMenu,
    QSizePolicy, QScrollArea, QVBoxLayout, QSpacerItem
)
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer
from view_pyqt6.api_controller import ApiControllerProxy
from view_pyqt6.controller_resolver import ControllerResolver
from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView
from view_pyqt6.medical_record.mr_list_view import MedicalRecordListView
try:
    from view_pyqt6.patient_view.patient_list import PatientListView
    from view_pyqt6.patient_view.patient_form import PatientFormView
except Exception:
    PatientListView = None
    PatientFormView = None

# en tête de dashboard_view_qt.py
try:
    from view_pyqt6.appointment_views.dashboard_appointment_view import AppointmentsDashboardView
except Exception:
    AppointmentsDashboardView = None

# en haut du fichier, ajoute si nécessaire :
from view_pyqt6.appointment_views.list_appointment import AppointmentsListView
from view_pyqt6.appointment_views.book_appoint_view import AppointmentsBookDialog


class DashboardView(QWidget):
    """
    Conversion PyQt6 de ta Dashboard customtkinter.
    - controllers doit être un objet contenant gateway (+ éventuellement controller/fallback_controller/network_manager)
    - user : objet user (doit fournir full_name ou username)
    - on_logout : callable
    """
    def __init__(self, parent, user: Any, controllers: Any, on_logout: Optional[Callable] = None):
        super().__init__(parent)
        self.user = user
        self.controllers = controllers
        self.on_logout = on_logout
        self.resolver = ControllerResolver(controllers)

        # Initialiser le dictionnaire view_instances
        self.view_instances = {}

        # layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar (left)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        self._build_sidebar()
        main_layout.addWidget(self.sidebar)

        # Centrale (topbar + content)
        central = QVBoxLayout()
        central.setContentsMargins(0, 0, 0, 0)
        self._build_topbar()
        central.addWidget(self.topbar)
        self._build_content_area()
        central.addWidget(self.content_area)
        main_layout.addLayout(central)

        # Appliquer le style avec la colorimétrie révisée
        self.setStyleSheet("""
            QWidget#sidebar { 
                background: #F8F9FA; 
                border-right: 1px solid #E0E0E0; 
            }
            QWidget#topbar { 
                background: #2e7d32; 
                color: white; 
            }
            QLabel#logoLabel { 
                color: #333333; 
                font-weight: bold; 
                font-size: 16px; 
            }
            QPushButton {
                color: #333333;
                text-align: left;
                padding: 8px;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #E3F2FD;
                color: #007bff;
                border-radius: 5px;
            }
        """)

        # affichage initial
        QTimer.singleShot(50, self.show_doctors_dashboard)


    # ---------- Sidebar build ----------
    def _build_sidebar(self):
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # toggle button
        self.toggle_btn = QPushButton("<")
        self.toggle_btn.setMaximumWidth(36)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # logo + title
        logo_h = QHBoxLayout()
        logo_lbl = QLabel()
        logo_lbl.setObjectName("logoLabel")
        img_path = os.path.join("assets", "glostone-kare.png")
        if os.path.exists(img_path):
            pix = QPixmap(img_path).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        title = QLabel(" Health")
        title.setObjectName("logoLabel")
        logo_h.addWidget(logo_lbl)
        logo_h.addWidget(title)
        layout.addLayout(logo_h)

        layout.addSpacing(8)

        # Sections (buttons + collapsible area)
        self.menu_buttons = []
        # helper to create a section
        def make_section(title, items):
            btn = QPushButton(title)
            btn.setFlat(True)
            btn.clicked.connect(lambda: self._toggle_section(title))
            self.menu_buttons.append(btn)
            layout.addWidget(btn)
            # container
            cont = QWidget()
            cont_layout = QVBoxLayout(cont)
            cont_layout.setContentsMargins(12, 0, 0, 0)
            cont_layout.setSpacing(2)
            cont.setVisible(False)
            for txt, cb in items:
                sub = QPushButton(txt)
                sub.setFlat(True)
                sub.clicked.connect(cb)
                cont_layout.addWidget(sub)
            layout.addWidget(cont)
            return btn, cont

        self.docs_btn, self.docs_sub = make_section("Médecins", [
            ("Dashboard Médecins", self.show_doctors_dashboard),
        ])

        self.pats_btn, self.pats_sub = make_section("Patients", [
            ("Dashboard Patients", self.show_patients_dashboard),
            ("Liste Patients", self.show_patients_list),
            ("Ajouter Patient", self.show_patient_add),
        ])

        self.apps_btn, self.apps_sub = make_section("Rendez-vous", [
            ("Dashboard Rendez-vous", self.show_appointments_dashboard),
            ("Liste Rendez-vous", self.show_appointments_list),
            ("Prendre Rendez-vous", self.show_appointments_book),
        ])

        self.medrec_btn, self.medrec_sub = make_section("Dossier Médical", [
            ("Enregistrer parametre medical", self.show_medical_record_form),
            ("Liste Parammetres Medicaux", self.show_medical_record_list),
        ])

        self.presc_btn, self.presc_sub = make_section("Prescription", [
            ("Nouvelle Prescription", self.show_prescription_form),
            ("Liste Prescriptions", self.show_prescription_list),
        ])

        layout.addStretch()

    def _toggle_section(self, title):
        mapping = {
            "Médecins": self.docs_sub,
            "Patients": self.pats_sub,
            "Rendez-vous": self.apps_sub,
            "Dossier Médical": self.medrec_sub,
            "Prescription": self.presc_sub,
        }
        w = mapping.get(title)
        if w:
            w.setVisible(not w.isVisible())

    # ---------- Topbar ----------
    def _build_topbar(self):
        self.topbar = QFrame()
        self.topbar.setObjectName("topbar")
        self.topbar.setFixedHeight(60)
        layout = QHBoxLayout(self.topbar)
        layout.setContentsMargins(8, 4, 8, 4)

        # logo small
        logo_lbl = QLabel()
        img_path = os.path.join("assets", "glostone-kare.png")
        if os.path.exists(img_path):
            pix = QPixmap(img_path).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pix)
        layout.addWidget(logo_lbl)

        title = QLabel(" Glostone-kare")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 18px;")
        layout.addWidget(title)

        # search
        layout.addSpacing(10)
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("🔍 Rechercher…")
        self.search_entry.setMaximumWidth(240)
        layout.addWidget(self.search_entry)

        layout.addStretch()

        # notifications
        not_btn = QToolButton()
        not_btn.setText("🔔")
        not_btn.setStyleSheet("color: white;")
        layout.addWidget(not_btn)

        # profile menu
        self.profile_btn = QToolButton()
        name = getattr(self.user, "full_name", getattr(self.user, "username", "Utilisateur"))
        self.profile_btn.setText(f"{name} ▼")
        self.profile_btn.setStyleSheet("color: white;")
        self.profile_menu = QMenu()
        self.profile_menu.addAction("Paramètres", lambda: None)
        self.profile_menu.addAction("Éditer Profil", lambda: None)
        self.profile_menu.addAction("Changer MDP", lambda: None)
        self.profile_menu.addSeparator()
        self.profile_menu.addAction("Déconnexion", self._logout)
        self.profile_btn.setMenu(self.profile_menu)
        self.profile_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(self.profile_btn)

    # ---------- Content area ----------
    def _build_content_area(self):
        self.content_area = QStackedWidget()
        # placeholder pages (you will replace by real converted views)
        self.page_placeholders = {}
        for name in ("doctors_dashboard", "patients_dashboard", "patients_list",
                     "appointments_dashboard", "appointments_list",
                     "medical_record_form", "medical_record_list",
                     "prescription_form", "prescription_list"):
            w = QWidget()
            l = QVBoxLayout(w)
            l.addWidget(QLabel(f"[{name}] — widget not converted yet."))
            l.addStretch()
            # mark as placeholder so logic can distinguish real views from placeholders
            setattr(w, "_is_placeholder", True)
            self.page_placeholders[name] = w
            self.content_area.addWidget(w)


    # ---------- toggle sidebar ----------
    def toggle_sidebar(self):
        if self.sidebar.width() > 100:
            self.sidebar.setFixedWidth(60)
            # hide texts of main buttons but keep submenu texts
            for btn in self.menu_buttons:
                btn.setText("")
        else:
            self.sidebar.setFixedWidth(200)
            titles = ["Médecins", "Patients", "Rendez-vous", "Dossier Médical", "Prescription"]
            for btn, txt in zip(self.menu_buttons, titles):
                btn.setText(txt)

    # ---------- navigation helpers ----------
    def _show_page(self, page_key: str):
        w = self.page_placeholders.get(page_key)
        if w:
            try:
                self.content_area.setCurrentWidget(w)
            except Exception:
                # fallback: try to find the widget in the stacked widgets
                for i in range(self.content_area.count()):
                    widget = self.content_area.widget(i)
                    if widget is w:
                        try:
                            self.content_area.setCurrentIndex(i)
                        except Exception:
                            pass
                        break

    def _replace_page_widget(self, page_key: str, new_widget: QWidget):
        """
        Remplace proprement la page placeholder identifiée par page_key
        par `new_widget` dans le QStackedWidget. Si la page n'existe pas,
        on l'ajoute à la fin.

        Important: ne supprime définitivement (deleteLater) que les placeholders.
        Les widgets provenant de self.view_instances sont retirés du stacked mais conservés en mémoire
        pour réutilisation éventuelle.
        """
        old = self.page_placeholders.get(page_key)
        try:
            if old is not None:
                # safe index retrieval
                try:
                    idx = self.content_area.indexOf(old)
                except Exception:
                    idx = -1

                # remove old widget from stacked if present
                try:
                    if idx >= 0:
                        self.content_area.removeWidget(old)
                except Exception:
                    # try generic remove
                    try:
                        self.content_area.removeWidget(old)
                    except Exception:
                        pass

                # delete only if placeholder (we don't want to destroy cached instances)
                if getattr(old, "_is_placeholder", False):
                    try:
                        old.deleteLater()
                    except Exception:
                        pass

                # insert new_widget at same index if possible, else add
                if idx >= 0:
                    try:
                        self.content_area.insertWidget(idx, new_widget)
                    except Exception:
                        try:
                            self.content_area.addWidget(new_widget)
                        except Exception:
                            pass
                else:
                    try:
                        self.content_area.addWidget(new_widget)
                    except Exception:
                        pass
            else:
                # no placeholder -> add normally
                try:
                    self.content_area.addWidget(new_widget)
                except Exception:
                    pass
        finally:
            # update mapping and show
            self.page_placeholders[page_key] = new_widget
            try:
                self.content_area.setCurrentWidget(new_widget)
            except Exception:
                # ignore if it fails; UI will remain stable
                pass


    # ---------- Show methods (bind to sidebar) ----------
    def show_doctors_dashboard(self):
        self._set_active(self.docs_btn)
        self._show_doctors_dashboard_view()

    def _show_doctors_dashboard_view(self):
        """
        Implémentation interne : instancie/réutilise DoctorsDashboardView
        et l'insère dans le stacked widget sous la clé 'doctors_dashboard'.
        """
        view_key = "doctors_dashboard"

        try:
            # réutiliser l'instance si déjà présente et vivante
            if view_key in self.view_instances and self._is_widget_alive(self.view_instances[view_key]):
                doctors_dashboard_view = self.view_instances[view_key]
            else:
                # Import corrigé : fichier attendu view_pyqt6/doctor_views/doctors_dashboard_view.py
                try:
                    from view_pyqt6.doctor_views.dashboard_doctor import DoctorsDashboardView
                except Exception as imp_err:
                    # fallback si path différent sur ton projet : tenter ancien nom possible
                    try:
                        from view_pyqt6.doctor_views.dashboard_doctor import DoctorsDashboardView
                    except Exception:
                        raise ImportError(f"Impossible d'importer DoctorsDashboardView: {imp_err}")

                # créer l'instance et la mémoriser
                doctors_dashboard_view = DoctorsDashboardView(
                    parent=self,
                    user=self.user,
                    controllers=self.controllers,
                    on_start_consultation=getattr(self, "_start_consultation", None),
                    on_open_record=getattr(self, "_open_medical_record", None),
                    on_logout=getattr(self, "_logout", None)
                )

                # retenir l'instance pour réutilisation ultérieure
                self.view_instances[view_key] = doctors_dashboard_view

                # ajouter proprement au stacked (utiliser _replace_page_widget pour gérer placeholders)
                try:
                    self._replace_page_widget("doctors_dashboard", doctors_dashboard_view)
                except Exception:
                    # fallback direct add si _replace_page_widget échoue
                    try:
                        self.content_area.addWidget(doctors_dashboard_view)
                    except Exception:
                        pass

            # afficher la vue
            try:
                self.content_area.setCurrentWidget(self.view_instances[view_key])
            except Exception:
                # ensure widget is in stacked
                try:
                    self._replace_page_widget("doctors_dashboard", self.view_instances[view_key])
                except Exception:
                    pass

            # lancer un rafraîchissement si la vue expose un refresh async ou sync
            try:
                v = self.view_instances[view_key]
                if hasattr(v, "refresh") and callable(getattr(v, "refresh")):
                    v.refresh()
                elif hasattr(v, "_refresh_all_async") and callable(getattr(v, "_refresh_all_async")):
                    v._refresh_all_async()
            except Exception:
                pass

        except ImportError as e:
            print(f"ImportError show doctors dashboard: {e}")
            self._show_fallback_view("Dashboard médecin non disponible")
        except Exception as e:
            print(f"Erreur affichage dashboard médecin: {e}")
            self._show_fallback_view("Erreur de chargement du dashboard médecin")


    def _show_fallback_view(self, message):
        """Affiche une vue de secours avec un message"""
        fallback_widget = QLabel(message)
        fallback_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fallback_widget.setStyleSheet("font-size: 16px; color: #666; padding: 50px;")

        # Ajouter temporairement au content_area
        self.content_area.addWidget(fallback_widget)
        self.content_area.setCurrentWidget(fallback_widget)

        # Nettoyer après 3 secondes
        QTimer.singleShot(3000, lambda: self._cleanup_fallback(fallback_widget))

    def _cleanup_fallback(self, fallback_widget):
        """Nettoie la vue de secours"""
        try:
            if fallback_widget:
                self.content_area.removeWidget(fallback_widget)
                fallback_widget.deleteLater()
        except Exception:
            pass


    def show_patients_dashboard(self):
        self._set_active(self.pats_btn)
        self._show_page("patients_dashboard")

    def show_patients_list(self):
        self._set_active(self.pats_btn)
        self._show_patient_list_view()

    def show_patient_add(self):
        self._set_active(self.pats_btn)
        self._show_patient_form_view()


    def _clear_content(self):
        """Vide la zone de contenu principale"""
        if isinstance(self.content_area, QStackedWidget):
            # retire toutes les widgets du stacked (sans détruire celles stockées si nécessaire)
            while self.content_area.count():
                widget = self.content_area.widget(0)
                try:
                    self.content_area.removeWidget(widget)
                except Exception:
                    pass
                try:
                    # delete placeholders only
                    if getattr(widget, "_is_placeholder", False):
                        widget.deleteLater()
                except Exception:
                    pass
        elif hasattr(self.content_area, 'layout'):
            layout = self.content_area.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)
                        try:
                            widget.deleteLater()
                        except Exception:
                            pass
        else:
            for child in list(self.content_area.children()):
                if isinstance(child, QWidget):
                    try:
                        child.setParent(None)
                        child.deleteLater()
                    except Exception:
                        pass

    def _show_patient_list_view(self):
        """Affiche la liste des patients avec QStackedWidget"""
        view_key = "patient_list_view"

        # Vérifier si la vue existe déjà
        if view_key in self.view_instances and self._is_widget_alive(self.view_instances[view_key]):
            patient_list_view = self.view_instances[view_key]
        else:
            if PatientListView is None:
                # placeholder if missing
                w = QWidget()
                l = QVBoxLayout(w)
                l.addWidget(QLabel("Liste Patients non convertie."))
                l.addStretch()
                patient_list_view = w
            else:
                patient_list_view = PatientListView(self, self.controllers)
            self.view_instances[view_key] = patient_list_view
            try:
                self.content_area.addWidget(patient_list_view)
            except Exception:
                pass

        # Afficher la vue
        try:
            self.content_area.setCurrentWidget(patient_list_view)
        except Exception:
            self._replace_page_widget("patients_list", patient_list_view)

        # Rafraîchir les données
        try:
            if hasattr(patient_list_view, 'refresh'):
                patient_list_view.refresh()
        except Exception as e:
            print(f"Erreur rafraîchissement liste patients: {e}")

    def _show_patient_form_view(self, patient_id=None):
        """Affiche le formulaire patient"""
        view_key = f"patient_form_view_{patient_id or 'new'}"

        def on_patient_saved(code_patient):
            QMessageBox.information(self, "Succès", f"Patient créé: {code_patient}")
            self.show_patients_list()

        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            if PatientFormView is None:
                placeholder = QWidget()
                pl = QVBoxLayout(placeholder)
                pl.addWidget(QLabel("Formulaire patient non disponible."))
                pl.addStretch()
                self.view_instances[view_key] = placeholder
                try:
                    self.content_area.addWidget(placeholder)
                except Exception:
                    pass
            else:
                patient_form = PatientFormView(
                    parent=self.content_area,
                    controllers=self.controllers,
                    current_user=self.user,
                    patient_id=patient_id,
                    on_save=on_patient_saved
                )
                self.view_instances[view_key] = patient_form
                try:
                    self.content_area.addWidget(patient_form)
                except Exception:
                    pass

        try:
            self.content_area.setCurrentWidget(self.view_instances[view_key])
        except Exception:
            self._replace_page_widget(view_key, self.view_instances[view_key])

    def _after_patient_save(self, code_patient: str):
        QMessageBox.information(self, "Info", f"Patient créé: {code_patient}")


    # Appointment call
    def show_appointments_dashboard(self):
        self._set_active(self.apps_btn)
        view_key = "appointments_dashboard_view"
        try:
            # reuse alive instance if available
            if view_key in self.view_instances and self._is_widget_alive(self.view_instances[view_key]):
                widget = self.view_instances[view_key]
            else:
                # instantiate and store
                from view_pyqt6.appointment_views.dashboard_appointment_view import AppointmentsDashboardView
                widget = AppointmentsDashboardView(parent=self, controllers=self.controllers,
                                                   on_day_selected=self.show_appointments_list)
                self.view_instances[view_key] = widget

            # Replace or add once (méthode gère placeholders en sécurité)
            self._replace_page_widget("appointments_dashboard", widget)

        except Exception as e:
            print("Warning show_appointments_dashboard:", e)
            self._show_page("appointments_dashboard")

    def show_appointments_list(self, target_date=None):
        """
        target_date: optional datetime.date -> if provided, the list will be filtered by that day.
        """
        self._set_active(self.apps_btn)
        self._show_appointments_list_view(target_date=target_date)


    def _show_appointments_list_view(self, target_date=None):
        view_key = "appointments_list_view"
        try:
            if view_key in self.view_instances and self._is_widget_alive(self.view_instances[view_key]):
                appt_list_view = self.view_instances[view_key]
            else:
                if AppointmentsListView:
                    appt_list_view = AppointmentsListView(
                            parent=self,
                            controllers=self.controllers,
                            on_book=lambda: self.show_appointments_book(),
                            on_edit=lambda appt_id: self.show_appointments_book(appointment=appt_id)
                        )
                else:
                    w = QWidget()
                    l = QVBoxLayout(w)
                    l.addWidget(QLabel("[appointments_list] — widget not converted yet."))
                    l.addStretch()
                    appt_list_view = w

                self.view_instances[view_key] = appt_list_view
                try:
                    self.content_area.addWidget(appt_list_view)
                except Exception:
                    try:
                        self._replace_page_widget("appointments_list", appt_list_view)
                    except Exception:
                        pass

            try:
                self.content_area.setCurrentWidget(appt_list_view)
            except Exception:
                self._replace_page_widget("appointments_list", appt_list_view)

            try:
                if hasattr(appt_list_view, "refresh"):
                    if target_date is not None:
                        try:
                            appt_list_view.refresh(target_date=target_date)
                        except TypeError:
                            appt_list_view.refresh()
                    else:
                        appt_list_view.refresh()
            except Exception as e:
                print("Erreur rafraîchissement appointments list:", e)

        except Exception as e:
            print("Warning show_appointments_list:", e)
            self._show_page("appointments_list")


    def show_appointments_book(self, appointment=None):
        self._set_active(self.apps_btn)
        try:
            from view_pyqt6.appointment_views.book_appoint_view import AppointmentsBookDialog

            appt_obj = appointment
            if isinstance(appointment, int):
                try:
                    appt_ctrl = self.resolver.appointment_controller()
                    if hasattr(appt_ctrl, "get_appointment"):
                        appt_obj = appt_ctrl.get_appointment(appointment)
                    elif hasattr(appt_ctrl, "repo") and hasattr(appt_ctrl.repo, "get_by_id"):
                        appt_obj = appt_ctrl.repo.get_by_id(appointment)
                    else:
                        appt_obj = None
                except Exception:
                    appt_obj = None

            dlg = AppointmentsBookDialog(parent=self, controllers=self.controllers,
                                        current_user=self.user, appointment=appt_obj,
                                        on_save=lambda: self.show_appointments_list())
            dlg.exec()
        except Exception as e:
            print("Erreur ouverture AppointmentsBookDialog:", e)
            try:
                QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir le formulaire de Rendez-vous: {e}")
            except Exception:
                pass


    # Medical record
    def show_medical_record_form(self):
        self._set_active(self.medrec_btn)
        self._show_medical_record_form_view()

    def show_medical_record_list(self):
        self._set_active(self.medrec_btn)
        self._show_medical_record_list_view()

    def _show_medical_record_form_view(self, record_id=None):
        """Affiche le formulaire de dossier médical"""
        view_key = f"medical_record_form_view_{record_id or 'new'}"

        def on_medical_record_saved():
            QMessageBox.information(self, "Succès", "Dossier médical enregistré avec succès")
            self.show_medical_record_list()

        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            medical_record_form = MedicalRecordFormView(
                parent=self.content_area,
                controllers=self.controllers,
                current_user=self.user,
                record_id=record_id,
                on_save=on_medical_record_saved
            )
            self.view_instances[view_key] = medical_record_form
            try:
                self.content_area.addWidget(medical_record_form)
            except Exception:
                pass

        try:
            self.content_area.setCurrentWidget(self.view_instances[view_key])
        except Exception:
            self._replace_page_widget("medical_record_form", self.view_instances[view_key])

    def _show_medical_record_list_view(self):
        """Affiche la liste des dossiers médicaux"""
        view_key = "medical_record_list_view"

        def on_prescribe(patient_id=None, medical_record_id=None):
            self.show_prescription_form(patient_id, medical_record_id)

        if view_key not in self.view_instances or not self._is_widget_alive(self.view_instances.get(view_key)):
            medical_record_list = MedicalRecordListView(
                parent=self.content_area,
                controllers=self.controllers,
                on_prescribe=on_prescribe
            )
            self.view_instances[view_key] = medical_record_list
            try:
                self.content_area.addWidget(medical_record_list)
            except Exception:
                pass

        try:
            self.content_area.setCurrentWidget(self.view_instances[view_key])
            if hasattr(self.view_instances[view_key], 'refresh'):
                self.view_instances[view_key].refresh()
        except Exception as e:
            print(f"Erreur rafraîchissement liste dossiers médicaux: {e}")


    def _show_prescription_form_view(self, prescription_id: Optional[int] = None,
                                    patient_id: Optional[int] = None,
                                    medical_record_id: Optional[int] = None):
        view_key = f"prescription_form_{prescription_id or 'new'}_{patient_id or ''}_{medical_record_id or ''}"

        if view_key in self.view_instances and self._is_widget_alive(self.view_instances[view_key]):
            form_widget = self.view_instances[view_key]
        else:
            try:
                from view_pyqt6.prescription_views.prescription_form_viewqt import PrescriptionFormView
            except Exception as e:
                print(f"Impossible d'importer PrescriptionFormView: {e}")
                placeholder = QWidget()
                placeholder_layout = QVBoxLayout(placeholder)
                placeholder_layout.addWidget(QLabel("Formulaire prescription non converti."))
                placeholder_layout.addStretch()
                self._replace_page_widget("prescription_form", placeholder)
                return

            def _on_saved():
                QMessageBox.information(self, "Succès", "Prescription enregistrée.")
                list_key = "prescription_list_view"
                try:
                    if list_key in self.view_instances:
                        lv = self.view_instances[list_key]
                        if hasattr(lv, "refresh"):
                            lv.refresh()
                except Exception:
                    pass
                self._show_prescription_list_view()

            form_widget = PrescriptionFormView(
                parent=self.content_area,
                controllers=self.controllers,
                current_user=self.user,
                prescription_id=prescription_id,
                patient_id=patient_id,
                medical_record_id=medical_record_id,
                on_save=_on_saved
            )
            self.view_instances[view_key] = form_widget
            try:
                self.content_area.addWidget(form_widget)
            except Exception:
                pass

        try:
            self.content_area.setCurrentWidget(self.view_instances[view_key])
        except Exception:
            self._replace_page_widget("prescription_form", form_widget)


    def _show_prescription_list_view(self):
        view_key = "prescription_list_view"

        if view_key in self.view_instances and self._is_widget_alive(self.view_instances[view_key]):
            list_widget = self.view_instances[view_key]
        else:
            try:
                from view_pyqt6.prescription_views.prescription_list import PrescriptionListView
            except Exception as e:
                print(f"Impossible d'importer PrescriptionListView: {e}")
                placeholder = QWidget()
                placeholder_layout = QVBoxLayout(placeholder)
                placeholder_layout.addWidget(QLabel("Liste prescriptions non convertie."))
                placeholder_layout.addStretch()
                self._replace_page_widget("prescription_list", placeholder)
                return

            list_widget = PrescriptionListView(
                parent=self.content_area,
                controllers=self.controllers,
                current_user=self.user
            )
            self.view_instances[view_key] = list_widget
            try:
                self.content_area.addWidget(list_widget)
            except Exception:
                pass

        try:
            self.content_area.setCurrentWidget(self.view_instances[view_key])
            if hasattr(self.view_instances[view_key], "refresh"):
                self.view_instances[view_key].refresh()
        except Exception:
            self._replace_page_widget("prescription_list", list_widget)


    def show_prescription_form(self, patient_id=None, medical_record_id=None, prescription_id=None):
        self._set_active(self.presc_btn)
        self._show_prescription_form_view(
            prescription_id=prescription_id,
            patient_id=patient_id,
            medical_record_id=medical_record_id
        )

    def show_prescription_list(self):
        self._set_active(self.presc_btn)
        self._show_prescription_list_view()

    def _is_widget_alive(self, w):
        """Détecte de façon sûre si l'objet widget est encore valide (non supprimé)."""
        try:
            if w is None:
                return False
            # accéder à une propriété simple ; Qt lèvera RuntimeError si l'objet C++ a été détruit
            _ = w.parent()
            return True
        except RuntimeError:
            return False
        except Exception:
            return False


    def _set_active(self, btn):
        # simple visual feedback
        for b in self.menu_buttons:
            b.setStyleSheet("")
        btn.setStyleSheet("font-weight: bold; color: #2e7d32;")

    def _logout(self):
        if callable(self.on_logout):
            self.on_logout()
