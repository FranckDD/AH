# repositories/pharmacy_repo.py
from sqlalchemy.orm import Session
from models.pharmacy import Pharmacy

class PharmacyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        return self.session.query(Pharmacy).all()

    def create(self, data: dict, current_user):
        prod = Pharmacy(
            patient_id       = data.get('patient_id'),
            drug_name        = data['drug_name'],
            quantity         = data.get('quantity'),
            medication_type  = data['medication_type'],
            prescribed_by    = data.get('prescribed_by'),
            name_dr          = data.get('name_dr')
        )
        self.session.add(prod)
        self.session.commit()
        return prod