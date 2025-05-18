# controllers/auth_controller.py
from repositories.user_repo import UserRepository
from models.user import pwd_context
from controller.patient_controller import PatientController
from repositories.patient_repo import PatientRepository
from controller.medical_controller import MedicalRecordController
from repositories.medical_repo import MedicalRecordRepository
from controller.prescription_controller import PrescriptionController
from repositories.prescription_repo import PrescriptionRepository
from repositories.appointment_repo import AppointmentRepository
from controller.appointment_controller import AppointmentController


class AuthController:
    def __init__(self):
        self.user_repo = UserRepository()
        self.current_user = None
        # sous-contrôleurs initialisés après authentification
        self.patient_controller = None
        self.medical_record_controller = None
        self.prescription_controller = None
        self.appointment_controller = None

    def authenticate(self, username: str, password: str):
        try:
            user = self.user_repo.get_user_by_username(username)
            if not user:
                print(f"Utilisateur {username} non trouvé")
                return None
            if not user.is_active:
                print(f"Compte {username} désactivé")
                return None
            if not pwd_context.verify(password, user.password_hash):
                print(f"Échec de vérification du mot de passe pour {username}")
                return None

            self.current_user = user

            # instanciation des sous-contrôleurs
            pat_repo = PatientRepository()
            self.patient_controller = PatientController(pat_repo, self.current_user)

            med_repo = MedicalRecordRepository()
            self.medical_record_controller = MedicalRecordController(
                repo=med_repo,
                patient_controller=self.patient_controller,
                current_user=self.current_user
            )

            presc_repo = PrescriptionRepository()
            self.prescription_controller = PrescriptionController(
                repo=presc_repo,
                patient_controller=self.patient_controller,
                current_user=self.current_user
            )

            repo = AppointmentRepository(pat_repo.session)
            self.appointment_controller = AppointmentController(
                repo=repo,
                patient_controller=self.patient_controller,
                current_user=self.current_user
        )

            return user

        except Exception as e:
            print(f"Erreur d'authentification pour {username}: {e}")
            import traceback; traceback.print_exc()
            return None

    # — pass-through pour Patients —
    def list_patients(self, *args, **kwargs):
        return self.patient_controller.list_patients(*args, **kwargs)
    def get_patient(self, *args, **kwargs):
        return self.patient_controller.get_patient(*args, **kwargs)
    def create_patient(self, *args, **kwargs):
        return self.patient_controller.create_patient(*args, **kwargs)
    def update_patient(self, *args, **kwargs):
        return self.patient_controller.update_patient(*args, **kwargs)

    # — pass-through pour Dossiers Médicaux —
    def list_motifs(self, *args, **kwargs):
        return self.medical_record_controller.list_motifs(*args, **kwargs)
    def list_records(self, *args, **kwargs):
        return self.medical_record_controller.list_records(*args, **kwargs)
    def create_record(self, *args, **kwargs):
        return self.medical_record_controller.create_record(*args, **kwargs)
    def update_record(self, *args, **kwargs):
        return self.medical_record_controller.update_record(*args, **kwargs)
    def delete_record(self, *args, **kwargs):
        return self.medical_record_controller.delete_record(*args, **kwargs)

    # — pass-through pour Prescriptions —
    def list_prescriptions(self, *args, **kwargs):
        return self.prescription_controller.list_prescriptions(*args, **kwargs)
    def get_prescription(self, *args, **kwargs):
        return self.prescription_controller.get_prescription(*args, **kwargs)
    def create_prescription(self, *args, **kwargs):
        return self.prescription_controller.create_prescription(*args, **kwargs)
    def update_prescription(self, *args, **kwargs):
        return self.prescription_controller.update_prescription(*args, **kwargs)
    def delete_prescription(self, *args, **kwargs):
        return self.prescription_controller.delete_prescription(*args, **kwargs)
    
    def find_patient(self, query: str):
        if not self.patient_controller:
            raise RuntimeError("PatientController non initialisé")
        # si c’est un entier, on cherche par ID
        if query.isdigit():
            return self.patient_controller.get_patient(int(query))
        # sinon on cherche par code_patient
        return self.patient_controller.find_by_code(query)
