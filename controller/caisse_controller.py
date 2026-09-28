# controllers/caisse_controller.py

import os
import json
import logging
import redis
from datetime import datetime, date
from typing import Dict, List, Optional
from dotenv import load_dotenv
from celery import Task

# --- Imports App ---
from models.caisse import Caisse
from repositories.caisse_repo import CaisseRepository
from repositories.audit_repo import AuditRepository
from models.consultation_spirituelle import ConsultationSpirituel

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


class CaisseController:
    def __init__(self, repo: CaisseRepository, current_user, audit_repo: Optional[AuditRepository] = None,
                 discount_repo=None):
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

        total_calc = sum(line["line_total"] for line in data["items"])
        if total_calc != data["amount"]:
            raise ValueError(f"Incohérence montant: Lignes({total_calc}) != Total({data['amount']}).")

        # 2. Création DB (Action bloquante)
        tx = self.repo.create_transaction(data, self.user)

        # 3. 🟢 Invalidation Cache (Le total du jour a changé)
        try:
            today = date.today()
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
            
        result = self.repo.add_payment_installment(transaction_id, data, self.user)

        # 🟢 Invalidation Cache
        try:
            today = date.today()
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

        if "items" in data:
            if not data["items"] and data.get("advance_amount", 0) == 0:
                raise ValueError("La liste d'items ne peut pas être vide ET advance_amount = 0.")
            total_calc = sum(line["line_total"] for line in data["items"])
            if "amount" in data and total_calc != data["amount"]:
                raise ValueError(f"Incohérence montant.")
            
            # Validation consultation items... (inchangé)

        updated_tx = self.repo.update_transaction(transaction_id, data, self.user)
        
        # Invalidation cache simple (on suppose que le montant a pu changer)
        try:
            redis_client.delete(f"caisse:daily_total:{date.today()}")
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
            redis_client.delete(f"caisse:daily_total:{date.today()}")
        except Exception: pass

        return tx

    def delete_transaction(self, transaction_id: int) -> Caisse:
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        # Action destructrice, on invalide tout ce qu'on peut
        try:
            redis_client.delete(f"caisse:daily_total:{date.today()}")
        except Exception: pass
        return self.repo.delete_transaction(transaction_id)

    def settle_transaction(self, transaction_id: int):
        tx = self.repo.get_by_id(transaction_id)
        if tx and tx.status == "pending_approval":
            raise ValueError("Facture en attente de validation d'une réduction - action impossible.")
        res = self.repo.settle_transaction(transaction_id, self.user.user_id)
        try:
            redis_client.delete(f"caisse:daily_total:{date.today()}")
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

        return data