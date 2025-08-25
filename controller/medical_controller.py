# controllers/medical_controller.py
import logging
from repositories.medical_repo import MedicalRecordRepository
from datetime import date, timedelta
from typing import Optional, Dict

class MedicalRecordController:
    def __init__(self, repo=None, patient_controller=None, current_user=None):
        self.repo = repo or MedicalRecordRepository() # type: ignore
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.logger = logging.getLogger(__name__)

    def list_records(self, patient_id=None, page=1, per_page=20):
        try:
            return self.repo.list_records(patient_id=patient_id, page=page, per_page=per_page)
        except Exception as e:
            self.logger.error(f"Erreur list_records: {e}", exc_info=True)
            raise

    def get_record(self, record_id: int):
        return self.repo.get(record_id)

    def create_record(self, data: dict):
        return self.repo.create(data)

    def update_record(self, record_id: int, data: dict):
        return self.repo.update(record_id, data)

    def delete_record(self, record_id: int):
        return self.repo.delete(record_id)

    def list_motifs(self) -> list[dict]:
        """Récupère les codes et labels fr des motifs."""
        return self.repo.get_motifs()

    def find_patient(self, query: str):
        """Recherche un patient par id numérique ou code_patient."""
        if not self.patient_ctrl:
            raise RuntimeError("PatientController non fourni")
        if query.isdigit():
            return self.patient_ctrl.get_patient(int(query))
        return self.patient_ctrl.find_by_code(query)
    
    def get_by_day(self, target_date: date) -> list:
        return self.repo.find_by_date_range(target_date, target_date)
    
    def get_last_for_patient(self, patient_id: int):
        return self.repo.get_last_for_patient(patient_id)
    
    #Wrappers KPI

    def _resolve_doctor(self, doctor_id: Optional[int]) -> int:
        if doctor_id is not None:
            return doctor_id
        if self.user and getattr(self.user, 'user_id', None) is not None:
            return self.user.user_id
        raise RuntimeError("doctor_id non disponible")

    def count_records_for_doctor(self, doctor_id: Optional[int]=None, start: Optional[date]=None, end: Optional[date]=None) -> int:
        d = self._resolve_doctor(doctor_id)
        return self.repo.count_records_for_doctor(d, start, end)

    def consultation_type_distribution(self, doctor_id: Optional[int]=None, start: Optional[date]=None, end: Optional[date]=None) -> Dict[str,int]:
        d = self._resolve_doctor(doctor_id)
        return self.repo.breakdown_by_motif_for_doctor(d, start, end)
    
    def count_preconsultations(self, period="day"):
        today = date.today()
        if period == "day":
            return self.repo.count_preconsultations(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return self.repo.count_preconsultations(start_week, end_week)
        return 0
    
    def count_consultations(self, period: str = "day") -> int:
        """
        Retourne le nombre de consultations selon la période.
        period: "day" pour aujourd'hui, "week" pour cette semaine
        """
        today = date.today()
        
        if period == "day":
            return self.repo.count_by_consultation_date(today)
        elif period == "week":
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)
            return self.repo.count_by_consultation_date_range(start_week, end_week)
        else:
            raise ValueError("Période non valide. Utilisez 'day' ou 'week'")
    

    
    

    
    

    
    """def consultation_type_distribution(self, doctor_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> Dict[str, int]:
    # Vérification sécurisée que self.user existe et a un user_id
    if doctor_id is None:
        if not hasattr(self, 'user') or self.user is None:
            raise ValueError("Doctor ID must be provided or user must be authenticated")
        
        if not hasattr(self.user, 'user_id') or self.user.user_id is None:
            raise ValueError("Authenticated user must have a valid user ID")
        
        target_doctor_id = self.user.user_id
    else:
        target_doctor_id = doctor_id
    
    return self.repo.breakdown_by_motif_for_doctor(doctor_id=target_doctor_id, start_date=start, end_date=end) """

    
    