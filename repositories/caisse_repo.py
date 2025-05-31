# repositories/caisse_repo.py
from sqlalchemy.orm import Session
from models.caisse import Caisse
from datetime import datetime

class CaisseRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        return self.session.query(Caisse).all()

    def find_by_patient(self, patient_id: int):
        return (self.session.query(Caisse)
                .filter_by(patient_id=patient_id).all())

    def create(self, data: dict, current_user):
        tx = Caisse(
            patient_id      = data['patient_id'],
            amount          = data['amount'],
            date            = data.get('date', datetime.utcnow()),
            created_by_name = current_user.username,
            handled_by      = current_user.user_id
        )
        self.session.add(tx)
        self.session.commit()
        return tx

    def delete(self, tx_id: int):
        tx = self.session.get(Caisse, tx_id)
        if tx:
            self.session.delete(tx)
            self.session.commit()
        return tx
