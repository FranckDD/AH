# controllers/caisse_controller.py

from typing import List
from datetime import datetime, date
from models.caisse import Caisse
from repositories.caisse_repo import CaisseRepository
from models.consultation_spirituelle import ConsultationSpirituel


class CaisseController:
    def __init__(self, repo: CaisseRepository, current_user):
        """
        - repo         : instance de CaisseRepository
        - current_user : instance de User (doit avoir l’attribut 'user_id' et 'username')
        """
        self.repo = repo
        self.user = current_user

    def list_transactions(self) -> List[Caisse]:
        """
        Retourne toutes les transactions (sans filtrer le statut), triées par date décroissante.
        """
        return self.repo.list_all()

    def get_transaction(self, transaction_id: int) -> Caisse:
        """
        Récupère une transaction par son ID, lève ValueError si non trouvée.
        """
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        return tx

    def list_for_patient(self, patient_id: int) -> List[Caisse]:
        """
        Retourne toutes les transactions d’un patient donné.
        """
        return self.repo.list_by_patient(patient_id)

    def list_by_payment_method(self, payment_method: str) -> List[Caisse]:
        """
        Retourne toutes les transactions dont le mode de paiement correspond.
        """
        return self.repo.list_by_payment_method(payment_method)

    def list_by_date_range(self, date_from: date, date_to: date) -> List[Caisse]:
        """
        Retourne toutes les transactions dont paid_at est entre date_from et date_to.
        """
        return self.repo.list_by_date_range(date_from, date_to)

    def get_daily_total(self, for_date: date) -> float:
        """
        Somme des montants encaissés pour la date spécifiée (for_date).
        """
        return self.repo.get_daily_total(for_date)

    def search_transactions(
        self,
        term: str = None,
        payment_method: str = None,
        date_from: date = None,
        date_to: date = None
    ) -> List[Caisse]:
        return self.repo.search_transactions(term, payment_method, date_from, date_to)

    def get_total_transactions(
        self,
        date_from: datetime | None = None,
        date_to:   datetime | None = None
    ) -> float:
        """
        Renvoie la somme des montants des transactions dans l’intervalle [date_from..date_to].
        Si date_from ou date_to est None, on n’applique pas cette borne.
        """
        return self.repo.get_total_transactions(date_from=date_from, date_to=date_to)

    def create_transaction(self, data: dict) -> Caisse:
        """
        Crée une nouvelle transaction (paiement) avec ses lignes.
        data doit contenir obligatoirement :
         - payment_method (str)
         - transaction_type (str)       ← concaténation des types cochés
         - amount (float)               ← somme des line_total
         - items (list of dict)
         - advance_amount (float)
        Optionnellement :
         - patient_id     (int)
         - patient_label  (str)         ← si patient_id est None ET advance_amount > 0
         - paid_at        (datetime)
         - note           (str)
        """
        required_keys = ["payment_method", "transaction_type", "amount", "items", "advance_amount"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Champ manquant : {key}")

        # 1) Au moins une ligne OU advance_amount > 0
        if not data["items"] and data.get("advance_amount", 0) == 0:
            raise ValueError("La transaction doit contenir au moins une ligne ou indiquer une avance.")

        # 2) Validation existence consultations (lignes de type "Consultation")
        for line in data["items"]:
            if line["item_type"].lower() == "consultation":
                cs = self.repo.session.get(ConsultationSpirituel, line["item_ref_id"])
                if not cs:
                    raise ValueError(f"Aucune consultation pour l'ID = {line['item_ref_id']}")

        # 3) Vérifier cohérence montant des lignes vs total
        total_calc = sum(line["line_total"] for line in data["items"])
        if total_calc != data["amount"]:
            raise ValueError(
                f"Le montant total des lignes ({total_calc}) ne correspond pas à data['amount'] ({data['amount']})."
            )

        # 4) Déléguer au repository en passant l’utilisateur courant
        return self.repo.create_transaction(data, self.user)

    def update_transaction(self, transaction_id: int, data: dict) -> Caisse:
        """
        Met à jour une transaction existante, en réajustant le stock si nécessaire.
        Refuse si tx.status == 'cancelled'.
        """
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        if tx.status == "cancelled":
            raise ValueError("Impossible de modifier une transaction annulée.")

        # Si on modifie les lignes, on vérifie cohérence et existence des consultations
        if "items" in data:
            if not data["items"] and data.get("advance_amount", 0) == 0:
                raise ValueError("La liste d'items ne peut pas être vide ET advance_amount = 0.")
            total_calc = sum(line["line_total"] for line in data["items"])
            if "amount" in data and total_calc != data["amount"]:
                raise ValueError(
                    f"Le montant total des lignes ({total_calc}) ne correspond pas à data['amount'] ({data['amount']})."
                )
            for line in data["items"]:
                if line["item_type"].lower() == "consultation":
                    cs = self.repo.session.get(ConsultationSpirituel, line["item_ref_id"])
                    if not cs:
                        raise ValueError(f"Aucune consultation pour l'ID = {line['item_ref_id']}")

        return self.repo.update_transaction(transaction_id, data, self.user)

    def cancel_transaction(self, transaction_id: int) -> Caisse:
        """
        Annule la transaction :
         - remet en stock chaque ligne 'Médicament' ou 'Carnet'
         - passe tx.status = 'cancelled'
         - marque chaque CaisseItem.status = 'cancelled'
        """
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        if tx.status == "cancelled":
            raise ValueError("Cette transaction est déjà annulée.")
        return self.repo.cancel_transaction(transaction_id, self.user)

    def delete_transaction(self, transaction_id: int) -> Caisse:
        """
        Supprime définitivement la transaction (usage exceptionnel, sans remettre en stock).
        """
        return self.repo.delete_transaction(transaction_id)
