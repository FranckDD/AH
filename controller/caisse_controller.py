# controllers/caisse_controller.py

import os
import json
import logging
import redis
from datetime import datetime, date
from utils.business_time import business_today
from typing import Dict, List, Optional
from dotenv import load_dotenv
from celery import Task

# --- Imports App ---
from models.caisse import Caisse
from repositories.caisse_repo import CaisseRepository
from repositories.audit_repo import AuditRepository
from models.consultation_spirituelle import ConsultationSpirituel
from models.patient import Patient
from repositories.staff_discount_repo import StaffDiscountRepository
from utils.staff_discount import compute_staff_discount
from utils.payment_mode_guard import resolve_payment_mode
from utils.price_lock import check_line_prices, record_price_mismatches, validate_lines
from decimal import Decimal, ROUND_HALF_UP

# --- Imports Optimisation ---
# On suppose l'existence d'un fichier de tâches pour la finance
# Si ce fichier n'existe pas encore, créez-le ou commentez cette ligne
try:
    from tasks.finance_tasks import task_process_payment_notification
    task_process_payment_notification: Task = task_process_payment_notification # type: ignore
except ImportError:
    # Fallback si le fichier task n'est pas encore créé
    task_process_payment_notification = None # type: ignore

# 🟢 CONFIGURATION REDIS
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

logger = logging.getLogger(__name__)


STAFF_MSG = "Réduction personnel incohérente avec les règles en vigueur."
_CENTS = Decimal("0.01")


def _q(v) -> Decimal:
    return Decimal(str(v)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def _same_instant(raw, stored) -> bool:
    """paid_at du payload (chaine ISO ou datetime) == valeur stockee (a la seconde, sans fuseau)."""
    try:
        val = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if stored is None:
        return False
    strip = lambda d: d.replace(tzinfo=None, microsecond=0)
    return strip(val) == strip(stored)


def _gross(items) -> Decimal:
    """Σ line_total des lignes actives ; line_total absent/None -> ValueError (400)."""
    total = Decimal("0")
    for line in items or []:
        lt = line.get("line_total") if isinstance(line, dict) else line
        if lt is None:
            raise ValueError("Ligne de facture sans montant (line_total manquant).")
        if isinstance(line, dict) and line.get("status") == "cancelled":
            continue
        total += Decimal(str(lt))
    return _q(total)


def _details_to_json(details):
    """Decimal -> float pour stockage JSONB (None conserve)."""
    if not details:
        return None
    return [
        {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}
        for d in details
    ]


def compute_staff_discount_for(session, data: dict) -> dict:
    """is_staff lu en base via patient_id (patient de passage -> non
    personnel) ; regles actives lues en base au moment de la sync."""
    patient_id = data.get("patient_id")
    is_staff = False
    if patient_id:
        patient = session.get(Patient, patient_id)
        is_staff = bool(patient and patient.is_staff)
    if not is_staff:
        return compute_staff_discount([], False, [])
    rules = StaffDiscountRepository(session).list_active_rules()
    lines = [
        {
            "item_type": l.get("item_type"),
            "line_total": l.get("line_total"),
            "status": l.get("status") or "active",
        }
        for l in data["items"]
    ]
    return compute_staff_discount(lines, True, rules)


def check_invoice_amounts(data: dict) -> tuple:
    """Invariant net : Σ lignes - reduction personnel == amount (montant du),
    en arrondi 2 decimales. Retourne (staff_sent, amount) Decimal ;
    ValueError sinon."""
    gross = _gross(data["items"])
    staff_sent = _q(data.get("staff_discount_amount") or 0)
    amount = _q(data["amount"])
    if _q(gross - staff_sent) != amount:
        raise ValueError(
            f"Incohérence montant: Lignes({gross}) - Réduction personnel({staff_sent}) "
            f"!= Total({amount})."
        )
    return staff_sent, amount


def validate_staff_discount(session, data: dict, sent) -> tuple:
    """Recalcule la reduction personnel cote serveur (le client ne fait pas
    foi) et la compare a la valeur envoyee (0 si absente). Retourne
    (montant Decimal, details JSON) ; ValueError(STAFF_MSG) si incoherent."""
    sent_q = _q(sent or 0)
    calc = compute_staff_discount_for(session, data)
    if _q(calc["amount"]) != sent_q:
        raise ValueError(STAFF_MSG)
    return sent_q, _details_to_json(calc["details"])


class CaisseController:
    def __init__(self, repo: CaisseRepository, current_user, audit_repo: Optional[AuditRepository] = None,
                 discount_repo=None, notification_repo=None):
        """
        - repo         : instance de CaisseRepository
        - current_user : instance de User (doit avoir l’attribut 'user_id' et 'username')
        - discount_repo : instance de DiscountRequestRepository, optionnel -
          seule build_ticket_data() en a besoin (recherche d'une reduction
          approuvee). None -> aucun bloc reduction n'est jamais recherche
          (comportement degrade, jamais une exception).
        """
        self.repo = repo
        self.user = current_user
        self.audit_repo = audit_repo
        self.discount_repo = discount_repo
        # Notifications d'ecart de prix (rejeu hors ligne) : cablee par
        # get_caisse_controller ; None -> audit seul, jamais d'exception.
        self.notification_repo = notification_repo

    # --- LECTURE AVEC CACHE REDIS ---

    def get_financial_kpis(self, date_from: date, date_to: date) -> Dict:
        """
        Récupère les agrégations financières (Total Payé, Impayé, Taux)
        Optimisé avec Redis (TTL: 5 minutes pour éviter de recalculer en boucle sur le dashboard).
        """
        if date_from > date_to:
            raise ValueError("La date de début ne peut pas être postérieure à la date de fin.")

        # Clé de cache unique basée sur la plage de date
        CACHE_KEY = f"caisse:kpis:{date_from}:{date_to}"

        # 1. Vérification Cache
        try:
            cached_data = redis_client.get(CACHE_KEY)
            if cached_data:
                return json.loads(cached_data) # type: ignore
        except Exception as e:
            print(f"⚠️ [REDIS] Erreur lecture cache KPI: {e}")

        # 2. Calcul DB (Lourd)
        result = self.repo.get_caisse_kpis(date_from, date_to)

        # 3. Mise en cache (300 secondes = 5 minutes)
        # On ne met pas trop longtemps car c'est de la finance, on veut des données fraiches
        try:
            redis_client.setex(CACHE_KEY, 300, json.dumps(result))
        except Exception: pass

        return result

    def get_payment_distribution_kpi(self, date_from: date, date_to: date) -> Dict[str, float]:
        """
        KPI Dashboard: Répartition des paiements.
        Optimisé avec Redis.
        """
        if date_from > date_to:
            raise ValueError("La date de début ne peut pas être postérieure à la date de fin.")

        CACHE_KEY = f"caisse:distrib:{date_from}:{date_to}"

        try:
            cached_data = redis_client.get(CACHE_KEY)
            if cached_data:
                return json.loads(cached_data) # type: ignore
        except Exception: pass

        raw_data = self.repo.get_payment_mode_distribution(date_from, date_to)
        
        # Transformation
        result = {}
        for item in raw_data:
            result[item["method"]] = item["total"]
            
        try:
            redis_client.setex(CACHE_KEY, 300, json.dumps(result))
        except Exception: pass

        return result

    def get_daily_total(self, for_date: date) -> float:
        """
        Somme des montants encaissés pour une date.
        """
        CACHE_KEY = f"caisse:daily_total:{for_date}"
        
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return float(cached) # type: ignore
        except Exception: pass

        total = self.repo.get_daily_total(for_date)
        
        # On cache pour 10 minutes
        try:
            redis_client.setex(CACHE_KEY, 600, total)
        except Exception: pass
        
        return total

    # --- MÉTHODES STANDARD (Sans Cache ou Cache inutile pour recherche) ---

    def list_transactions(self, page: int = 1, per_page: int = 50) -> dict:
        return self.search_transactions(page=page, per_page=per_page)

    def get_transaction(self, transaction_id: int) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        return tx

    def list_for_patient(self, patient_id: int) -> List[Caisse]:
        return self.repo.list_by_patient(patient_id)

    def list_by_payment_method(self, payment_method: str) -> List[Caisse]:
        return self.repo.list_by_payment_method(payment_method)

    def list_by_date_range(self, date_from: date, date_to: date) -> List[Caisse]:
        return self.repo.list_by_date_range(date_from, date_to)

    def search_transactions(self, term: str = None, payment_method: str = None, status: str = None, date_from: date = None, date_to: date = None, page: int = 1, per_page: int = 50) -> dict:
        items, total = self.repo.search_transactions(term, payment_method, status, date_from, date_to, page, per_page)
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_total_transactions(self, status: str = None, date_from: datetime | None = None, date_to: datetime | None = None) -> float:
        return self.repo.get_total_transactions(status, date_from=date_from, date_to=date_to)
    
    def get_total_payments(self, status: str = None, date_from: datetime | None = None, date_to: datetime | None = None) -> float:
        return self.repo.get_total_payments(status, date_from, date_to)
    
    def get_total_remaining_due(self, status: str = None, date_from: datetime | None = None, date_to: datetime | None = None) -> float:
        return self.repo.get_total_remaining_due(status, date_from, date_to)
    
    def get_unpaid_action_list(self, date_from: date, date_to: date) -> List[Dict]:
        if date_from > date_to:
            raise ValueError("La date de début ne peut pas être postérieure à la date de fin.")
        return self.repo.get_unpaid_transactions_details(date_from, date_to)    

    # --- ÉCRITURE AVEC INVALIDATION CACHE & CELERY ---

    def create_transaction(self, data: dict) -> Caisse:
        """
        Crée une transaction + Invalidation Cache + Notification Async.
        """
        required_keys = ["payment_method", "transaction_type", "amount", "items", "advance_amount"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Champ manquant : {key}")

        # 1. Validations métier
        if not data["items"] and data.get("advance_amount", 0) == 0:
            raise ValueError("La transaction doit contenir au moins une ligne ou indiquer une avance.")

        for line in data["items"]:
            if line["item_type"].lower() == "consultation":
                cs = self.repo.session.get(ConsultationSpirituel, line["item_ref_id"])
                if not cs:
                    raise ValueError(f"Aucune consultation pour l'ID = {line['item_ref_id']}")

        # Prix verrouille au catalogue (secretaire) : 422 en ligne, trace en rejeu.
        replay = bool(data.get("uuid"))
        validate_lines(data["items"])  # tous roles, rejeu compris
        price_mismatches = check_line_prices(self.repo.session, data["items"], self.user, replay)

        # Invariant net : Σ lignes − reduction personnel == amount (montant du)
        staff_sent, amount = check_invoice_amounts(data)

        # Recalcul serveur de la reduction personnel (le client ne fait pas foi)
        staff_sent, staff_details = validate_staff_discount(self.repo.session, data, staff_sent)
        data = {
            **data,
            "amount": amount,
            "staff_discount_amount": staff_sent,
            "staff_discount_details": staff_details,
            # Code officiel (valeur ancienne normalisee, mode desactive refuse)
            # uuid client = operation rejouee depuis la file hors ligne (jamais refusee pour le mode)
            "payment_method": resolve_payment_mode(self.repo.session, data["payment_method"], required=False,
                                                   replay=bool(data.get("uuid"))),
        }

        # 2. Création DB (Action bloquante)
        tx = self.repo.create_transaction(data, self.user)
        record_price_mismatches(self.repo.session, self.audit_repo, self.notification_repo,
                                self.user, tx, price_mismatches)

        # 3. 🟢 Invalidation Cache (Le total du jour a changé)
        try:
            today = business_today()
            # On supprime la clé du total journalier pour forcer le recalcul
            redis_client.delete(f"caisse:daily_total:{today}")
            # Note: Invalider les KPIs par range de date est complexe, on laisse le TTL (5min) expirer
            # ou on pourrait supprimer toutes les clés correspondantes si nécessaire.
        except Exception as e:
            print(f"⚠️ [REDIS] Erreur invalidation: {e}")

        # 4. 🟢 Tâche Async (Notification / Facture)
        if task_process_payment_notification:
            try:
                # On passe l'ID de la transaction. Celery ira chercher les infos (patient email, etc.)
                task_process_payment_notification.delay(
                    transaction_id=tx.transaction_id,
                    action="create"
                )
                print("⚡ [CELERY] Notification de paiement lancée.")
            except Exception as e:
                print(f"⚠️ [CELERY] Erreur tâche: {e}")

        return tx

    def _compute_staff_discount_for(self, data: dict) -> dict:
        return compute_staff_discount_for(self.repo.session, data)

    def add_installment_payment(self, transaction_id: int, data: dict):
        """
        Ajout paiement partiel + Invalidation + Notification.
        """
        tx = self.repo.get_by_id(transaction_id)
        if not tx: raise ValueError("Transaction introuvable")
        if tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")

        remaining = float(tx.amount) - float(tx.advance_amount)
        # Petite tolérance pour les float
        if data["paid_amount"] > remaining + 0.01: 
            raise ValueError(f"Montant trop élevé. Reste à payer : {remaining}")
        data = {**data, "payment_method": resolve_payment_mode(
            self.repo.session, data.get("payment_method"), required=False,
            replay=bool(data.get("uuid")))}

        result = self.repo.add_payment_installment(transaction_id, data, self.user)

        # 🟢 Invalidation Cache
        try:
            today = business_today()
            redis_client.delete(f"caisse:daily_total:{today}")
        except Exception: pass

        # 🟢 Tâche Async
        if task_process_payment_notification:
            try:
                task_process_payment_notification.delay(
                    transaction_id=transaction_id,
                    action="installment",
                    amount_paid=data["paid_amount"]
                )
            except Exception: pass

        return result

    def update_transaction(self, transaction_id: int, data: dict) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if not tx:
            raise ValueError(f"Aucune transaction trouvée pour l'ID = {transaction_id}")
        if tx.status == "cancelled":
            raise ValueError("Impossible de modifier une transaction annulée.")
        if tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")

        stored_details = getattr(tx, "staff_discount_details", None)
        locked = isinstance(stored_details, dict) and "replaced_by_discount_request" in stored_details
        if not locked and self.discount_repo is not None and any(k in data for k in ("items", "patient_id", "amount")):
            approved = self.discount_repo.get_approved_for_transaction(transaction_id)
            locked = bool(approved and approved.decision_percent)
        if locked and any(k in data for k in ("items", "patient_id", "amount")):
            raise ValueError("Facture avec réduction manuelle validée : modification des lignes, "
                             "du patient ou du montant impossible.")

        if (tx.staff_discount_amount or 0) > 0 and any(k in data for k in ("items", "patient_id", "amount")):
            raise ValueError("Facture avec réduction personnel : modification des lignes, du patient "
                             "ou du montant impossible. Annulez la facture puis créez-en une nouvelle.")

        if "items" in data:
            if not data["items"] and data.get("advance_amount", 0) == 0:
                raise ValueError("La liste d'items ne peut pas être vide ET advance_amount = 0.")
            # Meme controles qu'a la creation (PUT = toujours en ligne, uuid ignore).
            validate_lines(data["items"])
            check_line_prices(self.repo.session, data["items"], self.user, replay=False)

        # La reduction personnel n'est jamais fournie par le client sur PUT.
        data = {k: v for k, v in data.items()
                if k not in ("staff_discount_amount", "staff_discount_details")}

        # Cloture de caisse : l'argent encaisse ne bouge que via une ligne
        # paiement_echelonne (/payment, /settle). PUT accepte une valeur identique
        # (ignoree) mais refuse de changer advance_amount, ou paid_at d'une vente encaissee.
        if "advance_amount" in data:
            try:
                same = _q(data["advance_amount"] or 0) == _q(tx.advance_amount or 0)
            except Exception:
                same = False
            if not same:
                raise ValueError("Le montant payé ne se modifie pas : enregistrez un versement.")
            data.pop("advance_amount")
        if "paid_at" in data:
            if _q(tx.advance_amount or 0) > 0 and not _same_instant(data["paid_at"], tx.paid_at):
                raise ValueError("La date d'une facture déjà encaissée ne se modifie pas.")
            if _q(tx.advance_amount or 0) > 0:
                data.pop("paid_at")
        if "payment_method" in data:
            data["payment_method"] = resolve_payment_mode(self.repo.session, data["payment_method"],
                                                          required=False)

        if any(k in data for k in ("items", "patient_id", "amount")):
            # Etat fusionne : valeur du payload, sinon valeur stockee.
            if "items" in data:
                lines = data["items"]
            else:
                lines = [
                    {"item_type": i.item_type, "line_total": i.line_total, "status": i.status}
                    for i in tx.items if (i.status or "active") != "cancelled"
                ]
            merged = {
                "patient_id": data["patient_id"] if "patient_id" in data else tx.patient_id,
                "items": lines,
            }
            gross = _gross(lines)
            staff_calc = self._compute_staff_discount_for(merged)
            staff_amount = _q(staff_calc["amount"])
            net = _q(gross - staff_amount)
            stored_discount = _q(tx.staff_discount_amount or 0)
            if staff_amount == 0 and stored_discount == 0:
                # Aucune reduction en jeu : comportement historique inchange
                if "items" in data and "amount" in data and gross != _q(data["amount"]):
                    raise ValueError(
                        f"Incohérence montant: Lignes({gross}) - Réduction personnel(0.00) "
                        f"!= Total({_q(data['amount'])})."
                    )
                if "amount" in data:
                    data["amount"] = _q(data["amount"])
            else:
                if "amount" in data and _q(data["amount"]) != net:
                    raise ValueError(STAFF_MSG)
                data["amount"] = net
                data["staff_discount_amount"] = staff_amount
                data["staff_discount_details"] = _details_to_json(staff_calc["details"])

        updated_tx = self.repo.update_transaction(transaction_id, data, self.user)
        
        # Invalidation cache simple (on suppose que le montant a pu changer)
        try:
            redis_client.delete(f"caisse:daily_total:{business_today()}")
        except Exception: pass

        return updated_tx

    def cancel_transaction(self, transaction_id: int, justification: str) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        tx = self.repo.cancel_transaction(transaction_id, self.user, justification)

        # --- AUDIT ---
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="Transaction",
                    action_performed="CANCEL",
                    resource_id=transaction_id,
                    details=f"Annulation transaction financière : {justification}"
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")
            
        # Invalidation Cache
        try:
            redis_client.delete(f"caisse:daily_total:{business_today()}")
        except Exception: pass

        return tx

    def delete_transaction(self, transaction_id: int) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        # Action destructrice, on invalide tout ce qu'on peut
        try:
            redis_client.delete(f"caisse:daily_total:{business_today()}")
        except Exception: pass
        return self.repo.delete_transaction(transaction_id)

    def settle_transaction(self, transaction_id: int):
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        # Mode de la ligne SOLDE : celui de la vente, normalise (valeur ancienne -> code officiel)
        mode = resolve_payment_mode(self.repo.session, getattr(tx, "payment_method", None), required=False)
        res = self.repo.settle_transaction(transaction_id, self.user, mode)
        try:
            redis_client.delete(f"caisse:daily_total:{business_today()}")
        except Exception: pass
        return res
    
    def generate_invoice_pdf(self, transaction_id: int):
        # Cette méthode reste synchrone car souvent appelée par un bouton "Télécharger" direct
        # Anti-fraude : aucune facture imprimable tant qu'une réduction est en attente
        # (sinon un document au prix non valide pourrait sortir de l'établissement).
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        pdf_content = self.repo.generate_invoice_pdf_content(transaction_id)
        return pdf_content

    def build_ticket_data(self, transaction_id: int) -> dict:
        """Contenu structure du ticket thermique - reutilise integralement
        get_transaction_details_for_invoice() (meme source que la facture
        PDF, memes noms d'articles deja resolus via item.note). Le rendu
        ESC/POS lui-meme est la responsabilite du service pont local, pas
        de ce controller."""
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")

        data = self.repo.get_transaction_details_for_invoice(transaction_id)
        if not data:
            raise ValueError(f"Transaction ID {transaction_id} non trouvée.")

        data["remaining"] = data["amount"] - data["advance_amount"]
        data["payment_method"] = getattr(tx, "payment_method", None)

        data["discount"] = None
        if self.discount_repo:
            approved = self.discount_repo.get_approved_for_transaction(transaction_id)
            if approved:
                data["discount"] = {
                    "decision_percent": approved.decision_percent,
                    "decided_by_name": (approved.decider.full_name or approved.decider.username) if approved.decider else None,
                }

        staff_amount = float(getattr(tx, "staff_discount_amount", 0) or 0)
        data["staff_discount"] = (
            {"amount": staff_amount, "details": getattr(tx, "staff_discount_details", None) or []}
            if staff_amount > 0 else None
        )

        return data