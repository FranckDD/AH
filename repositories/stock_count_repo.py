# repositories/stock_count_repo.py
"""Acces donnees du comptage physique du stock de la pharmacie.

Ne commit jamais : la transaction appartient a StockCountController.
Reutilise StockRepository (lock_product, get_product, admin_user_ids, user_names, add).
"""
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import func, text

from models.pharmacy import Pharmacy
from models.stock_count import StockCount, StockCountLine, StockCountSettings
from models.stock_movement import StockMovement
from repositories.stock_repo import StockRepository


class StockCountRepository(StockRepository):
    # ---------- reglage ----------
    def get_settings(self) -> Optional[StockCountSettings]:
        return self.session.get(StockCountSettings, 1, populate_existing=True)

    def upsert_interval(self, days: int, user_id: int, now: datetime) -> None:
        self.session.execute(text(
            "INSERT INTO stock_count_settings (id, interval_days, updated_by, updated_at) "
            "VALUES (1, :d, :u, :t) ON CONFLICT (id) DO UPDATE SET "
            "interval_days = EXCLUDED.interval_days, updated_by = EXCLUDED.updated_by, "
            "updated_at = EXCLUDED.updated_at"), {"d": days, "u": user_id, "t": now})

    # ---------- comptages ----------
    def has_open_count(self, user_id: int) -> bool:
        return (self.session.query(StockCount.id)
                .filter(StockCount.started_by == user_id, StockCount.status == "en_cours")
                .first() is not None)

    def get_count(self, count_id: int, lock: bool = False) -> Optional[StockCount]:
        q = self.session.query(StockCount).filter(StockCount.id == count_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_counts(self, started_by: Optional[int], status: Optional[str], start_from: Optional[datetime],
                    start_before: Optional[datetime], limit: int, offset: int) -> Tuple[List[StockCount], int]:
        q = self.session.query(StockCount)
        if started_by is not None:
            q = q.filter(StockCount.started_by == started_by)
        if status:
            q = q.filter(StockCount.status == status)
        if start_from is not None:
            q = q.filter(StockCount.started_at >= start_from)
        if start_before is not None:
            q = q.filter(StockCount.started_at < start_before)
        total = q.order_by(None).count()
        rows = q.order_by(StockCount.started_at.desc(), StockCount.id.desc()).offset(offset).limit(limit).all()
        return rows, total

    def line_summaries(self, count_ids: List[int]) -> Dict[int, Tuple[int, int]]:
        """{count_id: (nombre de lignes, nombre d'ecarts non nuls)}."""
        if not count_ids:
            return {}
        rows = (self.session.query(StockCountLine.count_id, func.count(StockCountLine.id),
                                   func.count(StockCountLine.id).filter(StockCountLine.difference != 0))
                .filter(StockCountLine.count_id.in_(count_ids)).group_by(StockCountLine.count_id).all())
        return {cid: (int(n), int(g)) for cid, n, g in rows}

    def lines_with_names(self, count_id: int) -> List[Tuple[StockCountLine, str]]:
        return (self.session.query(StockCountLine, Pharmacy.drug_name)
                .join(Pharmacy, Pharmacy.medication_id == StockCountLine.product_id)
                .filter(StockCountLine.count_id == count_id)
                .order_by(Pharmacy.drug_name, StockCountLine.product_id).all())

    # ---------- produits ----------
    def product_ids(self) -> Set[int]:
        return {r[0] for r in self.session.query(Pharmacy.medication_id).all()}

    def movements_after(self, product_id: int, after: datetime) -> Tuple[int, int]:
        """(nombre, somme nette de change_qty) des mouvements du produit crees STRICTEMENT apres `after`
        (UTC naif). A appeler sous le verrou produit : aucun nouveau mouvement ne peut s'intercaler."""
        n, net = (self.session.query(func.count(StockMovement.movement_id),
                                     func.coalesce(func.sum(StockMovement.change_qty), 0))
                  .filter(StockMovement.medication_id == product_id, StockMovement.created_at > after)
                  .one())
        return int(n or 0), int(net or 0)

    def last_counted_by_product(self) -> Dict[int, datetime]:
        """{product_id: max(submitted_at)} sur les lignes des comptages valides."""
        rows = (self.session.query(StockCountLine.product_id, func.max(StockCount.submitted_at))
                .join(StockCount, StockCount.id == StockCountLine.count_id)
                .filter(StockCount.status == "valide")
                .group_by(StockCountLine.product_id).all())
        return {pid: last for pid, last in rows}

    # ---------- remplacement des demandes de comptage en attente ----------
    def lock_pending_count_requests(self, product_ids, exclude_count_id: int):
        """Demandes 'en_attente' nees d'un comptage ANTERIEUR (via stock_count_lines.adjustment_request_id)
        pour ces produits, verrouillees FOR UPDATE par ordre d'id. Les demandes d'autre origine
        (secretaire...) ne sont jamais renvoyees."""
        from models.stock_reception import StockAdjustmentRequest as SAR
        ids = list(product_ids)
        if not ids:
            return []
        return (self.session.query(SAR)
                .join(StockCountLine, StockCountLine.adjustment_request_id == SAR.id)
                .filter(SAR.product_id.in_(ids), SAR.status == "en_attente",
                        StockCountLine.count_id != exclude_count_id)
                .order_by(SAR.id).with_for_update(of=SAR).populate_existing().all())

    def superseded_by_count(self, count_id: int, note: str) -> Dict[int, List[int]]:
        """{product_id: [ids des demandes de comptage annulees par ce comptage]}."""
        from models.stock_reception import StockAdjustmentRequest as SAR
        rows = (self.session.query(SAR.product_id, SAR.id)
                .join(StockCountLine, StockCountLine.adjustment_request_id == SAR.id)
                .filter(SAR.status == "annule", SAR.decision_note == note,
                        StockCountLine.count_id != count_id)
                .order_by(SAR.id).all())
        out: Dict[int, List[int]] = {}
        for pid, rid in rows:
            out.setdefault(pid, []).append(rid)
        return out

    def previous_counts(self, product_ids, count_id: int, before: datetime, since: datetime) -> Dict[int, int]:
        """{product_id: id du dernier comptage valide (autre que count_id) soumis dans [since, before)}."""
        ids = list(product_ids)
        if not ids:
            return {}
        rows = (self.session.query(StockCountLine.product_id, StockCount.id)
                .join(StockCount, StockCount.id == StockCountLine.count_id)
                .filter(StockCountLine.product_id.in_(ids), StockCount.status == "valide",
                        StockCount.id != count_id, StockCount.submitted_at >= since,
                        StockCount.submitted_at < before)
                .order_by(StockCount.submitted_at.desc(), StockCount.id.desc()).all())
        out: Dict[int, int] = {}
        for pid, cid in rows:
            out.setdefault(pid, cid)
        return out
