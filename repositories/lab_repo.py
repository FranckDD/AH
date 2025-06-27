from sqlalchemy.orm import Session, joinedload, subqueryload
from models.lab import (
    Examen, Parametre, ReferenceRange, 
    LabResult, LabResultDetail
)
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import func, desc

class LabRepository:
    def __init__(self, session: Session):
        self.session = session
        
    
    # Examens
    def create_examen(self, data: dict) -> Examen:
        examen = Examen(**data)
        self.session.add(examen)
        self.session.commit()
        self.session.refresh(examen)
        return examen

    def update_examen(self, examen_id: int, data: dict) -> Optional[Examen]:
        examen = self.session.get(Examen, examen_id)
        if examen:
            for key, value in data.items():
                setattr(examen, key, value)
            self.session.commit()
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
    
    # Paramètres
    def create_parametre(self, data: dict) -> Parametre:
        parametre = Parametre(**data)
        self.session.add(parametre)
        self.session.commit()
        self.session.refresh(parametre)
        return parametre

    def get_parametre(self, parametre_id: int) -> Optional[Parametre]:
        return self.session.get(Parametre, parametre_id)
    
    def list_parametres_for_examen(self, examen_id: int) -> List[Parametre]:
        return self.session.query(Parametre).filter(Parametre.examen_id == examen_id).all()
    
    # Plages de référence
    def create_reference_range(self, data: dict) -> ReferenceRange:
        ref_range = ReferenceRange(**data)
        self.session.add(ref_range)
        self.session.commit()
        self.session.refresh(ref_range)
        return ref_range

    def get_reference_ranges(self, parametre_id: int) -> List[ReferenceRange]:
        return self.session.query(ReferenceRange).filter(
            ReferenceRange.parametre_id == parametre_id
        ).all()
    
    def list_reference_ranges(self, parametre_id: Optional[int] = None) -> List[ReferenceRange]:
        """
        Si parametre_id est None => renvoie toutes les plages,
        sinon renvoie celles du paramètre donné.
        """
        q = self.session.query(ReferenceRange)
        if parametre_id is not None:
            q = q.filter(ReferenceRange.parametre_id == parametre_id)
        return q.all()
    
    # Résultats
    def create_lab_result(self, data: dict) -> LabResult:
        result = LabResult(**data)
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result
    
    def update_lab_result(self, result_id: int, data: dict) -> Optional[LabResult]:
        result = self.session.get(LabResult, result_id)
        if result:
            for key, value in data.items():
                setattr(result, key, value)
            self.session.commit()
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
                    joinedload(LabResult.patient),   # Patient: jointure directe
                    joinedload(LabResult.examen),    # Examen: jointure directe
                    subqueryload(LabResult.details)  # Détails: chargement par sous-requête
                              .joinedload(LabResultDetail.parametre)  # Paramètre associé
                )
                .filter(LabResult.status == status)
                .all()
        )
    
    # Détails de résultats
    def add_result_detail(self, data: dict) -> LabResultDetail:
        detail = LabResultDetail(**data)
        self.session.add(detail)
        self.session.commit()
        self.session.refresh(detail)
        return detail
    
    def update_result_detail(self, detail_id: int, data: dict) -> Optional[LabResultDetail]:
        detail = self.session.get(LabResultDetail, detail_id)
        if detail:
            for key, value in data.items():
                setattr(detail, key, value)
            self.session.commit()
            return detail
        return None
    
    def interpret_result(self, detail_id: int, patient_age: int, patient_sex: str) -> Optional[LabResultDetail]:
        detail = self.session.get(LabResultDetail, detail_id)
        if not detail or not detail.valeur_num:
            return None
        
        # Trouver la plage de référence appropriée
        ref_range = self.session.query(ReferenceRange).filter(
            ReferenceRange.parametre_id == detail.parametre_id,
            ReferenceRange.sexe.in_(['X', patient_sex]),
            ReferenceRange.age_min <= patient_age,
            ReferenceRange.age_max >= patient_age
        ).first()
        
        if ref_range:
            if ref_range.valeur_min <= detail.valeur_num <= ref_range.valeur_max:
                detail.interpretation = "normal"
                detail.flagged = False
            else:
                detail.interpretation = "abnormal"
                detail.flagged = True
            self.session.commit()
        return detail
    
    def complete_result(self, result_id: int, patient_age: int, patient_sex: str) -> Optional[LabResult]:
        result = self.get_full_lab_result(result_id)
        if not result:
            return None
        
        for detail in result.details:
            self.interpret_result(detail.detail_id, patient_age, patient_sex)
        
        result.status = 'completed'
        self.session.commit()
        return result
    

    def generate_lab_code(self, patient_id: Optional[int]) -> str:
        today = datetime.now()
        month = today.strftime("%m")
        doy_str = f"{today.timetuple().tm_yday:03d}"
        # count des tests déjà enregistrés aujourd'hui
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = today.replace(hour=23, minute=59, second=59, microsecond=999999)
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

    


         # Paramètres
    def list_parametres(self) -> List[Parametre]:
        """Retourne la liste de tous les paramètres."""
        return self.session.query(Parametre).all()

    def update_parametre(self, parametre_id: int, data: dict) -> Optional[Parametre]:
        """Met à jour un paramètre existant."""
        p = self.session.get(Parametre, parametre_id)
        if p:
            for key, value in data.items():
                setattr(p, key, value)
            self.session.commit()
            self.session.refresh(p)
            return p
        return None

    def delete_parametre(self, parametre_id: int) -> bool:
        """Supprime un paramètre."""
        p = self.session.get(Parametre, parametre_id)
        if p:
            self.session.delete(p)
            self.session.commit()
            return True
        return False

         # (1) Récupérer toutes les plages d’un paramètre
    def get_reference_ranges(self, parametre_id: int) -> List[ReferenceRange]:
        return (
            self.session
                .query(ReferenceRange)
                .filter(ReferenceRange.parametre_id == parametre_id)
                .all()
        )

    # (2) Récupérer une plage par son ID
    def get_reference_range(self, range_id: int) -> Optional[ReferenceRange]:
        return self.session.get(ReferenceRange, range_id)

    # (3) Mettre à jour une plage
    def update_reference_range(self, range_id: int, data: dict) -> Optional[ReferenceRange]:
        rr = self.get_reference_range(range_id)
        if not rr:
            return None
        for key, val in data.items():
            setattr(rr, key, val)
        self.session.commit()
        self.session.refresh(rr)
        return rr

    # (4) Supprimer une plage
    def delete_reference_range(self, range_id: int) -> bool:
        rr = self.get_reference_range(range_id)
        if not rr:
            return False
        self.session.delete(rr)
        self.session.commit()
        return True