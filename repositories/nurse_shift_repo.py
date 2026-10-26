# repositories/nurse_shift_repo.py
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from models.nurse_shift import NurseShift, SHIFT_TYPES
from models.user import User
from models.application_role import ApplicationRole


class ShiftConflictError(ValueError):
    """Refus d'affectation avec un code stable (traduit cote frontend) et un
    message francais de repli."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


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
            raise ShiftConflictError("shift_already_assigned", "Cet infirmier est déjà affecté à ce créneau.")

        # Conflit de garde (decision du proprietaire) : MATIN + APRES_MIDI le meme
        # jour restent permis ; NUIT est exclusive (jamais avec un autre creneau).
        # Plusieurs infirmiers par creneau : aucune limite.
        others = (
            self.session.query(NurseShift)
            .filter(
                NurseShift.shift_date == shift_date,
                NurseShift.nurse_id == nurse_id,
                NurseShift.shift_type != shift_type,
            )
            .all()
        )
        if others and (shift_type == "NUIT" or any(o.shift_type == "NUIT" for o in others)):
            if shift_type == "NUIT":
                raise ShiftConflictError(
                    "shift_night_exclusive",
                    "Cet infirmier a déjà un créneau ce jour-là : la nuit ne peut pas être cumulée avec le matin ou l'après-midi."
                )
            raise ShiftConflictError(
                "shift_night_exclusive",
                "Cet infirmier est déjà de nuit ce jour-là : la nuit ne peut pas être cumulée avec le matin ou l'après-midi."
            )

        # Repos obligatoire : NUIT le jour D interdit MATIN le jour D+1 (les deux sens).
        if shift_type in ("MATIN", "NUIT"):
            from datetime import timedelta
            if shift_type == "MATIN":
                neighbour_date, neighbour_type = shift_date - timedelta(days=1), "NUIT"
            else:
                neighbour_date, neighbour_type = shift_date + timedelta(days=1), "MATIN"
            clash = (
                self.session.query(NurseShift)
                .filter(
                    NurseShift.shift_date == neighbour_date,
                    NurseShift.nurse_id == nurse_id,
                    NurseShift.shift_type == neighbour_type,
                )
                .first()
            )
            if clash is not None:
                if shift_type == "MATIN":
                    raise ShiftConflictError("shift_rest_after_night", "Cet infirmier était de nuit la veille : repos obligatoire le matin.")
                raise ShiftConflictError("shift_rest_after_night", "Cet infirmier est déjà de matin le lendemain : repos obligatoire après une nuit.")

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
            raise ShiftConflictError("shift_already_assigned", "Cet infirmier est déjà affecté à ce créneau.")
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
