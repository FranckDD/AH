from repositories.prescription_repo import PrescriptionRepository
from models.prescription import Prescription
from sqlalchemy import text
import logging

class PrescriptionService:
    def __init__(self):
        self.repo = PrescriptionRepository()
        self.logger = logging.getLogger(__name__)

    def create_prescription(self, prescription_data: dict) -> Prescription:
        """Utilise la procédure stockée pour créer une prescription"""
        try:
            # Appel à la procédure stockée
            self.repo.execute_procedure(
                "create_prescription",
                {
                    'patient_id': prescription_data['patient_id'],
                    'medication': prescription_data['medication'],
                    'dosage': prescription_data['dosage'],
                    'frequency': prescription_data['frequency'],
                    'duration': prescription_data['duration'],
                    'medical_record_id': prescription_data.get('medical_record_id'),
                    'start_date': prescription_data.get('start_date'),
                    'end_date': prescription_data.get('end_date'),
                    'notes': prescription_data.get('notes'),
                    'created_by': prescription_data['created_by']
                }
            )
            
            # Récupération et retour de la prescription créée
            return self.repo.get_last_prescription()
            
        except Exception as e:
            self.logger.error(f"Erreur service prescription: {str(e)}", exc_info=True)
            raise