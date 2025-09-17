from sqlalchemy import or_
from sqlalchemy import text, func, desc
from models.database import DatabaseManager
from models.patient import Patient 
from sqlalchemy.orm import Session
from models.medical_record import MedicalRecord
from sqlalchemy.orm import joinedload
from sqlalchemy import cast, Date, and_
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple

class MedicalRecordRepository:
    def __init__(self, session: Session):
        self.session = session
        self.model = MedicalRecord




    def list_records(self, patient_id=None, page=1, per_page=20, 
                    date_from=None, date_to=None, motif_code=None, 
                    severity=None, search=None):
        """
        Liste les dossiers médicaux avec tous les filtres
        """
        q = self.session.query(MedicalRecord).options(joinedload(MedicalRecord.patient))
        
        # DEBUG: Compter le total SANS filtres pour référence
        total_no_filter = q.count()
        print(f"DEBUG REPO - Total records without filters: {total_no_filter}")
        
        # FILTRE PAR DATE - SOLUTION CORRECTE POUR timestamp without time zone
        if date_from or date_to:
            print(f"DEBUG REPO - Applying date filters: {date_from} to {date_to}")
            
            if date_from and date_to:
                # Plage de dates complète
                start_dt = datetime.strptime(date_from, "%Y-%m-%d")
                end_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                q = q.filter(MedicalRecord.consultation_date.between(start_dt, end_dt))
                print(f"DEBUG REPO - Date range: {start_dt} to {end_dt}")
                
            elif date_from:
                # Seulement date de début
                start_dt = datetime.strptime(date_from, "%Y-%m-%d")
                q = q.filter(MedicalRecord.consultation_date >= start_dt)
                print(f"DEBUG REPO - Date from: {start_dt}")
                
            elif date_to:
                # Seulement date de fin
                end_dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                q = q.filter(MedicalRecord.consultation_date <= end_dt)
                print(f"DEBUG REPO - Date to: {end_dt}")
        
        # Compter après filtres date
        total_after_date_filter = q.count()
        print(f"DEBUG REPO - Total after date filters: {total_after_date_filter}")
        
        # Appliquer les autres filtres...
        # Filtre par motif
        if motif_code:
            q = q.filter(MedicalRecord.motif_code == motif_code)
            print(f"DEBUG REPO - After motif filter: {q.count()}")
        
        # Filtre par gravité
        if severity:
            q = q.filter(MedicalRecord.severity == severity)
            print(f"DEBUG REPO - After severity filter: {q.count()}")
        
        # Filtre par recherche texte
        if search:
            q = q.join(Patient).filter(
                or_(
                    Patient.code_patient.ilike(f"%{search}%"),
                    Patient.first_name.ilike(f"%{search}%"),
                    Patient.last_name.ilike(f"%{search}%")
                )
            )
            print(f"DEBUG REPO - After search filter: {q.count()}")
        
        # Compter le total final AVANT pagination
        total_final = q.count()
        print(f"DEBUG REPO - Final total before pagination: {total_final}")
        
        # Tri par date décroissante et pagination
        records = q.order_by(desc(MedicalRecord.consultation_date))\
                .offset((page-1)*per_page)\
                .limit(per_page).all()
        
        print(f"DEBUG REPO - Records returned: {len(records)}")
        
        return {
            "data": records,
            "total": total_final,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_final + per_page - 1) // per_page if per_page > 0 else 1
        }

    def get(self, record_id):
        return self.session.get(MedicalRecord, record_id)

    def create(self, data: dict):
        # Appelle la procédure SQL
        sql = text(
            "CALL public.create_medical_record(:patient_id, LOCALTIMESTAMP, :marital_status, :bp,"
            " :temperature, :weight, :height, :medical_history, :allergies,"
            " :symptoms, :diagnosis, :treatment, :severity, :notes, :motif_code)"
        )
        self.session.execute(sql, data)
        self.session.commit()
        return True

    def update(self, record_id: int, data: dict):
        # on ne veut plus passer patient_id à la procédure d’update
        # supprimez-le du dict si présent
        data = data.copy()
        data.pop('patient_id', None)

        # ajoute le record_id
        data['record_id'] = record_id

        sql = text(
            "CALL public.update_medical_record("
            " :record_id,"
            " :marital_status,"
            " :bp,"
            " :temperature,"
            " :weight,"
            " :height,"
            " :medical_history,"
            " :allergies,"
            " :symptoms,"
            " :diagnosis,"
            " :treatment,"
            " :severity,"
            " :notes,"
            " :motif_code)"
        )
        self.session.execute(sql, data)
        self.session.commit()
        return True


    def delete(self, record_id: int):
        # On suppose exist proc delete_medical_record
        sql = text("CALL public.delete_medical_record(:record_id)")
        self.session.execute(sql, {'record_id': record_id})
        self.session.commit()
        return True

    def get_motifs(self) -> list:
        # Récupère code et label_fr
        result = self.session.execute(text(
            "SELECT code, label_fr FROM motif_translations ORDER BY label_fr"
        ))
                # row here is a Row; use mappings() to get dict-like rows
        return [dict(row) for row in result.mappings()]
    
    def find_by_date_range(self, start_date: date, end_date: date) -> List[MedicalRecord]:
        return (
            self.session
                .query(MedicalRecord)
                .filter(func.date(MedicalRecord.consultation_date) >= start_date)
                .filter(func.date(MedicalRecord.consultation_date) <= end_date)
                .all()
        )
    

    def get_last_for_patient(self, patient_id: int):
        """
        Renvoie le dernier MedicalRecord (par date décroissante) pour ce patient,
        ou None s’il n’y en a pas.
        """
        return (
            self.session
                .query(self.model)
                .filter(self.model.patient_id == patient_id)
                .order_by(desc(self.model.consultation_date))
                .first()
        )
    
    #KPI Dashboard Medecin
    
    def count_records_for_doctor(self, doctor_id: int, start_date: Optional[date]=None, end_date: Optional[date]=None) -> int:
        q = self.session.query(func.count(self.model.record_id)).filter(self.model.created_by == doctor_id)
        if start_date:
            q = q.filter(func.date(self.model.consultation_date) >= start_date)
        if end_date:
            q = q.filter(func.date(self.model.consultation_date) <= end_date)
        return int(q.scalar() or 0)

    def breakdown_by_motif_for_doctor(self, doctor_id: int, start_date: Optional[date]=None, end_date: Optional[date]=None) -> Dict[str,int]:
        q = self.session.query(self.model.motif_code, func.count(self.model.record_id)).filter(self.model.created_by == doctor_id)
        if start_date:
            q = q.filter(self.model.consultation_date >= start_date)
        if end_date:
            q = q.filter(self.model.consultation_date <= end_date)
        rows = q.group_by(self.model.motif_code).all()
        return { (motif or "Non spécifié"): int(cnt) for motif, cnt in rows }

    def latest_record_per_patient_for_doctor(self, doctor_id: int, limit: Optional[int]=None):
        # utile si tu veux determiner consultation type par patient (version avancée)
        subq = (
            self.session.query(
                self.model.patient_id,
                func.max(self.model.consultation_date).label('max_date')
            )
            .filter(self.model.created_by == doctor_id)
            .group_by(self.model.patient_id)
        ).subquery('last_rec')

        q = (
            self.session.query(self.model)
            .join(subq, (self.model.patient_id == subq.c.patient_id) & (self.model.consultation_date == subq.c.max_date))
        )
        if limit:
            q = q.limit(limit)
        return q.all()
    
    # medical_record_repo.py
    def count_preconsultations(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        if start_date is None:
            start_date = date.today()

        q = self.session.query(MedicalRecord)

        if end_date:
            q = q.filter(MedicalRecord.consultation_date >= start_date,
                        MedicalRecord.consultation_date <= end_date)
        else:
            q = q.filter(MedicalRecord.consultation_date >= start_date)

        return q.count()

    
    def count_by_consultation_date(self, consultation_date: date) -> int:
        """Compte les consultations pour une date spécifique."""
        return (
            self.session.query(MedicalRecord)
            .filter(func.date(MedicalRecord.consultation_date) == consultation_date)
            .count()
        )

    def count_by_consultation_date_range(self, start_date: date, end_date: date) -> int:
        """Compte les consultations dans une plage de dates."""
        return (
            self.session.query(MedicalRecord)
            .filter(func.date(MedicalRecord.consultation_date) >= start_date)
            .filter(func.date(MedicalRecord.consultation_date) <= end_date)
            .count()
        )

    

