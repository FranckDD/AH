# controllers/auth_controller.py
from repositories.user_repo import UserRepository
from controller.user_controller import UserController
from repositories.role_repo import RoleRepository
from models.user import pwd_context
from controller.patient_controller import PatientController
from repositories.patient_repo import PatientRepository
from controller.medical_controller import MedicalRecordController
from repositories.medical_repo import MedicalRecordRepository
from controller.prescription_controller import PrescriptionController
from repositories.prescription_repo import PrescriptionRepository
from repositories.appointment_repo import AppointmentRepository
from controller.appointment_controller import AppointmentController
from repositories.cs_repo import ConsultationSpirituelRepository
from controller.cs_controller import ConsultationSpirituelController
from repositories.pharmacy_repo import PharmacyRepository
from controller.pharmacy_controller import PharmacyController
from repositories.caisse_repo import CaisseRepository
from controller.caisse_controller import CaisseController
from repositories.caisse_retrait_repo import CaisseRetraitRepository
from controller.caisse_retrait_controller import CaisseRetraitController
from repositories.lab_repo import LabRepository
from controller.lab_controller import LabController
from models.database import DatabaseManager


class AuthController:
    def __init__(self, db_session=None):
        # Utilise la session passée par FastAPI ou crée la sienne
        if db_session:
            self.session = db_session
        else:
            self.db = DatabaseManager("postgresql://postgres:Admin_2025@localhost/AH2")
            self.session = self.db.get_session()

        # 2) Passe la session à TOUS tes repositories
        self.user_repo = UserRepository(self.session)
        self.role_repo         = RoleRepository(self.session) 
        self.patient_repo = PatientRepository(self.session)
        self.medical_repo = MedicalRecordRepository(self.session)
        self.prescription_repo = PrescriptionRepository(self.session)
        self.appointment_repo = AppointmentRepository(self.session)
        self.cs_repo = ConsultationSpirituelRepository(self.session)
        self.pharmacy_repo = PharmacyRepository(self.session)
        self.caisse_repo = CaisseRepository(self.session)
        self.lab_repo = LabRepository(self.session)


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
            self.user_controller         = UserController(self.user_repo, self.role_repo)
            pat_repo = PatientRepository(self.session)
            self.patient_controller = PatientController(pat_repo, self.current_user)

            med_repo = MedicalRecordRepository(self.session)
            self.medical_record_controller = MedicalRecordController(
                repo=med_repo,
                patient_controller=self.patient_controller,
                current_user=self.current_user
            )

            presc_repo = PrescriptionRepository(self.session)
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
            cs_repo = ConsultationSpirituelRepository(self.session)
            self.consultation_spirituel_controller = ConsultationSpirituelController(
                repo=cs_repo,
                patient_controller=self.patient_controller,
                current_user=self.current_user
            )
            pharm_repo = PharmacyRepository(self.session)
            self.pharmacy_controller = PharmacyController(
                pharm_repo,
                self.current_user
            )
            caisse_retrait_repo = CaisseRetraitRepository(self.session)
            self.caisse_retrait_controller = CaisseRetraitController(
                repo=caisse_retrait_repo,
                current_user=self.current_user
            )
            self.stock_controller = self.pharmacy_controller

            caisse_repo = CaisseRepository(self.session)
            self.caisse_controller = CaisseController(caisse_repo, self.current_user)

            self.lab_repo = LabRepository(self.session)
            self.lab_controller = LabController(
                repo=self.lab_repo,
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
