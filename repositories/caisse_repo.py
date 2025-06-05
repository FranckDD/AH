# repositories/caisse_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, date

from models.caisse import Caisse
from models.caisse_item import CaisseItem
from models.pharmacy import Pharmacy


class CaisseRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self):
        """
        Retourne toutes les transactions (Caisse) avec leurs lignes (CaisseItem), triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def get_by_id(self, transaction_id: int) -> Caisse:
        """
        Récupère une transaction par son ID (avec ses items).
        """
        return self.session.get(Caisse, transaction_id)

    def list_by_patient(self, patient_id: int):
        """
        Retourne toutes les transactions associées à un patient (même NULLABLE), triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .filter(Caisse.patient_id == patient_id)
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def list_by_payment_method(self, payment_method: str):
        """
        Filtre par mode de paiement (ex. 'Espèces', 'Carte', 'Chèque', ...), triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .filter(Caisse.payment_method == payment_method)
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def list_by_date_range(self, date_from: date, date_to: date):
        """
        Liste les transactions dont paid_at est entre date_from et date_to (inclus),
        triées par paid_at DESC.
        """
        return (
            self.session
                .query(Caisse)
                .filter(func.date(Caisse.paid_at).between(date_from, date_to))
                .order_by(Caisse.paid_at.desc())
                .all()
        )

    def get_daily_total(self, for_date: date) -> float:
        """
        Somme des montants encaissés pour la date spécifiée.
        """
        total = (
            self.session
                .query(func.coalesce(func.sum(Caisse.amount), 0.0))
                .filter(func.date(Caisse.paid_at) == for_date)
                .scalar()
        )
        # scalar() retourne un Decimal ou un int ; on force en float avant de renvoyer
        return float(total or 0.0)

    def search_transactions(
        self,
        term: str = None,
        payment_method: str = None,
        date_from: date = None,
        date_to: date = None
    ):
        """
        Recherche générique sur plusieurs critères :
         - term : recherche partielle sur transaction_type ou created_by_name
         - payment_method : filtre sur mode de paiement
         - date_from / date_to : plage de dates sur paid_at
        """
        query = self.session.query(Caisse)

        if term:
            term_like = f"%{term.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Caisse.transaction_type).like(term_like),
                    func.lower(Caisse.created_by_name).like(term_like)
                )
            )
        if payment_method and payment_method.lower() not in ("tous", "all"):
            query = query.filter(Caisse.payment_method == payment_method)
        if date_from and date_to:
            query = query.filter(
                func.date(Caisse.paid_at).between(date_from, date_to)
            )
        elif date_from:
            query = query.filter(func.date(Caisse.paid_at) >= date_from)
        elif date_to:
            query = query.filter(func.date(Caisse.paid_at) <= date_to)

        return query.order_by(Caisse.paid_at.desc()).all()

    def get_total_transactions(
        self,
        date_from: datetime | None = None,
        date_to:   datetime | None = None
    ) -> float:
        """
        Calcule la somme des montants (Caisse.amount) de toutes les transactions
        dans l’intervalle [date_from .. date_to] (bornes inclusives).
        - date_from / date_to : si None, on n’applique pas la borne correspondante.
        - Renvoie 0.0 si aucune transaction dans la plage.
        """
        # On utilise coalesce(sum(amount), 0.0) pour éviter None
        query = self.session.query(func.coalesce(func.sum(Caisse.amount), 0.0))

        if date_from is not None:
            query = query.filter(Caisse.paid_at >= date_from)

        if date_to is not None:
            query = query.filter(Caisse.paid_at <= date_to)

        total = query.scalar()
        return float(total or 0.0)

    def create_transaction(self, data: dict, current_user) -> Caisse:
        """
        Crée une transaction + ses lignes correspondantes.
        Le champ `status` est automatiquement ‘active’.
        data contient :
         - patient_id (ou None)
         - patient_label (str) ou None
         - amount (float)
         - advance_amount (float)
         - paid_at (datetime)
         - created_by_name, handled_by
         - payment_method, transaction_type, note
         - items : liste de dict {item_type, item_ref_id, unit_price, quantity, line_total, note}
        """
        # 1) Création de l’en-tête Caisse
        tx = Caisse(
            patient_id       = data.get("patient_id"),
            patient_label    = data.get("patient_label"),
            amount           = data["amount"],
            advance_amount   = data.get("advance_amount", 0.0),
            paid_at          = data.get("paid_at", datetime.utcnow()),
            created_by_name  = current_user.username,
            handled_by       = current_user.user_id,
            payment_method   = data["payment_method"],
            transaction_type = data["transaction_type"],
            note             = data.get("note"),
            status           = 'active'
        )
        self.session.add(tx)
        self.session.flush()  # pour récupérer tx.transaction_id immédiatement

        # 2) Création des lignes CaisseItem
        items = data.get("items", [])
        for line in items:
            item_type = line["item_type"]
            ref_id    = line["item_ref_id"]
            unit_price= line["unit_price"]
            qty       = line["quantity"]
            line_tot  = line["line_total"]
            item_note = line.get("note")

            # 2.a) Si c’est une vente de Médicament ou de Carnet, on décrémente le stock
            if item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                med = self.session.get(Pharmacy, ref_id)
                if not med:
                    raise ValueError(f"Produit introuvable pour ID={ref_id}")
                if med.quantity < qty:
                    raise ValueError(
                        f"Stock insuffisant pour produit ID={ref_id}. "
                        f"Demandé={qty}, disponible={med.quantity}"
                    )
                med.quantity -= qty
                med.update_stock_status()
                self.session.add(med)

            # 2.b) Création du CaisseItem
            caisse_item = CaisseItem(
                transaction_id = tx.transaction_id,
                item_type      = item_type,
                item_ref_id    = ref_id,
                unit_price     = unit_price,
                quantity       = qty,
                line_total     = line_tot,
                note           = item_note,
                status         = 'active'
            )
            self.session.add(caisse_item)

        # 3) Commit final
        self.session.commit()
        return tx

    def update_transaction(self, transaction_id: int, data: dict, current_user) -> Caisse:
        """
        Met à jour une transaction existante, et ajuste le stock si nécessaire.
        Refuse si tx.status='cancelled'.
        """
        tx = self.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID={transaction_id}")

        # 1) Empêcher la MAJ si status = 'cancelled'
        if tx.status == 'cancelled':
            raise ValueError(f"Impossible de modifier une transaction annulée (ID={transaction_id}).")

        # 2) Rétablir d'abord le stock des anciennes lignes (avant MAJ)
        existing_items = list(tx.items)
        for old_item in existing_items:
            if old_item.item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                med = self.session.get(Pharmacy, old_item.item_ref_id)
                if med:
                    med.quantity += old_item.quantity
                    med.update_stock_status()
                    self.session.add(med)
        # Supprimer les anciennes lignes
        for old_item in existing_items:
            self.session.delete(old_item)
        self.session.flush()

        # 3) Mettre à jour les champs de l’en-tête
        if "amount" in data:
            tx.amount = data["amount"]
        if "advance_amount" in data:
            tx.advance_amount = data["advance_amount"]
        if "payment_method" in data:
            tx.payment_method = data["payment_method"]
        if "transaction_type" in data:
            tx.transaction_type = data["transaction_type"]
        if "patient_id" in data:
            tx.patient_id = data["patient_id"]
        if "patient_label" in data:
            tx.patient_label = data["patient_label"]
        if "note" in data:
            tx.note = data["note"]
        if "paid_at" in data:
            tx.paid_at = data["paid_at"]
        # status reste inchangé (normalement 'active')

        # 4) Réinsérer les nouvelles lignes
        new_items = data.get("items", [])
        for line in new_items:
            item_type = line["item_type"]
            ref_id    = line["item_ref_id"]
            unit_price= line["unit_price"]
            qty       = line["quantity"]
            line_tot  = line["line_total"]
            item_note = line.get("note")

            if item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                med = self.session.get(Pharmacy, ref_id)
                if not med:
                    raise ValueError(f"Produit introuvable pour ID={ref_id}")
                if med.quantity < qty:
                    raise ValueError(
                        f"Stock insuffisant pour produit ID={ref_id}. "
                        f"Demandé={qty}, disponible={med.quantity}"
                    )
                med.quantity -= qty
                med.update_stock_status()
                self.session.add(med)

            new_item = CaisseItem(
                transaction_id = transaction_id,
                item_type      = item_type,
                item_ref_id    = ref_id,
                unit_price     = unit_price,
                quantity       = qty,
                line_total     = line_tot,
                note           = item_note,
                status         = 'active'
            )
            self.session.add(new_item)

        # 5) Commit final
        self.session.commit()
        return tx

    def cancel_transaction(self, transaction_id: int, current_user) -> Caisse:
        """
        Annule la transaction :
         - remet en stock chaque ligne 'Médicament' ou 'Carnet'
         - passe tx.status = 'cancelled'
         - marque chaque CaisseItem.status = 'cancelled'
        """
        tx = self.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID={transaction_id}")

        if tx.status == 'cancelled':
            return tx

        # 1) Rétablir le stock des lignes existantes
        for item in tx.items:
            if item.item_type.lower() in ("médicament", "medication", "carnet", "booklet"):
                med = self.session.get(Pharmacy, item.item_ref_id)
                if med:
                    med.quantity += item.quantity
                    med.update_stock_status()
                    self.session.add(med)

        # 2) Marquer la transaction comme annulée
        tx.status = 'cancelled'
        self.session.add(tx)

        # 3) Marquer chaque ligne comme annulée
        for item in tx.items:
            item.status = 'cancelled'
            self.session.add(item)

        # 4) Commit
        self.session.commit()
        return tx

    def delete_transaction(self, transaction_id: int) -> Caisse:
        """
        Supprime définitivement la transaction (usage exceptionnel, sans remettre en stock).
        """
        tx = self.get_by_id(transaction_id)
        if tx:
            self.session.delete(tx)
            self.session.commit()
        return tx
