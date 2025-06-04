# repositories/pharmacy_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func, or_  
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from datetime import datetime

class PharmacyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        return self.session.query(Pharmacy).all()

    def get_by_id(self, medication_id: int) -> Pharmacy:
        return self.session.get(Pharmacy, medication_id)
    
    def search(self, term=None, type_filter=None, status_filter=None):
        query = self.session.query(Pharmacy)
        if term:
            like_pattern = f"%{term.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Pharmacy.drug_name).like(like_pattern),
                    func.lower(Pharmacy.medication_type).like(like_pattern)
                )
            )
        if type_filter and type_filter != "Tous":
            query = query.filter(Pharmacy.medication_type == type_filter)
        if status_filter and status_filter != "Tous":
            query = query.filter(Pharmacy.stock_status == status_filter)
        return query.all()


    def create(self, data: dict, current_user=None) -> Pharmacy:
        """
        data doit désormais inclure :
          - drug_name (str)
          - quantity (int)
          - threshold (int)
          - medication_type (str)
          - forme (str)
          - dosage_mg (float) [facultatif]
          - expiry_date (datetime) [facultatif]
          - prescribed_by, name_dr…
        """
        prod = Pharmacy(
            drug_name       = data['drug_name'],
            quantity        = data.get('quantity', 0),
            threshold       = data.get('threshold', 0),
            medication_type = data['medication_type'],
            forme           = data.get('forme', 'Autre'),   # ← prendre la forme depuis data
            dosage_mg       = data.get('dosage_mg'),
            expiry_date     = data.get('expiry_date'),
            stock_status    = 'normal',
            prescribed_by   = data.get('prescribed_by'),
            name_dr         = data.get('name_dr')
        )
        prod.update_stock_status()
        self.session.add(prod)
        self.session.commit()

        movement = StockMovement(
            medication_id = prod.medication_id,
            change_qty    = prod.quantity,
            movement_type = 'initial',
            note          = f"Création du produit par {current_user.username if current_user else 'système'}",
            created_by    = current_user.username if current_user else 'système',
            created_at    = datetime.utcnow()
        )
        self.session.add(movement)
        self.session.commit()
        return prod

    def update(self, medication_id: int, data: dict, current_user=None) -> Pharmacy:
        prod = self.get_by_id(medication_id)
        if not prod:
            raise ValueError(f"Aucun produit trouvé pour l'ID {medication_id}")

        old_qty = prod.quantity
        new_qty = data.get('quantity', old_qty)

        # Mettre à jour tous les champs passés, y compris 'forme'
        for key, value in data.items():
            setattr(prod, key, value)

        prod.update_stock_status()
        self.session.commit()

        if new_qty != old_qty:
            diff = new_qty - old_qty
            movement = StockMovement(
                medication_id = medication_id,
                change_qty    = diff,
                movement_type = 'update',
                note          = f"Mise à jour par {current_user.username if current_user else 'système'}",
                created_by    = current_user.username if current_user else 'système',
                created_at    = datetime.utcnow()
            )
            self.session.add(movement)
            self.session.commit()

        return prod

    def delete(self, medication_id: int) -> Pharmacy:
        """
        Supprime le produit (et supprime cascade ses mouvements).
        """
        prod = self.get_by_id(medication_id)
        if prod:
            self.session.delete(prod)
            self.session.commit()
        return prod

    def renew_stock(self, medication_id: int, added_quantity: int, current_user=None) -> Pharmacy:
        """
        Réapprovisionne le produit existant : on ajoute added_quantity à quantity,
        met à jour stock_status, et crée une ligne dans stock_movement.
        """
        if added_quantity <= 0:
            raise ValueError("La quantité ajoutée doit être strictement positive.")

        prod = self.get_by_id(medication_id)
        if not prod:
            raise ValueError(f"Aucun produit trouvé pour l'ID {medication_id}")

        old_qty = prod.quantity
        prod.quantity = old_qty + added_quantity
        prod.update_stock_status()

        self.session.commit()

        # Création du mouvement de réapprovisionnement
        movement = StockMovement(
            medication_id = medication_id,
            change_qty    = added_quantity,
            movement_type = 'renew',
            note          = f"Réapprovisionnement par {current_user.username if current_user else 'système'}",
            created_by    = current_user.username if current_user else 'système',
            created_at    = datetime.utcnow()
        )
        self.session.add(movement)
        self.session.commit()

        return prod

    def get_critical_or_empty(self):
        """
        Retourne la liste des produits dont stock_status est 'critique' ou 'épuisé'.
        """
        return (
            self.session.query(Pharmacy)
            .filter(Pharmacy.stock_status.in_(('critique','épuisé')))
            .all()
        )
