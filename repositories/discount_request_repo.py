# repositories/discount_request_repo.py
from datetime import datetime, time
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import joinedload
from models.discount_request import DiscountRequest
from models.caisse import Caisse
from models.user import User


class DiscountRequestRepository:
    def __init__(self, session):
        self.session = session

    def get_pending_for_transaction(self, transaction_id: int) -> Optional[DiscountRequest]:
        return (
            self.session.query(DiscountRequest)
            .filter(DiscountRequest.transaction_id == transaction_id, DiscountRequest.status == "pending")
            .first()
        )

    def get_approved_for_transaction(self, transaction_id: int) -> Optional[DiscountRequest]:
        """Au plus une demande approuvee par transaction en pratique (le
        workflow ne permet pas de re-demander sur une facture deja active),
        mais order_by+first() reste defensif si ce jour cette hypothese
        change un jour."""
        return (
            self.session.query(DiscountRequest)
            .options(joinedload(DiscountRequest.decider))
            .filter(DiscountRequest.transaction_id == transaction_id, DiscountRequest.status == "approved")
            .order_by(DiscountRequest.decided_at.desc())
            .first()
        )

    def create(self, transaction_id: int, requested_by: int, requested_to: int, original_amount: Decimal) -> DiscountRequest:
        req = DiscountRequest(
            transaction_id=transaction_id,
            requested_by=requested_by,
            requested_to=requested_to,
            original_amount=original_amount,
            status="pending",
        )
        self.session.add(req)
        self.session.flush()
        return req

    def get_by_id(self, request_id: int) -> Optional[DiscountRequest]:
        return self.session.query(DiscountRequest).filter(DiscountRequest.id == request_id).first()

    def list_pending_for_recipient(self, requested_to: int) -> list[DiscountRequest]:
        """Le manager decide desormais avec le contexte complet (patient,
        articles, nom du demandeur) au lieu de decider "a l'aveugle" sur
        seuls montant+date - residu documente au chantier notifications,
        corrige le 2026-09-28. Une seule requete (2 joinedload) pour eviter
        le N+1 sur une liste potentiellement longue."""
        return (
            self.session.query(DiscountRequest)
            .options(
                joinedload(DiscountRequest.transaction).joinedload(Caisse.items),
                joinedload(DiscountRequest.requester),
            )
            .filter(DiscountRequest.requested_to == requested_to, DiscountRequest.status == "pending")
            .order_by(DiscountRequest.created_at.asc())
            .all()
        )

    def cancel(self, request: DiscountRequest) -> DiscountRequest:
        request.status = "cancelled"
        return request

    def decide(self, request: DiscountRequest, decided_by: int, refuse: bool,
               decision_percent: Optional[int], decision_echelonne_deadline) -> DiscountRequest:
        request.decided_by = decided_by
        request.decided_at = datetime.utcnow()
        if refuse:
            request.status = "refused"
        else:
            request.decision_percent = decision_percent
            request.decision_echelonne_deadline = decision_echelonne_deadline
            request.status = "approved"
        return request

    def _history_query(self, requested_by: Optional[int], date_from, date_to, status: Optional[str]):
        """requested_by=None -> toutes les demandes (admin/promoteur, decision
        utilisateur brainstorming 2026-09-28 : vue de supervision complete) ;
        requested_by=<id> -> uniquement les demandes de ce demandeur
        (secretaire, moindre privilege). Filtre sur created_at (date de la
        demande, pas de la decision - une demande encore en attente n'a pas
        de decided_at)."""
        query = self.session.query(DiscountRequest).options(
            joinedload(DiscountRequest.transaction),
            joinedload(DiscountRequest.requester),
            joinedload(DiscountRequest.recipient),
            joinedload(DiscountRequest.decider),
        )
        if requested_by is not None:
            query = query.filter(DiscountRequest.requested_by == requested_by)
        if date_from:
            query = query.filter(DiscountRequest.created_at >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.filter(DiscountRequest.created_at <= datetime.combine(date_to, time.max))
        if status:
            query = query.filter(DiscountRequest.status == status)
        return query

    def list_history(self, requested_by: Optional[int] = None, date_from=None, date_to=None,
                      status: Optional[str] = None, page: int = 1, per_page: int = 20) -> tuple[list[DiscountRequest], int]:
        query = self._history_query(requested_by, date_from, date_to, status).order_by(DiscountRequest.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return items, total

    def kpi(self, requested_by: Optional[int] = None, date_from=None, date_to=None) -> dict:
        """Recalcule toujours cote serveur sur le filtre de periode/scope
        courant - jamais derive de la page affichee, pour rester exact meme
        pagine (decision brainstorming 2026-09-28)."""
        base = self._history_query(requested_by, date_from, date_to, status=None)
        rows = base.with_entities(DiscountRequest.status, DiscountRequest.original_amount, DiscountRequest.decision_percent).all()
        approved_count = sum(1 for r in rows if r.status == "approved")
        refused_count = sum(1 for r in rows if r.status == "refused")
        pending_count = sum(1 for r in rows if r.status == "pending")
        cancelled_count = sum(1 for r in rows if r.status == "cancelled")
        total_reduced_amount = sum(
            float(r.original_amount) * (r.decision_percent / 100)
            for r in rows if r.status == "approved" and r.decision_percent
        )
        return {
            "approved_count": approved_count,
            "refused_count": refused_count,
            "pending_count": pending_count,
            "cancelled_count": cancelled_count,
            "total_reduced_amount": total_reduced_amount,
        }
