# repositories/consultation_spirituel_repo.py
from sqlalchemy.orm import Session
from models.consultation_spirituelle import ConsultationSpirituel
from datetime import datetime

class ConsultationSpirituelRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        return self.session.query(ConsultationSpirituel).all()

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

    def delete(self, cs_id: int):
        cs = self.session.get(ConsultationSpirituel, cs_id)
        if cs:
            self.session.delete(cs)
            self.session.commit()
        return cs
    
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
