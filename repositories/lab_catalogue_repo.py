# repositories/lab_catalogue_repo.py
"""Acces donnees du catalogue du laboratoire (ecriture par la cheffe du laboratoire / l'admin).

Ne commit jamais : le controleur valide la transaction avec l'ecriture d'audit.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from models.lab import Examen, LabResult, LabResultDetail, Parametre, ReferenceRange


class LabCatalogueRepository:
    def __init__(self, session: Session):
        self.session = session

    # ---- lecture
    def list_exams(self, include_inactive: bool) -> List[Examen]:
        q = self.session.query(Examen).options(
            joinedload(Examen.parametres).joinedload(Parametre.reference_ranges))
        if not include_inactive:
            q = q.filter(Examen.is_active.is_(True))
        return q.order_by(Examen.sort_order, Examen.nom, Examen.id).all()

    def used_exam_ids(self) -> Set[int]:
        ids = {r[0] for r in self.session.query(LabResult.examen_id).filter(LabResult.examen_id.isnot(None)).distinct()}
        ids |= {r[0] for r in self.session.query(Parametre.examen_id).join(
            LabResultDetail, LabResultDetail.parametre_id == Parametre.id).distinct()}
        return ids

    def used_parameter_ids(self) -> Set[int]:
        return {r[0] for r in self.session.query(LabResultDetail.parametre_id).distinct()}

    def exam_in_use(self, examen_id: int) -> bool:
        if self.session.query(LabResult.result_id).filter(LabResult.examen_id == examen_id).first() is not None:
            return True
        return self.session.query(LabResultDetail.detail_id).join(
            Parametre, Parametre.id == LabResultDetail.parametre_id
        ).filter(Parametre.examen_id == examen_id).first() is not None

    def parameter_in_use(self, parametre_id: int) -> bool:
        return self.session.query(LabResultDetail.detail_id).filter(
            LabResultDetail.parametre_id == parametre_id).first() is not None

    def get_exam(self, examen_id: int) -> Optional[Examen]:
        return self.session.get(Examen, examen_id)

    def get_exam_by_code(self, code: str) -> Optional[Examen]:
        return self.session.query(Examen).filter(func.upper(Examen.code) == code.upper()).first()

    def get_parameter(self, parametre_id: int) -> Optional[Parametre]:
        return self.session.get(Parametre, parametre_id)

    def get_range(self, range_id: int) -> Optional[ReferenceRange]:
        return self.session.get(ReferenceRange, range_id)

    def exams_ordered(self) -> List[Examen]:
        return self.session.query(Examen).order_by(Examen.sort_order, Examen.nom, Examen.id).all()

    def parameters_ordered(self, examen_id: int) -> List[Parametre]:
        return self.session.query(Parametre).filter(Parametre.examen_id == examen_id).order_by(
            Parametre.ordre, Parametre.id).all()

    def next_parameter_order(self, examen_id: int) -> int:
        top = self.session.query(func.max(Parametre.ordre)).filter(Parametre.examen_id == examen_id).scalar()
        return (top or 0) + 1

    def find_duplicate_range(self, parametre_id: int, cols: Dict[str, Any], exclude_id: Optional[int] = None):
        q = self.session.query(ReferenceRange).filter(
            ReferenceRange.parametre_id == parametre_id,
            ReferenceRange.sexe == cols["sexe"],
            ReferenceRange.valeur_min == cols["valeur_min"],
            ReferenceRange.valeur_max == cols["valeur_max"])
        for key in ("age_min_days", "age_max_days", "ga_min_weeks", "ga_max_weeks"):
            col = getattr(ReferenceRange, key)
            q = q.filter(col.is_(None)) if cols[key] is None else q.filter(col == cols[key])
        if exclude_id is not None:
            q = q.filter(ReferenceRange.id != exclude_id)
        return q.first()

    # ---- ecriture (sans commit)
    def add(self, obj) -> None:
        self.session.add(obj)
        self.session.flush()

    def delete_exam_cascade(self, examen: Examen) -> None:
        param_ids = [r[0] for r in self.session.query(Parametre.id).filter(Parametre.examen_id == examen.id)]
        if param_ids:
            self.session.query(ReferenceRange).filter(
                ReferenceRange.parametre_id.in_(param_ids)).delete(synchronize_session=False)
            self.session.query(Parametre).filter(Parametre.id.in_(param_ids)).delete(synchronize_session=False)
        self.session.expire(examen)
        self.session.delete(examen)
        self.session.flush()

    def delete_parameter_cascade(self, parametre: Parametre) -> None:
        self.session.query(ReferenceRange).filter(
            ReferenceRange.parametre_id == parametre.id).delete(synchronize_session=False)
        self.session.expire(parametre)
        self.session.delete(parametre)
        self.session.flush()

    def delete(self, obj) -> None:
        self.session.delete(obj)
        self.session.flush()
