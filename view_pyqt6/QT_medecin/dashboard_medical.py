import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QPushButton, QLabel,
    QStackedLayout, QFrame, QSplitter, QMenu, QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from view_pyqt6.doctor_views.dashboard_doctor import DoctorsDashboardView
from view_pyqt6.doctor_views.doctor_list import DoctorsListView
from view_pyqt6.doctor_views.doctor_edit import DoctorsEditView
from view_pyqt6.patient_view.patient_dashboard_view import PatientsDashboardView
from view_pyqt6.patient_view.patient_list import PatientListView
from view_pyqt6.patient_view.patient_edit_view import PatientsEditView
from view_pyqt6.patient_view.patient_form import PatientFormView
from view_pyqt6.appointment_views.dashboard_appointment_view import AppointmentsDashboardView
from view_pyqt6.appointment_views.list_appointment import AppointmentsListView
from view_pyqt6.appointment_views.book_appoint_view import AppointmentBook
from view_pyqt6.medical_record.mr_form_view import MedicalRecordFormView
from view_pyqt6.medical_record.mr_list_view import MedicalRecordListView
from view_pyqt6.prescription_views.prescription_form_viewqt import PrescriptionFormView
from view_pyqt6.prescription_views.prescription_list import PrescriptionListView

class DashboardView(QWidget):
    def __init__(self, parent, user, controller, on_logout=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.controller = controller
        self.on_logout = on_logout
        
        self._init_ui()
        self.show_doctors_dashboard()

    def _init_ui(self):
        # Main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setHandleWidth(5)

        # Sidebar setup
        self._create_sidebar()
        # Content setup
        self._create_content()

        # Layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.splitter)

        # Animation for sidebar
        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.sidebar_expanded = True

    def _create_sidebar(self):
        # Frame
        self.sidebar = QFrame(self)
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background:#ffffff; border-right:1px solid #c8e6c9;")
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_layout.setSpacing(5)

        # Toggle button
        self.toggle_btn = QToolButton(self.sidebar)
        self.toggle_btn.setIcon(QIcon(os.path.join("assets", "chevron-left.svg")))
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        side_layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Logo
        logo_pix = QPixmap(os.path.join("assets", "logo_light.png")).scaled(32, 32,
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label = QLabel(self.sidebar)
        logo_label.setPixmap(logo_pix)
        logo_label.setText(" One Health")
        logo_label.setStyleSheet("font-size:18px; font-weight:bold; color:#2e7d32;")
        side_layout.addWidget(logo_label)

        # Scroll area for menu
        scroll = QScrollArea(self.sidebar)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;")
        menu_container = QWidget()
        self.menu_layout = QVBoxLayout(menu_container)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(0)
        scroll.setWidget(menu_container)
        side_layout.addWidget(scroll)

        # Menu sections
        self.sections = {}
        self._add_section("Médecins", [
            ("Dashboard Médecins", self.show_doctors_dashboard),
            ("Liste Médecins", self.show_doctors_list),
            ("Ajouter/Éditer Médecin", self.show_doctors_edit),
        ])
        self._add_section("Patients", [
            ("Dashboard Patients", self.show_patients_dashboard),
            ("Liste Patients", self.show_patients_list),
            ("Ajouter Patient", self.show_patient_add),
        ])
        self._add_section("RDV", [
            ("Dashboard RDV", self.show_appointments_dashboard),
            ("Liste RDV", self.show_appointments_list),
            ("Prendre RDV", self.show_appointments_book),
        ])
        self._add_section("Dossier Médical", [
            ("Enregistrer MR", self.show_medical_record_form),
            ("Liste MR", self.show_medical_record_list),
        ])
        self._add_section("Prescription", [
            ("Nouvelle Prescription", self.show_prescription_form),
            ("Liste Prescriptions", self.show_prescription_list),
        ])

        side_layout.addStretch()
        self.splitter.addWidget(self.sidebar)

    def _add_section(self, title, items):
        # Header button
        header = QToolButton(self.sidebar)
        header.setText(title)
        header.setStyleSheet("font-weight:bold; text-align:left; padding:5px;")
        header.setCheckable(True)
        header.setChecked(True)
        header.clicked.connect(lambda checked, t=title: self._toggle_section(t, checked))
        self.menu_layout.addWidget(header)

        # Submenu container
        container = QWidget(self.sidebar)
        v = QVBoxLayout(container)
        v.setContentsMargins(15, 0, 0, 0)
        v.setSpacing(0)
        for text, cmd in items:
            btn = QPushButton(text, container)
            btn.setFlat(True)
            btn.setStyleSheet("text-align:left; padding:5px;")
            btn.clicked.connect(cmd)
            v.addWidget(btn)
        self.menu_layout.addWidget(container)
        self.sections[title] = (header, container)

    def _toggle_section(self, title, checked):
        header, container = self.sections[title]
        container.setVisible(checked)

    def _create_content(self):
        self.content_frame = QWidget(self)
        self.stack = QStackedLayout(self.content_frame)
        # Pages dict
        self.pages = {
            'Dashboard Médecins': DoctorsDashboardView(self.content_frame),
            'Liste Médecins': DoctorsListView(self.content_frame),
            'Ajouter/Éditer Médecin': DoctorsEditView(self.content_frame),
            'Dashboard Patients': PatientsDashboardView(self.content_frame),
            'Liste Patients': PatientListView(self.content_frame),
            'Ajouter Patient': PatientFormView(self.content_frame),
            'Dashboard RDV': AppointmentsDashboardView(self.content_frame),
            'Liste RDV': AppointmentsListView(self.content_frame),
            'Prendre RDV': AppointmentBook(self.content_frame),
            'Enregistrer MR': MedicalRecordFormView(self.content_frame),
            'Liste MR': MedicalRecordListView(self.content_frame),
            'Nouvelle Prescription': PrescriptionFormView(self.content_frame),
            'Liste Prescriptions': PrescriptionListView(self.content_frame),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.splitter.addWidget(self.content_frame)

    def toggle_sidebar(self):
        start, end = (200, 60) if self.sidebar_expanded else (60, 200)
        icon = 'chevron-left.svg' if self.sidebar_expanded else 'chevron-right.svg'
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start()
        self.toggle_btn.setIcon(QIcon(os.path.join("assets", icon)))
        self.sidebar_expanded = not self.sidebar_expanded

    def switch_page(self, key):
        if key in self.pages:
            widget = self.pages[key]
            self.stack.setCurrentWidget(widget)

    # Navigation methods
    def show_doctors_dashboard(self): self.switch_page('Dashboard Médecins')
    def show_doctors_list(self):     self.switch_page('Liste Médecins')
    def show_doctors_edit(self):     self.switch_page('Ajouter/Éditer Médecin')
    def show_patients_dashboard(self): self.switch_page('Dashboard Patients')
    def show_patients_list(self):    self.switch_page('Liste Patients')
    def show_patient_add(self):      self.switch_page('Ajouter Patient')
    def show_appointments_dashboard(self): self.switch_page('Dashboard RDV')
    def show_appointments_list(self): self.switch_page('Liste RDV')
    def show_appointments_book(self): self.switch_page('Prendre RDV')
    def show_medical_record_form(self): self.switch_page('Enregistrer MR')
    def show_medical_record_list(self): self.switch_page('Liste MR')
    def show_prescription_form(self): self.switch_page('Nouvelle Prescription')
    def show_prescription_list(self): self.switch_page('Liste Prescriptions')

    # Profile menu (optional)
    def _open_profile_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Paramètres", lambda: None)
        menu.addAction("Éditer Profil", lambda: None)
        menu.addAction("Changer MDP", lambda: None)
        menu.addSeparator()
        menu.addAction("Déconnexion", self.logout)
        menu.exec(pos)

    def logout(self):
        if callable(self.on_logout):
            self.on_logout()
