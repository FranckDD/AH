# repositories/pharmacy_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func, or_  
from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from datetime import datetime, timedelta

class PharmacyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        return self.session.query(Pharmacy).all()

    def get_by_id(self, medication_id: int) -> Pharmacy:
        return self.session.get(Pharmacy, medication_id)
    
    def search(
        self,
        term=None,
        type_filter=None,
        status_filter=None,
        page: int = 1,
        per_page: int = 20
    ) -> dict:
        query = self.session.query(Pharmacy)

        # --- 1. APPLICATION DES FILTRES (Même logique) ---
        
        # Filtre Texte
        if term:
            like_pattern = f"%{term.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Pharmacy.drug_name).like(like_pattern),
                    func.lower(Pharmacy.medication_type).like(like_pattern),
                    func.lower(Pharmacy.forme).like(like_pattern)
                )
            )
        
        # Filtre Catégorie (Insensible à la casse)
        if type_filter and type_filter != "ALL":
            search_pattern = f"%{type_filter.strip()}%"
            query = query.filter(Pharmacy.medication_type.ilike(search_pattern))
        
        # Filtre Statut / Périmés
        if status_filter:
            if status_filter == "EXPIRED_ONLY":
                query = query.filter(Pharmacy.expiry_date < datetime.utcnow())
            elif status_filter != "ALL":
                query = query.filter(Pharmacy.stock_status == status_filter.lower())

        # --- 2. CALCULS SUR LE RÉSULTAT FILTRÉ ---

        # A. Nombre total d'éléments trouvés
        total_count = query.count()

        # B. 🟢 NOUVEAU : Valeur totale de ces éléments filtrés
        # On utilise with_entities pour faire la somme sur la requête déjà filtrée
        total_value_query = query.with_entities(func.sum(Pharmacy.quantity * Pharmacy.price))
        total_value_result = total_value_query.scalar()
        filtered_value = float(total_value_result) if total_value_result else 0.0

        # --- 3. PAGINATION ---
        offset = (page - 1) * per_page
        products = query.offset(offset).limit(per_page).all() # On remet les entités par défaut implicitement

        return {
            "data": products,
            "total": total_count,
            "filtered_value": filtered_value, # 👈 On renvoie la somme calculée
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page if per_page > 0 else 1
        }


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
            price           = data.get('price', 0.0),
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
        prod.quantity = old_qty + added_quantity # type: ignore
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
    
    # --- MÉTHODES KPI ---

    def count_by_category(self, category_name: str) -> int:
        # Ajout des % pour matcher "Pharmaceutique" avec "pharm"
        search_pattern = f"%{category_name}%"
        return self.session.query(Pharmacy).filter(
            Pharmacy.medication_type.ilike(search_pattern)
        ).count()

    def count_expired(self) -> int:
        """Compte les produits dont la date d'expiration est passée."""
        return self.session.query(Pharmacy).filter(Pharmacy.expiry_date < datetime.utcnow()).count()

    def count_low_stock(self) -> int:
        """Compte les produits critiques ou épuisés."""
        return self.session.query(Pharmacy).filter(
            Pharmacy.stock_status.in_(['critique', 'épuisé']) # type: ignore
        ).count()

    def get_total_valuation(self) -> float:
        """
        Calcule la valeur totale du stock (quantity * price) directement en SQL.
        Beaucoup plus performant que de le faire en Python.
        """
        total = self.session.query(
            func.sum(Pharmacy.quantity * Pharmacy.price)
        ).scalar()
        return float(total) if total else 0.0

    def get_critical_or_empty(self):
        """
        Retourne la liste des produits dont stock_status est 'critique' ou 'épuisé'.
        """
        return (
            self.session.query(Pharmacy)
            .filter(Pharmacy.stock_status.in_(('critique','épuisé'))) # type: ignore
            .all()
        )
    
    def get_expiring_soon(self, days: int) -> list[Pharmacy]:
        """
        Liste les produits dont expiry_date est dans les {days} prochains jours.
        """
        expiry_limit = datetime.utcnow() + timedelta(days=days)
        return (
            self.session.query(Pharmacy)
            .filter(Pharmacy.expiry_date <= expiry_limit)
            .filter(Pharmacy.expiry_date >= datetime.utcnow())
            .order_by(Pharmacy.expiry_date.asc())
            .all()
        )
    
    # Helper interne pour les mouvements
    def _log_movement(self, med_id, qty, m_type, user):
        username = user.username if user else 'système'
        movement = StockMovement(
            medication_id = med_id,
            change_qty    = qty,
            movement_type = m_type,
            note          = f"Action {m_type} par {username}",
            created_by    = username,
            created_at    = datetime.utcnow()
        )
        self.session.add(movement)
        self.session.commit()
    
    
