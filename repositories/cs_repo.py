# repositories/consultation_spirituel_repo.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, func
from models.consultation_spirituelle import ConsultationSpirituel
from models.prayer_book_type import PrayerBookType
from models.patient import Patient
from datetime import datetime
from typing import List, Optional
#from models.consultation_spirituelle import ConsultationSpirituel

class ConsultationSpirituelRepository:
    def __init__(self, session: Session):
        self.session = session
        self.model = ConsultationSpirituel

    def list_all(self, search: Optional[str] = None):
        # registre J1 : "search" etait deja declare cote endpoint mais
        # jamais branche jusqu'ici (aucun filtre applique). joinedload
        # systematique (pas seulement quand search est fourni) : le
        # mapping de reponse a aussi besoin du nom/code patient pour
        # remplacer l'affichage brut de patient_id cote frontend.
        query = (
            self.session.query(ConsultationSpirituel)
            .options(joinedload(ConsultationSpirituel.patient))
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.join(Patient, ConsultationSpirituel.patient_id == Patient.patient_id).filter(
                or_(
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.code_patient.ilike(term),
                )
            )
        return query.all()

    def list_all_for_export(self, search: Optional[str] = None, date_from=None, date_to=None):
        """Meme filtre que list_all (recherche + jointure Patient), plus
        periode sur consultation_date - destine a l'export, sans
        pagination."""
        query = (
            self.session.query(ConsultationSpirituel)
            .options(joinedload(ConsultationSpirituel.patient))
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.join(Patient, ConsultationSpirituel.patient_id == Patient.patient_id).filter(
                or_(
                    Patient.first_name.ilike(term),
                    Patient.last_name.ilike(term),
                    Patient.code_patient.ilike(term),
                )
            )
        if date_from:
            query = query.filter(func.date(ConsultationSpirituel.consultation_date) >= date_from)
        if date_to:
            query = query.filter(func.date(ConsultationSpirituel.consultation_date) <= date_to)
        return query.order_by(desc(ConsultationSpirituel.consultation_date)).all()

    def find_by_patient(self, patient_id: int):
        return (self.session.query(ConsultationSpirituel)
                .filter_by(patient_id=patient_id).all())

    def create(self, data: dict, current_user):
        cs = ConsultationSpirituel(
            patient_id         = data['patient_id'],
            type_consultation  = data['type_consultation'],
            presc_generic      = data.get('presc_generic'),
            presc_med_spirituel= data.get('presc_med_spirituel'),
            mp_type            = data.get('mp_type'),
            psaume             = data.get('psaume'),
            fr_registered_at   = data.get('fr_registered_at'),
            fr_appointment_at  = data.get('fr_appointment_at'),
            fr_amount_paid     = data.get('fr_amount_paid'),
            fr_observation     = data.get('fr_observation'),
            notes              = data.get('notes'),
            created_by         = current_user.user_id,
            created_by_name    = current_user.username,
            consultation_date  = data.get('consultation_date', datetime.utcnow())
        )
        self.session.add(cs)
        self.session.commit()
        return cs

    
    def get_history_for_patient(self, patient_id: int):
        """
        Récupère l'historique spirituel d'un patient trié par date décroissante.
        """
        return (
            self.session.query(self.model)
            .filter(self.model.patient_id == patient_id) # 🟢 Filtre Patient
            .order_by(desc(self.model.consultation_date)) # 🟢 Tri par date
            .all()
        )
    
    def get_history(self, patient_id: int):
        return (
            self.session.query(self.model)
            .filter(self.model.patient_id == patient_id)
            # 🔴 ERREUR : .order_by(desc(self.model.date))
            # 🟢 CORRECTION :
            .order_by(desc(self.model.consultation_date)) 
            .all()
        )
    
    def get_by_id(self, cs_id: int):
        return self.session.get(ConsultationSpirituel, cs_id)
    
    def update(self, cs_id: int, data: dict):
        """
        Met à jour les champs d’une consultation existante puis commit.
        """
        cs = self.get_by_id(cs_id)
        if not cs:
            return None

        # On met à jour uniquement les clés présentes dans `data`.
        # Attention : les clés de `data` doivent correspondre aux attributs SQLAlchemy !
        for key, value in data.items():
            setattr(cs, key, value)

        self.session.commit()
        return cs
    
    def delete(self, cs_id: int):
        cs = self.session.get(ConsultationSpirituel, cs_id)
        if cs:
            self.session.delete(cs)
            self.session.commit()
        return cs
    
    def get_last_for_patient(self, patient_id: int):
        return (
            self.session
                .query(self.model)
                .filter(self.model.patient_id == patient_id)
                .order_by(desc(self.model.consultation_date))
                .first()
        )
    
    def get_prayer_book_types(self) -> List[PrayerBookType]:
        """
        Retourne tous les types de Prayer Book disponibles.
        """
        return (
            self.session.query(PrayerBookType)
            .order_by(PrayerBookType.type_code)
            .all()
        )
