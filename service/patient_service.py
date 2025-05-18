from datetime import datetime
import logging

class PatientService:
    def __init__(self, patient_repository):
        self.repo = patient_repository
        self.logger = logging.getLogger(__name__)

    def generate_patient_code(self, birth_date: datetime, patient_id: int) -> str:
        """Génère le code PAT-YYYYMMDD-ID"""
        return f"PAT-{birth_date.strftime('%Y%m%d')}-{patient_id:04d}"

    def create_patient_with_code(self, patient_data: dict, creator) -> tuple:
        """Crée un patient et retourne (patient, code)"""
        try:
            # 1. Création initiale
            patient = self.repo.create_patient(patient_data, creator)
            
            # 2. Génération du code
            patient_code = self.generate_patient_code(patient.birth_date, patient.patient_id)
            
            # 3. Mise à jour
            patient.patient_code = patient_code
            updated_patient = self.repo.update_patient(patient)
            
            return updated_patient, patient_code
            
        except Exception as e:
            self.logger.error(f"Erreur création patient: {str(e)}")
            raise