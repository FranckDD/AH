# controllers/medical_controller.py
import logging
from repositories.medical_repo import MedicalRecordRepository

class MedicalRecordController:
    def __init__(self, repo=None, patient_controller=None, current_user=None):
        self.repo = repo or MedicalRecordRepository()
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.logger = logging.getLogger(__name__)

    def list_records(self, patient_id=None, page=1, per_page=20):
        try:
            return self.repo.list_records(patient_id=patient_id, page=page, per_page=per_page)
        except Exception as e:
            self.logger.error(f"Erreur list_records: {e}", exc_info=True)
            raise

    def get_record(self, record_id: int):
        return self.repo.get(record_id)

    def create_record(self, data: dict):
        return self.repo.create(data)

    def update_record(self, record_id: int, data: dict):
        return self.repo.update(record_id, data)

    def delete_record(self, record_id: int):
        return self.repo.delete(record_id)

    def list_motifs(self) -> list[dict]:
        """Récupère les codes et labels fr des motifs."""
        return self.repo.get_motifs()

    def find_patient(self, query: str):
        """Recherche un patient par id numérique ou code_patient."""
        if not self.patient_ctrl:
            raise RuntimeError("PatientController non fourni")
        if query.isdigit():
            return self.patient_ctrl.get_patient(int(query))
        return self.patient_ctrl.find_by_code(query)
    
    