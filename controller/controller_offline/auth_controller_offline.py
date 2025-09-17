# controllers/controller_offline/auth_controller_offline.py
import logging
from typing import Optional, Any, Type

from repositories.repo_offline.user_repo_offline import UserRepositoryOffline
from repositories.repo_offline.sqlite_manager import SQLiteManager

# Repos offline par défaut (fallback)
from repositories.repo_offline.patient_repo_offline import PatientRepositoryOffline
from repositories.repo_offline.medical_repo_offline import MedicalRecordRepositoryOffline
from repositories.repo_offline.prescription_repo_offline import PrescriptionRepositoryOffline
from repositories.repo_offline.appointment_repo_offline import AppointmentRepositoryOffline

# Controllers (même implémentation que pour online)
from controller.patient_controller import PatientController
from controller.medical_controller import MedicalRecordController
from controller.prescription_controller import PrescriptionController
from controller.appointment_controller import AppointmentController

logger = logging.getLogger(__name__)


class AuthControllerOffline:
    """
    Auth controller pour le mode offline.
    Peut recevoir:
      - une session SQLAlchemy (session)
      - un SQLiteManager (sqlite_manager) qui expose get_session()
      - ou un db_path (chemin fichier) — alors il crée son SQLiteManager interne.
    Si patient_repo_class / medical_repo_class / ... non fournis, on utilise
    automatiquement les repo_offline par défaut importés ci-dessus.
    """

    def __init__(
        self,
        session: Optional[Any] = None,
        sqlite_manager: Optional[SQLiteManager] = None,
        db_path: Optional[str] = None,
        patient_repo_class: Optional[Type] = None,
        medical_repo_class: Optional[Type] = None,
        prescription_repo_class: Optional[Type] = None,
        appointment_repo_class: Optional[Type] = None
    ):
        self.logger = logging.getLogger(__name__)

        # session / manager handling
        self._own_manager = False
        self.sqlite_manager = None

        if session is not None:
            # on suppose que c'est une Session SQLAlchemy
            self.session = session
        elif sqlite_manager is not None:
            self.sqlite_manager = sqlite_manager
            self.session = sqlite_manager.get_session()
        elif db_path is not None:
            self.sqlite_manager = SQLiteManager(db_path=db_path)
            self.session = self.sqlite_manager.get_session()
            self._own_manager = True
        else:
            raise ValueError("Vous devez fournir session, sqlite_manager ou db_path")

        # repos offline de base
        self.user_repo = UserRepositoryOffline(self.session)

        # si aucune classe fournie, on utilisera les implementations offline par défaut
        self.patient_repo_class = patient_repo_class or PatientRepositoryOffline
        self.medical_repo_class = medical_repo_class or MedicalRecordRepositoryOffline
        self.prescription_repo_class = prescription_repo_class or PrescriptionRepositoryOffline
        self.appointment_repo_class = appointment_repo_class or AppointmentRepositoryOffline

        # controllers (instanciés après authent)
        self.patient_controller: Optional[PatientController] = None
        self.medical_record_controller: Optional[MedicalRecordController] = None
        self.prescription_controller: Optional[PrescriptionController] = None
        self.appointment_controller: Optional[AppointmentController] = None

        self.current_user = None

    def _init_subcontrollers(self):
        """
        Instancie les controllers offline (après authentification).
        """
        try:
            if self.current_user:
                pat_repo = self.patient_repo_class(self.session)
                self.patient_controller = PatientController(pat_repo, self.current_user)

                med_repo = self.medical_repo_class(self.session)
                self.medical_record_controller = MedicalRecordController(
                    repo=med_repo,
                    patient_controller=self.patient_controller,
                    current_user=self.current_user
                )

                presc_repo = self.prescription_repo_class(self.session)
                self.prescription_controller = PrescriptionController(
                    repo=presc_repo,
                    patient_controller=self.patient_controller,
                    current_user=self.current_user
                )

                appt_repo = self.appointment_repo_class(self.session)
                self.appointment_controller = AppointmentController(
                    repo=appt_repo,
                    patient_controller=self.patient_controller,
                    current_user=self.current_user
                )
        except Exception as e:
            self.logger.exception("Erreur initialisation sous-controllers offline: %s", e)
            # On continue : certains sous-controllers peuvent rester None.

    def authenticate(self, username: str, password: str):
        """
        Auth offline. Retourne OfflineUser ou None.
        """
        try:
            user = self.user_repo.get_user_by_username(username)
            if not user:
                logger.info(f"[OFFLINE] Utilisateur {username} non trouvé")
                return None
            if not getattr(user, "is_active", True):
                logger.info(f"[OFFLINE] Compte {username} désactivé")
                return None
            if not user.check_password(password):
                logger.info(f"[OFFLINE] Échec mot de passe pour {username}")
                return None

            self.current_user = user
            self._init_subcontrollers()
            return user

        except Exception as e:
            logger.exception("Erreur lors de l'authen offline: %s", e)
            return None

    # ----------------- Pass-throughs (mêmes noms & signatures que AuthController online) -----------------

    # Patients
    def list_patients(self, *args, **kwargs):
        if not self.patient_controller:
            raise RuntimeError("PatientController offline non initialisé")
        return self.patient_controller.list_patients(*args, **kwargs)

    def get_patient(self, *args, **kwargs):
        if not self.patient_controller:
            raise RuntimeError("PatientController offline non initialisé")
        return self.patient_controller.get_patient(*args, **kwargs)

    def create_patient(self, *args, **kwargs):
        if not self.patient_controller:
            raise RuntimeError("PatientController offline non initialisé")
        return self.patient_controller.create_patient(*args, **kwargs)

    def update_patient(self, *args, **kwargs):
        if not self.patient_controller:
            raise RuntimeError("PatientController offline non initialisé")
        return self.patient_controller.update_patient(*args, **kwargs)

    def delete_patient(self, *args, **kwargs):
        if not self.patient_controller:
            raise RuntimeError("PatientController offline non initialisé")
        return self.patient_controller.delete_patient(*args, **kwargs)

    # Medical records
    def list_motifs(self, *args, **kwargs):
        if not self.medical_record_controller:
            raise RuntimeError("MedicalRecordController offline non initialisé")
        return self.medical_record_controller.list_motifs(*args, **kwargs)

    def list_records(self, *args, **kwargs):
        if not self.medical_record_controller:
            raise RuntimeError("MedicalRecordController offline non initialisé")
        return self.medical_record_controller.list_records(*args, **kwargs)

    def create_record(self, *args, **kwargs):
        if not self.medical_record_controller:
            raise RuntimeError("MedicalRecordController offline non initialisé")
        return self.medical_record_controller.create_record(*args, **kwargs)

    def update_record(self, *args, **kwargs):
        if not self.medical_record_controller:
            raise RuntimeError("MedicalRecordController offline non initialisé")
        return self.medical_record_controller.update_record(*args, **kwargs)

    def delete_record(self, *args, **kwargs):
        if not self.medical_record_controller:
            raise RuntimeError("MedicalRecordController offline non initialisé")
        return self.medical_record_controller.delete_record(*args, **kwargs)

    # Prescriptions
    def list_prescriptions(self, *args, **kwargs):
        if not self.prescription_controller:
            raise RuntimeError("PrescriptionController offline non initialisé")
        return self.prescription_controller.list_prescriptions(*args, **kwargs)

    def get_prescription(self, *args, **kwargs):
        if not self.prescription_controller:
            raise RuntimeError("PrescriptionController offline non initialisé")
        return self.prescription_controller.get_prescription(*args, **kwargs)

    def create_prescription(self, *args, **kwargs):
        if not self.prescription_controller:
            raise RuntimeError("PrescriptionController offline non initialisé")
        return self.prescription_controller.create_prescription(*args, **kwargs)

    def update_prescription(self, *args, **kwargs):
        if not self.prescription_controller:
            raise RuntimeError("PrescriptionController offline non initialisé")
        return self.prescription_controller.update_prescription(*args, **kwargs)

    def delete_prescription(self, *args, **kwargs):
        if not self.prescription_controller:
            raise RuntimeError("PrescriptionController offline non initialisé")
        return self.prescription_controller.delete_prescription(*args, **kwargs)

    # Appointments
    def book_appointment(self, *args, **kwargs):
        if not self.appointment_controller:
            raise RuntimeError("AppointmentController offline non initialisé")
        return self.appointment_controller.book_appointment(*args, **kwargs)

    def get_appointments_by_day(self, *args, **kwargs):
        if not self.appointment_controller:
            raise RuntimeError("AppointmentController offline non initialisé")
        return self.appointment_controller.get_by_day(*args, **kwargs)

    # close / cleanup
    def close(self):
        try:
            if self.sqlite_manager and hasattr(self.sqlite_manager, "close") and self._own_manager:
                try:
                    self.sqlite_manager.close()
                except Exception:
                    pass
            if getattr(self, "session", None) is not None:
                try:
                    self.session.close()
                except Exception:
                    pass
        except Exception:
            logger.exception("Erreur lors du close de AuthControllerOffline")
