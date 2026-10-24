# repositories/cash_closure_repo.py
"""Cloture de caisse : entrees et sorties d'une periode [t0, t1), lecture du depart et de la
derniere cloture. Ne commit jamais (l'appelant gere la transaction).

Regles (plan, "Global Constraints") :
- Entrees = paiement_echelonne.paid_amount dont received_at est dans [t0, t1), au mode du
  paiement. JAMAIS caisse.advance_amount (cache de la meme somme). Ventes pending_approval
  exclues. Les paiements d'une vente annulee restent des entrees de leur periode : l'annulation
  est une sortie dans la periode de cancelled_at.
- Plus les retraits annules dans la periode mais recus avant t0 (argent rendu au tiroir).
- Sorties = retraits recus dans [t0, t1) et non annules avant t1 ; plus, pour chaque vente
  annulee dans [t0, t1), la somme de ses paiements, aux modes de ces paiements.
- cancelled_at (caisse, caisse_retrait) est en UTC naif : converti avec AT TIME ZONE 'UTC'.
- Mode : normalize_mode. Retrait sans mode (anciennes lignes) = especes (regle du plan).
  Paiement au mode vide (colonne NOT NULL, ne devrait pas arriver) = non_classe, pour ne
  jamais gonfler l'attendu en especes avec une somme d'origine inconnue.
- flows() utilise les bornes recues telles quelles ; l'appelant passe
  t0 = max(start_row().started_at, last_closure().period_end).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import text

from models.cash_closure import (
    CashClosure, CashClosureCorrection, CashClosureLine, CashClosureStart, PaymentMode,
)
from models.application_role import ApplicationRole
from models.audit import AuditUserAction
from models.user import User
from utils.cash_lock import CASH_CLOSURE_LOCK_KEY
from utils.cash_rules import CASH, OFFICIAL_MODES, UNCLASSIFIED, normalize_mode


class CashClosureConflictError(Exception):
    """-> 409"""


class CashClosureNotFoundError(Exception):
    """-> 404"""


LOCK_KEY = CASH_CLOSURE_LOCK_KEY  # cle fixe du verrou consultatif de la cloture (partage par les ecritures, utils/cash_lock.py)
RECIPIENT_ROLES = ("promoteur", "admin")
ZERO = Decimal("0")
DETAIL_KEYS = ("payments", "retrait_reversals", "retraits", "cancelled_sales")
ALL_MODES = tuple(sorted(OFFICIAL_MODES)) + (UNCLASSIFIED,)

_PAYMENTS_SQL = text("""
    SELECT pe.payment_method AS mode, SUM(pe.paid_amount) AS total
    FROM paiement_echelonne pe
    JOIN caisse c ON c.transaction_id = pe.transaction_id
    WHERE pe.received_at >= :t0 AND pe.received_at < :t1
      AND c.status <> 'pending_approval'
    GROUP BY pe.payment_method
""")

# Un seul passage sur caisse_retrait : sortie (recu dans la periode, pas annule avant t1)
# ou rentree (annule dans la periode, recu avant t0). Annule dans la periode et recu dans
# la periode : ni l'un ni l'autre.
_RETRAITS_SQL = text("""
    SELECT r.payment_method AS mode,
        SUM(CASE WHEN r.received_at >= :t0 AND r.received_at < :t1
                  AND NOT (r.status = 'cancelled' AND r.cancelled_at IS NOT NULL
                           AND (r.cancelled_at AT TIME ZONE 'UTC') < :t1)
                 THEN r.amount ELSE 0 END) AS exits,
        SUM(CASE WHEN r.status = 'cancelled' AND r.received_at < :t0
                  AND (r.cancelled_at AT TIME ZONE 'UTC') >= :t0
                  AND (r.cancelled_at AT TIME ZONE 'UTC') < :t1
                 THEN r.amount ELSE 0 END) AS reversals
    FROM caisse_retrait r
    WHERE (r.received_at >= :t0 AND r.received_at < :t1)
       OR (r.status = 'cancelled'
           AND (r.cancelled_at AT TIME ZONE 'UTC') >= :t0
           AND (r.cancelled_at AT TIME ZONE 'UTC') < :t1)
    GROUP BY r.payment_method
""")

# Ventes annulees dans la periode, avec leurs paiements par mode (LEFT JOIN : une vente
# annulee sans paiement apparait avec un montant nul, pour la liste des annulations).
_CANCELLED_SALES_SQL = text("""
    SELECT c.transaction_id, (c.cancelled_at AT TIME ZONE 'UTC') AS cancelled_at,
           c.cancelled_by, u.username AS cancelled_by_name, c.cancel_justification,
           c.amount AS invoice_amount, pe.payment_method AS mode,
           COALESCE(SUM(pe.paid_amount), 0) AS total
    FROM caisse c
    LEFT JOIN paiement_echelonne pe ON pe.transaction_id = c.transaction_id
    LEFT JOIN users u ON u.user_id = c.cancelled_by
    WHERE c.status = 'cancelled' AND c.cancelled_at IS NOT NULL
      AND (c.cancelled_at AT TIME ZONE 'UTC') >= :t0
      AND (c.cancelled_at AT TIME ZONE 'UTC') < :t1
    GROUP BY c.transaction_id, c.cancelled_at, c.cancelled_by, u.username,
             c.cancel_justification, c.amount, pe.payment_method
    ORDER BY c.cancelled_at, c.transaction_id
""")


def _check_bounds(t0: datetime, t1: datetime) -> dict:
    if t0.tzinfo is None or t1.tzinfo is None:
        raise ValueError("t0 and t1 must be timezone-aware")
    if t1 <= t0:
        raise ValueError("t1 must be after t0")
    return {"t0": t0, "t1": t1}


def _payment_mode(raw: Optional[str]) -> str:
    return normalize_mode(raw) or UNCLASSIFIED


def _retrait_mode(raw: Optional[str]) -> str:
    return normalize_mode(raw) or CASH


class CashClosureRepository:
    def __init__(self, session):
        self.session = session

    # --- lecture du depart et de la chaine ---------------------------------------------
    def start_row(self) -> Optional[CashClosureStart]:
        return self.session.get(CashClosureStart, 1)

    def last_closure(self) -> Optional[CashClosure]:
        return (self.session.query(CashClosure)
                .order_by(CashClosure.period_end.desc()).first())

    # --- verrou, modes, destinataires, ecriture (tache 4) --------------------------------
    def try_lock(self) -> bool:
        """Verrou de transaction (relache au commit/rollback). False si une autre
        transaction le tient deja : l'appelant refuse (409) au lieu d'attendre."""
        return bool(self.session.execute(
            text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": LOCK_KEY}).scalar())

    def active_modes(self) -> List[PaymentMode]:
        return (self.session.query(PaymentMode).filter(PaymentMode.is_active.is_(True))
                .order_by(PaymentMode.sort_order, PaymentMode.code).all())

    def recipient_user_ids(self) -> List[int]:
        """Promoteur + admins actifs (copie de LabStockRepository.active_user_ids_with_roles)."""
        rows = (self.session.query(User.user_id)
                .join(ApplicationRole, ApplicationRole.role_id == User.role_id)
                .filter(ApplicationRole.role_name.in_(RECIPIENT_ROLES), User.is_active.is_(True))
                .order_by(User.user_id).all())
        return [r[0] for r in rows]

    def insert_start(self, started_at: datetime, opening_cash: Decimal,
                     set_by: Optional[int]) -> CashClosureStart:
        row = CashClosureStart(id=1, started_at=started_at, opening_cash=opening_cash, set_by=set_by)
        self.session.add(row)
        self.session.flush()
        return row

    def insert_closure(self, closure: CashClosure, lines: List[CashClosureLine]) -> CashClosure:
        """Insere une cloture complete (les triggers refusent toute modification ulterieure).
        Chainage verifie ici : period_start == period_end de la derniere cloture."""
        last = self.last_closure()
        if last is not None and closure.period_start != last.period_end:
            raise ValueError("Chainage des periodes rompu")
        self.session.add(closure)
        self.session.flush()
        for line in lines:
            line.closure_id = closure.id
            self.session.add(line)
        self.session.flush()
        return closure

    def count_gap_refusals(self, period_start_iso: str) -> int:
        """Refus 'ecart sans commentaire' pour la periode commencant a period_start_iso (UTC
        ISO, ecrit par le controleur dans l'audit), TOUS utilisateurs confondus : un second
        compte n'obtient pas 3 sondages de plus."""
        return (self.session.query(AuditUserAction)
                .filter(AuditUserAction.resource_type == "CashClosure",
                        AuditUserAction.action_performed == "CLOSURE_GAP_REFUSED",
                        AuditUserAction.new_values["period_start"].astext == period_start_iso)
                .count())

    def get(self, closure_id: int) -> Optional[CashClosure]:
        return self.session.get(CashClosure, closure_id)

    def lines_for(self, closure_ids: List[int]) -> dict:
        out: dict = {i: [] for i in closure_ids}
        if not closure_ids:
            return out
        for line in (self.session.query(CashClosureLine)
                     .filter(CashClosureLine.closure_id.in_(closure_ids))
                     .order_by(CashClosureLine.closure_id, CashClosureLine.id)):
            out[line.closure_id].append(line)
        return out

    def list_closures(self, date_from: Optional[date] = None, date_to: Optional[date] = None,
                      kind: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[CashClosure]:
        q = self.session.query(CashClosure)
        if date_from is not None:
            q = q.filter(CashClosure.business_date >= date_from)
        if date_to is not None:
            q = q.filter(CashClosure.business_date <= date_to)
        if kind is not None:
            q = q.filter(CashClosure.kind == kind)
        return q.order_by(CashClosure.period_end.desc()).offset(offset).limit(limit).all()

    # --- modes de paiement et corrections (tache 5) --------------------------------------
    def list_modes(self) -> List[PaymentMode]:
        return self.session.query(PaymentMode).order_by(PaymentMode.sort_order, PaymentMode.code).all()

    def get_mode(self, code: str) -> Optional[PaymentMode]:
        return self.session.get(PaymentMode, code)

    def add_correction(self, corr: CashClosureCorrection) -> CashClosureCorrection:
        self.session.add(corr)
        self.session.flush()
        return corr

    def get_correction(self, correction_id: int, for_update: bool = False) -> Optional[CashClosureCorrection]:
        q = self.session.query(CashClosureCorrection).filter(CashClosureCorrection.id == correction_id)
        if for_update:
            q = q.with_for_update()
        return q.one_or_none()

    def approved_corrections(self, t0: datetime, t1: datetime) -> List[CashClosureCorrection]:
        """Corrections approuvees dont decided_at est dans [t0, t1) : elles se compensent dans
        la periode ou elles ont ete approuvees (jamais dans la cloture d'origine)."""
        _check_bounds(t0, t1)
        return (self.session.query(CashClosureCorrection)
                .filter(CashClosureCorrection.status == "approved",
                        CashClosureCorrection.decided_at >= t0,
                        CashClosureCorrection.decided_at < t1)
                .order_by(CashClosureCorrection.decided_at, CashClosureCorrection.id).all())

    def list_corrections(self, status: Optional[str] = None, limit: int = 200) -> List[CashClosureCorrection]:
        q = self.session.query(CashClosureCorrection)
        if status is not None:
            q = q.filter(CashClosureCorrection.status == status)
        return q.order_by(CashClosureCorrection.requested_at.desc(),
                          CashClosureCorrection.id.desc()).limit(limit).all()

    # --- flux d'une periode -------------------------------------------------------------
    def flows(self, t0: datetime, t1: datetime) -> dict:
        """{mode: {"entries", "exits", "detail": {payments, retrait_reversals, retraits,
        cancelled_sales}}} pour les 4 modes officiels et non_classe (toujours presents)."""
        params = _check_bounds(t0, t1)
        out = {m: {"entries": ZERO, "exits": ZERO, "detail": {k: ZERO for k in DETAIL_KEYS}}
               for m in ALL_MODES}

        def add(mode, key, amount):
            out[mode]["detail"][key] += Decimal(amount or 0)

        for row in self.session.execute(_PAYMENTS_SQL, params):
            add(_payment_mode(row.mode), "payments", row.total)
        for row in self.session.execute(_RETRAITS_SQL, params):
            mode = _retrait_mode(row.mode)
            add(mode, "retraits", row.exits)
            add(mode, "retrait_reversals", row.reversals)
        for sale in self.cancellations(t0, t1):
            for mode, amount in sale["by_mode"].items():
                add(mode, "cancelled_sales", amount)

        for line in out.values():
            d = line["detail"]
            line["entries"] = d["payments"] + d["retrait_reversals"]
            line["exits"] = d["retraits"] + d["cancelled_sales"]
        return out

    def cancellations(self, t0: datetime, t1: datetime) -> list[dict]:
        """Ventes annulees dans [t0, t1) : auteur, montant rendu (somme des paiements),
        repartition par mode, justification, vente."""
        params = _check_bounds(t0, t1)
        sales: dict[int, dict] = {}
        for row in self.session.execute(_CANCELLED_SALES_SQL, params):
            sale = sales.setdefault(row.transaction_id, {
                "transaction_id": row.transaction_id,
                "cancelled_at": row.cancelled_at,
                "cancelled_by": row.cancelled_by,
                "cancelled_by_name": row.cancelled_by_name,
                "justification": row.cancel_justification,
                "invoice_amount": Decimal(row.invoice_amount),
                "amount": ZERO,
                "by_mode": {},
            })
            total = Decimal(row.total or 0)
            if row.mode is None and total == 0:
                continue  # vente sans aucun paiement
            mode = _payment_mode(row.mode)
            sale["by_mode"][mode] = sale["by_mode"].get(mode, ZERO) + total
            sale["amount"] += total
        return list(sales.values())
