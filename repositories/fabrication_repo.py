# repositories/fabrication_repo.py
"""Acces donnees de la Fabrication (tables fab_*).

Ne commit jamais : la transaction appartient a FabricationController.
Tout calcul de quantite se fait en Decimal.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from models.fabrication import FabBatch, FabBatchOutput, FabConsumption, FabIntrant, FabIntrantPurchase, FabSettings
from models.pharmacy import Pharmacy
from models.user import User
from models.stock_reception import ProductionLot, StockReceipt, StockReceiptLine
from repositories.stock_repo import StockRepository
from utils.business_time import BUSINESS_TZ


def _local_day_start_utc(d: date) -> datetime:
    """Debut du jour local (Douala) d, en datetime UTC naif (format de declared_at)."""
    from datetime import timezone
    return datetime(d.year, d.month, d.day, tzinfo=BUSINESS_TZ).astimezone(timezone.utc).replace(tzinfo=None)


# Produits fabricables : type naturel ou traditionnel (valeurs reelles : 'Naturel', 'Traditionnel'...).
# Meme logique que le filtre NATUREL de la pharmacie (ilike 'natur'), etendue au traditionnel.
FABRICABLE_PREFIXES = ("natur", "tradi")


def fabricable_product_filter():
    """Predicat SQL unique : medication_type naturel ou traditionnel, insensible a la casse."""
    return or_(*[Pharmacy.medication_type.ilike(f"{p}%") for p in FABRICABLE_PREFIXES])


class FabricationConflictError(Exception):
    """Etat incompatible (achat consomme, deja annule...) -> 409."""


class FabricationJustificationRequired(ValueError):
    """Expedition hors tolerance sans justification -> 422 avec code structure 'justification_required'."""


class FabricationNotFoundError(ValueError):
    """Objet designe par l'URL ou le corps introuvable -> 404 (sous-classe de ValueError)."""


class FabricationRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)
        self.session.flush()
        return obj

    # ---------- intrants ----------
    def get_intrant(self, intrant_id: int, lock: bool = False) -> Optional[FabIntrant]:
        q = self.session.query(FabIntrant).filter(FabIntrant.id == intrant_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_intrants_with_stock(self, include_inactive: bool = False) -> List[tuple]:
        """Liste de (intrant, stock Decimal) ; stock = somme des restants des achats actifs."""
        stock = func.coalesce(func.sum(FabIntrantPurchase.remaining_qty), 0)
        q = (self.session.query(FabIntrant, stock)
             .outerjoin(FabIntrantPurchase,
                        (FabIntrantPurchase.intrant_id == FabIntrant.id)
                        & (FabIntrantPurchase.status == 'actif'))
             .group_by(FabIntrant.id))
        if not include_inactive:
            q = q.filter(FabIntrant.is_active.is_(True))
        rows = q.order_by(func.lower(FabIntrant.name), FabIntrant.id).all()
        return [(i, Decimal(s)) for i, s in rows]

    def delivered_purchase_counts(self, intrant_ids=None) -> Dict[int, int]:
        """{intrant_id: nombre d'achats non annules} ; un achat annule mais deja consomme
        (consommation restituee) compte aussi. Sert au verrou de modification d'un intrant."""
        used = self.session.query(FabConsumption.id).filter(
            FabConsumption.purchase_id == FabIntrantPurchase.id).exists()
        q = (self.session.query(FabIntrantPurchase.intrant_id, func.count(FabIntrantPurchase.id))
             .filter((FabIntrantPurchase.status == 'actif') | used)
             .group_by(FabIntrantPurchase.intrant_id))
        if intrant_ids is not None:
            q = q.filter(FabIntrantPurchase.intrant_id.in_(list(intrant_ids)))
        return {i: int(n) for i, n in q.all()}

    # ---------- achats ----------
    def get_purchase(self, purchase_id: int) -> Optional[FabIntrantPurchase]:
        return self.session.get(FabIntrantPurchase, purchase_id)

    def lock_purchase(self, purchase_id: int) -> Optional[FabIntrantPurchase]:
        """Verrou FOR UPDATE (rafraichit l'objet depuis la base)."""
        return (self.session.query(FabIntrantPurchase)
                .filter(FabIntrantPurchase.id == purchase_id)
                .with_for_update().populate_existing().one_or_none())

    def purchases_for(self, intrant_id: Optional[int] = None, date_from: Optional[date] = None,
                      date_to: Optional[date] = None) -> List[FabIntrantPurchase]:
        q = self.session.query(FabIntrantPurchase)
        if intrant_id is not None:
            q = q.filter(FabIntrantPurchase.intrant_id == intrant_id)
        if date_from is not None:
            q = q.filter(FabIntrantPurchase.purchase_date >= date_from)
        if date_to is not None:
            q = q.filter(FabIntrantPurchase.purchase_date <= date_to)
        return q.order_by(FabIntrantPurchase.purchase_date.desc(), FabIntrantPurchase.id.desc()).all()

    def has_live_consumption(self, purchase_id: int) -> bool:
        """Vrai si une consommation non restituee puise dans cet achat."""
        return self.session.query(FabConsumption.id).filter(
            FabConsumption.purchase_id == purchase_id,
            FabConsumption.restored_at.is_(None)).first() is not None

    def intrant_names(self, ids) -> Dict[int, str]:
        ids = {i for i in ids if i is not None}
        if not ids:
            return {}
        return dict(self.session.query(FabIntrant.id, FabIntrant.name).filter(FabIntrant.id.in_(ids)))

    # ---------- lots ----------
    def get_batch(self, batch_id: int, lock: bool = False) -> Optional[FabBatch]:
        q = self.session.query(FabBatch).filter(FabBatch.id == batch_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def list_batches(self, status: Optional[str] = None, date_from: Optional[date] = None,
                     date_to: Optional[date] = None) -> List[FabBatch]:
        q = self.session.query(FabBatch)
        if status is not None:
            q = q.filter(FabBatch.status == status)
        if date_from is not None:
            q = q.filter(FabBatch.production_date >= date_from)
        if date_to is not None:
            q = q.filter(FabBatch.production_date <= date_to)
        return q.order_by(FabBatch.created_at.desc(), FabBatch.id.desc()).all()

    def product_exists(self, product_id) -> bool:
        if product_id is None:
            return False
        return self.session.query(Pharmacy.medication_id).filter(
            Pharmacy.medication_id == product_id).first() is not None

    def product_fabricable(self, product_id) -> bool:
        if product_id is None:
            return False
        return self.session.query(Pharmacy.medication_id).filter(
            Pharmacy.medication_id == product_id, fabricable_product_filter()).first() is not None

    def intrant_active_map(self, ids) -> Dict[int, bool]:
        ids = {i for i in ids if i is not None}
        if not ids:
            return {}
        return dict(self.session.query(FabIntrant.id, FabIntrant.is_active).filter(FabIntrant.id.in_(ids)))

    def list_products(self) -> List[tuple]:
        """(medication_id, drug_name) des produits naturels/traditionnels, tries par nom."""
        return (self.session.query(Pharmacy.medication_id, Pharmacy.drug_name)
                .filter(fabricable_product_filter())
                .order_by(Pharmacy.drug_name, Pharmacy.medication_id).all())

    def product_name(self, product_id) -> Optional[str]:
        row = self.session.query(Pharmacy.drug_name).filter(Pharmacy.medication_id == product_id).first()
        return row[0] if row else None

    def product_names(self, ids) -> Dict[int, str]:
        """{id: nom} sans filtre de type (les lots existants gardent le nom de leur produit)."""
        ids = {i for i in ids if i is not None}
        if not ids:
            return {}
        return dict(self.session.query(Pharmacy.medication_id, Pharmacy.drug_name)
                    .filter(Pharmacy.medication_id.in_(ids)))

    def production_lot_number(self, production_lot_id) -> Optional[str]:
        if production_lot_id is None:
            return None
        row = self.session.query(ProductionLot.lot_number).filter(ProductionLot.id == production_lot_id).first()
        return row[0] if row else None

    def last_batch_number(self, year: int) -> Optional[str]:
        """Dernier numero de l'annee, sous verrou consultatif de transaction (numerotation sans doublon)."""
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext('fab_batch_number'))"))
        return (self.session.query(FabBatch.batch_number)
                .filter(FabBatch.batch_number.like(f"FAB-{year:04d}-%"))
                .order_by(FabBatch.batch_number.desc()).limit(1).scalar())

    def consumptions_of(self, batch_id: int) -> List[FabConsumption]:
        return (self.session.query(FabConsumption).filter(FabConsumption.batch_id == batch_id)
                .order_by(FabConsumption.purchase_id, FabConsumption.id).all())

    def delete_consumptions(self, batch_id: int) -> None:
        self.session.query(FabConsumption).filter(FabConsumption.batch_id == batch_id).delete(
            synchronize_session=False)
        self.session.flush()

    def provenance(self, batch_id: int) -> List[tuple]:
        """(consommation, achat, intrant) d'un lot."""
        return (self.session.query(FabConsumption, FabIntrantPurchase, FabIntrant)
                .join(FabIntrantPurchase, FabIntrantPurchase.id == FabConsumption.purchase_id)
                .join(FabIntrant, FabIntrant.id == FabIntrantPurchase.intrant_id)
                .filter(FabConsumption.batch_id == batch_id)
                .order_by(FabConsumption.id).all())

    # ---------- sorties declarees ----------
    def outputs_of(self, batch_id: int, include_cancelled: bool = True) -> List[FabBatchOutput]:
        q = self.session.query(FabBatchOutput).filter(FabBatchOutput.batch_id == batch_id)
        if not include_cancelled:
            q = q.filter(FabBatchOutput.status == 'active')
        return q.order_by(FabBatchOutput.declared_at, FabBatchOutput.id).all()

    def active_output_total(self, batch_id: int) -> int:
        return int(self.session.query(func.coalesce(func.sum(FabBatchOutput.quantity), 0))
                   .filter(FabBatchOutput.batch_id == batch_id, FabBatchOutput.status == 'active')
                   .scalar())

    def active_output_totals(self, batch_ids) -> Dict[int, int]:
        """{batch_id: somme des sorties actives} en une requete groupee."""
        ids = {i for i in batch_ids if i is not None}
        if not ids:
            return {}
        rows = (self.session.query(FabBatchOutput.batch_id, func.sum(FabBatchOutput.quantity))
                .filter(FabBatchOutput.batch_id.in_(ids), FabBatchOutput.status == 'active')
                .group_by(FabBatchOutput.batch_id))
        return {b: int(s) for b, s in rows}

    def get_output(self, output_id: int, lock: bool = False) -> Optional[FabBatchOutput]:
        q = self.session.query(FabBatchOutput).filter(FabBatchOutput.id == output_id)
        if lock:
            q = q.with_for_update().populate_existing()
        return q.one_or_none()

    def recent_outputs(self, date_from: Optional[date] = None, date_to: Optional[date] = None,
                       reason: Optional[str] = None, limit: int = 200) -> List[tuple]:
        """(sortie, numero de lot, product_id), du plus recent au plus ancien."""
        q = (self.session.query(FabBatchOutput, FabBatch.batch_number, FabBatch.product_id)
             .join(FabBatch, FabBatch.id == FabBatchOutput.batch_id))
        # declared_at est en UTC naif ; les bornes recues sont des jours locaux (Douala) :
        # [date_from 00:00 local, date_to + 1 jour 00:00 local) converti en UTC naif.
        if date_from is not None:
            q = q.filter(FabBatchOutput.declared_at >= _local_day_start_utc(date_from))
        if date_to is not None:
            q = q.filter(FabBatchOutput.declared_at < _local_day_start_utc(date_to + timedelta(days=1)))
        if reason is not None:
            q = q.filter(FabBatchOutput.reason == reason)
        return q.order_by(FabBatchOutput.declared_at.desc(), FabBatchOutput.id.desc()).limit(limit).all()

    def user_names(self, ids) -> Dict[int, str]:
        ids = {i for i in ids if i is not None}
        if not ids:
            return {}
        return {u: n for u, n in self.session.query(User.user_id, User.full_name)
                .filter(User.user_id.in_(ids))}

    def get_settings(self, lock: bool = False) -> Optional[FabSettings]:
        if not lock:
            return self.session.get(FabSettings, 1)
        return (self.session.query(FabSettings).filter(FabSettings.id == 1)
                .with_for_update().populate_existing().one_or_none())

    # ---------- raccord au circuit lot -> reception existant ----------
    def create_production_lot(self, product_id: int, quantity_produced: int, production_date: date,
                              delivery_date: Optional[date], expiry_date: Optional[date],
                              producer: Optional[str], created_by: int) -> ProductionLot:
        """Cree un ProductionLot 'produit' dans la transaction courante, sans commit.

        Reutilise la numerotation existante LOT-AAAAMMJJ-NNN de StockRepository.next_number
        (verrou consultatif) et StockRepository.add ; StockController.create_lot n'est pas
        appele car il commite lui-meme.
        """
        stock = StockRepository(self.session)
        return stock.add(ProductionLot(
            lot_number=stock.next_number("LOT", date.today()), product_id=product_id,
            quantity_produced=quantity_produced, production_date=production_date,
            delivery_date=delivery_date, expiry_date=expiry_date, producer=producer,
            status="produit", created_by=created_by))

    # ================= lectures pour anomalies, resume, cout, tracabilite (lecture seule) =================
    def batches_out_of_tolerance(self) -> List[FabBatch]:
        """Lots termines ou expedies dont le manque depasse la tolerance."""
        return (self.session.query(FabBatch)
                .filter(FabBatch.out_of_tolerance.is_(True), FabBatch.status.in_(("termine", "expedie")))
                .order_by(FabBatch.id).all())

    def stale_batches(self, stale_days: int, now: Optional[datetime] = None) -> List[FabBatch]:
        """Lots en_production ou termine demarres depuis plus de stale_days jours."""
        limit = (now or datetime.utcnow()) - timedelta(days=stale_days)
        return (self.session.query(FabBatch)
                .filter(FabBatch.status.in_(("en_production", "termine")),
                        FabBatch.started_at.isnot(None), FabBatch.started_at < limit)
                .order_by(FabBatch.started_at, FabBatch.id).all())

    def shipped_vs_received(self) -> List[tuple]:
        """(lot, quantite expediee, bouteilles bonnes recues) des lots expedies ayant au moins
        une reception validee.

        'Expedie' = production_lots.quantity_produced, figee a l'expedition (bonnes moins
        sorties declarees actives). 'Recu bon' = somme de stock_receipt_lines.qty_good des
        receptions au statut 'valide' liees au lot de production (ce que validate_receipt
        ajoute au stock).
        """
        received = func.coalesce(func.sum(StockReceiptLine.qty_good), 0)
        rows = (self.session.query(FabBatch, ProductionLot.quantity_produced, received)
                .join(ProductionLot, ProductionLot.id == FabBatch.production_lot_id)
                .join(StockReceipt, StockReceipt.production_lot_id == FabBatch.production_lot_id)
                .join(StockReceiptLine, StockReceiptLine.receipt_id == StockReceipt.id)
                .filter(FabBatch.status == "expedie", StockReceipt.status == "valide",
                        StockReceiptLine.product_id == FabBatch.product_id)
                .group_by(FabBatch.id, ProductionLot.quantity_produced).order_by(FabBatch.id).all())
        return [(b, int(s or 0), int(r)) for b, s, r in rows]

    def counts_by_status(self) -> Dict[str, int]:
        return dict(self.session.query(FabBatch.status, func.count(FabBatch.id)).group_by(FabBatch.status))

    def recent_batches(self, limit: int = 10) -> List[FabBatch]:
        return (self.session.query(FabBatch)
                .order_by(FabBatch.created_at.desc(), FabBatch.id.desc()).limit(limit).all())

    def shipped_unit_costs(self, product_id: int) -> List[Decimal]:
        """unit_cost des lots expedies du produit, du plus ancien au plus recent."""
        rows = (self.session.query(FabBatch.unit_cost)
                .filter(FabBatch.product_id == product_id, FabBatch.status == "expedie",
                        FabBatch.unit_cost.isnot(None))
                .order_by(FabBatch.expedited_at, FabBatch.id).all())
        return [Decimal(r[0]) for r in rows]

    def batch_by_production_lot(self, production_lot_id: int) -> Optional[FabBatch]:
        return (self.session.query(FabBatch)
                .filter(FabBatch.production_lot_id == production_lot_id).one_or_none())
