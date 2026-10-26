# controller/fabrication_controller.py
"""Fabrication : intrants et achats d'intrants.

Le controleur possede la transaction (commit ici, rollback sur toute exception).
Les roles sont verifies par les endpoints (/fabrication).
Erreurs : FabricationNotFoundError -> 404, FabricationConflictError -> 409,
PermissionError -> 403, ValueError -> 422.
Lots et consommations (tache 4) : sections a la suite.
"""
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from models.fabrication import FabBatch, FabBatchOutput, FabConsumption, FabIntrant, FabIntrantPurchase, FabSettings
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from utils.fabrication_rules import (
    OUTPUT_REASONS, TRANSITIONS, OutputExceedsAvailable, compute_bilan, compute_cost, next_batch_number,
    validate_output,
)
from repositories.fabrication_repo import (
    FabricationConflictError, FabricationJustificationRequired, FabricationNotFoundError, FabricationRepository,
)

__all__ = ["FabricationController", "FabricationConflictError", "FabricationNotFoundError"]

QTY_STEP = Decimal("0.001")
COST_STEP = Decimal("0.01")
MAX_QTY = Decimal("999999999.999")   # Numeric(12, 3)
MAX_COST = Decimal("9999999999.99")  # Numeric(12, 2)
INTRANT_FIELDS = ("name", "unit", "is_container", "is_active")
# figes des qu'un achat non annule existe (is_active reste modifiable)
LOCKED_INTRANT_FIELDS = {"name", "unit", "is_container"}


def _check_range(date_from: Optional[date], date_to: Optional[date]) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("La date de debut doit preceder la date de fin.")
BATCH_COLUMNS = ("id", "batch_number", "product_id", "status", "production_date", "producer_name",
                 "qty_good", "qty_damaged", "qty_rejected", "liquid_lost", "expected_qty", "found_qty",
                 "missing_qty", "missing_pct", "tolerance_applied", "out_of_tolerance", "justification",
                 "total_cost", "unit_cost", "delivery_date", "expiry_date", "production_lot_id",
                 "cancel_reason", "created_by", "created_at", "started_at", "finished_at",
                 "expedited_at", "expedited_by")
PURCHASE_FIELDS = ("supplier", "delivery_ref", "purchase_date", "quantity", "unit_cost")


def _jsonable(d):
    """Audit JSONB : Decimal/date en texte (None reste None)."""
    return None if d is None else json.loads(json.dumps(d, default=str))


def _text(v, label, max_len, required=False) -> Optional[str]:
    if v is None:
        if required:
            raise ValueError(f"{label} est obligatoire.")
        return None
    if not isinstance(v, str):
        raise ValueError(f"{label} invalide.")
    v = v.strip()
    if not v:
        if required:
            raise ValueError(f"{label} est obligatoire.")
        return None
    if len(v) > max_len:
        raise ValueError(f"{label} depasse {max_len} caracteres.")
    return v


def _decimal(v, label, step: Decimal, upper: Decimal, positive: bool) -> Decimal:
    """Valide un Decimal : fini, borne, au plus la precision de la colonne."""
    if v is None or isinstance(v, (bool, float)):
        raise ValueError(f"{label} invalide.")
    try:
        d = Decimal(str(v).strip())
    except Exception:
        raise ValueError(f"{label} invalide.")
    if not d.is_finite():
        raise ValueError(f"{label} invalide.")
    if positive and d <= 0:
        raise ValueError(f"{label} doit etre superieur a zero.")
    if d < 0:
        raise ValueError(f"{label} ne peut pas etre negatif.")
    if d > upper:
        raise ValueError(f"{label} depasse la limite autorisee.")
    if d != d.quantize(step):
        raise ValueError(f"{label} : precision excessive.")
    return d.quantize(step)


def _intrant_d(i: FabIntrant) -> Dict[str, Any]:
    return {"id": i.id, "name": i.name, "unit": i.unit, "is_container": i.is_container,
            "alert_threshold": i.alert_threshold, "is_active": i.is_active}


def _purchase_d(p: FabIntrantPurchase, intrant_name: Optional[str] = None,
                intrant_active: Optional[bool] = None) -> Dict[str, Any]:
    return {"id": p.id, "intrant_id": p.intrant_id, "intrant_name": intrant_name,
            "intrant_active": intrant_active,
            "supplier": p.supplier, "delivery_ref": p.delivery_ref,
            "purchase_date": p.purchase_date, "quantity": p.quantity, "unit_cost": p.unit_cost,
            "remaining_qty": p.remaining_qty, "status": p.status, "cancel_reason": p.cancel_reason,
            "created_by": p.created_by, "created_at": p.created_at}


def _iso_utc_naive(dt: Optional[datetime]) -> Optional[str]:
    """Horodatage UTC naif (colonne DateTime sans fuseau) -> ISO avec +00:00 explicite.
    Sans decalage, le navigateur le lirait comme une heure locale (1 h d'avance a Douala)."""
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt is not None else None


def _output_d(o: FabBatchOutput, names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    names = names or {}
    return {"id": o.id, "batch_id": o.batch_id, "reason": o.reason, "quantity": o.quantity,
            "note": o.note, "status": o.status, "declared_by": o.declared_by,
            "declared_by_name": names.get(o.declared_by), "declared_at": _iso_utc_naive(o.declared_at),
            "cancelled_by": o.cancelled_by, "cancelled_at": _iso_utc_naive(o.cancelled_at),
            "cancel_reason": o.cancel_reason}


class FabricationController:
    LOW_STOCK_TYPE = "fab_intrant_low"
    LOW_STOCK_ROLES = ("ProductionManager", "admin", "promoteur")

    def __init__(self, repo: FabricationRepository, audit_repo: AuditRepository, current_user,
                 notification_repo: Optional[NotificationRepository] = None):
        if repo is None or audit_repo is None:
            raise TypeError("FabricationController exige repo et audit_repo.")
        self.repo = repo
        self.audit_repo = audit_repo
        self.user = current_user
        self.session = repo.session
        # jamais None : un appelant qui oublie de l'injecter ne doit pas faire taire les alertes de seuil
        self.notification_repo = notification_repo or NotificationRepository(repo.session)

    # ---- alerte « intrant sous le seuil » : une notification par franchissement ----
    def _stock_state(self, intrant_ids) -> Dict[int, tuple]:
        """{intrant_id: (stock, seuil)} a l'instant T (avant ou apres une operation)."""
        ids = list(dict.fromkeys(intrant_ids))
        stocks = self.repo.intrant_stocks(ids)
        out = {}
        for i in ids:
            intr = self.repo.get_intrant(i)
            out[i] = (stocks.get(i, Decimal(0)), Decimal(intr.alert_threshold or 0) if intr else Decimal(0))
        return out

    def _notify_crossings(self, before: Dict[int, tuple]) -> None:
        """Notifie quand un intrant ACTIF passe de « au seuil ou au dessus » a « sous le seuil » ;
        pas de repetition tant que le stock reste sous le seuil."""
        after = self._stock_state(before.keys())
        recipients = None
        for iid, (stock_b, thr_b) in before.items():
            stock_a, thr_a = after[iid]
            if stock_b < thr_b or not stock_a < thr_a:
                continue
            intr = self.repo.get_intrant(iid)
            if intr is None or not intr.is_active:
                continue
            if recipients is None:
                recipients = self.repo.active_user_ids_with_roles(self.LOW_STOCK_ROLES)
            payload = _jsonable({"intrant_id": iid, "intrant_name": intr.name, "unit": intr.unit,
                                 "stock": stock_a, "alert_threshold": thr_a})
            for uid in recipients:
                self.notification_repo.create(uid, self.LOW_STOCK_TYPE, payload)

    def _audit(self, resource_type, action, resource_id, old=None, new=None):
        self.audit_repo.log_user_action(current_user=self.user, resource_type=resource_type,
                                        action_performed=action, resource_id=resource_id,
                                        old_values=_jsonable(old), new_values=_jsonable(new))

    def _tx(self, fn):
        """Execute fn dans une transaction : commit si OK, rollback sur toute exception."""
        try:
            out = fn()
            self.session.commit()
            return out
        except Exception:
            self.session.rollback()
            raise

    # ================= intrants =================
    def _clean_intrant(self, data: Dict[str, Any], partial: bool) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not partial or "name" in data:
            out["name"] = _text(data.get("name"), "Le nom", 150, required=True)
        if not partial or "unit" in data:
            out["unit"] = _text(data.get("unit"), "L'unite", 20, required=True)
        for f in ("is_container", "is_active"):
            if f in data:
                if not isinstance(data[f], bool):
                    raise ValueError(f"{f} invalide.")
                out[f] = data[f]
        return out

    def create_intrant(self, data: Dict[str, Any]) -> Dict[str, Any]:
        def run():
            clean = self._clean_intrant(data, partial=False)
            i = self.repo.add(FabIntrant(**clean))
            out = _intrant_d(i)
            self._audit("FabIntrant", "CREATE", i.id, new=out)
            return out
        return self._tx(run)

    def update_intrant(self, intrant_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        def run():
            i = self.repo.get_intrant(intrant_id, lock=True)
            if i is None:
                raise FabricationNotFoundError("Intrant introuvable.")
            clean = self._clean_intrant({k: v for k, v in data.items() if k in INTRANT_FIELDS}, partial=True)
            if not clean:
                raise ValueError("Aucune modification fournie.")
            if set(clean) & LOCKED_INTRANT_FIELDS and self.repo.delivered_purchase_counts([i.id]).get(i.id):
                raise FabricationConflictError(
                    "Cet intrant a deja ete livre : son nom, son unite et son type ne sont plus "
                    "modifiables. Seule l'activation reste possible.")
            old = _intrant_d(i)
            for k, v in clean.items():
                setattr(i, k, v)
            self.session.flush()
            out = _intrant_d(i)
            self._audit("FabIntrant", "UPDATE", i.id, old=old, new=out)
            return out
        return self._tx(run)

    def set_threshold(self, intrant_id: int, value) -> Dict[str, Any]:
        """Seuil d'alerte d'un intrant (admin, garde par l'endpoint)."""
        def run():
            v = _decimal(value, "Le seuil", QTY_STEP, MAX_QTY, positive=False)
            i = self.repo.get_intrant(intrant_id, lock=True)
            if i is None:
                raise FabricationNotFoundError("Intrant introuvable.")
            old = _intrant_d(i)
            before = self._stock_state([i.id])
            i.alert_threshold = v
            self.session.flush()
            out = _intrant_d(i)
            self._audit("FabIntrant", "UPDATE_THRESHOLD", i.id, old=old, new=out)
            # etat « avant » = ancien seuil ; apres = nouveau seuil, meme stock
            self._notify_crossings({i.id: (before[i.id][0], Decimal(old["alert_threshold"] or 0))})
            return out
        return self._tx(run)

    def list_intrants(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        out = []
        counts = self.repo.delivered_purchase_counts()
        for i, stock in self.repo.list_intrants_with_stock(include_inactive):
            d = _intrant_d(i)
            d["stock"] = stock
            d["below_threshold"] = stock < Decimal(i.alert_threshold or 0)
            d["purchases_count"] = counts.get(i.id, 0)
            d["editable"] = d["purchases_count"] == 0
            out.append(d)
        return out

    # ================= achats =================
    def _clean_purchase(self, data: Dict[str, Any], partial: bool) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for f, label, n in (("supplier", "Le fournisseur", 150), ("delivery_ref", "La reference", 100)):
            if not partial or f in data:
                out[f] = _text(data.get(f), label, n)
        if not partial or "purchase_date" in data:
            d = data.get("purchase_date")
            if not isinstance(d, date) or isinstance(d, datetime):
                raise ValueError("La date d'achat est obligatoire.")
            out["purchase_date"] = d
        if not partial or "quantity" in data:
            out["quantity"] = _decimal(data.get("quantity"), "La quantite", QTY_STEP, MAX_QTY, positive=True)
        if not partial or "unit_cost" in data:
            out["unit_cost"] = _decimal(data.get("unit_cost"), "Le cout unitaire", COST_STEP, MAX_COST,
                                        positive=False)
        return out

    def create_purchase(self, data: Dict[str, Any]) -> Dict[str, Any]:
        def run():
            clean = self._clean_purchase(data, partial=False)
            intrant = self.repo.get_intrant(data.get("intrant_id"), lock=True)
            if intrant is None:
                raise FabricationNotFoundError("Intrant introuvable.")
            if not intrant.is_active:
                raise FabricationConflictError("Cet intrant est desactive.")
            p = self.repo.add(FabIntrantPurchase(
                intrant_id=intrant.id, remaining_qty=clean["quantity"], status="actif",
                created_by=self.user.user_id, **clean))
            out = _purchase_d(p, intrant.name)
            self._audit("FabIntrantPurchase", "CREATE", p.id, new=out)
            return out
        return self._tx(run)

    def _locked_editable_purchase(self, purchase_id: int) -> FabIntrantPurchase:
        p = self.repo.lock_purchase(purchase_id)
        if p is None:
            raise FabricationNotFoundError("Achat introuvable.")
        if p.status != "actif":
            raise FabricationConflictError("Cet achat est annule.")
        if self.repo.has_live_consumption(p.id) or p.remaining_qty != p.quantity:
            raise FabricationConflictError("Cet achat a deja ete consomme par un lot.")
        return p

    def update_purchase(self, purchase_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Correction d'un achat non consomme ; le restant suit la quantite."""
        def run():
            p = self._locked_editable_purchase(purchase_id)
            clean = self._clean_purchase({k: v for k, v in data.items() if k in PURCHASE_FIELDS},
                                         partial=True)
            if not clean:
                raise ValueError("Aucune modification fournie.")
            name = self.repo.intrant_names([p.intrant_id]).get(p.intrant_id)
            old = _purchase_d(p, name)
            before = self._stock_state([p.intrant_id])
            for k, v in clean.items():
                setattr(p, k, v)
            if "quantity" in clean:
                p.remaining_qty = clean["quantity"]
            self.session.flush()
            out = _purchase_d(p, name)
            self._audit("FabIntrantPurchase", "UPDATE", p.id, old=old, new=out)
            self._notify_crossings(before)
            return out
        return self._tx(run)

    def cancel_purchase(self, purchase_id: int, reason) -> Dict[str, Any]:
        def run():
            r = _text(reason, "Le motif", 500, required=True)
            p = self._locked_editable_purchase(purchase_id)
            name = self.repo.intrant_names([p.intrant_id]).get(p.intrant_id)
            old = _purchase_d(p, name)
            before = self._stock_state([p.intrant_id])
            p.status = "annule"
            p.cancel_reason = r
            p.remaining_qty = Decimal(0)  # un achat annule n'a plus rien de disponible (la quantite d'origine reste lisible)
            self.session.flush()
            out = _purchase_d(p, name)
            self._audit("FabIntrantPurchase", "CANCEL", p.id, old=old, new=out)
            self._notify_crossings(before)
            return out
        return self._tx(run)

    def list_purchases(self, intrant_id: Optional[int] = None, date_from: Optional[date] = None,
                       date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        _check_range(date_from, date_to)
        rows = self.repo.purchases_for(intrant_id, date_from, date_to)
        names = self.repo.intrant_names(p.intrant_id for p in rows)
        active = self.repo.intrant_active_map(p.intrant_id for p in rows)
        return [_purchase_d(p, names.get(p.intrant_id), active.get(p.intrant_id)) for p in rows]

    # ================= lots =================
    def _batch_d(self, b: FabBatch, with_detail: bool = False) -> Dict[str, Any]:
        out = {c: getattr(b, c) for c in BATCH_COLUMNS}
        if with_detail:
            cons, pairs = [], []
            for c, p, i in self.repo.provenance(b.id):
                unit_cost = c.unit_cost_snapshot if c.unit_cost_snapshot is not None else p.unit_cost
                line = (Decimal(c.quantity) * Decimal(unit_cost)).quantize(COST_STEP)
                pairs.append((Decimal(c.quantity), Decimal(unit_cost)))
                cons.append({"id": c.id, "purchase_id": p.id, "intrant_id": i.id, "intrant_name": i.name,
                             "unit": i.unit, "is_container": i.is_container, "supplier": p.supplier,
                             "delivery_ref": p.delivery_ref, "purchase_date": p.purchase_date,
                             "quantity": c.quantity, "unit_cost": unit_cost,
                             "unit_cost_snapshot": c.unit_cost_snapshot, "line_cost": line,
                             "restored_at": c.restored_at})
            out["consumptions"] = cons
            out["cost_so_far"] = compute_cost(pairs, 0)[0]
            out["product_name"] = self.repo.product_name(b.product_id)
            out["production_lot_number"] = self.repo.production_lot_number(b.production_lot_id)
            outputs = self.repo.outputs_of(b.id)
            names = self.repo.user_names(o.declared_by for o in outputs)
            out["outputs"] = [_output_d(o, names) for o in outputs]
            out["qty_outputs"] = sum(o.quantity for o in outputs if o.status == "active")
            out["qty_shipped"] = (b.qty_good or 0) - out["qty_outputs"]
        return out

    def _locked_batch(self, batch_id: int) -> FabBatch:
        b = self.repo.get_batch(batch_id, lock=True)
        if b is None:
            raise FabricationNotFoundError("Lot introuvable.")
        return b

    def _move(self, b: FabBatch, target: str) -> None:
        """Valide le changement d'etat par TRANSITIONS (409 sinon)."""
        if target not in TRANSITIONS.get(b.status, set()):
            raise FabricationConflictError(f"Transition impossible : {b.status} vers {target}.")
        b.status = target

    def _clean_items(self, items) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            raise ValueError("Consommations invalides.")
        out, seen = [], set()
        for it in items:
            if not isinstance(it, dict):
                raise ValueError("Consommation invalide.")
            pid = it.get("purchase_id")
            if not isinstance(pid, int) or isinstance(pid, bool):
                raise ValueError("Achat invalide.")
            if pid in seen:
                raise ValueError("Un achat ne peut figurer qu'une fois dans un lot.")
            seen.add(pid)
            out.append({"purchase_id": pid,
                        "quantity": _decimal(it.get("quantity"), "La quantite consommee", QTY_STEP,
                                             MAX_QTY, positive=True)})
        return out

    def _replace_consumptions(self, b: FabBatch, items) -> None:
        clean = self._clean_items(items)
        for it in clean:
            p = self.repo.get_purchase(it["purchase_id"])
            if p is None:
                raise FabricationNotFoundError("Achat introuvable.")
            if p.status != "actif":
                raise FabricationConflictError("Cet achat est annule.")
            if not self.repo.intrant_active_map([p.intrant_id]).get(p.intrant_id):
                raise FabricationConflictError("Un intrant de cet achat est desactive.")
        self.repo.delete_consumptions(b.id)
        for it in clean:
            self.repo.add(FabConsumption(batch_id=b.id, purchase_id=it["purchase_id"],
                                         quantity=it["quantity"], unit_cost_snapshot=None,
                                         restored_at=None))

    def _check_product(self, product_id) -> None:
        if not self.repo.product_exists(product_id):
            raise FabricationNotFoundError("Produit introuvable.")
        if not self.repo.product_fabricable(product_id):
            raise ValueError("Produit non fabricable.")

    def create_batch(self, product_id, production_date, producer_name=None) -> Dict[str, Any]:
        def run():
            if not isinstance(production_date, date) or isinstance(production_date, datetime):
                raise ValueError("La date de production est obligatoire.")
            self._check_product(product_id)
            year = date.today().year
            number = next_batch_number(self.repo.last_batch_number(year), year)
            b = self.repo.add(FabBatch(batch_number=number, product_id=product_id, status="brouillon",
                                       production_date=production_date,
                                       producer_name=_text(producer_name, "Le producteur", 150),
                                       created_by=self.user.user_id))
            out = self._batch_d(b)
            self._audit("FabBatch", "CREATE", b.id, new=out)
            return out
        return self._tx(run)

    def update_batch(self, batch_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Edition d'un lot brouillon (en-tete et/ou remplacement des consommations)."""
        def run():
            b = self._locked_batch(batch_id)
            if b.status != "brouillon":
                raise FabricationConflictError("Seul un lot brouillon est modifiable.")
            if not data:
                raise ValueError("Aucune modification fournie.")
            old = self._batch_d(b, with_detail=True)
            if "product_id" in data:
                self._check_product(data["product_id"])
                b.product_id = data["product_id"]
            if "production_date" in data:
                d = data["production_date"]
                if not isinstance(d, date) or isinstance(d, datetime):
                    raise ValueError("La date de production est obligatoire.")
                b.production_date = d
            if "producer_name" in data:
                b.producer_name = _text(data["producer_name"], "Le producteur", 150)
            if "consumptions" in data:
                self._replace_consumptions(b, data["consumptions"])
            self.session.flush()
            out = self._batch_d(b, with_detail=True)
            self._audit("FabBatch", "UPDATE", b.id, old=old, new=out)
            return out
        return self._tx(run)

    def replace_consumptions(self, batch_id: int, items) -> Dict[str, Any]:
        """Remplace les consommations d'un lot brouillon."""
        return self.update_batch(batch_id, {"consumptions": items})

    def start_batch(self, batch_id: int) -> Dict[str, Any]:
        """Reservation du stock : verrou FOR UPDATE de chaque achat (ids croissants), puis decrement."""
        def run():
            b = self._locked_batch(batch_id)
            old = self._batch_d(b)
            self._move(b, "en_production")
            cons = self.repo.consumptions_of(b.id)
            if not cons:
                raise ValueError("Le lot n'a aucune consommation.")
            locked = {}
            for pid in sorted({c.purchase_id for c in cons}):
                p = self.repo.lock_purchase(pid)
                if p is None:
                    raise FabricationNotFoundError("Achat introuvable.")
                locked[pid] = p
            containers = []
            for c in cons:
                p = locked[c.purchase_id]
                if p.status != "actif":
                    raise FabricationConflictError("Un achat consomme est annule.")
                intrant = self.repo.get_intrant(p.intrant_id, lock=True)
                if not intrant.is_active:
                    raise FabricationConflictError("Un intrant consomme est desactive.")
                if intrant.is_container:
                    containers.append(c)
            if len(containers) != 1:
                raise ValueError("Le lot doit avoir exactement une consommation de contenant.")
            qty = Decimal(containers[0].quantity)
            if qty != qty.to_integral_value():
                raise ValueError("La quantite de contenant doit etre un nombre entier.")
            before = self._stock_state(locked[c.purchase_id].intrant_id for c in cons)
            for c in cons:
                p = locked[c.purchase_id]
                if Decimal(c.quantity) > Decimal(p.remaining_qty):
                    raise ValueError("Quantite consommee superieure au restant de l'achat.")
                p.remaining_qty = Decimal(p.remaining_qty) - Decimal(c.quantity)
                c.unit_cost_snapshot = p.unit_cost
                c.restored_at = None
            b.expected_qty = int(qty)
            b.started_at = datetime.utcnow()
            self.session.flush()
            out = self._batch_d(b, with_detail=True)
            self._audit("FabBatch", "START", b.id, old=old, new=out)
            self._notify_crossings(before)
            return out
        return self._tx(run)

    def finish_batch(self, batch_id: int, qty_good, qty_damaged=0, qty_rejected=0,
                     liquid_lost=0) -> Dict[str, Any]:
        def run():
            counts = {}
            for k, v in (("qty_good", qty_good), ("qty_damaged", qty_damaged),
                         ("qty_rejected", qty_rejected)):
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    raise ValueError(f"{k} invalide.")
                counts[k] = v
            lost = _decimal(liquid_lost, "Le liquide perdu", QTY_STEP, MAX_QTY, positive=False)
            b = self._locked_batch(batch_id)
            old = self._batch_d(b)
            self._move(b, "termine")
            settings = self.repo.get_settings()
            tol = Decimal(settings.tolerance_pct) if settings else Decimal("2.00")
            try:
                bilan = compute_bilan(b.expected_qty or 0, counts["qty_good"], counts["qty_damaged"],
                                      counts["qty_rejected"], tol)
            except ValueError:
                raise ValueError("Le total trouve depasse l'attendu.")
            for k, v in counts.items():
                setattr(b, k, v)
            b.liquid_lost = lost
            b.found_qty = bilan["found"]
            b.missing_qty = bilan["missing"]
            b.missing_pct = bilan["missing_pct"]
            b.out_of_tolerance = bilan["out_of_tolerance"]
            pairs = [(Decimal(c.quantity), Decimal(c.unit_cost_snapshot or 0))
                     for c in self.repo.consumptions_of(b.id)]
            b.total_cost, b.unit_cost = compute_cost(pairs, counts["qty_good"])
            b.finished_at = datetime.utcnow()
            self.session.flush()
            out = self._batch_d(b, with_detail=True)
            self._audit("FabBatch", "FINISH", b.id, old=old, new=out)
            return out
        return self._tx(run)

    def reopen_batch(self, batch_id: int) -> Dict[str, Any]:
        def run():
            b = self._locked_batch(batch_id)
            if b.status != "termine":
                raise FabricationConflictError("Seul un lot termine peut etre rouvert.")
            if self.repo.active_output_total(b.id) > 0:
                raise FabricationConflictError("Annulez d'abord les sorties declarees.")
            old = self._batch_d(b)
            self._move(b, "en_production")
            b.finished_at = None
            # le bilan de la fin de production est a refaire : ni comptes, ni ecart, ni drapeau hors tolerance
            b.qty_good = b.qty_damaged = b.qty_rejected = 0
            b.liquid_lost = Decimal(0)
            b.found_qty = b.missing_qty = b.missing_pct = None
            b.out_of_tolerance = False
            b.total_cost = b.unit_cost = None
            self.session.flush()
            out = self._batch_d(b, with_detail=True)
            self._audit("FabBatch", "REOPEN", b.id, old=old, new=out)
            return out
        return self._tx(run)

    def cancel_batch(self, batch_id: int, reason) -> Dict[str, Any]:
        """Annulation ; un lot reserve (en_production, termine) rend ses quantites aux achats."""
        def run():
            r = _text(reason, "Le motif", 500, required=True)
            b = self._locked_batch(batch_id)
            # comme reopen_batch : un lot termine qui a des sorties actives ne s'annule pas en bloc
            if b.status == "termine" and self.repo.active_output_total(b.id) > 0:
                raise FabricationConflictError("Annulez d'abord les sorties declarees.")
            old = self._batch_d(b, with_detail=True)
            reserved = b.status in ("en_production", "termine")
            self._move(b, "annule")
            now = datetime.utcnow()
            cons = [c for c in self.repo.consumptions_of(b.id) if c.restored_at is None]
            locked = {pid: self.repo.lock_purchase(pid) for pid in sorted({c.purchase_id for c in cons})}
            for c in cons:
                if reserved:
                    p = locked[c.purchase_id]
                    p.remaining_qty = Decimal(p.remaining_qty) + Decimal(c.quantity)
                c.restored_at = now
            b.cancel_reason = r
            self.session.flush()
            out = self._batch_d(b, with_detail=True)
            self._audit("FabBatch", "CANCEL", b.id, old=old, new=out)
            return out
        return self._tx(run)

    def ship_batch(self, batch_id: int, delivery_date, expiry_date=None,
                   justification=None) -> Dict[str, Any]:
        """Expedition d'un lot termine : bilan et cout figes avec la tolerance globale du moment,
        creation du lot de production (circuit de reception existant), le tout en une transaction."""
        def run():
            for d, label, req in ((delivery_date, "La date de livraison", True),
                                  (expiry_date, "La date de peremption", False)):
                if d is None and not req:
                    continue
                if not isinstance(d, date) or isinstance(d, datetime):
                    raise ValueError(f"{label} est obligatoire." if d is None else f"{label} invalide.")
            just = _text(justification, "La justification", 5000)
            b = self._locked_batch(batch_id)
            old = self._batch_d(b)
            self._move(b, "expedie")
            if not b.qty_good or b.qty_good <= 0:
                raise ValueError("Aucune bouteille bonne : rien a expedier.")
            # somme active lue sous le verrou du lot : les sorties sont figees une fois expedie
            shipped = b.qty_good - self.repo.active_output_total(b.id)
            if shipped <= 0:
                raise ValueError("Toutes les bouteilles sont sorties : rien a expedier.")
            settings = self.repo.get_settings()
            tol = Decimal(settings.tolerance_pct) if settings else Decimal("2.00")
            try:
                bilan = compute_bilan(b.expected_qty or 0, b.qty_good, b.qty_damaged or 0,
                                      b.qty_rejected or 0, tol)
            except ValueError:
                raise ValueError("Bilan du lot incoherent.")
            if bilan["out_of_tolerance"] and just is None:
                raise FabricationJustificationRequired("Manque hors tolerance : une justification est obligatoire.")
            pairs = [(Decimal(c.quantity), Decimal(c.unit_cost_snapshot or 0))
                     for c in self.repo.consumptions_of(b.id) if c.restored_at is None]
            b.expected_qty = bilan["expected"]
            b.found_qty = bilan["found"]
            b.missing_qty = bilan["missing"]
            b.missing_pct = bilan["missing_pct"]
            b.tolerance_applied = tol
            b.out_of_tolerance = bilan["out_of_tolerance"]
            b.justification = just
            b.total_cost, b.unit_cost = compute_cost(pairs, b.qty_good)
            b.delivery_date = delivery_date
            b.expiry_date = expiry_date
            lot = self.repo.create_production_lot(
                product_id=b.product_id, quantity_produced=shipped,
                production_date=b.production_date, delivery_date=delivery_date,
                expiry_date=expiry_date,
                producer=(getattr(self.user, "full_name", None) or getattr(self.user, "username", None)),
                created_by=self.user.user_id)
            b.production_lot_id = lot.id
            b.expedited_at = datetime.utcnow()
            b.expedited_by = self.user.user_id
            self.session.flush()
            self._audit("ProductionLot", "CREATE", lot.id, new={
                "id": lot.id, "lot_number": lot.lot_number, "product_id": lot.product_id,
                "quantity_produced": lot.quantity_produced, "status": lot.status,
                "fab_batch_id": b.id})
            out = self._batch_d(b, with_detail=True)
            self._audit("FabBatch", "SHIP", b.id, old=old, new=out)
            return out
        return self._tx(run)

    # ================= reglages =================
    @staticmethod
    def _settings_d(s) -> Dict[str, Any]:
        if s is None:
            return {"tolerance_pct": Decimal("2.00"), "stale_days": 7, "updated_by": None,
                    "updated_at": None}
        return {"tolerance_pct": s.tolerance_pct, "stale_days": s.stale_days,
                "updated_by": s.updated_by, "updated_at": s.updated_at}

    def get_settings(self) -> Dict[str, Any]:
        return self._settings_d(self.repo.get_settings())

    def update_settings(self, tolerance_pct, stale_days) -> Dict[str, Any]:
        """Tolerance globale et delai d'alerte (admin, garde par l'endpoint)."""
        def run():
            tol = _decimal(tolerance_pct, "La tolerance", COST_STEP, Decimal("100"), positive=False)
            if not isinstance(stale_days, int) or isinstance(stale_days, bool) or stale_days <= 0:
                raise ValueError("Le delai doit etre un entier superieur a zero.")
            s = self.repo.get_settings(lock=True)
            old = self._settings_d(s) if s is not None else None
            if s is None:
                s = self.repo.add(FabSettings(id=1, tolerance_pct=tol, stale_days=stale_days))
            s.tolerance_pct = tol
            s.stale_days = stale_days
            s.updated_by = self.user.user_id
            s.updated_at = datetime.utcnow()
            self.session.flush()
            out = self._settings_d(s)
            self._audit("FabSettings", "UPDATE", 1, old=old, new=out)
            return out
        return self._tx(run)

    def get_batch(self, batch_id: int) -> Dict[str, Any]:
        b = self.repo.get_batch(batch_id)
        if b is None:
            raise FabricationNotFoundError("Lot introuvable.")
        return self._batch_d(b, with_detail=True)

    def list_products(self) -> List[Dict[str, Any]]:
        """Liste minimale {id, name} des produits finis (aucun cout ni prix)."""
        return [{"id": pid, "name": name} for pid, name in self.repo.list_products()]

    def list_batches(self, status: Optional[str] = None, date_from: Optional[date] = None,
                     date_to: Optional[date] = None) -> List[Dict[str, Any]]:
        _check_range(date_from, date_to)
        batches = self.repo.list_batches(status, date_from, date_to)
        names = self.repo.product_names(b.product_id for b in batches)
        totals = self.repo.active_output_totals(b.id for b in batches)
        out = [self._batch_d(b) for b in batches]
        for d in out:
            d["product_name"] = names.get(d["product_id"])
            d["qty_outputs"] = totals.get(d["id"], 0)
            d["qty_shipped"] = (d["qty_good"] or 0) - d["qty_outputs"]
        return out

    # ================= sorties declarees (echantillons, autres) =================
    def declare_output(self, batch_id: int, reason, quantity, note=None) -> Dict[str, Any]:
        """Sortie declaree d'un lot termine ; verrou du lot avant la lecture de la somme active
        (deux declarations simultanees sont serialisees)."""
        def run():
            b = self._locked_batch(batch_id)
            if b.status != "termine":
                raise FabricationConflictError("Une sortie ne se declare que sur un lot termine.")
            available = (b.qty_good or 0) - self.repo.active_output_total(b.id)
            try:
                r, q, n = validate_output(reason, quantity, note, available)
            except OutputExceedsAvailable as e:
                raise FabricationConflictError(str(e))
            o = self.repo.add(FabBatchOutput(batch_id=b.id, reason=r, quantity=q, note=n, status="active",
                                             declared_by=self.user.user_id))
            out = _output_d(o, self.repo.user_names([o.declared_by]))
            self._audit("FabBatchOutput", "CREATE", o.id, new=out)
            return out
        return self._tx(run)

    def cancel_output(self, batch_id: int, output_id: int, reason) -> Dict[str, Any]:
        def run():
            r = _text(reason, "Le motif", 500, required=True)
            b = self._locked_batch(batch_id)
            o = self.repo.get_output(output_id, lock=True)
            if o is None or o.batch_id != b.id:
                raise FabricationNotFoundError("Sortie introuvable.")
            if b.status != "termine":
                raise FabricationConflictError("Une sortie ne s'annule que sur un lot termine.")
            if o.status != "active":
                raise FabricationConflictError("Cette sortie est deja annulee.")
            names = self.repo.user_names([o.declared_by])
            old = _output_d(o, names)
            uid, now = self.user.user_id, datetime.utcnow()
            with self.session.no_autoflush:
                o.cancelled_by, o.cancelled_at, o.cancel_reason = uid, now, r
                o.status = "annulee"
            self.session.flush()
            out = _output_d(o, names)
            self._audit("FabBatchOutput", "CANCEL", o.id, old=old, new=out)
            return out
        return self._tx(run)

    def list_outputs(self, date_from: Optional[date] = None, date_to: Optional[date] = None,
                     reason: Optional[str] = None) -> List[Dict[str, Any]]:
        _check_range(date_from, date_to)
        if reason is not None and reason not in OUTPUT_REASONS:
            raise ValueError("Motif de sortie invalide : echantillon ou autre.")
        rows = self.repo.recent_outputs(date_from, date_to, reason, limit=200)
        products = self.repo.product_names(pid for _, _, pid in rows)
        names = self.repo.user_names(o.declared_by for o, _, _ in rows)
        out = []
        for o, number, pid in rows:
            d = _output_d(o, names)
            d.update({"batch_number": number, "product_id": pid, "product_name": products.get(pid)})
            out.append(d)
        return out

    # ================= anomalies, resume, cout, tracabilite (lecture seule) =================
    def list_anomalies(self) -> List[Dict[str, Any]]:
        """Anomalies courantes ; chaque element {kind, ref, detail}. Reutilisable par le controle quotidien."""
        out: List[Dict[str, Any]] = []
        for b in self.repo.batches_out_of_tolerance():
            out.append({"kind": "hors_tolerance", "ref": b.batch_number, "detail": {
                "batch_id": b.id, "status": b.status, "missing_qty": b.missing_qty,
                "missing_pct": b.missing_pct, "tolerance_applied": b.tolerance_applied,
                "justification": b.justification}})
        for i, stock in self.repo.list_intrants_with_stock():
            threshold = Decimal(i.alert_threshold or 0)
            if stock < threshold:
                out.append({"kind": "intrant_sous_seuil", "ref": i.name, "detail": {
                    "intrant_id": i.id, "stock": stock, "alert_threshold": threshold, "unit": i.unit}})
        settings = self.repo.get_settings()
        stale_days = settings.stale_days if settings else 7
        now = datetime.utcnow()
        for b in self.repo.stale_batches(stale_days, now):
            out.append({"kind": "lot_trop_long", "ref": b.batch_number, "detail": {
                "batch_id": b.id, "status": b.status, "started_at": b.started_at,
                "days": (now - b.started_at).days, "stale_days": stale_days}})
        for b, shipped, received in self.repo.shipped_vs_received():
            if received != shipped:
                out.append({"kind": "ecart_expedie_recu", "ref": b.batch_number, "detail": {
                    "batch_id": b.id, "production_lot_id": b.production_lot_id,
                    "qty_good": b.qty_good, "expedie": shipped, "received_good": received,
                    "gap": shipped - received}})
        return out

    def summary(self) -> Dict[str, Any]:
        counts = {s: 0 for s in ("brouillon", "en_production", "termine", "expedie", "annule")}
        counts.update(self.repo.counts_by_status())
        return {"recent_batches": [self._batch_d(b) for b in self.repo.recent_batches()],
                "counts_by_status": counts, "anomalies_count": len(self.list_anomalies())}

    def cost_by_product(self, product_id: int) -> Dict[str, Any]:
        costs = self.repo.shipped_unit_costs(product_id)
        if not costs:
            return {"last_unit_cost": None, "average_unit_cost": None, "batches": 0}
        avg = (sum(costs, Decimal(0)) / len(costs)).quantize(COST_STEP)
        return {"last_unit_cost": costs[-1], "average_unit_cost": avg, "batches": len(costs)}

    def trace_production_lot(self, production_lot_id: int) -> Optional[Dict[str, Any]]:
        """Lot de Fabrication a l'origine d'un lot de production, avec consommations et achats ; None sinon."""
        b = self.repo.batch_by_production_lot(production_lot_id)
        if b is None:
            return None
        detail = self._batch_d(b, with_detail=True)
        return {"production_lot_id": production_lot_id, "batch": detail,
                "consumptions": detail["consumptions"]}
