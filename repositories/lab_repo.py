# repositories/lab_repo.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import func, desc
from decimal import Decimal, InvalidOperation
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from models.lab import (
    Examen, Parametre, ReferenceRange,
    LabResult, LabResultDetail
)


class LabRepository:
    def __init__(self, session: Session):
        self.session = session

    # -----------------
    # Exams / Paramètres
    # -----------------
    def create_examen(self, data: Dict[str, Any]) -> Examen:
        examen = Examen(**data)
        self.session.add(examen)
        self.session.commit()
        self.session.refresh(examen)
        return examen

    def update_examen(self, examen_id: int, data: Dict[str, Any]) -> Optional[Examen]:
        examen = self.session.get(Examen, examen_id)
        if examen:
            for k, v in data.items():
                setattr(examen, k, v)
            self.session.commit()
            self.session.refresh(examen)
            return examen
        return None

    def delete_examen(self, examen_id: int) -> bool:
        examen = self.session.get(Examen, examen_id)
        if examen:
            self.session.delete(examen)
            self.session.commit()
            return True
        return False

    def get_examen(self, examen_id: int) -> Optional[Examen]:
        return self.session.get(Examen, examen_id)

    def get_examen_by_code(self, code: str) -> Optional[Examen]:
        return self.session.query(Examen).filter(Examen.code == code).first()

    def list_examens(self) -> List[Examen]:
        return self.session.query(Examen).all()

    # -----------------
    # Parametres
    # -----------------
    def create_parametre(self, data: Dict[str, Any]) -> Parametre:
        param = Parametre(**data)
        self.session.add(param)
        self.session.commit()
        self.session.refresh(param)
        return param

    def get_parametre(self, parametre_id: int) -> Optional[Parametre]:
        return self.session.get(Parametre, parametre_id)

    def list_parametres_for_examen(self, examen_id: int) -> List[Parametre]:
        return self.session.query(Parametre).filter(Parametre.examen_id == examen_id).all()

    def list_parametres(self) -> List[Parametre]:
        return self.session.query(Parametre).all()

    def update_parametre(self, parametre_id: int, data: Dict[str, Any]) -> Optional[Parametre]:
        p = self.session.get(Parametre, parametre_id)
        if p:
            for k, v in data.items():
                setattr(p, k, v)
            self.session.commit()
            self.session.refresh(p)
            return p
        return None

    def delete_parametre(self, parametre_id: int) -> bool:
        p = self.session.get(Parametre, parametre_id)
        if p:
            self.session.delete(p)
            self.session.commit()
            return True
        return False

    # -----------------
    # Reference ranges
    # -----------------
    def list_reference_ranges(self, parametre_id: Optional[int] = None) -> List[ReferenceRange]:
        q = self.session.query(ReferenceRange)
        if parametre_id is not None:
            q = q.filter(ReferenceRange.parametre_id == parametre_id)
        return q.all()

    def get_reference_range(self, range_id: int) -> Optional[ReferenceRange]:
        return self.session.get(ReferenceRange, range_id)

    def create_reference_range(self, data: Dict[str, Any]) -> ReferenceRange:
        rr = ReferenceRange(**data)
        self.session.add(rr)
        self.session.commit()
        self.session.refresh(rr)
        return rr

    def update_reference_range(self, range_id: int, data: Dict[str, Any]) -> Optional[ReferenceRange]:
        rr = self.get_reference_range(range_id)
        if not rr:
            return None
        for k, v in data.items():
            setattr(rr, k, v)
        self.session.commit()
        self.session.refresh(rr)
        return rr

    def delete_reference_range(self, range_id: int) -> bool:
        rr = self.get_reference_range(range_id)
        if not rr:
            return False
        self.session.delete(rr)
        self.session.commit()
        return True

    # -----------------
    # Lab results
    # -----------------
    def _build_lab_code_from_id(self, result_id: int, patient_id: Optional[int]) -> str:
        """Compose deterministic code using result_id and test_date context."""
        now = datetime.now()
        month = now.strftime("%m")
        doy = f"{now.timetuple().tm_yday:03d}"
        base = f"{month}{doy}-{result_id}"
        return f"EXT-{base}" if patient_id is None else base

    def create_lab_result(self, data: Dict[str, Any]) -> LabResult:
        """
        Create a LabResult and (optionally) its details.
        Behavior:
         - If Session has no active transaction: repo WILL commit/rollback.
         - If Session already has transaction: repo will flush but NOT commit/rollback (caller owns tx).
        Expected input: dict possibly containing 'details': List[dict]
        """
        details = data.pop('details', None)
        own_tx = not bool(self.session.in_transaction())

        try:
            # Build result object
            result = LabResult(**{k: v for k, v in data.items()})
            self.session.add(result)
            # assign PK
            self.session.flush()

            # generate stable code if not provided (use result_id to avoid races)
            if not getattr(result, "code_lab_patient", None):
                result.code_lab_patient = self._build_lab_code_from_id(result.result_id, result.patient_id)

            # create details if provided
            if details:
                for d in details:
                    d_copy = dict(d)
                    d_copy['result_id'] = result.result_id
                    detail = LabResultDetail(**d_copy)
                    self.session.add(detail)

            # commit or leave to caller
            if own_tx:
                self.session.commit()
            else:
                # ensure DB receives changes when caller continues
                self.session.flush()

            self.session.refresh(result)
            return result

        except Exception:
            # rollback only if we started the transaction
            if own_tx:
                try:
                    self.session.rollback()
                except Exception:
                    pass
            raise

    def add_result_detail(self, data: Dict[str, Any]) -> LabResultDetail:
        """
        Legacy behaviour: adds a single detail and commits immediately.
        If you want atomic multi-detail creation, pass details list to create_lab_result.
        """
        detail = LabResultDetail(**data)
        self.session.add(detail)
        self.session.commit()
        self.session.refresh(detail)
        return detail

    def update_lab_result(self, result_id: int, data: Dict[str, Any]) -> Optional[LabResult]:
        result = self.session.get(LabResult, result_id)
        if result:
            for k, v in data.items():
                setattr(result, k, v)
            self.session.commit()
            self.session.refresh(result)
            return result
        return None

    def get_lab_result(self, result_id: int) -> Optional[LabResult]:
        return self.session.get(LabResult, result_id)

    def get_full_lab_result(self, result_id: int) -> Optional[LabResult]:
        return self.session.query(LabResult).options(
            joinedload(LabResult.details).joinedload(LabResultDetail.parametre),
            joinedload(LabResult.examen),
            joinedload(LabResult.patient)
        ).filter(LabResult.result_id == result_id).first()

    def list_results_for_patient(self, patient_id: int) -> List[LabResult]:
        return self.session.query(LabResult).filter(
            LabResult.patient_id == patient_id
        ).order_by(desc(LabResult.test_date)).all()

    def list_results_by_date(self, start_date: datetime, end_date: datetime) -> List[LabResult]:
        return self.session.query(LabResult).filter(
            LabResult.test_date.between(start_date, end_date)
        ).all()

    def list_results_by_status(self, status: str) -> List[LabResult]:
        return (
            self.session
                .query(LabResult)
                .options(
                    joinedload(LabResult.patient),
                    joinedload(LabResult.examen),
                    subqueryload(LabResult.details).joinedload(LabResultDetail.parametre)
                )
                .filter(LabResult.status == status)
                .all()
        )

    def interpret_result(
        self,
        detail_id: int,
        patient_age: int,
        patient_sex: str,
        commit: Optional[bool] = None
    ) -> Optional[LabResultDetail]:
        """
        Interprets a single LabResultDetail according to reference ranges.
        commit:
            - None (default): decide automatically (commit if no outer transaction)
            - True: commit here
            - False: flush only (no commit)
        """
        detail = self.session.get(LabResultDetail, detail_id)
        if not detail:
            return None

        if detail.valeur_num is None:
            return detail

        # stable numeric conversion
        try:
            val = Decimal(str(detail.valeur_num))
        except (InvalidOperation, TypeError):
            # cannot interpret non-numeric
            return detail

        ref_range = self.session.query(ReferenceRange).filter(
            ReferenceRange.parametre_id == detail.parametre_id,
            ReferenceRange.sexe.in_(['X', patient_sex]),
            ReferenceRange.age_min <= patient_age,
            ReferenceRange.age_max >= patient_age
        ).first()

        if not ref_range:
            return detail

        try:
            minv = Decimal(str(ref_range.valeur_min))
            maxv = Decimal(str(ref_range.valeur_max))
        except (InvalidOperation, TypeError):
            return detail

        if minv <= val <= maxv:
            detail.interpretation = "normal"
            detail.flagged = False
        else:
            detail.interpretation = "abnormal"
            detail.flagged = True

        # decide commit behaviour
        if commit is None:
            own_tx = not bool(self.session.in_transaction())
            commit = own_tx

        if commit:
            self.session.commit()
            self.session.refresh(detail)
        else:
            # do not commit outer transaction - only flush
            self.session.flush()

        return detail

    def complete_result(
        self,
        result_id: int,
        patient_age: int,
        patient_sex: str,
        commit: Optional[bool] = None
    ) -> Optional[LabResult]:
        """
        Interprets all details for a result and marks it as completed.
        If commit is None => commit only if we are not already in a transaction.
        """
        result = self.get_full_lab_result(result_id)
        if not result:
            return None

        own_tx = not bool(self.session.in_transaction())
        if commit is None:
            commit = own_tx

        try:
            # interpret each detail without committing each time
            for detail in result.details:
                # call interpret_result but avoid commit per-detail (commit only at end if requested)
                self.interpret_result(detail.detail_id, patient_age, patient_sex, commit=False)

            result.status = 'completed'

            if commit:
                self.session.commit()
                self.session.refresh(result)
            else:
                self.session.flush()

            return result

        except Exception:
            if commit:
                try:
                    self.session.rollback()
                except Exception:
                    pass
            raise

    def generate_lab_code(self, patient_id: Optional[int]) -> str:
        # Keep previous behaviour for external code generation (same semantics)
        today = datetime.now()
        month = today.strftime("%m")
        doy_str = f"{today.timetuple().tm_yday:03d}"
        # count of tests registered today (still possible race if used alone)
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        count_today = (
            self.session
                .query(func.count(LabResult.result_id))
                .filter(LabResult.test_date.between(start, end))
                .scalar()
            or 0
        )
        rank = count_today + 1
        base = f"{month}{doy_str}-{rank}"
        return f"EXT-{base}" if patient_id is None else base
