# controllers/prescription_controller.py
import logging
from repositories.prescription_repo import PrescriptionRepository
from repositories.audit_repo import AuditRepository
from datetime import date, timedelta
from typing import Dict, Any, Optional
import datetime


class PrescriptionController:
    def __init__(self, repo=None, patient_controller=None, current_user=None, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo or PrescriptionRepository()  # type: ignore
        self.patient_ctrl = patient_controller
        self.current_user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)



# --- NOUVELLE MÉTHODE POUR LE DOSSIER ---
    def get_patient_prescriptions(self, patient_id: int, status: str = None):
        """
        Récupère toutes les prescriptions d'un patient spécifique pour son dossier.
        """
        # On utilise le repo existant mais on simplifie l'appel pour le controller
        items, total = self.repo.list_paginated_with_relations(
            page=1, per_page=100, # On veut souvent tout voir dans le dossier
            patient_id=patient_id
        )
        # Filtrage optionnel par statut (ex: 'active') si besoin en post-traitement ou via param repo
        if status:
            items = [p for p in items if p.status == status]
            
        return items


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
        # Inject audit fields (existant)
        if self.current_user:
            data['prescribed_by'] = self.current_user.user_id
            data['prescribed_by_name'] = self.current_user.username
        else:
            data['prescribed_by'] = None
            data['prescribed_by_name'] = None
            
        presc = self.repo.create(data)
        
        # --- AUDIT LOG ---
        if self.audit_repo and self.current_user:
            try:
                presc_id = getattr(presc, 'prescription_id', None)
                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="CREATE",
                    resource_id=presc_id,
                    details=f"Patient: {data.get('patient_id')}. Médicament: {data.get('medication')}" # type: ignore
                )
            except Exception: pass
            
        return presc

    def update_prescription(self, prescription_id: int, data: dict):
        # Inject audit fields (existant)
        if self.current_user:
            data['prescribed_by'] = self.current_user.user_id
            data['prescribed_by_name'] = self.current_user.username
            
        presc = self.repo.update(prescription_id, data)
        
        if self.audit_repo and self.current_user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="UPDATE",
                    resource_id=prescription_id,
                    new_values=data
                )
            except Exception: pass
        return presc

    def delete_prescription(self, prescription_id: int):
        res = self.repo.delete(prescription_id)
        
        if res and self.audit_repo and self.current_user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.current_user,
                    resource_type="Prescription",
                    action_performed="DELETE",
                    resource_id=prescription_id
                )
            except Exception: pass
        return res
    
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
        

        
    
    
