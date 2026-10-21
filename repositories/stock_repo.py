# repositories/stock_repo.py
"""Acces donnees : lots de fabrication, receptions, et changement atomique du stock.

Ne commit jamais : la transaction appartient a StockController.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import Integer, cast, func, text, update
from sqlalchemy.orm import Session, selectinload

from models.pharmacy import Pharmacy
from models.stock_movement import StockMovement
from models.stock_reception import (
    ProductionLot, StockAdjustmentRequest, StockIncident, StockReceipt, StockReceiptLine,
)
from models.user import User
from models.application_role import ApplicationRole


class StockConflictError(Exception):
    """Etat incompatible (operation deja decidee, stock insuffisant...) -> 409.

    Definie ici (couche la plus basse) pour que le depot puisse la lever sans
    importer le controleur ; controller/stock_controller.py la re-exporte.
    """


class StockNotFoundError(ValueError):
    """Objet designe par l'URL introuvable -> 404 (sous-classe de ValueError :
    les appelants directs qui attrapent ValueError restent compatibles)."""


class StockRepository:
    def __init__(self, session: Session):
        self.session = session

    # ---------- stock atomique (reutilise par Tasks 3/4) ----------
    def apply_stock_delta(self, product_id: int, delta: int, movement_type: str, note: str, user,
                          allow_negative: bool = False, write_movement: bool = True) -> int:
        """Verrouille le produit FOR UPDATE, incremente quantity en SQL, recalcule
        stock_status, ecrit le StockMovement. Retourne la nouvelle quantite."""
        prod = self.lock_product(product_id)
        if prod is None:
            raise ValueError(f"Produit introuvable : {product_id}")
        if not allow_negative and (prod.quantity or 0) + delta < 0:
            raise StockConflictError(
                f"Stock insuffisant pour {prod.drug_name} : {prod.quantity} disponible(s), {-delta} demandé(s).")
        self.session.execute(
            update(Pharmacy)
            .where(Pharmacy.medication_id == product_id)
            .values(quantity=Pharmacy.quantity + delta, updated_at=datetime.utcnow())
            .execution_options(synchronize_session=False)
        )
        self.session.refresh(prod)
        prod.update_stock_status()
        if write_movement:
            username = getattr(user, 'username', None) or 'système'
            self.session.add(StockMovement(
                medication_id=product_id, change_qty=delta, movement_type=movement_type,
                note=note, created_by=username, created_at=datetime.utcnow()))
        self.session.flush()
        return prod.quantity

    def set_stock_quantity(self, product_id: int, new_quantity: int, movement_type: str, note: str, user):
        """Fixe le stock a `new_quantity` sans lecture-puis-ecriture non verrouillee :
        verrouille la ligne produit FOR UPDATE, calcule delta = new - quantite verrouillee,
        puis delegue a apply_stock_delta (meme transaction, verrou deja detenu ; mouvement
        ecrit meme si delta == 0). Retourne (stock_avant, stock_apres)."""
        prod = self.lock_product(product_id)
        if prod is None:
            raise ValueError(f"Produit introuvable : {product_id}")
        before = prod.quantity or 0
        after = self.apply_stock_delta(product_id, new_quantity - before, movement_type, note, user,
                                       allow_negative=False)
        return before, after

    def lock_product(self, product_id: int) -> Optional[Pharmacy]:
        return (self.session.query(Pharmacy).filter(Pharmacy.medication_id == product_id)
                .with_for_update().populate_existing().one_or_none())

    def get_product(self, product_id: int) -> Optional[Pharmacy]:
        return self.session.get(Pharmacy, product_id)

    # ---------- numerotation ----------
    def next_number(self, prefix: str, day: date) -> str:
        """`PREFIX-AAAAMMJJ-NNN`. Verrou consultatif transactionnel par (prefixe, jour)
        puis MAX du suffixe : deux creations concurrentes sont serialisees."""
        stem = f"{prefix}-{day:%Y%m%d}-"
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": stem})
        model, col = ((ProductionLot, ProductionLot.lot_number) if prefix == 'LOT'
                      else (StockReceipt, StockReceipt.receipt_number))
        # MAX numerique du suffixe (un MAX texte classerait '-1000' sous '-999')
        last = (self.session.query(func.max(cast(func.substr(col, len(stem) + 1), Integer)))
                .filter(col.op('~')('^' + stem + '[0-9]+$')).scalar())
        n = int(last) + 1 if last else 1
        return f"{stem}{n:03d}"

    # ---------- lots ----------
    def add(self, obj):
        self.session.add(obj)
        self.session.flush()
        return obj

    def get_lot(self, lot_id: int, lock: bool = False) -> Optional[ProductionLot]:
        q = self.session.query(ProductionLot).filter(ProductionLot.id == lot_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_lots(self, status: Optional[str]) -> List[ProductionLot]:
        q = self.session.query(ProductionLot)
        if status:
            q = q.filter(ProductionLot.status == status)
        return q.order_by(ProductionLot.created_at.desc(), ProductionLot.id.desc()).all()

    def lot_has_active_receipt(self, lot_id: int, exclude_receipt_id: Optional[int] = None) -> bool:
        """Une reception a_controler ou valide est-elle deja liee a ce lot ?"""
        q = self.session.query(StockReceipt.id).filter(
            StockReceipt.production_lot_id == lot_id,
            StockReceipt.status.in_(('a_controler', 'valide')))
        if exclude_receipt_id is not None:
            q = q.filter(StockReceipt.id != exclude_receipt_id)
        return q.first() is not None

    # ---------- receptions ----------
    def get_receipt(self, receipt_id: int, lock: bool = False) -> Optional[StockReceipt]:
        q = self.session.query(StockReceipt).filter(StockReceipt.id == receipt_id)
        if lock:
            q = q.with_for_update().populate_existing()
        else:
            q = q.options(selectinload(StockReceipt.lines))
        return q.one_or_none()

    def list_receipts(self, status: Optional[str], created_by: Optional[int]) -> List[StockReceipt]:
        q = self.session.query(StockReceipt).options(selectinload(StockReceipt.lines))
        if status:
            q = q.filter(StockReceipt.status == status)
        if created_by is not None:
            q = q.filter(StockReceipt.created_by == created_by)
        return q.order_by(StockReceipt.created_at.desc(), StockReceipt.id.desc()).all()

    # ---------- avaries ----------
    def get_incident(self, incident_id: int, lock: bool = False) -> Optional[StockIncident]:
        q = self.session.query(StockIncident).filter(StockIncident.id == incident_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_incidents(self, status: Optional[str], created_by: Optional[int]) -> List[StockIncident]:
        q = self.session.query(StockIncident)
        if status:
            q = q.filter(StockIncident.status == status)
        if created_by is not None:
            q = q.filter(StockIncident.created_by == created_by)
        return q.order_by(StockIncident.created_at.desc(), StockIncident.id.desc()).all()

    # ---------- demandes d'ajustement ----------
    def get_adjustment(self, request_id: int, lock: bool = False) -> Optional[StockAdjustmentRequest]:
        q = self.session.query(StockAdjustmentRequest).filter(StockAdjustmentRequest.id == request_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_products_lookup(self):
        """(medication_id, drug_name) de tous les produits, tries par nom."""
        return (self.session.query(Pharmacy.medication_id, Pharmacy.drug_name)
                .order_by(Pharmacy.drug_name, Pharmacy.medication_id).all())

    def list_adjustments(self, status: Optional[str], requested_by: Optional[int]) -> List[StockAdjustmentRequest]:
        q = self.session.query(StockAdjustmentRequest).options(selectinload(StockAdjustmentRequest.product))
        if status:
            q = q.filter(StockAdjustmentRequest.status == status)
        if requested_by is not None:
            q = q.filter(StockAdjustmentRequest.requested_by == requested_by)
        return q.order_by(StockAdjustmentRequest.requested_at.desc(), StockAdjustmentRequest.id.desc()).all()

    def user_names(self, ids) -> dict:
        """{user_id: full_name} en UNE requete ; ids NULL ignores, inconnus absents."""
        wanted = {i for i in ids if i is not None}
        if not wanted:
            return {}
        rows = self.session.query(User.user_id, User.full_name).filter(User.user_id.in_(wanted)).all()
        return {uid: name for uid, name in rows}

    # ---------- historique des mouvements ----------
    def list_movements(self, product_id: Optional[int], movement_type: Optional[str],
                       date_from: Optional[date], date_to: Optional[date], offset: int, limit: int):
        """(rows, total) ; rows = (StockMovement, drug_name), plus recent d'abord.
        date_to est inclusive (created_at < date_to + 1 jour)."""
        q = (self.session.query(StockMovement, Pharmacy.drug_name)
             .join(Pharmacy, Pharmacy.medication_id == StockMovement.medication_id))
        if product_id is not None:
            q = q.filter(StockMovement.medication_id == product_id)
        if movement_type:
            q = q.filter(StockMovement.movement_type == movement_type)
        if date_from is not None:
            q = q.filter(StockMovement.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to is not None:
            q = q.filter(StockMovement.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
        total = q.order_by(None).count()
        rows = (q.order_by(StockMovement.created_at.desc(), StockMovement.movement_id.desc())
                .offset(offset).limit(limit).all())
        return rows, total

    def admin_user_ids(self) -> List[int]:
        rows = (self.session.query(User.user_id)
                .join(ApplicationRole, ApplicationRole.role_id == User.role_id)
                .filter(ApplicationRole.role_name == 'admin', User.is_active.is_(True))
                .all())
        return [r[0] for r in rows]

    def get_user(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def checker_user_ids(self, exclude_user_id: int) -> List[int]:
        rows = (self.session.query(User.user_id)
                .join(ApplicationRole, ApplicationRole.role_id == User.role_id)
                .filter(ApplicationRole.role_name.in_(('StockController', 'admin')),
                        User.is_active.is_(True), User.user_id != exclude_user_id)
                .all())
        return [r[0] for r in rows]
