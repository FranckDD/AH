# controller/lab_stock_controller.py
"""Stock labo : produits, signalement, demandes « a commander » et suivi de commande.

Le controleur possede la transaction (commit ici, rollback sur toute exception).
Les roles sont verifies par les endpoints (/lab-stock).
Erreurs : LabStockNotFoundError -> 404, ValueError -> 422, PermissionError -> 403,
LabStockConflictError -> 409.
Tasks 3-5 ajoutent receptions, comptages/alertes et depenses sur ce meme controleur.
"""
import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from controller.stock_controller import _date, _int
from models.lab_stock import (
    LabStockCount, LabStockCountLine, LabStockProduct, LabStockReceipt, LabStockReceiptLine, LabStockRequest,
)
from repositories.audit_repo import AuditRepository
from repositories.lab_stock_repo import (
    OPEN_REQUEST_STATUSES, LabStockConflictError, LabStockNotFoundError, LabStockRepository,
)
from repositories.notification_repo import NotificationRepository
from utils.lab_stock_rules import COUNT_REMINDER_DAYS, EXPIRY_WARNING_DAYS

logger = logging.getLogger(__name__)

__all__ = ["LabStockController", "LabStockConflictError", "LabStockCountConflictError",
           "LabStockNotFoundError"]


class LabStockCountConflictError(LabStockConflictError):
    """Toutes les lignes du comptage sont en conflit -> 409 avec la liste."""

    def __init__(self, message, conflicts):
        super().__init__(message)
        self.conflicts = conflicts

SIGNAL_LEVELS = ("bientot_fini", "fini")
REQUEST_STATUSES = ("a_commander", "commande", "recu", "annule")
MAX_THRESHOLD = 1_000_000
PRODUCT_FIELDS = ("name", "packaging", "alert_threshold", "supplier", "is_active")
MAX_RECEIPT_LINES = 200
CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("99999999.99")  # Numeric(10, 2)
DUP_INDEX = "uq_lab_stock_receipts_supplier_invoice"
DELIVERY_TOLERANCE_DAYS = 1
MAX_COUNT_LINES = 500
MAX_MOVEMENTS = 1000
PRODUCT_DEACTIVATED_REASON = "produit désactivé"
_DUP_MSG = "Une réception valide existe déjà pour ce fournisseur et ce numéro de facture."


def _product_dict(p: LabStockProduct, names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    names = names or {}
    return {
        "id": p.id, "name": p.name, "packaging": p.packaging, "alert_threshold": p.alert_threshold,
        "supplier": p.supplier, "quantity": p.quantity, "last_counted_at": p.last_counted_at,
        "is_active": p.is_active, "created_by": p.created_by, "created_at": p.created_at,
        "created_by_name": names.get(p.created_by),
    }


def _request_dict(r: LabStockRequest, names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    names = names or {}
    p = r.product
    return {
        "id": r.id, "product_id": r.product_id,
        "product_name": p.name if p else None,
        "quantity": p.quantity if p else None,
        "alert_threshold": p.alert_threshold if p else None,
        "packaging": p.packaging if p else None,
        "supplier": p.supplier if p else None,
        "origin": r.origin, "level": r.level, "status": r.status,
        "requested_by": r.requested_by, "ordered_by": r.ordered_by,
        "expected_date": r.expected_date, "closed_by_receipt_id": r.closed_by_receipt_id,
        "cancel_reason": r.cancel_reason, "created_at": r.created_at,
        "ordered_at": r.ordered_at, "closed_at": r.closed_at,
        "requested_by_name": names.get(r.requested_by), "ordered_by_name": names.get(r.ordered_by),
    }


def _receipt_dict(r: LabStockReceipt, names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    names = names or {}
    return {
        "id": r.id, "invoice_number": r.invoice_number, "supplier": r.supplier,
        "delivery_date": r.delivery_date, "total_amount": r.total_amount, "status": r.status,
        "cancel_reason": r.cancel_reason, "created_by": r.created_by, "created_at": r.created_at,
        "cancelled_by": r.cancelled_by, "cancelled_at": r.cancelled_at,
        "created_by_name": names.get(r.created_by), "cancelled_by_name": names.get(r.cancelled_by),
        "lines": [{
            "id": ln.id, "product_id": ln.product_id,
            "product_name": ln.product.name if ln.product else None,
            "packaging": ln.product.packaging if ln.product else None,
            "ordered_qty": ln.ordered_qty, "received_qty": ln.received_qty,
            "unit_price": ln.unit_price, "line_total": ln.line_total,
            "lot_number": ln.lot_number, "expiry_date": ln.expiry_date, "note": ln.note,
        } for ln in sorted(r.lines, key=lambda x: x.id or 0)],
    }


def _constraint_name(exc: IntegrityError) -> Optional[str]:
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    name = getattr(diag, "constraint_name", None)
    if name:
        return name
    return DUP_INDEX if DUP_INDEX in str(getattr(exc, "orig", exc)) else None


def _jsonable(d):
    """Audit JSONB : Decimal/date en texte."""
    return json.loads(json.dumps(d, default=str))


def _money(v, name) -> Decimal:
    if v is None or v == "":
        raise ValueError(f"{name} est obligatoire.")
    if isinstance(v, bool):
        raise ValueError(f"{name} invalide.")
    try:
        d = Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} invalide.")
    if not d.is_finite():
        raise ValueError(f"{name} invalide.")
    if d < 0:
        raise ValueError(f"{name} ne peut pas être négatif.")
    if d > MAX_AMOUNT:
        raise ValueError(f"{name} dépasse la limite autorisée.")
    if d != d.quantize(CENT):
        raise ValueError(f"{name} : au plus 2 décimales.")
    return d.quantize(CENT)


def _text(v, name, max_len, required=False) -> Optional[str]:
    if v is None:
        if required:
            raise ValueError(f"{name} est obligatoire.")
        return None
    if not isinstance(v, str):
        raise ValueError(f"{name} invalide.")
    v = v.strip()
    if not v:
        if required:
            raise ValueError(f"{name} est obligatoire.")
        return None
    if len(v) > max_len:
        raise ValueError(f"{name} dépasse {max_len} caractères.")
    return v


class LabStockController:
    def __init__(self, repo: LabStockRepository, notification_repo: NotificationRepository,
                 audit_repo: AuditRepository, current_user):
        if repo is None or notification_repo is None or audit_repo is None:
            raise TypeError("LabStockController exige repo, notification_repo et audit_repo.")
        self.repo = repo
        self.notification_repo = notification_repo
        self.audit_repo = audit_repo
        self.user = current_user
        self.session = repo.session

    # ---------------- produits ----------------
    def _clean_product(self, data: Dict[str, Any], partial: bool) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not partial or "name" in data:
            out["name"] = _text(data.get("name"), "Le nom", 150, required=True)
        for f, label, n in (("packaging", "Le conditionnement", 100), ("supplier", "Le fournisseur", 150)):
            if not partial or f in data:
                out[f] = _text(data.get(f), label, n)
        if not partial or "alert_threshold" in data:
            if "alert_threshold" in data and data["alert_threshold"] is None:
                raise ValueError("Le seuil d'alerte est obligatoire.")
            t =_int(data.get("alert_threshold"), "Le seuil d'alerte", 0, limit=MAX_THRESHOLD)
            if t < 0:
                raise ValueError("Le seuil d'alerte ne peut pas être négatif.")
            out["alert_threshold"] = t
        if "is_active" in data:
            v = data.get("is_active")
            if not isinstance(v, bool):
                raise ValueError("is_active invalide.")
            out["is_active"] = v
        return out

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            clean = self._clean_product(data, partial=False)
            clean.setdefault("is_active", True)
            if clean["is_active"] and self.repo.active_name_exists(clean["name"]):
                raise LabStockConflictError(f"Un produit actif nommé « {clean['name']} » existe déjà.")
            # quantity toujours 0 a la creation : le stock n'entre que par reception/comptage
            p = self.repo.add(LabStockProduct(quantity=0, created_by=self.user.user_id, **clean))
            out = self._product_d(p)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockProduct",
                                            action_performed="CREATE", resource_id=p.id, new_values=out)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise LabStockConflictError("Un produit actif portant ce nom existe déjà.")
        except Exception:
            self.session.rollback()
            raise
        return out

    def update_product(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            p = self.repo.get_product(product_id, lock=True)
            if p is None:
                raise LabStockNotFoundError("Produit introuvable.")
            clean = self._clean_product(data, partial=True)
            if not clean:
                raise ValueError("Aucune modification fournie.")
            name = clean.get("name", p.name)
            active = clean.get("is_active", p.is_active)
            if active and self.repo.active_name_exists(name, exclude_id=p.id):
                raise LabStockConflictError(f"Un produit actif nommé « {name} » existe déjà.")
            old = self._product_d(p)
            deactivating = bool(p.is_active) and clean.get("is_active") is False
            for k, v in clean.items():
                setattr(p, k, v)
            self.session.flush()
            if deactivating:
                # produit desactive : sa demande ouverte (a_commander / commande) est annulee
                req = self.repo.open_request_for(p.id)
                if req is not None:
                    req_old = {"status": req.status}
                    req.status = "annule"
                    req.cancel_reason = PRODUCT_DEACTIVATED_REASON
                    req.closed_at = datetime.utcnow()
                    self.session.flush()
                    self.audit_repo.log_user_action(
                        current_user=self.user, resource_type="LabStockRequest",
                        action_performed="CANCEL", resource_id=req.id, old_values=req_old,
                        new_values={"status": "annule", "cancel_reason": PRODUCT_DEACTIVATED_REASON})
            out = self._product_d(p)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockProduct",
                                            action_performed="UPDATE", resource_id=p.id,
                                            old_values=old, new_values=out)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise LabStockConflictError("Un produit actif portant ce nom existe déjà.")
        except Exception:
            self.session.rollback()
            raise
        return out

    def list_products(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        rows = self.repo.list_products(include_inactive)
        names = self.repo.names(p.created_by for p in rows)
        return [_product_dict(p, names) for p in rows]

    # ---------------- signalement ----------------
    def signal(self, product_id: int, level: str) -> Dict[str, Any]:
        """Course sur l'index « une demande ouverte par produit » : l'INSERT perdant leve
        IntegrityError -> rollback puis UNE relance (qui trouve et met a jour la demande
        gagnante) ; second echec -> 409, jamais 500."""
        for attempt in range(2):
            try:
                return self._signal_once(product_id, level)
            except IntegrityError:
                self.session.rollback()
                if attempt == 1:
                    raise LabStockConflictError("Signalement concurrent : réessayez.")

    def _signal_once(self, product_id: int, level: str) -> Dict[str, Any]:
        try:
            if level not in SIGNAL_LEVELS:
                raise ValueError("Niveau invalide (bientot_fini ou fini).")
            p = self.repo.get_product(product_id)
            if p is None:
                raise LabStockNotFoundError("Produit introuvable.")
            if not p.is_active:
                raise ValueError("Ce produit est désactivé.")
            # verrou produit : deux signalements concurrents sont serialises (une seule demande ouverte)
            self.repo.lock_products([product_id])
            req = self.repo.open_request_for(product_id)
            if req is None:
                req = self.repo.add(LabStockRequest(
                    product_id=product_id, origin="signalement", level=level, status="a_commander",
                    requested_by=self.user.user_id))
                action, old = "SIGNAL_CREATE", None
            else:
                old = {"level": req.level}
                req.level = level
                self.session.flush()
                action = "SIGNAL_UPDATE"
            out = self._request_d(req)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockRequest",
                                            action_performed=action, resource_id=req.id,
                                            old_values=old, new_values=out)
            self._notify_managers("lab_stock_signal", "request_id", req.id, {
                "request_id": req.id, "product_id": p.id, "product_name": p.name, "level": level,
                "requested_by_name": getattr(self.user, "full_name", None)})
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    # ---------------- demandes / commande ----------------
    def list_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if status and status not in REQUEST_STATUSES:
            raise ValueError("Statut invalide.")
        rows = self.repo.list_requests(status or None)
        names = self.repo.names(i for r in rows for i in (r.requested_by, r.ordered_by))
        return [_request_dict(r, names) for r in rows]

    def mark_ordered(self, request_id: int, expected_date) -> Dict[str, Any]:
        try:
            req = self._lock_request(request_id)
            if req.status != "a_commander":
                raise LabStockConflictError(f"La demande n'est pas « à commander » (statut : {req.status}).")
            d = self._future_date(expected_date)
            old = {"status": req.status, "expected_date": req.expected_date}
            req.status = "commande"
            req.expected_date = d
            req.ordered_by = self.user.user_id
            req.ordered_at = datetime.utcnow()
            self.session.flush()
            out = self._request_d(req)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockRequest",
                                            action_performed="ORDER", resource_id=req.id,
                                            old_values=old, new_values=out)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def update_expected_date(self, request_id: int, expected_date) -> Dict[str, Any]:
        try:
            req = self._lock_request(request_id)
            if req.status != "commande":
                raise LabStockConflictError(f"La demande n'est pas « commandée » (statut : {req.status}).")
            d = self._future_date(expected_date)
            old = {"expected_date": req.expected_date}
            req.expected_date = d
            self.session.flush()
            out = self._request_d(req)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockRequest",
                                            action_performed="UPDATE_EXPECTED_DATE", resource_id=req.id,
                                            old_values=old, new_values={"expected_date": d})
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def cancel_request(self, request_id: int, reason) -> Dict[str, Any]:
        try:
            reason = _text(reason, "Le motif", 2000, required=True)
            req = self._lock_request(request_id)
            if req.status not in OPEN_REQUEST_STATUSES:
                raise LabStockConflictError(f"La demande n'est plus ouverte (statut : {req.status}).")
            old = {"status": req.status}
            req.status = "annule"
            req.cancel_reason = reason
            req.closed_at = datetime.utcnow()
            self.session.flush()
            out = self._request_d(req)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockRequest",
                                            action_performed="CANCEL", resource_id=req.id,
                                            old_values=old, new_values={"status": "annule", "cancel_reason": reason})
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    # ---------------- receptions ----------------
    def _clean_receipt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("Réception invalide.")
        head = {
            "invoice_number": _text(data.get("invoice_number"), "Le numéro de facture", 100, required=True),
            "supplier": _text(data.get("supplier"), "Le fournisseur", 150, required=True),
            "delivery_date": _date(data.get("delivery_date"), "La date de livraison", required=True),
        }
        # tolerance d'un jour : serveur (Londres) et site n'ont pas le meme fuseau
        if head["delivery_date"] > date.today() + timedelta(days=DELIVERY_TOLERANCE_DAYS):
            raise ValueError("La date de livraison ne peut pas être dans le futur.")
        raw = data.get("lines")
        if not isinstance(raw, list) or not raw:
            raise ValueError("La réception doit comporter au moins une ligne.")
        if len(raw) > MAX_RECEIPT_LINES:
            raise ValueError(f"Trop de lignes (maximum {MAX_RECEIPT_LINES}).")
        lines, seen = [], set()
        for i, ln in enumerate(raw, start=1):
            if not isinstance(ln, dict):
                raise ValueError(f"Ligne {i} invalide.")
            if ln.get("product_id") is None:
                raise ValueError(f"Ligne {i} : produit obligatoire.")
            pid = _int(ln.get("product_id"), f"Ligne {i} : produit", limit=None)
            if pid in seen:
                raise ValueError(f"Ligne {i} : produit en double dans la réception.")
            seen.add(pid)
            if ln.get("received_qty") is None:
                raise ValueError(f"Ligne {i} : quantité reçue obligatoire.")
            received = _int(ln.get("received_qty"), f"Ligne {i} : quantité reçue")
            if received <= 0:
                raise ValueError(f"Ligne {i} : la quantité reçue doit être supérieure à 0.")
            ordered = None
            if ln.get("ordered_qty") not in (None, ""):
                ordered = _int(ln.get("ordered_qty"), f"Ligne {i} : quantité commandée")
                if ordered < 0:
                    raise ValueError(f"Ligne {i} : la quantité commandée ne peut pas être négative.")
            price = _money(ln.get("unit_price"), f"Ligne {i} : prix unitaire")
            lines.append({
                "product_id": pid, "ordered_qty": ordered, "received_qty": received,
                "unit_price": price,
                # recalcule cote serveur : tout total fourni est ignore
                "line_total": (price * received).quantize(CENT),
                "lot_number": _text(ln.get("lot_number"), f"Ligne {i} : n° de lot", 50, required=True),
                "expiry_date": _date(ln.get("expiry_date"), f"Ligne {i} : date de péremption", required=True),
                "note": _text(ln.get("note"), f"Ligne {i} : note", 2000),
            })
        head["lines"] = lines
        head["total_amount"] = sum((ln["line_total"] for ln in lines), Decimal("0.00"))
        if head["total_amount"] > MAX_AMOUNT:
            raise ValueError("Montant total trop élevé.")
        return head

    def create_receipt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            clean = self._clean_receipt(data)
            # pre-controle convivial ; la vraie garde est l'index unique partiel (IntegrityError ci-dessous)
            if self.repo.valid_receipt_exists(clean["supplier"], clean["invoice_number"]):
                raise LabStockConflictError(_DUP_MSG)
            ids = [ln["product_id"] for ln in clean["lines"]]
            products = self.repo.lock_products(ids)
            for pid in ids:
                p = products.get(pid)
                if p is None:
                    raise ValueError(f"Produit introuvable : {pid}.")
                if not p.is_active:
                    raise ValueError(f"Le produit « {p.name} » est désactivé.")
            receipt = LabStockReceipt(
                invoice_number=clean["invoice_number"], supplier=clean["supplier"],
                delivery_date=clean["delivery_date"], total_amount=clean["total_amount"],
                status="valide", created_by=self.user.user_id, created_at=datetime.utcnow())
            for ln in clean["lines"]:
                receipt.lines.append(LabStockReceiptLine(**ln))
            self.repo.add(receipt)  # flush : l'index unique leve ici en cas de doublon concurrent
            now = datetime.utcnow()
            to_notify: Dict[int, List[Dict[str, Any]]] = {}
            for pid in sorted(ids):
                ln = next(x for x in clean["lines"] if x["product_id"] == pid)
                new_qty = self.repo.apply_delta(pid, ln["received_qty"], "reception", "receipt",
                                                receipt.id, self.user)
                p = products[pid]
                req = self.repo.open_request_for(pid)
                if req is not None:
                    req.status = "recu"
                    req.closed_by_receipt_id = receipt.id
                    req.closed_at = now
                    self.session.flush()
                    if req.origin == "signalement" and req.requested_by is not None:
                        to_notify.setdefault(req.requested_by, []).append(
                            {"product_id": pid, "product_name": p.name, "received_qty": ln["received_qty"]})
                self._ensure_threshold_request(p, new_qty)
            out = self._receipt_d(receipt)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockReceipt",
                                            action_performed="CREATE", resource_id=receipt.id,
                                            new_values=_jsonable(out))
            for uid, items in to_notify.items():
                self._notify_user(uid, "lab_stock_received", "receipt_id", receipt.id, {
                    "receipt_id": receipt.id, "supplier": receipt.supplier,
                    "invoice_number": receipt.invoice_number, "products": items})
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            if _constraint_name(e) == DUP_INDEX:
                raise LabStockConflictError(_DUP_MSG)
            raise
        except Exception:
            self.session.rollback()
            raise
        return out

    def get_receipt(self, receipt_id: int) -> Dict[str, Any]:
        r = self.repo.get_receipt(receipt_id)
        if r is None:
            raise LabStockNotFoundError("Réception introuvable.")
        return self._receipt_d(r)

    def list_receipts(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        f = filters or {}
        supplier = _text(f.get("supplier"), "Le fournisseur", 150)
        d_from = _date(f.get("from"), "La date de début")
        d_to = _date(f.get("to"), "La date de fin")
        if d_from and d_to and d_from > d_to:
            raise ValueError("La date de début doit précéder la date de fin.")
        rows = self.repo.list_receipts(supplier, d_from, d_to)
        names = self.repo.names(i for r in rows for i in (r.created_by, r.cancelled_by))
        return [_receipt_dict(r, names) for r in rows]

    def cancel_receipt(self, receipt_id: int, reason) -> Dict[str, Any]:
        try:
            if not self._is_admin():
                raise PermissionError("Seul un administrateur peut annuler une réception.")
            reason = _text(reason, "Le motif", 2000, required=True)
            r = self.repo.get_receipt(receipt_id, lock=True)
            if r is None:
                raise LabStockNotFoundError("Réception introuvable.")
            if r.status != "valide":
                raise LabStockConflictError("Cette réception est déjà annulée.")
            qty_by_pid = {ln.product_id: ln.received_qty for ln in r.lines}
            products = self.repo.lock_products(qty_by_pid)
            short = [f"{products[pid].name} ({products[pid].quantity} en stock, {q} à retirer)"
                     for pid, q in sorted(qty_by_pid.items())
                     if pid in products and products[pid].quantity < q]
            if short:
                raise LabStockConflictError(
                    "Stock insuffisant pour annuler la réception : " + ", ".join(short) + ".")
            old = {"status": r.status}
            r.status = "annule"
            r.cancel_reason = reason
            r.cancelled_by = self.user.user_id
            r.cancelled_at = datetime.utcnow()
            self.session.flush()  # libere l'index unique (fournisseur, facture) avant toute suite
            new_qtys = {}
            for pid in sorted(qty_by_pid):
                new_qtys[pid] = self.repo.apply_delta(pid, -qty_by_pid[pid], "annulation_reception",
                                                      "receipt", r.id, self.user)
            reopened = set()
            reopened_ids: List[int] = []
            reopened_detail: List[Dict[str, Any]] = []
            for req in self.repo.requests_closed_by(r.id):
                if self.repo.open_request_for(req.product_id) is not None:
                    continue  # une autre demande est ouverte entre-temps : on la laisse
                # deja commandee avant la livraison (ordered_at conserve a la cloture) : retour a « commande »
                # avec ordered_by / ordered_at / expected_date intacts ; sinon « a_commander ».
                req.status = "commande" if req.ordered_at is not None else "a_commander"
                req.closed_at = None
                req.closed_by_receipt_id = None
                self.session.flush()
                reopened.add(req.product_id)
                reopened_ids.append(req.id)
                reopened_detail.append({"id": req.id, "status": req.status})
            for pid in sorted(qty_by_pid):
                if pid not in reopened:
                    self._ensure_threshold_request(products[pid], new_qtys[pid])
            for n in self.repo.unread_notifications("lab_stock_received"):
                if isinstance(n.payload, dict) and n.payload.get("receipt_id") == r.id:
                    n.status = "read"
                    n.read_at = datetime.utcnow()
            out = self._receipt_d(r)
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockReceipt",
                                            action_performed="CANCEL", resource_id=r.id, old_values=old,
                                            new_values={"status": "annule", "cancel_reason": reason,
                                                        "removed": {str(k): v for k, v in sorted(qty_by_pid.items())},
                                                        "reopened_request_ids": reopened_ids,
                                                        "reopened": reopened_detail})
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return out

    def _ensure_threshold_request(self, p: LabStockProduct, qty: int):
        """Demande « seuil » si stock <= seuil et aucune demande ouverte (seuil 0 + stock > 0 : rien),
        puis notification lab_stock_low via _notify_managers (dedupliquee sur request_id).
        CHEMIN UNIQUE : Task 4 (comptage) doit reutiliser _ensure_threshold_request + _notify_managers
        pour toute demande « seuil » et sa notification, sans dupliquer cette logique."""
        if not p.is_active or qty > (p.alert_threshold or 0):
            return
        if self.repo.open_request_for(p.id) is not None:
            return
        req = self.repo.add(LabStockRequest(product_id=p.id, origin="seuil", status="a_commander"))
        self._notify_managers("lab_stock_low", "request_id", req.id, {
            "request_id": req.id, "product_id": p.id, "product_name": p.name,
            "quantity": qty, "alert_threshold": p.alert_threshold})

    def _notify_user(self, uid: int, type_: str, key: str, value, payload: Dict[str, Any]):
        existing = self.repo.find_unread_notification(uid, type_, key, value)
        if existing is not None:
            existing.payload = dict(payload)
        else:
            self.notification_repo.create(uid, type_, payload)
        self.session.flush()

    def _is_admin(self) -> bool:
        if "admin" in (getattr(self.user, "roles", None) or []):
            return True
        role = getattr(self.user, "application_role", None)
        return bool(role and role.role_name == "admin")

    def _receipt_d(self, r):
        return _receipt_dict(r, self.repo.names([r.created_by, r.cancelled_by]))

    # ---------------- helpers ----------------
    def _lock_request(self, request_id: int) -> LabStockRequest:
        req = self.repo.get_request(request_id, lock=True)
        if req is None:
            raise LabStockNotFoundError("Demande introuvable.")
        return req

    @staticmethod
    def _future_date(v) -> date:
        d = _date(v, "La date prévue", required=True)
        if d < date.today():
            raise ValueError("La date prévue ne peut pas être dans le passé.")
        return d

    def _notify_managers(self, type_: str, key: str, value, payload: Dict[str, Any]):
        """Promoteur + ToxicoManager actifs ; pas de doublon non lu pour (type, cle)."""
        for uid in self.repo.manager_user_ids():
            existing = self.repo.find_unread_notification(uid, type_, key, value)
            if existing is not None:
                existing.payload = dict(payload)  # reaffectation : la colonne JSON est bien marquee modifiee
            else:
                self.notification_repo.create(uid, type_, payload)
        self.session.flush()

    def _product_d(self, p):
        return _product_dict(p, self.repo.names([p.created_by]))

    # ---------------- comptage ----------------
    def _clean_count(self, lines) -> List[Dict[str, int]]:
        if not isinstance(lines, list) or not lines:
            raise ValueError("Le comptage doit comporter au moins une ligne.")
        if len(lines) > MAX_COUNT_LINES:
            raise ValueError(f"Trop de lignes (maximum {MAX_COUNT_LINES}).")
        out, seen = [], set()
        for i, ln in enumerate(lines, start=1):
            if not isinstance(ln, dict):
                raise ValueError(f"Ligne {i} invalide.")
            vals = {}
            for f, label in (("product_id", "produit"), ("previous_qty", "quantité avant"),
                             ("counted_qty", "quantité comptée")):
                if ln.get(f) is None:
                    raise ValueError(f"Ligne {i} : {label} obligatoire.")
                vals[f] = _int(ln.get(f), f"Ligne {i} : {label}", limit=None if f == "product_id" else MAX_THRESHOLD)
            if vals["previous_qty"] < 0 or vals["counted_qty"] < 0:
                raise ValueError(f"Ligne {i} : les quantités ne peuvent pas être négatives.")
            if vals["product_id"] in seen:
                raise ValueError(f"Ligne {i} : produit en double dans le comptage.")
            seen.add(vals["product_id"])
            out.append(vals)
        return out

    def submit_count(self, lines, today: Optional[date] = None) -> Dict[str, Any]:
        """Comptage : fixe le stock a la valeur comptee, ligne par ligne sous verrou.
        Ligne dont previous_qty != stock actuel -> conflit (rien d'ecrit pour elle) ;
        toutes en conflit -> LabStockCountConflictError (409)."""
        try:
            clean = self._clean_count(lines)
            by_pid = {ln["product_id"]: ln for ln in clean}
            products = self.repo.lock_products(by_pid)  # ordre d'id croissant
            for pid in sorted(by_pid):
                p = products.get(pid)
                if p is None:
                    raise ValueError(f"Produit introuvable : {pid}.")
                if not p.is_active:
                    raise ValueError(f"Le produit « {p.name} » est désactivé.")
            conflicts, todo = [], []
            for pid in sorted(by_pid):
                p, ln = products[pid], by_pid[pid]
                if p.quantity != ln["previous_qty"]:
                    conflicts.append({"product_id": pid, "name": p.name,
                                      "expected": ln["previous_qty"], "actual": p.quantity})
                else:
                    todo.append(ln)
            if not todo:
                raise LabStockCountConflictError(
                    "Le stock a changé pendant le comptage : recomptez ces produits.", conflicts)
            now = datetime.utcnow()
            count = self.repo.add(LabStockCount(counted_by=self.user.user_id, counted_at=now))
            applied = []
            for ln in todo:
                pid, p = ln["product_id"], products[ln["product_id"]]
                new_qty = self.repo.apply_delta(pid, ln["counted_qty"] - p.quantity, "comptage",
                                                "count", count.id, self.user)
                p.last_counted_at = now
                count.lines.append(LabStockCountLine(product_id=pid, previous_qty=ln["previous_qty"],
                                                     counted_qty=ln["counted_qty"]))
                self.session.flush()
                self._after_count(p, new_qty)
                applied.append({"product_id": pid, "name": p.name, "previous_qty": ln["previous_qty"],
                                "counted_qty": new_qty, "delta": new_qty - ln["previous_qty"]})
            out = {"count_id": count.id, "applied": applied, "conflicts": conflicts}
            self.audit_repo.log_user_action(current_user=self.user, resource_type="LabStockCount",
                                            action_performed="CREATE", resource_id=count.id,
                                            new_values=_jsonable(out))
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        # apres le commit du comptage : alertes (peremption, rappel efface) sans le mettre en peril
        self._emit_alerts_safely(self._compute_alerts(today), clear_reminder=True)
        return out

    def _after_count(self, p: LabStockProduct, qty: int):
        if qty <= (p.alert_threshold or 0):
            self._ensure_threshold_request(p, qty)  # chemin unique demande seuil + lab_stock_low
            return
        req = self.repo.open_request_for(p.id)
        if req is not None and req.origin == "seuil" and req.status == "a_commander":
            req.status = "annule"
            req.cancel_reason = "stock remonté"
            req.closed_at = datetime.utcnow()
            self.session.flush()

    # ---------------- alertes ----------------
    def _compute_alerts(self, today: Optional[date] = None) -> Dict[str, Any]:
        today = today or date.today()
        open_by_pid = self.repo.open_requests_by_product()
        low = []
        for p in self.repo.list_products():
            thr = p.alert_threshold or 0
            req = open_by_pid.get(p.id)
            # seuil 0 + stock 0 : alerte seulement si une demande est ouverte (pas de fausse alerte)
            if p.quantity <= thr and (thr > 0 or req is not None):
                low.append({"product_id": p.id, "name": p.name, "packaging": p.packaging,
                            "quantity": p.quantity, "alert_threshold": thr,
                            "request_id": req.id if req else None,
                            "request_status": req.status if req else None,
                            "request_origin": req.origin if req else None})
        expiring = [{
            "receipt_line_id": ln.id, "product_id": ln.product_id,
            "product_name": ln.product.name if ln.product else None,
            "lot_number": ln.lot_number, "expiry_date": ln.expiry_date,
            "days_left": (ln.expiry_date - today).days, "receipt_id": ln.receipt_id,
        } for ln in self.repo.expiring_lines(today + timedelta(days=EXPIRY_WARNING_DAYS))]
        last = self.repo.last_count_at()
        days_since = (today - last.date()).days if last else None
        if last is None:
            due = self.repo.active_product_count() > 0
        else:
            due = days_since >= COUNT_REMINDER_DAYS
        status = {"last_counted_at": last, "days_since": days_since, "reminder_due": due}
        iso = today.isocalendar()
        return {"low": low, "expiring": expiring, "count_status": status,
                "_week": f"{iso[0]}-W{iso[1]:02d}"}

    def _emit_alerts_safely(self, alerts: Dict[str, Any], clear_reminder: bool = False):
        """Notifications peremption (une par lot) et rappel (une par semaine ISO), au plus une fois.
        Un echec est journalise et annule (rollback) sans casser la lecture ni le comptage."""
        try:
            managers = self.repo.manager_user_ids()
            for e in alerts["expiring"]:
                payload = _jsonable({k: e[k] for k in ("receipt_line_id", "product_id", "product_name",
                                                         "lot_number", "expiry_date", "days_left", "receipt_id")})
                for uid in managers:
                    if not self.repo.notification_exists(uid, "lab_stock_expiry", "receipt_line_id",
                                                         e["receipt_line_id"]):
                        self.notification_repo.create(uid, "lab_stock_expiry", payload)
            if clear_reminder:
                for n in self.repo.unread_notifications("lab_stock_count_reminder"):
                    n.status = "read"
                    n.read_at = datetime.utcnow()
            st = alerts["count_status"]
            if st["reminder_due"]:
                week = alerts["_week"]
                for uid in self.repo.active_user_ids_with_roles(("laborantin",)):
                    if not self.repo.notification_exists(uid, "lab_stock_count_reminder", "iso_week", week):
                        self.notification_repo.create(uid, "lab_stock_count_reminder", _jsonable({
                            "iso_week": week, "last_counted_at": st["last_counted_at"],
                            "days_since": st["days_since"]}))
            self.session.commit()
        except Exception:
            self.session.rollback()
            logger.exception("Stock labo : emission des notifications d'alerte impossible")

    def get_alerts(self, today: Optional[date] = None) -> Dict[str, Any]:
        alerts = self._compute_alerts(today)
        self._emit_alerts_safely(alerts)
        alerts.pop("_week", None)
        return alerts

    def get_count_status(self, today: Optional[date] = None) -> Dict[str, Any]:
        return self.get_alerts(today)["count_status"]

    def list_movements(self, product_id: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_MOVEMENTS:
            raise ValueError(f"limit doit être entre 1 et {MAX_MOVEMENTS}.")
        rows = self.repo.list_movements(product_id, limit)
        names = self.repo.names(m.created_by for m in rows)
        return [{"id": m.id, "product_id": m.product_id,
                 "product_name": m.product.name if m.product else None,
                 "change_qty": m.change_qty, "movement_type": m.movement_type,
                 "ref_type": m.ref_type, "ref_id": m.ref_id, "quantity_after": m.quantity_after,
                 "created_by": m.created_by, "created_by_name": names.get(m.created_by),
                 "created_at": m.created_at} for m in rows]

    def _request_d(self, r):
        return _request_dict(r, self.repo.names([r.requested_by, r.ordered_by]))

    # ---------------- depenses ----------------
    def expenses(self, date_from=None, date_to=None) -> Dict[str, Any]:
        """Depenses (receptions valides, par delivery_date). Defaut : 12 derniers mois."""
        today = date.today()
        d_from = _date(date_from, "La date de début")
        d_to = _date(date_to, "La date de fin")
        if d_to is None:
            d_to = today + timedelta(days=DELIVERY_TOLERANCE_DAYS)
        if d_from is None:
            y, m = today.year, today.month - 11
            if m < 1:
                y, m = y - 1, m + 12
            d_from = date(y, m, 1)
        if d_from > d_to:
            raise ValueError("La date de début doit précéder la date de fin.")
        zero = Decimal("0.00")
        return {
            "from": d_from, "to": d_to,
            "total": self.repo.expenses_total(d_from, d_to) or zero,
            "by_month": [{"month": m, "total": t} for m, t in self.repo.expenses_by_month(d_from, d_to)],
            "by_supplier": [{"supplier": s, "total": t}
                            for s, t in self.repo.expenses_by_supplier(d_from, d_to)],
        }

    def price_history(self, product_id: int) -> List[Dict[str, Any]]:
        if self.repo.get_product(product_id) is None:
            raise LabStockNotFoundError("Produit introuvable.")
        return [{"delivery_date": dd, "receipt_id": rid, "supplier": sup, "unit_price": price,
                 "received_qty": qty} for dd, rid, sup, price, qty in self.repo.price_history(product_id)]
