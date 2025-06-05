# controllers/caisse_retrait_controller.py

from typing import List
from datetime import datetime
from models.retrait import CaisseRetrait
from repositories.caisse_retrait_repo import CaisseRetraitRepository


class CaisseRetraitController:
    """
    Controller pour la logique métier des retraits de caisse.
    """

    def __init__(self, repo: CaisseRetraitRepository, current_user):
        """
        - repo         : instance de CaisseRetraitRepository
        - current_user : objet User (doit avoir l’attribut user_id)
        """
        self.repo = repo
        self.user = current_user

    def list_retraits(
        self,
        status:     str | None = None,
        date_from:  datetime | None = None,
        date_to:    datetime | None = None
    ) -> List[CaisseRetrait]:
        """
        Récupère les retraits selon filtres :
         - status   : "active", "cancelled" ou None (None = tous statuts)
         - date_from / date_to : bornes inclusives sur retrait_at
        """
        return self.repo.list_filtered(
            status=status,
            date_from=date_from,
            date_to=date_to
        )

    def get_retrait(self, retrait_id: int) -> CaisseRetrait:
        """
        Récupère un retrait par son ID. Lève ValueError si non trouvé.
        """
        retrait = self.repo.get_by_id(retrait_id)
        if not retrait:
            raise ValueError(f"Aucun retrait trouvé pour l'ID = {retrait_id}")
        return retrait

    def get_total_retraits(
        self,
        status:     str | None = None,
        date_from:  datetime | None = None,
        date_to:    datetime | None = None
    ) -> float:
        """
        Renvoie la somme des montants des retraits, selon :
         - status   : "active", "cancelled" ou None (tous statuts)
         - date_from / date_to : bornes inclusives sur retrait_at
        """
        return self.repo.get_total_retraits(
            status=status,
            date_from=date_from,
            date_to=date_to
        )

    def effectuer_retrait(self, amount: float, justification: str) -> CaisseRetrait:
        """
        Crée un nouveau retrait (status='active'), lié à self.user.user_id.
        Lève ValueError si le montant est invalide (≤ 0).
        """
        if amount <= 0:
            raise ValueError("Le montant du retrait doit être strictement positif.")
        return self.repo.create(
            amount=amount,
            justification=justification,
            handled_by=self.user.user_id
        )

    def annuler_retrait(
        self,
        retrait_id:          int,
        cancel_justification: str
    ) -> None:
        """
        Annule un retrait existant :
         - status → 'cancelled'
         - enregistre who (cancelled_by) et when (cancelled_at) + raison
        Lève ValueError si déjà annulé ou inexistant.
        """
        self.repo.cancel_with_justification(
            retrait_id=retrait_id,
            cancelled_by=self.user.user_id,
            justification=cancel_justification
        )
