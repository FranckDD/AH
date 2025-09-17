# controllers/prescription_controller.py
import logging
from repositories.prescription_repo import PrescriptionRepository
from datetime import date, timedelta
from typing import Dict, Any, Optional
import datetime


class PrescriptionController:
    def __init__(self, repo=None, patient_controller=None, current_user=None):
        self.repo = repo or PrescriptionRepository()  # type: ignore
        self.patient_ctrl = patient_controller
        self.current_user = current_user
        self.logger = logging.getLogger(__name__)

    def list_prescriptions(self, page: int = 1, per_page: int = 20,
                           date_from: Optional[str] = None, date_to: Optional[str] = None,
                           patient_id: Optional[int] = None, search: Optional[str] = None) -> Dict[str, Any]:
        """
        Retourne un dict {data: [...], total: N} — accepte date_from/date_to en ISO strings ou date objects.
        """
        df = date_from
        dt = date_to
        try:
            if isinstance(date_from, str):
                df = datetime.datetime.fromisoformat(date_from).date()
            if isinstance(date_to, str):
                dt = datetime.datetime.fromisoformat(date_to).date()
        except Exception:
            # si parse échoue, laisser tel quel (None ou valeur fournie)
            df, dt = date_from, date_to

        try:
            items, total = self.repo.list_paginated_with_relations(
                page=page, per_page=per_page,
                date_from=df, date_to=dt, # type: ignore
                patient_id=patient_id,
                search=search
            )
            return {"data": items, "total": total}
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
    
    def get_by_day(self, target_date: date) -> list:
        return self.repo.find_by_date_range(target_date, target_date)
    
     # Wrappers KPI
    
    def renewals_for_doctor(self, doctor_id: Optional[int] = None, within_days: int = 14):
        d = doctor_id or getattr(self.current_user, 'user_id', None)
        if d is None:
            raise RuntimeError("Doctor id non disponible pour renewals_for_doctor")
        return self.repo.find_renewals_for_doctor(d, within_days)

    def count_renewals_for_doctor(self, doctor_id: Optional[int] = None, within_days: int = 14) -> int:
        d = doctor_id or getattr(self.current_user, 'user_id', None)
        if d is None:
            raise RuntimeError("Doctor id non disponible")
        return self.repo.count_renewals_for_doctor(d, within_days)
    
    def count_prescriptions(self, period: str = "day") -> int:
        """
        Retourne le nombre de prescriptions selon la période.
        period: "day" pour aujourd'hui, "week" pour cette semaine
        """
        today = date.today()
        
        if period == "day":
            return self.repo.count_by_prescription_date(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return self.repo.count_by_prescription_date_range(start_week, end_week)
        else:
            raise ValueError("Période non valide. Utilisez 'day' ou 'week'")
        

        
    
    
