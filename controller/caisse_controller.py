# controllers/caisse_controller.py

from typing import List
from datetime import date
from models.caisse import Caisse
from repositories.caisse_repo import CaisseRepository
from models.consultation_spirituelle import ConsultationSpirituel


class CaisseController:
    def __init__(self, repo: CaisseRepository, current_user):
        self.repo = repo
        self.user = current_user

    def list_transactions(self) -> List[Caisse]:
        return self.repo.list_all()

    def get_transaction(self, transaction_id: int) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        return tx

    def list_for_patient(self, patient_id: int) -> List[Caisse]:
        return self.repo.list_by_patient(patient_id)

    def list_by_payment_method(self, payment_method: str) -> List[Caisse]:
        return self.repo.list_by_payment_method(payment_method)

    def list_by_date_range(self, date_from: date, date_to: date) -> List[Caisse]:
        return self.repo.list_by_date_range(date_from, date_to)

    def get_daily_total(self, for_date: date):
        return self.repo.get_daily_total(for_date)

    def search_transactions(self,
                            term: str = None,
                            payment_method: str = None,
                            date_from: date = None,
                            date_to: date = None) -> List[Caisse]:
        return self.repo.search_transactions(term, payment_method, date_from, date_to)

    def create_transaction(self, data: dict) -> Caisse:
        """
        Crée une nouvelle transaction (paiement) avec ses lignes.
        """
        # 1. Validation des clés essentielles
        required_keys = ["payment_method", "transaction_type", "amount", "items"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Champ manquant : {key}")

        # 2. On s’assure qu’il y a au moins une ligne
        if not data["items"]:
            raise ValueError("La transaction doit contenir au moins une ligne (consultation ou médicament).")

        # 3. Vérifier l’existence des consultations pour les lignes de type "Consultation"
        for line in data["items"]:
            if line["item_type"].lower() == "consultation":
                cs = self.repo.session.get(ConsultationSpirituel, line["item_ref_id"])
                if not cs:
                    raise ValueError(f"Aucune consultation pour l'ID = {line['item_ref_id']}")

        # 4. Vérifier cohérence des montants lignes vs total
        total_calc = sum(line["line_total"] for line in data["items"])
        if total_calc != data["amount"]:
            raise ValueError(
                f"Le montant total ({data['amount']}) ne correspond pas à la somme des lignes ({total_calc})."
            )

        return self.repo.create_transaction(data, self.user)

    def update_transaction(self, transaction_id: int, data: dict) -> Caisse:
        """
        Met à jour une transaction existante, en réajustant le stock si nécessaire.
        """
        # 1. Vérifier que la transaction existe
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")

        # 2. Empêcher la MAJ si status = 'cancelled'
        if tx.status == 'cancelled':
            raise ValueError("Impossible de modifier une transaction annulée.")

        # 3. Si on modifie les lignes, vérification de la cohérence montant
        if "items" in data:
            if not data["items"]:
                raise ValueError("La liste d'items ne peut pas être vide.")
            total_calc = sum(line["line_total"] for line in data["items"])
            if "amount" in data and total_calc != data["amount"]:
                raise ValueError(
                    f"Le montant total ({data['amount']}) ne correspond pas à la somme des lignes ({total_calc})."
                )

            # 4. Vérifier que les consultations citées existent
            for line in data["items"]:
                if line["item_type"].lower() == "consultation":
                    cs = self.repo.session.get(ConsultationSpirituel, line["item_ref_id"])
                    if not cs:
                        raise ValueError(f"Aucune consultation pour l'ID = {line['item_ref_id']}")

        return self.repo.update_transaction(transaction_id, data, self.user)

    def cancel_transaction(self, transaction_id: int) -> Caisse:
        """
        Annule une transaction (restock puis passage du status à 'cancelled').
        """
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        if tx.status == 'cancelled':
            raise ValueError("Cette transaction est déjà annulée.")
        return self.repo.cancel_transaction(transaction_id, self.user)

    def delete_transaction(self, transaction_id: int) -> Caisse:
        """
        Supprime définitivement la transaction (usage exceptionnel).
        """
        return self.repo.delete_transaction(transaction_id)
