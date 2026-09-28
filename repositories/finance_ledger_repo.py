# repositories/finance_ledger_repo.py
"""
Journal financier unifie : recettes (caisse) et depenses (caisse_retrait)
vues comme un seul flux de mouvements, trie et pagine EN BASE.

Raison d'etre : ces deux tables etaient paginees separement puis fusionnees
cote client, ce qui rendait le tri faux d'une page a l'autre, les dernieres
pages vides et le filtre categorie inoperant (registre L1e). Deux sources
paginees independamment ne peuvent pas etre fusionnees correctement apres
coup, quelle que soit l'astuce : la fusion doit avoir lieu avant la
pagination, donc en base.
"""

from typing import Any, Dict, Optional

from sqlalchemy import String, case, cast, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from models.caisse import Caisse
from models.retrait import CaisseRetrait
from models.user import User


class FinanceLedgerRepository:
    def __init__(self, session: Session):
        self.session = session

    def _flux_unifie(self):
        """Construit l'union des deux tables sous une projection commune."""
        recettes = select(
            Caisse.transaction_id.label("id"),
            literal("INCOME").label("sens"),
            # Montant reellement encaisse, pas le total du : meme convention
            # que le tableau de bord (dashboardStore).
            Caisse.advance_amount.label("amount"),
            Caisse.amount.label("amount_total"),
            Caisse.paid_at.label("date"),
            Caisse.transaction_type.label("category"),
            Caisse.payment_method.label("payment_method"),
            Caisse.note.label("description"),
            Caisse.patient_label.label("patient_label"),
            Caisse.created_by_name.label("created_by_name"),
            Caisse.status.label("status"),
        )

        depenses = select(
            CaisseRetrait.retrait_id.label("id"),
            literal("EXPENSE").label("sens"),
            CaisseRetrait.amount.label("amount"),
            CaisseRetrait.amount.label("amount_total"),
            CaisseRetrait.retrait_at.label("date"),
            CaisseRetrait.category.label("category"),
            CaisseRetrait.payment_method.label("payment_method"),
            CaisseRetrait.justification.label("description"),
            # caisse_retrait n'a pas de notion de patient : NULL type-compatible
            # requis par UNION ALL (les colonnes des deux SELECT doivent
            # s'aligner 1-pour-1 en ordre ET en type).
            cast(literal(None), String(100)).label("patient_label"),
            # caisse_retrait ne stocke pas le nom de l'auteur, seulement la
            # cle etrangere - on le resout ici pour homogeneiser la projection.
            User.full_name.label("created_by_name"),
            CaisseRetrait.status.label("status"),
        ).join(User, User.user_id == CaisseRetrait.handled_by, isouter=True)

        return union_all(recettes, depenses).subquery("mouvements")

    def _appliquer_filtres(self, requete, flux, date_from, date_to, category, search, sens, status):
        if sens in ("INCOME", "EXPENSE"):
            requete = requete.where(flux.c.sens == sens)
        if status:
            requete = requete.where(flux.c.status == status)
        # func.date() sur la colonne : inclut la journee entiere quel que soit
        # le format envoye par l'appelant (meme regle que caisse_repo:127).
        if date_from is not None:
            requete = requete.where(func.date(flux.c.date) >= date_from)
        if date_to is not None:
            requete = requete.where(func.date(flux.c.date) <= date_to)
        if category:
            requete = requete.where(flux.c.category == category)
        if search:
            motif = f"%{search.lower()}%"
            # patient_label est NULL cote depenses (voir _flux_unifie) : func.lower(NULL)
            # vaut NULL en Postgres, donc la condition LIKE est simplement fausse pour
            # ces lignes - pas de filtrage parasite, pas de crash (meme precedent que
            # note/patient_label dans caisse_repo.py::search_transactions).
            requete = requete.where(
                or_(
                    func.lower(flux.c.description).like(motif),
                    func.lower(flux.c.category).like(motif),
                    func.lower(flux.c.created_by_name).like(motif),
                    func.lower(flux.c.patient_label).like(motif),
                )
            )
        return requete

    def list_mouvements(
        self,
        page: int = 1,
        per_page: int = 20,
        date_from=None,
        date_to=None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sens: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        flux = self._flux_unifie()

        # Total calcule sur le flux filtre AVANT pagination.
        requete_total = self._appliquer_filtres(
            select(func.count()).select_from(flux), flux,
            date_from, date_to, category, search, sens, status,
        )
        total = self.session.execute(requete_total).scalar() or 0

        requete = self._appliquer_filtres(
            select(flux), flux,
            date_from, date_to, category, search, sens, status,
        )
        lignes = self.session.execute(
            requete.order_by(flux.c.date.desc(), flux.c.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).mappings().all()

        return {
            "data": [
                {
                    "id": l["id"],
                    "sens": l["sens"],
                    "amount": float(l["amount"] or 0),
                    "amount_total": float(l["amount_total"] or 0),
                    "date": l["date"],
                    "category": l["category"],
                    "payment_method": l["payment_method"],
                    "description": l["description"],
                    "created_by_name": l["created_by_name"],
                    "status": l["status"],
                }
                for l in lignes
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
        }

    def get_totals(
        self,
        date_from=None,
        date_to=None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sens: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, float]:
        """Totaux recettes/depenses sur le flux unifie, filtre exactement comme
        list_mouvements() - garantit que ces totaux ne peuvent jamais diverger
        de la liste affichee juste en dessous, puisqu'ils partagent le meme
        filtrage (categorie, recherche, dates, statut)."""
        flux = self._flux_unifie()
        requete = self._appliquer_filtres(
            select(
                func.coalesce(
                    func.sum(case((flux.c.sens == "INCOME", flux.c.amount), else_=0)), 0
                ).label("income"),
                func.coalesce(
                    func.sum(case((flux.c.sens == "EXPENSE", flux.c.amount), else_=0)), 0
                ).label("expense"),
            ),
            flux,
            date_from, date_to, category, search, sens, status,
        )
        ligne = self.session.execute(requete).one()
        return {"income": float(ligne.income), "expense": float(ligne.expense)}

    def list_categories(self) -> list[str]:
        """Categories reellement presentes dans le journal. Evite de coder en
        dur un vocabulaire : la base contient un melange de libelles francais
        et de codes anglais selon l'anciennete des lignes."""
        flux = self._flux_unifie()
        lignes = self.session.execute(
            select(flux.c.category).where(flux.c.category.isnot(None)).distinct().order_by(flux.c.category)
        ).scalars().all()
        return [c for c in lignes if c]
