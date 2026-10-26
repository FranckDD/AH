# controllers/caisse_retrait_controller.py

from typing import List
from datetime import datetime
from models.retrait import CaisseRetrait
from repositories.caisse_retrait_repo import CaisseRetraitRepository
from utils.payment_mode_guard import resolve_payment_mode


class CashShortageError(ValueError):
    """Retrait en especes superieur aux especes presentes en caisse (impossible)."""


CASH_MODE = "especes"


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

    def exceeds_cash_in_till(self, amount, payment_method) -> bool:
        """Vrai si un retrait EN ESPECES depasse les especes qui devraient etre en caisse. Faux pour un autre
        mode, ou si la caisse n'a pas de depart (rien a comparer). Ne revele jamais le montant de la caisse."""
        from decimal import Decimal
        from controller.cash_closure_controller import get_cash_closure_controller
        if str(payment_method or "").lower() != CASH_MODE:
            return False
        till = get_cash_closure_controller(self.repo.session, self.user).cash_in_till()
        return till is not None and Decimal(str(amount)) > till

    def effectuer_retrait(self, amount: float, justification: str,
                          category: str = None, payment_method: str = None, uuid: str = None) -> CaisseRetrait:
        """
        Crée un nouveau retrait avec catégorie et méthode de paiement.
        """
        if amount <= 0:
            raise ValueError("Le montant du retrait doit être strictement positif.")
        # Mode obligatoire ; valeur ancienne normalisee (jamais rejetee) ; mode desactive refuse.
        # uuid client = operation venue de la file hors ligne : jamais refusee pour le mode.
        payment_method = resolve_payment_mode(self.repo.session, payment_method, required=True,
                                              replay=bool(uuid))

        # Retrait saisi en ligne : on refuse ce qui est impossible. Un rejeu hors ligne (uuid client) est deja
        # fait et n'est jamais refuse ; l'ecart apparaitra a la cloture.
        if not uuid and self.exceeds_cash_in_till(amount, payment_method):
            raise CashShortageError("Retrait refuse : le montant depasse les especes presentes en caisse.")

        return self.repo.create(
            amount=amount,
            justification=justification,
            handled_by=self.user.user_id,
            # 🟢 Passage des nouveaux paramètres
            category=category,
            payment_method=payment_method,
            uuid=uuid,
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

    def list_transactions(self):
        """
        Méthode appelée par la vue pour récupérer toutes les transactions.
        """
        return self.repo.list_retraits()
    
    # Ajoute ceci à ta classe CaisseRetraitController

    def search_retraits(
        self,
        page: int = 1,
        per_page: int = 50,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        term: str | None = None
    ) -> dict:
        """
        Méthode dédiée pour le module Finance (avec pagination).
        """
        items, total = self.repo.get_paginated_list(
            page=page,
            per_page=per_page,
            status=status,
            date_from=date_from,
            date_to=date_to,
            term=term
        )
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page
        }

        
