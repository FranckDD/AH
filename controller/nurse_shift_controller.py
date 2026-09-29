# controller/nurse_shift_controller.py
import logging
from typing import Optional, List

from repositories.nurse_shift_repo import NurseShiftRepository
from repositories.user_repo import UserRepository
from repositories.audit_repo import AuditRepository


class NurseShiftController:
    def __init__(
        self,
        repo: NurseShiftRepository,
        user_repo: UserRepository,
        current_user,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.repo = repo
        self.user_repo = user_repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)

    def _ensure_can_manage_schedule(self):
        roles = getattr(self.user, "roles", []) or []
        if "medecin" in roles:
            return
        if "nurse" in roles and getattr(self.user, "is_head_nurse", False):
            return
        raise PermissionError(
            "Seuls le médecin ou le chef infirmier/infirmière peuvent modifier le planning."
        )

    def _log_audit(self, action_performed: str, resource_id: int, details: Optional[str] = None):
        if not (self.audit_repo and self.user):
            return
        try:
            self.audit_repo.log_user_action(
                current_user=self.user,
                resource_type="NurseShift",
                action_performed=action_performed,
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            self.logger.exception("Échec de l'écriture d'audit")

    def assign_shift(self, shift_date, shift_type: str, nurse_id: int):
        self._ensure_can_manage_schedule()
        shift = self.repo.assign(shift_date, shift_type, nurse_id, self.user.user_id)
        self._log_audit("ASSIGN", shift.id, details=f"{shift_type} {shift_date} -> nurse {nurse_id}")
        return shift

    def remove_shift(self, shift_id: int):
        self._ensure_can_manage_schedule()
        self.repo.remove(shift_id)
        self._log_audit("REMOVE", shift_id)

    def list_shifts(self, start_date, end_date) -> List:
        return self.repo.list_for_range(start_date, end_date)

    def list_active_nurses(self) -> List:
        return self.user_repo.get_users_by_role_names(["nurse"])
