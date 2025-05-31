# controllers/caisse_controller.py
from typing import List

class CaisseController:
    def __init__(self, repo, current_user):
        self.repo = repo
        self.user = current_user

    def list_transactions(self) -> List:
        return self.repo.list_all()

    def list_for_patient(self, patient_id: int) -> List:
        return self.repo.find_by_patient(patient_id)

    def create_transaction(self, data: dict):
        return self.repo.create(data, self.user)

    def delete_transaction(self, tx_id: int):
        return self.repo.delete(tx_id)
