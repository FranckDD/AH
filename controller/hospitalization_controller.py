import logging
from typing import Optional, List

from repositories.hospitalization_repo import HospitalizationRepository
from repositories.audit_repo import AuditRepository


class HospitalizationController:
    def __init__(
        self,
        repo: HospitalizationRepository,
        current_user,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)

    def _log_audit(self, action_performed: str, resource_id: int, details: Optional[str] = None):
        if not (self.audit_repo and self.user):
            return
        try:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="Hospitalization",
                action_performed=action_performed,
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            self.logger.exception("Échec de l'écriture d'audit")

    def admit(self, patient_id: int, admission_reason: Optional[str]):
        hosp = self.repo.admit(patient_id, self.user.user_id, admission_reason)
        self._log_audit("ADMIT", hosp.id, details=admission_reason)
        return hosp

    def add_status_update(self, hospitalization_id: int, status: str, note: Optional[str]):
        return self.repo.add_status_update(hospitalization_id, status, note, self.user.user_id)

    def discharge(self, hospitalization_id: int, discharge_disposition: str, discharge_note: Optional[str]):
        hosp = self.repo.discharge(hospitalization_id, discharge_disposition, discharge_note, self.user.user_id)
        self._log_audit("DISCHARGE", hosp.id, details=discharge_disposition)
        return hosp

    def list_current(self) -> List:
        return self.repo.list_current()

    def get_history_for_patient(self, patient_id: int) -> List:
        return self.repo.get_history_for_patient(patient_id)

    def count_current(self) -> int:
        return self.repo.count_current()
