# repositories/lab_stock_repo.py
"""Acces donnees du stock labo (tables lab_stock_*).

Ne commit jamais : la transaction appartient a LabStockController.
Toute ecriture de lab_stock_products.quantity passe par apply_delta (verrou FOR UPDATE).
"""
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, aggregate_order_by
from sqlalchemy.orm import Session, selectinload

from models.application_role import ApplicationRole
from models.lab_stock import (
    LabStockCount, LabStockMovement, LabStockProduct, LabStockReceipt, LabStockReceiptLine,
    LabStockRequest,
)
from models.notification import Notification
from models.user import User

OPEN_REQUEST_STATUSES = ("a_commander", "commande")
MANAGER_ROLES = ("promoteur", "ToxicoManager")


class LabStockConflictError(Exception):
    """Etat incompatible (demande deja commandee, stock negatif, doublon...) -> 409."""


class LabStockNotFoundError(ValueError):
    """Objet designe par l'URL introuvable -> 404 (sous-classe de ValueError)."""


class LabStockRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)
        self.session.flush()
        return obj

    # ---------- produits ----------
    def get_product(self, product_id: int, lock: bool = False) -> Optional[LabStockProduct]:
        q = self.session.query(LabStockProduct).filter(LabStockProduct.id == product_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def lock_products(self, ids: Iterable[int]) -> Dict[int, LabStockProduct]:
        """Verrouille les produits FOR UPDATE, un par un en ordre d'id croissant (pas d'interblocage)."""
        out = {}
        for pid in sorted({i for i in ids if i is not None}):
            p = self.get_product(pid, lock=True)
            if p is not None:
                out[pid] = p
        return out

    def list_products(self, include_inactive: bool = False) -> List[LabStockProduct]:
        q = self.session.query(LabStockProduct)
        if not include_inactive:
            q = q.filter(LabStockProduct.is_active.is_(True))
        return q.order_by(func.lower(LabStockProduct.name), LabStockProduct.id).all()

    def active_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = self.session.query(LabStockProduct.id).filter(
            func.lower(LabStockProduct.name) == name.lower(), LabStockProduct.is_active.is_(True))
        if exclude_id is not None:
            q = q.filter(LabStockProduct.id != exclude_id)
        return q.first() is not None

    def apply_delta(self, product_id: int, delta: int, movement_type: str, ref_type: Optional[str],
                    ref_id: Optional[int], user) -> int:
        """Seul point d'ecriture de quantity : verrou, garde >= 0, mouvement. Retourne la nouvelle quantite."""
        prod = self.get_product(product_id, lock=True)
        if prod is None:
            raise LabStockNotFoundError(f"Produit introuvable : {product_id}")
        new_qty = (prod.quantity or 0) + int(delta)
        if new_qty < 0:
            raise LabStockConflictError(
                f"Stock insuffisant pour {prod.name} : {prod.quantity} disponible(s), {-delta} demandé(s).")
        prod.quantity = new_qty
        self.session.add(LabStockMovement(
            product_id=product_id, change_qty=int(delta), movement_type=movement_type,
            ref_type=ref_type, ref_id=ref_id, quantity_after=new_qty,
            created_by=user.user_id, created_at=datetime.utcnow()))
        self.session.flush()
        return new_qty

    # ---------- demandes ----------
    def get_request(self, request_id: int, lock: bool = False) -> Optional[LabStockRequest]:
        q = self.session.query(LabStockRequest).filter(LabStockRequest.id == request_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def open_request_for(self, product_id: int, lock: bool = True) -> Optional[LabStockRequest]:
        q = self.session.query(LabStockRequest).filter(
            LabStockRequest.product_id == product_id,
            LabStockRequest.status.in_(OPEN_REQUEST_STATUSES))
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_requests(self, status: Optional[str] = None) -> List[LabStockRequest]:
        q = self.session.query(LabStockRequest).options(selectinload(LabStockRequest.product))
        if status:
            q = q.filter(LabStockRequest.status == status)
        return q.order_by(LabStockRequest.created_at.desc(), LabStockRequest.id.desc()).all()

    def requests_closed_by(self, receipt_id: int) -> List[LabStockRequest]:
        return (self.session.query(LabStockRequest)
                .filter(LabStockRequest.closed_by_receipt_id == receipt_id,
                        LabStockRequest.status == "recu")
                .order_by(LabStockRequest.id).with_for_update().populate_existing().all())

    # ---------- receptions ----------
    def valid_receipt_exists(self, supplier: str, invoice_number: str) -> bool:
        q = self.session.query(LabStockReceipt.id).filter(
            func.lower(LabStockReceipt.supplier) == supplier.lower(),
            func.lower(LabStockReceipt.invoice_number) == invoice_number.lower(),
            LabStockReceipt.status == "valide")
        return q.first() is not None

    def get_receipt(self, receipt_id: int, lock: bool = False) -> Optional[LabStockReceipt]:
        q = self.session.query(LabStockReceipt).filter(LabStockReceipt.id == receipt_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_receipts(self, supplier: Optional[str] = None, date_from=None, date_to=None) -> List[LabStockReceipt]:
        q = (self.session.query(LabStockReceipt)
             .options(selectinload(LabStockReceipt.lines).selectinload(LabStockReceiptLine.product)))
        if supplier:
            q = q.filter(func.lower(LabStockReceipt.supplier).contains(supplier.strip().lower(), autoescape=True))
        if date_from:
            q = q.filter(LabStockReceipt.delivery_date >= date_from)
        if date_to:
            q = q.filter(LabStockReceipt.delivery_date <= date_to)
        return q.order_by(LabStockReceipt.delivery_date.desc(), LabStockReceipt.id.desc()).all()

    # ---------- utilisateurs / notifications ----------
    def names(self, user_ids) -> dict:
        """{user_id: full_name} en UNE requete ; NULL ignores."""
        wanted = {i for i in user_ids if i is not None}
        if not wanted:
            return {}
        rows = self.session.query(User.user_id, User.full_name).filter(User.user_id.in_(wanted)).all()
        return {uid: name for uid, name in rows}

    def active_user_ids_with_roles(self, role_names: Iterable[str]) -> List[int]:
        rows = (self.session.query(User.user_id)
                .join(ApplicationRole, ApplicationRole.role_id == User.role_id)
                .filter(ApplicationRole.role_name.in_(tuple(role_names)), User.is_active.is_(True))
                .order_by(User.user_id).all())
        return [r[0] for r in rows]

    def manager_user_ids(self) -> List[int]:
        """Destinataires « promoteur + ToxicoManager » actifs."""
        return self.active_user_ids_with_roles(MANAGER_ROLES)

    def find_unread_notification(self, user_id: int, type_: str, key: str, value) -> Optional[Notification]:
        """Notification non lue (user, type) dont payload[key] == value (deduplication)."""
        rows = (self.session.query(Notification)
                .filter(Notification.recipient_user_id == user_id, Notification.type == type_,
                        Notification.status == "unread").all())
        for n in rows:
            if isinstance(n.payload, dict) and n.payload.get(key) == value:
                return n
        return None

    def notification_exists(self, user_id: int, type_: str, key: str, value) -> bool:
        """Notification (lue ou non) dont payload[key] == value : emission « au plus une fois »."""
        rows = (self.session.query(Notification.payload)
                .filter(Notification.recipient_user_id == user_id, Notification.type == type_).all())
        return any(isinstance(pl, dict) and pl.get(key) == value for (pl,) in rows)

    def unread_notifications(self, type_: str) -> List[Notification]:
        return (self.session.query(Notification)
                .filter(Notification.type == type_, Notification.status == "unread").all())

    # ---------- comptages / alertes ----------
    def open_requests_by_product(self) -> Dict[int, LabStockRequest]:
        rows = (self.session.query(LabStockRequest)
                .filter(LabStockRequest.status.in_(OPEN_REQUEST_STATUSES)).all())
        return {r.product_id: r for r in rows}

    def expiring_lines(self, limit_date) -> List[LabStockReceiptLine]:
        """Lignes de receptions valides dont la peremption est <= limit_date (perimees incluses),
        produit actif avec du stock."""
        return (self.session.query(LabStockReceiptLine)
                .join(LabStockReceipt, LabStockReceipt.id == LabStockReceiptLine.receipt_id)
                .join(LabStockProduct, LabStockProduct.id == LabStockReceiptLine.product_id)
                .options(selectinload(LabStockReceiptLine.product))
                .filter(LabStockReceipt.status == "valide",
                        LabStockReceiptLine.expiry_date <= limit_date,
                        LabStockProduct.is_active.is_(True), LabStockProduct.quantity > 0)
                .order_by(LabStockReceiptLine.expiry_date, LabStockReceiptLine.id).all())

    def last_count_at(self) -> Optional[datetime]:
        return self.session.query(func.max(LabStockCount.counted_at)).scalar()

    def active_product_count(self) -> int:
        return (self.session.query(func.count(LabStockProduct.id))
                .filter(LabStockProduct.is_active.is_(True)).scalar() or 0)

    def list_movements(self, product_id: Optional[int] = None, limit: int = 200) -> List[LabStockMovement]:
        q = self.session.query(LabStockMovement).options(selectinload(LabStockMovement.product))
        if product_id is not None:
            q = q.filter(LabStockMovement.product_id == product_id)
        return q.order_by(LabStockMovement.created_at.desc(), LabStockMovement.id.desc()).limit(limit).all()

    # ---------- depenses (agregation SQL) ----------
    def expenses_total(self, date_from, date_to):
        q = (self.session.query(func.coalesce(func.sum(LabStockReceipt.total_amount), 0))
             .filter(LabStockReceipt.status == "valide",
                     LabStockReceipt.delivery_date >= date_from, LabStockReceipt.delivery_date <= date_to))
        return q.scalar()

    def expenses_by_month(self, date_from, date_to):
        month = func.to_char(LabStockReceipt.delivery_date, "YYYY-MM")
        return (self.session.query(month.label("month"), func.sum(LabStockReceipt.total_amount))
                .filter(LabStockReceipt.status == "valide",
                        LabStockReceipt.delivery_date >= date_from, LabStockReceipt.delivery_date <= date_to)
                .group_by(month).order_by(month).all())

    def expenses_by_supplier(self, date_from, date_to):
        """Regroupe sur lower(trim(supplier)) ; nom affiche = graphie de la reception la plus recente."""
        key = func.lower(func.trim(LabStockReceipt.supplier))
        display = func.array_agg(aggregate_order_by(
            LabStockReceipt.supplier, LabStockReceipt.delivery_date.desc(), LabStockReceipt.id.desc()),
            type_=PG_ARRAY(String))[1]
        total = func.sum(LabStockReceipt.total_amount)
        return (self.session.query(display.label("supplier"), total.label("total"))
                .filter(LabStockReceipt.status == "valide",
                        LabStockReceipt.delivery_date >= date_from, LabStockReceipt.delivery_date <= date_to)
                .group_by(key).order_by(total.desc(), key).all())

    def price_history(self, product_id: int):
        return (self.session.query(LabStockReceipt.delivery_date, LabStockReceipt.id, LabStockReceipt.supplier,
                                   LabStockReceiptLine.unit_price, LabStockReceiptLine.received_qty)
                .join(LabStockReceiptLine, LabStockReceiptLine.receipt_id == LabStockReceipt.id)
                .filter(LabStockReceiptLine.product_id == product_id, LabStockReceipt.status == "valide")
                .order_by(LabStockReceipt.delivery_date, LabStockReceipt.id).all())
