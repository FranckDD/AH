# repositories/nurse_shift_repo.py
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from models.nurse_shift import NurseShift, SHIFT_TYPES
from models.user import User
from models.application_role import ApplicationRole


class NurseShiftRepository:
    def __init__(self, session: Session):
        self.session = session

    def _get_active_nurse(self, nurse_id: int) -> Optional[User]:
        return (
            self.session.query(User)
            .join(ApplicationRole)
            .filter(
                User.user_id == nurse_id,
                ApplicationRole.role_name == "nurse",
                User.is_active == True,
            )
            .first()
        )

    def assign(self, shift_date, shift_type: str, nurse_id: int, created_by_id: int) -> NurseShift:
        if shift_type not in SHIFT_TYPES:
            raise ValueError(f"Créneau invalide : {shift_type}")

        nurse = self._get_active_nurse(nurse_id)
        if nurse is None:
            raise ValueError(f"Infirmier introuvable ou inactif (ID={nurse_id}).")

        existing = (
            self.session.query(NurseShift)
            .filter(
                NurseShift.shift_date == shift_date,
                NurseShift.shift_type == shift_type,
                NurseShift.nurse_id == nurse_id,
            )
            .one_or_none()
        )
        if existing is not None:
            raise ValueError("Cet infirmier est déjà affecté à ce créneau.")

        shift = NurseShift(
            shift_date=shift_date,
            shift_type=shift_type,
            nurse_id=nurse_id,
            created_by=created_by_id,
        )
        self.session.add(shift)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ValueError("Cet infirmier est déjà affecté à ce créneau.")
        self.session.refresh(shift)
        return shift

    def remove(self, shift_id: int) -> None:
        shift = self.session.get(NurseShift, shift_id)
        if shift is None:
            raise ValueError(f"Aucune affectation trouvée pour l'ID={shift_id}")
        self.session.delete(shift)
        self.session.commit()

    def list_for_range(self, start_date, end_date) -> List[NurseShift]:
        return (
            self.session.query(NurseShift)
            .options(joinedload(NurseShift.nurse), joinedload(NurseShift.created_by_user))
            .filter(NurseShift.shift_date >= start_date, NurseShift.shift_date <= end_date)
            .order_by(NurseShift.shift_date.asc(), NurseShift.shift_type.asc())
            .all()
        )
