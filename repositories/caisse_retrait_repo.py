# repositories/caisse_retrait_repo.py

from sqlalchemy.orm import Session
from sqlalchemy import func
from models.retrait import CaisseRetrait
from datetime import datetime


class CaisseRetraitRepository:
    """
    Repository pour gérer l’accès à la table ‘caisse_retrait’.
    Permet de lister, de créer, d'annuler et de calculer des totaux sur les retraits.
    """

    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> list[CaisseRetrait]:
        """
        Retourne tous les retraits (tous statuts), triés par date décroissante.
        """
        return (
            self.session
                .query(CaisseRetrait)
                .order_by(CaisseRetrait.retrait_at.desc())
                .all()
        )

    def get_by_id(self, retrait_id: int) -> CaisseRetrait | None:
        """
        Récupère un retrait par son ID. Renvoie None si aucun retrait trouvé.
        """
        return self.session.get(CaisseRetrait, retrait_id)

    def create(self, amount: float, justification: str, handled_by: int) -> CaisseRetrait:
        """
        Insère un nouveau retrait actif (status='active') :
         - amount (montant),
         - justification (texte, nullable),
         - handled_by (user_id de l’utilisateur qui fait le retrait).
        """
        new_retrait = CaisseRetrait(
            amount=amount,
            justification=justification,
            handled_by=handled_by
        )
        self.session.add(new_retrait)
        self.session.commit()
        return new_retrait

    def list_filtered(
        self,
        status:     str | None = None,
        date_from:  datetime | None = None,
        date_to:    datetime | None = None
    ) -> list[CaisseRetrait]:
        """
        Renvoie la liste des retraits, filtrés selon :
          - status   : "active", "cancelled" ou None (None = tous statuts)
          - date_from / date_to : bornes inclusives sur retrait_at.

        Si status=None, on n’applique aucun filtre sur le statut.
        Si date_from/date_to=None, on n’applique pas la borne correspondante.
        Résultat trié par retrait_at décroissant.
        """
        query = self.session.query(CaisseRetrait)

        if status is not None:
            query = query.filter(CaisseRetrait.status == status)

        if date_from is not None:
            query = query.filter(CaisseRetrait.retrait_at >= date_from)

        if date_to is not None:
            query = query.filter(CaisseRetrait.retrait_at <= date_to)

        return query.order_by(CaisseRetrait.retrait_at.desc()).all()

    def get_total_retraits(
        self,
        status:     str | None = None,
        date_from:  datetime | None = None,
        date_to:    datetime | None = None
    ) -> float:
        """
        Calcule la somme des montants des retraits filtrés par statut et date.
         - status : "active", "cancelled" ou None (None = tous statuts)
         - date_from / date_to : bornes inclusives sur retrait_at

        Si status=None, on prend tous les statuts.
        Si date_from/date_to=None, on n’applique pas la borne correspondante.
        """
        query = self.session.query(func.coalesce(func.sum(CaisseRetrait.amount), 0.0))

        if status is not None:
            query = query.filter(CaisseRetrait.status == status)

        if date_from is not None:
            query = query.filter(CaisseRetrait.retrait_at >= date_from)

        if date_to is not None:
            query = query.filter(CaisseRetrait.retrait_at <= date_to)

        total = query.scalar()
        return float(total)

    def cancel_with_justification(
        self,
        retrait_id:          int,
        cancelled_by:        int,
        justification:       str
    ) -> CaisseRetrait:
        """
        Passe un retrait existant en 'cancelled', en enregistrant :
         - cancelled_by (user_id qui annule),
         - cancelled_at (horodatage actuel),
         - cancel_justification (texte fourni),
         - status → 'cancelled'.

        Lève ValueError si :
          - le retrait n’existe pas,
          - déjà annulé.
        """
        retrait = self.get_by_id(retrait_id)
        if not retrait:
            raise ValueError(f"Aucun retrait trouvé pour l'ID = {retrait_id}")
        if retrait.status == 'cancelled':
            raise ValueError("Ce retrait est déjà annulé.")

        retrait.status               = 'cancelled'
        retrait.cancelled_by         = cancelled_by
        retrait.cancelled_at         = datetime.utcnow()
        retrait.cancel_justification = justification

        self.session.commit()
        return retrait

    def cancel(self, retrait_id: int) -> None:
        """
        Méthode simplifiée pour annuler sans justification.
        (Appelle cancel_with_justification avec justification vide ou None.)
        """
        self.cancel_with_justification(retrait_id, cancelled_by=None, justification="")
