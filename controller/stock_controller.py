# controller/stock_controller.py
"""Lots de fabrication et receptions controlees (regle des deux comptes).

Le controleur possede la transaction (commit ici). Les roles sont verifies par
les endpoints ; ici : etat de l'operation et validateur != auteur.
Erreurs : ValueError -> 422, PermissionError -> 403, StockConflictError -> 409.
"""
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from models.stock_reception import (
    ProductionLot, StockAdjustmentRequest, StockIncident, StockReceipt, StockReceiptLine,
)
from repositories.audit_repo import AuditRepository
from repositories.notification_repo import NotificationRepository
from repositories.stock_repo import StockConflictError, StockNotFoundError, StockRepository

__all__ = ["StockController", "StockConflictError", "StockNotFoundError"]

MAX_QTY = 1_000_000  # borne haute des quantites (evite DataError/500 sur un entier geant)
MAX_PER_PAGE = 200

QTY_FIELDS = ("qty_good", "qty_damaged", "qty_lost", "qty_defective")
CANCEL_REASON = "annulé par l'auteur"
CHECKER_ROLES = ("StockController", "admin")
INCIDENT_KINDS = ("endommage", "perdu", "defectueux")
ADJUSTMENT_KINDS = ("reapprovisionnement", "correction")


def _lot_dict(lot: ProductionLot) -> Dict[str, Any]:
    return {
        "id": lot.id, "lot_number": lot.lot_number, "product_id": lot.product_id,
        "product_name": lot.product.drug_name if lot.product else None,
        "quantity_produced": lot.quantity_produced, "production_date": lot.production_date,
        "delivery_date": lot.delivery_date, "expiry_date": lot.expiry_date, "producer": lot.producer,
        "status": lot.status, "created_by": lot.created_by, "created_at": lot.created_at,
    }


def _line_dict(l: StockReceiptLine) -> Dict[str, Any]:
    return {
        "id": l.id, "product_id": l.product_id,
        "product_name": l.product.drug_name if l.product else None,
        "qty_expected": l.qty_expected, **{f: getattr(l, f) for f in QTY_FIELDS},
        "lot_number": l.lot_number, "expiry_date": l.expiry_date,
    }


def _receipt_dict(r: StockReceipt) -> Dict[str, Any]:
    return {
        "id": r.id, "receipt_number": r.receipt_number, "origin": r.origin,
        "production_lot_id": r.production_lot_id, "supplier": r.supplier, "delivery_ref": r.delivery_ref,
        "received_date": r.received_date, "status": r.status, "created_by": r.created_by,
        "created_at": r.created_at, "controlled_by": r.controlled_by, "controlled_at": r.controlled_at,
        "reject_reason": r.reject_reason,
        "lines": [_line_dict(l) for l in sorted(r.lines, key=lambda x: x.id)],
    }


def _incident_dict(i: StockIncident) -> Dict[str, Any]:
    return {
        "id": i.id, "product_id": i.product_id,
        "product_name": i.product.drug_name if i.product else None,
        "kind": i.kind, "quantity": i.quantity, "reason": i.reason, "incident_date": i.incident_date,
        "status": i.status, "created_by": i.created_by, "created_at": i.created_at,
        "controlled_by": i.controlled_by, "controlled_at": i.controlled_at, "reject_reason": i.reject_reason,
    }


def _adjustment_dict(a: StockAdjustmentRequest) -> Dict[str, Any]:
    return {
        "id": a.id, "product_id": a.product_id,
        "product_name": a.product.drug_name if a.product else None,
        "kind": a.kind, "quantity": a.quantity, "reason": a.reason, "status": a.status,
        "requested_by": a.requested_by, "requested_at": a.requested_at,
        "decided_by": a.decided_by, "decided_at": a.decided_at, "decision_note": a.decision_note,
        "stock_before": a.stock_before, "stock_after": a.stock_after,
        "current_quantity": a.product.quantity if a.product else None,
    }


def _int(v, name, default=0, limit=MAX_QTY) -> int:
    if v is None:
        return default
    if isinstance(v, bool):
        raise ValueError(f"{name} invalide.")
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} invalide.")
    if n != v and not isinstance(v, str):
        raise ValueError(f"{name} doit être un entier.")
    if limit is not None and abs(n) > limit:
        raise ValueError(f"{name} dépasse la limite autorisée ({limit}).")
    return n


def _date(v, name, required=False) -> Optional[date]:
    """Accepte date ou chaine ISO AAAA-MM-JJ ; tout le reste -> ValueError."""
    if v is None or v == "":
        if required:
            raise ValueError(f"{name} est obligatoire.")
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip()):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            pass
    raise ValueError(f"{name} invalide (format attendu AAAA-MM-JJ).")


def _check_line_quantities(qtys: Dict[str, int], expected: Optional[int]):
    for f, v in qtys.items():
        if v < 0:
            raise ValueError(f"{f} ne peut pas être négatif.")
    total = sum(qtys.values())
    if total <= 0:
        raise ValueError("Chaque ligne doit porter au moins une quantité.")
    if expected is not None and total > expected:
        raise ValueError(f"La somme des quantités ({total}) dépasse la quantité attendue ({expected}).")


class StockController:
    def __init__(self, repo: StockRepository, notification_repo: NotificationRepository,
                 audit_repo: AuditRepository, current_user):
        if repo is None or notification_repo is None or audit_repo is None:
            raise TypeError("StockController exige repo, notification_repo et audit_repo.")
        self.repo = repo
        self.notification_repo = notification_repo
        self.audit_repo = audit_repo
        self.user = current_user
        self.session = repo.session

    # ---------------- lots ----------------
    def create_lot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        product_id = _int(data.get("product_id"), "product_id", None, limit=None)
        if product_id is None or self.repo.get_product(product_id) is None:
            raise ValueError("Produit introuvable.")
        qty = _int(data.get("quantity_produced"), "quantity_produced", 0)
        if qty <= 0:
            raise ValueError("La quantité produite doit être strictement positive.")
        production_date = _date(data.get("production_date"), "La date de production", required=True)
        delivery_date = _date(data.get("delivery_date"), "La date de livraison")
        expiry_date = _date(data.get("expiry_date"), "La date de péremption")
        try:
            lot = self.repo.add(ProductionLot(
                lot_number=self.repo.next_number("LOT", date.today()),
                product_id=product_id, quantity_produced=qty, production_date=production_date,
                delivery_date=delivery_date, expiry_date=expiry_date,
                producer=(data.get("producer") or None), status="produit", created_by=self.user.user_id))
            self.audit_repo.log_user_action(current_user=self.user, resource_type="ProductionLot",
                                            action_performed="CREATE", resource_id=lot.id,
                                            new_values=_lot_dict(lot))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return _lot_dict(lot)

    def list_lots(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return [_lot_dict(l) for l in self.repo.list_lots(status)]

    def mark_lot_delivered(self, lot_id: int, delivery_date: Optional[date] = None) -> Dict[str, Any]:
        try:
            lot = self.repo.get_lot(lot_id, lock=True)
            if lot is None:
                raise StockNotFoundError("Lot introuvable.")
            if lot.status != "produit":
                raise StockConflictError(f"Le lot est déjà « {lot.status} ».")
            old = _lot_dict(lot)
            lot.status = "livre"
            lot.delivery_date = _date(delivery_date, "La date de livraison") or date.today()
            self.session.flush()
            self.audit_repo.log_user_action(current_user=self.user, resource_type="ProductionLot",
                                            action_performed="DELIVER", resource_id=lot.id,
                                            old_values=old, new_values=_lot_dict(lot))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return _lot_dict(lot)

    def cancel_lot(self, lot_id: int) -> Dict[str, Any]:
        try:
            lot = self.repo.get_lot(lot_id, lock=True)
            if lot is None:
                raise StockNotFoundError("Lot introuvable.")
            if not self._is_admin() and lot.created_by != self.user.user_id:
                raise PermissionError("Seul le créateur du lot ou un administrateur peut l'annuler.")
            if lot.status not in ("produit", "livre"):
                raise StockConflictError(f"Un lot « {lot.status} » ne peut pas être annulé.")
            if self.repo.lot_has_active_receipt(lot.id):
                raise StockConflictError("Une réception est liée à ce lot : annulation impossible.")
            old = _lot_dict(lot)
            lot.status = "annule"
            self.session.flush()
            self.audit_repo.log_user_action(current_user=self.user, resource_type="ProductionLot",
                                            action_performed="CANCEL", resource_id=lot.id,
                                            old_values=old, new_values=_lot_dict(lot))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return _lot_dict(lot)

    # ---------------- receptions ----------------
    def create_receipt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            origin = data.get("origin")
            if origin not in ("fabrication", "fournisseur"):
                raise ValueError("Origine invalide (fabrication ou fournisseur).")
            received_date = _date(data.get("received_date"), "La date de réception", required=True)
            raw_lines = data.get("lines") or []
            if not raw_lines:
                raise ValueError("Le bon doit comporter au moins une ligne.")

            lot = None
            if origin == "fabrication":
                lot_id = data.get("production_lot_id")
                lot = self.repo.get_lot(lot_id, lock=True) if lot_id is not None else None
                if lot is None:
                    raise ValueError("Lot de fabrication introuvable.")
                if lot.status != "livre":
                    raise ValueError(f"Le lot doit être « livre » (statut actuel : {lot.status}).")
                # le verrou du lot (ci-dessus) serialise les creations concurrentes
                if self.repo.lot_has_active_receipt(lot.id):
                    raise ValueError("Ce lot est déjà lié à une réception non rejetée.")
                if len(raw_lines) != 1:
                    raise ValueError("Une réception de fabrication comporte une seule ligne.")

            lines = []
            for raw in raw_lines:
                product_id = raw.get("product_id")
                expected = raw.get("qty_expected")
                lot_number = raw.get("lot_number")
                expiry = _date(raw.get("expiry_date"), "La date de péremption")
                if lot is not None:
                    if product_id is not None and int(product_id) != lot.product_id:
                        raise ValueError("Le produit de la ligne ne correspond pas au lot.")
                    product_id = lot.product_id
                    expected = lot.quantity_produced if expected is None else expected
                    lot_number = lot_number or lot.lot_number
                    expiry = expiry or lot.expiry_date
                product_id = _int(product_id, "product_id", None, limit=None)
                if product_id is None or self.repo.get_product(product_id) is None:
                    raise ValueError("Produit introuvable.")
                expected = _int(expected, "qty_expected", None)
                if expected is not None and expected < 0:
                    raise ValueError("qty_expected ne peut pas être négatif.")
                qtys = {f: _int(raw.get(f), f) for f in QTY_FIELDS}
                _check_line_quantities(qtys, expected)
                lines.append(StockReceiptLine(product_id=product_id, qty_expected=expected,
                                              lot_number=lot_number or None, expiry_date=expiry, **qtys))

            receipt = self.repo.add(StockReceipt(
                receipt_number=self.repo.next_number("REC", date.today()),
                origin=origin, production_lot_id=lot.id if lot else None,
                supplier=(data.get("supplier") or None) if origin == "fournisseur" else None,
                delivery_ref=data.get("delivery_ref") or None, received_date=received_date,
                status="a_controler", created_by=self.user.user_id, lines=lines))
            out = _receipt_dict(receipt)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockReceipt",
                                            action_performed="CREATE", resource_id=receipt.id, new_values=out)
            payload = {"receipt_id": receipt.id, "receipt_number": receipt.receipt_number,
                       "created_by_name": self.user.full_name}
            for uid in self.repo.checker_user_ids(exclude_user_id=self.user.user_id):
                self.notification_repo.create(uid, "stock_to_check", payload)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def list_receipts(self, status: Optional[str] = None, mine_only: bool = False) -> List[Dict[str, Any]]:
        return [_receipt_dict(r) for r in
                self.repo.list_receipts(status, self.user.user_id if mine_only else None)]

    def get_receipt(self, receipt_id: int) -> Dict[str, Any]:
        r = self.repo.get_receipt(receipt_id)
        if r is None:
            raise StockNotFoundError("Réception introuvable.")
        return _receipt_dict(r)

    def update_receipt_lines(self, receipt_id: int, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            r = self._lock_pending(receipt_id)
            self._require_checker()
            if r.origin == "fabrication":
                lot = self.repo.get_lot(r.production_lot_id, lock=True) if r.production_lot_id else None
                if lot is None or lot.status != "livre":
                    raise ValueError("Le lot lié à cette réception n'est plus « livre ».")
            if not lines:
                raise ValueError("Aucune ligne à corriger.")
            by_id = {l.id: l for l in r.lines}
            old = _receipt_dict(r)
            for change in lines:
                line = by_id.get(change.get("id"))
                if line is None:
                    raise ValueError(f"Ligne {change.get('id')} absente de cette réception.")
                qtys = {f: _int(change.get(f, getattr(line, f)), f) for f in QTY_FIELDS}
                _check_line_quantities(qtys, line.qty_expected)
                # R9 : le controleur ne peut que REDUIRE ou REDISTRIBUER une ligne ;
                # son total ne depasse jamais le total ACTUEL (donc jamais celui de l'auteur).
                current_total = sum(int(getattr(line, f) or 0) for f in QTY_FIELDS)
                if sum(qtys.values()) > current_total:
                    raise ValueError(
                        f"Ligne {line.id} : une correction ne peut que réduire ou redistribuer "
                        f"les quantités (total actuel {current_total}, demandé {sum(qtys.values())}).")
                for f, v in qtys.items():
                    setattr(line, f, v)
            self.session.flush()
            new = _receipt_dict(r)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockReceipt",
                                            action_performed="UPDATE_LINES", resource_id=r.id,
                                            old_values={"lines": old["lines"]}, new_values={"lines": new["lines"]})
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return new

    def validate_receipt(self, receipt_id: int) -> Dict[str, Any]:
        try:
            # Verrou FOR UPDATE sur la reception puis re-verification du statut :
            # un second validateur concurrent attend ici, puis voit 'valide' -> 409.
            r = self._lock_pending(receipt_id)
            if r.created_by == self.user.user_id:
                raise PermissionError("Vous ne pouvez pas valider une réception que vous avez saisie.")
            self._require_checker()
            lot = None
            if r.origin == "fabrication":
                # verrou du lot AVANT tout effet stock : un lot ne peut entrer qu'une fois
                lot = self.repo.get_lot(r.production_lot_id, lock=True) if r.production_lot_id else None
                if lot is None or lot.status != "livre":
                    raise StockConflictError(
                        f"Le lot lié n'est plus « livre » (statut : {lot.status if lot else 'absent'}).")
            for line in sorted(r.lines, key=lambda x: x.product_id):  # ordre stable : pas d'interblocage
                if line.qty_good > 0:
                    avaries = []
                    for f, lbl in (("qty_damaged", "endommagé"), ("qty_lost", "perdu"),
                                   ("qty_defective", "défectueux")):
                        if getattr(line, f):
                            avaries.append(f"{lbl} {getattr(line, f)}")
                    note = f"Réception {r.receipt_number}" + (f" (avaries : {', '.join(avaries)})" if avaries else "")
                    self.repo.apply_stock_delta(line.product_id, line.qty_good, "reception", note, self.user)
                if line.expiry_date:
                    prod = self.repo.lock_product(line.product_id)
                    current = prod.expiry_date.date() if isinstance(prod.expiry_date, datetime) else prod.expiry_date
                    if current is None or line.expiry_date < current:
                        prod.expiry_date = datetime.combine(line.expiry_date, datetime.min.time())
            if lot is not None:
                lot.status = "recu"
            old_status = r.status
            r.status = "valide"
            r.controlled_by = self.user.user_id
            r.controlled_at = datetime.utcnow()
            self.session.flush()
            out = _receipt_dict(r)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockReceipt",
                                            action_performed="VALIDATE", resource_id=r.id,
                                            old_values={"status": old_status}, new_values=out)
            self._notify_decided(r)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def reject_receipt(self, receipt_id: int, reason: str) -> Dict[str, Any]:
        try:
            r = self._lock_pending(receipt_id)
            if r.created_by == self.user.user_id:
                raise PermissionError("Vous ne pouvez pas rejeter une réception que vous avez saisie (utilisez l'annulation).")
            self._require_checker()
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("Le motif du rejet est obligatoire.")
            out = self._close_rejected(r, reason.strip(), "REJECT")
            self._notify_decided(r)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def cancel_receipt(self, receipt_id: int) -> Dict[str, Any]:
        try:
            r = self._lock_pending(receipt_id)
            if r.created_by != self.user.user_id and not self._is_admin():
                raise PermissionError("Seul l'auteur ou un administrateur peut annuler cette réception.")
            out = self._close_rejected(r, CANCEL_REASON, "CANCEL")
            if r.created_by != self.user.user_id:
                self._notify_decided(r)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    # ---------------- avaries (stock en rayon) ----------------
    def create_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            product_id = _int(data.get("product_id"), "product_id", None, limit=None)
            prod = self.repo.get_product(product_id) if product_id is not None else None
            if prod is None:
                raise ValueError("Produit introuvable.")
            kind = data.get("kind")
            if kind not in INCIDENT_KINDS:
                raise ValueError("Type d'avarie invalide (endommage, perdu ou defectueux).")
            qty = _int(data.get("quantity"), "quantity", 0)
            if qty <= 0:
                raise ValueError("La quantité doit être strictement positive.")
            raw_reason = data.get("reason")
            reason = raw_reason.strip() if isinstance(raw_reason, str) else ""
            if not reason:
                raise ValueError("Le motif est obligatoire.")
            incident_date = _date(data.get("incident_date"), "La date de l'avarie", required=True)
            inc = self.repo.add(StockIncident(
                product_id=product_id, kind=kind, quantity=qty, reason=reason,
                incident_date=incident_date, status="a_controler", created_by=self.user.user_id))
            out = _incident_dict(inc)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockIncident",
                                            action_performed="CREATE", resource_id=inc.id, new_values=out)
            payload = {"incident_id": inc.id, "kind": kind, "product_name": prod.drug_name,
                       "quantity": qty, "created_by_name": self.user.full_name}
            for uid in self.repo.checker_user_ids(exclude_user_id=self.user.user_id):
                self.notification_repo.create(uid, "stock_to_check", payload)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def list_incidents(self, status: Optional[str] = None, mine_only: bool = False) -> List[Dict[str, Any]]:
        return [_incident_dict(i) for i in
                self.repo.list_incidents(status, self.user.user_id if mine_only else None)]

    def validate_incident(self, incident_id: int) -> Dict[str, Any]:
        try:
            # Verrou FOR UPDATE puis re-verification du statut (perdant -> 409), puis role et
            # auteur, TOUS avant la moindre ecriture de stock.
            inc = self._lock_pending_incident(incident_id)
            self._require_checker()
            if inc.created_by == self.user.user_id:
                raise PermissionError("Vous ne pouvez pas valider une avarie que vous avez saisie.")
            # Garde de stock au moment de la validation : StockConflictError, rien d'ecrit.
            self.repo.apply_stock_delta(
                inc.product_id, -inc.quantity, f"avarie_{inc.kind}",
                f"Avarie #{inc.id} ({inc.kind}) : {inc.reason}", self.user, allow_negative=False)
            old_status = inc.status
            inc.status = "valide"
            inc.controlled_by = self.user.user_id
            inc.controlled_at = datetime.utcnow()
            self.session.flush()
            out = _incident_dict(inc)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockIncident",
                                            action_performed="VALIDATE", resource_id=inc.id,
                                            old_values={"status": old_status}, new_values=out)
            self._notify_incident_decided(inc)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def reject_incident(self, incident_id: int, reason: str) -> Dict[str, Any]:
        try:
            inc = self._lock_pending_incident(incident_id)
            self._require_checker()
            if inc.created_by == self.user.user_id:
                raise PermissionError("Vous ne pouvez pas rejeter une avarie que vous avez saisie (utilisez l'annulation).")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("Le motif du rejet est obligatoire.")
            out = self._close_incident_rejected(inc, reason.strip(), "REJECT")
            self._notify_incident_decided(inc)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def cancel_incident(self, incident_id: int) -> Dict[str, Any]:
        try:
            inc = self._lock_pending_incident(incident_id)
            if inc.created_by != self.user.user_id and not self._is_admin():
                raise PermissionError("Seul l'auteur ou un administrateur peut annuler cette avarie.")
            out = self._close_incident_rejected(inc, CANCEL_REASON, "CANCEL")
            if inc.created_by != self.user.user_id:
                self._notify_incident_decided(inc)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def _lock_pending_incident(self, incident_id: int) -> StockIncident:
        inc = self.repo.get_incident(incident_id, lock=True)
        if inc is None:
            raise StockNotFoundError("Avarie introuvable.")
        if inc.status != "a_controler":
            raise StockConflictError(f"Avarie déjà décidée (statut : {inc.status}).")
        return inc

    def _close_incident_rejected(self, inc: StockIncident, reason: str, action: str) -> Dict[str, Any]:
        inc.status = "rejete"
        inc.reject_reason = reason
        inc.controlled_by = self.user.user_id
        inc.controlled_at = datetime.utcnow()
        self.session.flush()
        out = _incident_dict(inc)
        self.audit_repo.log_user_action(current_user=self.user, resource_type="StockIncident",
                                        action_performed=action, resource_id=inc.id,
                                        old_values={"status": "a_controler"},
                                        new_values={"status": "rejete", "reject_reason": reason})
        return out

    def _notify_incident_decided(self, inc: StockIncident):
        payload = {"kind": "incident", "id": inc.id, "number": f"AVA-{inc.id}", "status": inc.status}
        if inc.status == "rejete":
            payload["reason"] = inc.reject_reason
        self.notification_repo.create(inc.created_by, "stock_decided", payload)

    # ---------------- demandes d'ajustement (secretaire -> admin) ----------------
    def create_adjustment_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self._role_name() != "secretaire":
                raise PermissionError("Seule une secrétaire peut demander un ajustement de stock.")
            product_id = _int(data.get("product_id"), "product_id", None, limit=None)
            prod = self.repo.get_product(product_id) if product_id is not None else None
            if prod is None:
                raise ValueError("Produit introuvable.")
            kind = data.get("kind")
            if kind not in ADJUSTMENT_KINDS:
                raise ValueError("Type de demande invalide (reapprovisionnement ou correction).")
            qty = _int(data.get("quantity"), "quantity", None)
            if qty is None:
                raise ValueError("La quantité est obligatoire.")
            if kind == "reapprovisionnement" and qty <= 0:
                raise ValueError("La quantité d'un réapprovisionnement doit être strictement positive.")
            if qty < 0:
                raise ValueError("La quantité ne peut pas être négative.")
            raw_reason = data.get("reason")
            reason = raw_reason.strip() if isinstance(raw_reason, str) else ""
            if not reason:
                raise ValueError("Le motif est obligatoire.")
            req = self.repo.add(StockAdjustmentRequest(
                product_id=product_id, kind=kind, quantity=qty, reason=reason,
                status="en_attente", requested_by=self.user.user_id))
            out = _adjustment_dict(req)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockAdjustmentRequest",
                                            action_performed="CREATE", resource_id=req.id, new_values=out)
            payload = {"request_id": req.id, "product_name": prod.drug_name, "kind": kind,
                       "quantity": qty, "requested_by_name": self.user.full_name}
            for uid in self.repo.admin_user_ids():
                self.notification_repo.create(uid, "stock_adjustment_request", payload)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def list_products_lookup(self) -> List[Dict[str, Any]]:
        """Liste minimale {id, name} des produits (filtres), triee par nom."""
        return [{"id": pid, "name": name} for pid, name in self.repo.list_products_lookup()]

    def list_adjustment_requests(self, status: Optional[str] = None, mine_only: bool = False) -> List[Dict[str, Any]]:
        return [_adjustment_dict(a) for a in
                self.repo.list_adjustments(status, self.user.user_id if mine_only else None)]

    def approve_adjustment(self, request_id: int) -> Dict[str, Any]:
        try:
            # Verrou FOR UPDATE + re-verification du statut (perdant -> 409), puis role et
            # demandeuse != approbateur, TOUS avant la moindre ecriture de stock.
            req = self._lock_pending_adjustment(request_id)
            self._require_admin_decider(req)
            note = f"Ajustement AJU-{req.id} ({req.kind}) : {req.reason}"
            if req.kind == "reapprovisionnement":
                after = self.repo.apply_stock_delta(req.product_id, req.quantity, "renew", note, self.user)
                before = after - req.quantity
            else:
                # delta calcule sous le verrou produit (stock au moment de l'approbation)
                before, after = self.repo.set_stock_quantity(req.product_id, req.quantity, "update", note, self.user)
            old_status = req.status
            req.status = "approuve"
            req.stock_before = before
            req.stock_after = after
            req.decided_by = self.user.user_id
            req.decided_at = datetime.utcnow()
            self.session.flush()
            out = _adjustment_dict(req)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="StockAdjustmentRequest",
                                            action_performed="APPROVE", resource_id=req.id,
                                            old_values={"status": old_status}, new_values=out)
            self._notify_adjustment_decided(req)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def reject_adjustment(self, request_id: int, note: str) -> Dict[str, Any]:
        try:
            req = self._lock_pending_adjustment(request_id)
            self._require_admin_decider(req)
            if not isinstance(note, str) or not note.strip():
                raise ValueError("Le motif du refus est obligatoire.")
            out = self._close_adjustment(req, "refuse", note.strip(), "REJECT")
            self._notify_adjustment_decided(req)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def cancel_adjustment(self, request_id: int) -> Dict[str, Any]:
        try:
            req = self._lock_pending_adjustment(request_id)
            if req.requested_by != self.user.user_id:
                raise PermissionError("Seule la demandeuse peut annuler sa demande.")
            out = self._close_adjustment(req, "annule", None, "CANCEL")
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def _lock_pending_adjustment(self, request_id: int) -> StockAdjustmentRequest:
        req = self.repo.get_adjustment(request_id, lock=True)
        if req is None:
            raise StockNotFoundError("Demande introuvable.")
        if req.status != "en_attente":
            raise StockConflictError(f"Demande déjà décidée (statut : {req.status}).")
        return req

    def _require_admin_decider(self, req: StockAdjustmentRequest):
        if self._role_name() != "admin":
            raise PermissionError("Seul un administrateur peut décider d'une demande d'ajustement.")
        if req.requested_by == self.user.user_id:
            raise PermissionError("Vous ne pouvez pas décider une demande que vous avez saisie.")

    def _close_adjustment(self, req: StockAdjustmentRequest, status: str, note: Optional[str],
                          action: str) -> Dict[str, Any]:
        req.status = status
        req.decision_note = note
        req.decided_by = self.user.user_id
        req.decided_at = datetime.utcnow()
        self.session.flush()
        out = _adjustment_dict(req)
        self.audit_repo.log_user_action(current_user=self.user, resource_type="StockAdjustmentRequest",
                                        action_performed=action, resource_id=req.id,
                                        old_values={"status": "en_attente"},
                                        new_values={"status": status, "decision_note": note})
        return out

    def _notify_adjustment_decided(self, req: StockAdjustmentRequest):
        payload = {"kind": "adjustment", "id": req.id, "number": f"AJU-{req.id}", "status": req.status}
        if req.status == "refuse":
            payload["reason"] = req.decision_note
        self.notification_repo.create(req.requested_by, "stock_decided", payload)

    # ---------------- historique des mouvements ----------------
    def list_movements(self, product_id: Optional[int] = None, movement_type: Optional[str] = None,
                       date_from: Optional[date] = None, date_to: Optional[date] = None,
                       page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Tous les types (VENTE, ANNULATION_VENTE, initial, update, renew, reception, avarie_*)."""
        page = _int(page, "page", 1, limit=None)
        per_page = _int(per_page, "per_page", 50, limit=None)
        if page < 1 or not 1 <= per_page <= MAX_PER_PAGE:
            raise ValueError(f"Pagination invalide (page >= 1, 1 <= per_page <= {MAX_PER_PAGE}).")
        date_from = _date(date_from, "date_from")
        date_to = _date(date_to, "date_to")
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from doit précéder date_to.")
        rows, total = self.repo.list_movements(
            _int(product_id, "product_id", None, limit=None), movement_type or None,
            date_from, date_to, (page - 1) * per_page, per_page)
        items = [{"movement_id": m.movement_id, "product_id": m.medication_id, "product_name": name,
                  "movement_type": m.movement_type, "change_qty": m.change_qty, "note": m.note,
                  "created_by": m.created_by, "created_at": m.created_at} for m, name in rows]
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    # ---------------- helpers ----------------
    def _role_name(self) -> Optional[str]:
        role = getattr(self.user, "application_role", None)
        return role.role_name if role else None

    def _is_admin(self) -> bool:
        role = getattr(self.user, "application_role", None)
        return bool(role and role.role_name == "admin")

    def _require_checker(self):
        """Defense en profondeur (les endpoints filtrent deja) : seuls StockController/admin decident."""
        role = getattr(self.user, "application_role", None)
        if not (role and role.role_name in CHECKER_ROLES):
            raise PermissionError("Seul un contrôleur de stock ou un administrateur peut contrôler.")

    def _lock_pending(self, receipt_id: int) -> StockReceipt:
        r = self.repo.get_receipt(receipt_id, lock=True)
        if r is None:
            raise StockNotFoundError("Réception introuvable.")
        self.session.refresh(r, attribute_names=["lines"])
        if r.status != "a_controler":
            raise StockConflictError(f"Réception déjà décidée (statut : {r.status}).")
        return r

    def _close_rejected(self, r: StockReceipt, reason: str, action: str) -> Dict[str, Any]:
        r.status = "rejete"
        r.reject_reason = reason
        r.controlled_by = self.user.user_id
        r.controlled_at = datetime.utcnow()
        self.session.flush()
        out = _receipt_dict(r)
        self.audit_repo.log_user_action(current_user=self.user, resource_type="StockReceipt",
                                        action_performed=action, resource_id=r.id,
                                        old_values={"status": "a_controler"},
                                        new_values={"status": "rejete", "reject_reason": reason})
        return out

    def _notify_decided(self, r: StockReceipt):
        payload = {"kind": "receipt", "id": r.id, "number": r.receipt_number, "status": r.status}
        if r.status == "rejete":
            payload["reason"] = r.reject_reason
        self.notification_repo.create(r.created_by, "stock_decided", payload)
