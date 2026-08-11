# controllers/medical_controller.py
import logging
from repositories.medical_repo import MedicalRecordRepository
from datetime import date, timedelta
from typing import Optional, Dict,Any
from repositories.audit_repo import AuditRepository

class MedicalRecordController:
    def __init__(self, repo=None, patient_controller=None, current_user=None, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo or MedicalRecordRepository() # type: ignore
        self.patient_ctrl = patient_controller
        self.user = current_user
        self.audit_repo = audit_repo
        self.logger = logging.getLogger(__name__)


# --- NOUVELLE MÉTHODE CLÉ POUR LE DOSSIER ---
    def get_patient_dme_summary(self, patient_id: int) -> Dict[str, Any]:
        """
        Récupère les informations vitales pour l'en-tête du dossier patient.
        Agrège : Infos Patient + Dernières Constantes + Allergies.
        """
        # 1. Récupérer le patient de base
        if not self.patient_ctrl:
            raise RuntimeError("PatientController manquant")
        
        patient = self.patient_ctrl.get_patient(patient_id)
        if not patient:
            raise ValueError("Patient introuvable")

        # 2. Récupérer le dernier dossier médical (pour les constantes)
        last_record = self.repo.get_last_for_patient(patient_id)

        # 3. Construire le résumé
        summary = {
            # Infos administratives
            "patient_id": patient['patient_id'],
            "full_name": f"{patient['first_name']} {patient['last_name']}",
            "code": patient['code_patient'],
            "age": self._calculate_age(patient['birth_date']), # Helper à ajouter ou gérer front
            "gender": patient['gender'],
            "flags": {
                "is_clinical": patient.get('is_clinical', False),
                "is_toxicology": patient.get('is_toxicology', False),
                "is_spiritual": patient.get('is_spiritual', False),
            },
            
            # Infos Cliniques (Flash) provenant du dernier dossier
            "last_consultation_date": last_record.consultation_date if last_record else None,
            "last_bp": last_record.bp if last_record else None,
            "last_weight": float(last_record.weight) if last_record and last_record.weight else None,
            "last_temp": float(last_record.temperature) if last_record and last_record.temperature else None,
            "last_diagnosis": last_record.diagnosis if last_record else None,
            
            # Allergies (Critique : on prend celles du dernier dossier ou du patient s'il y a un champ dédié)
            "allergies": last_record.allergies if last_record else "Aucune signalée (Dossier vide)"
        }
        return summary

    def _calculate_age(self, birth_date):
        if not birth_date: return 0
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


# medical_controller.py
    def list_records(self, patient_id=None, page=1, per_page=20, 
                    date_from=None, date_to=None, motif_code=None, 
                    severity=None, search=None):
        """
        Liste les dossiers médicaux avec tous les filtres
        """ 
        try:
            # Conversion des valeurs de gravité si nécessaire
            severity_map = {"Faible": "low", "Moyen": "medium", "Élevé": "high"}
            if severity in severity_map:
                severity = severity_map[severity]
                
            print(f"DEBUG Controller - page: {page}, per_page: {per_page}, severity: {severity}")
            
            result = self.repo.list_records(
                patient_id=patient_id,
                page=page,
                per_page=per_page,
                date_from=date_from,
                date_to=date_to,
                motif_code=motif_code,
                severity=severity,
                search=search
            )
            
            print(f"DEBUG Controller result - total: {result.get('total')}, data: {len(result.get('data', []))}")
            
            return result
                
        except Exception as e:
            self.logger.error(f"Erreur list_records: {e}", exc_info=True)
            raise

    def get_record(self, record_id: int):
        return self.repo.get(record_id)

    def create_record(self, data: dict):
        record = self.repo.create(data)
        
        # --- AUDIT ---
        if self.audit_repo and self.user:
            try:
                # On suppose que record est un objet ORM avec un id
                rec_id = getattr(record, 'record_id', None)
                pat_id = data.get('patient_id')
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="CREATE",
                    resource_id=rec_id,
                    details=f"Patient ID: {pat_id}. Motif: {data.get('motif_code')}" # type: ignore
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return record

    def update_record(self, record_id: int, data: dict):
        record = self.repo.update(record_id, data)
        
        # --- AUDIT ---
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="UPDATE",
                    resource_id=record_id,
                    new_values=data # Log des champs modifiés
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return record

    def delete_record(self, record_id: int):
        result = self.repo.delete(record_id)
        
        # --- AUDIT ---
        if result and self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="MedicalRecord",
                    action_performed="DELETE",
                    resource_id=record_id
                )
            except Exception:
                self.logger.exception("Échec de l'écriture d'audit")
            
        return result

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
        
    def get_patient_history(self, patient_id: int):
        return self.repo.get_full_history(patient_id)    
    

    
    

    
    

    
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

    
    