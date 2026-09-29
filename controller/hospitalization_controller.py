import logging
from typing import Optional, List

from repositories.hospitalization_repo import HospitalizationRepository
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.user_repo import UserRepository


class HospitalizationController:
    def __init__(
        self,
        repo: HospitalizationRepository,
        current_user,
        audit_repo: Optional[AuditRepository] = None,
        notification_repo: Optional[NotificationRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ):
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.notification_repo = notification_repo
        self.user_repo = user_repo
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
        update = self.repo.add_status_update(hospitalization_id, status, note, self.user.user_id)
        if status == "AGGRAVATION":
            self._notify_team_of_aggravation(update)
        return update

    def _notify_team_of_aggravation(self, update):
        """Retour terrain 2026-09-28 (decision utilisateur) : une aggravation
        notee a 22h par un medecin ne doit pas rester invisible pour le reste
        de l'equipe jusqu'a ce que quelqu'un rouvre ce dossier precis. Diffuse
        a tout medecin/nurse actif AUTRE que l'auteur - jamais bloquant pour
        l'action metier elle-meme, meme motif que l'audit (_log_audit)."""
        if not (self.notification_repo and self.user_repo):
            return
        try:
            hosp = self.repo._get_or_raise(update.hospitalization_id)
            patient_name = "Patient"
            if hosp.patient:
                patient_name = f"{hosp.patient.first_name or ''} {hosp.patient.last_name or ''}".strip() or "Patient"

            payload = {
                "hospitalization_id": hosp.id,
                "patient_id": hosp.patient_id,
                "patient_name": patient_name,
                "note": update.note,
                "reported_by_name": getattr(self.user, "full_name", None) or getattr(self.user, "username", None),
            }
            for staff in self.user_repo.get_users_by_role_names(["medecin", "nurse"]):
                if staff.user_id == self.user.user_id:
                    continue
                self.notification_repo.create(
                    recipient_user_id=staff.user_id,
                    type="hospitalization_aggravation",
                    payload=payload,
                )
        except Exception:
            self.logger.exception("Échec de la diffusion de l'alerte d'aggravation à l'équipe")

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

    def generate_discharge_letter_pdf(self, hospitalization_id: int) -> bytes:
        return self.repo.generate_discharge_letter_pdf(hospitalization_id)
