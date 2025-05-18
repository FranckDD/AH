# controllers/prescription_controller.py
import logging
from repositories.prescription_repo import PrescriptionRepository

class PrescriptionController:
    def __init__(self, repo=None, patient_controller=None, current_user=None):
        self.repo = repo or PrescriptionRepository()
        self.patient_ctrl = patient_controller
        self.current_user = current_user
        self.logger = logging.getLogger(__name__)

    def list_prescriptions(self, patient_id=None, page=1, per_page=20):
        try:
            return self.repo.list(patient_id=patient_id, page=page, per_page=per_page)
        except Exception as e:
            self.logger.error(f"Erreur list_prescriptions: {e}", exc_info=True)
            raise

    def get_prescription(self, prescription_id: int):
        return self.repo.get(prescription_id)

    def create_prescription(self, data: dict):
        # Inject audit fields
        if self.current_user:
            data['prescribed_by'] = self.current_user.user_id
            data['prescribed_by_name'] = self.current_user.username
        else:
            data['prescribed_by'] = None
            data['prescribed_by_name'] = None
        return self.repo.create(data)

    def update_prescription(self, prescription_id: int, data: dict):
        # Inject audit fields
        if self.current_user:
            data['prescribed_by'] = self.current_user.user_id
            data['prescribed_by_name'] = self.current_user.username
        else:
            data['prescribed_by'] = None
            data['prescribed_by_name'] = None
        return self.repo.update(prescription_id, data)

    def delete_prescription(self, prescription_id: int):
        return self.repo.delete(prescription_id)
