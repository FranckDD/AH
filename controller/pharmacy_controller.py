# controllers/pharmacy_controller.py

import json
import logging
import redis
import os
from decimal import Decimal
from typing import Optional, Dict
from dotenv import load_dotenv
from celery import Task

# --- Imports App ---
from repositories.audit_repo import AuditRepository

# --- Optimisation ---
try:
    from tasks.pharmacy_tasks import task_check_low_stock_alert # type: ignore
    task_check_low_stock_alert: Task = task_check_low_stock_alert # type: ignore
except ImportError:
    task_check_low_stock_alert = None # type: ignore

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

logger = logging.getLogger(__name__)


class PharmacyController:
    def __init__(self, repo, current_user, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo
        self.user = current_user  
        self.audit_repo = audit_repo

    # --- LECTURE OPTIMISÉE (CACHE) ---

    def get_stock_dashboard_stats(self) -> dict:
        """
        Aggregateur pour le dashboard (Cache 5 min).
        """
        CACHE_KEY = "pharmacy:stats:dashboard"
        
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached: return json.loads(cached) # type: ignore
        except Exception: pass

        # Calcul DB
        stats = {
            "totalValue": self.repo.get_total_valuation(),
            "countPharma": self.repo.count_by_category('pharm'),
            "countNatural": self.repo.count_by_category('natur'),
            "lowStockAlerts": self.repo.count_low_stock(),
            "expiredCount": self.repo.count_expired()
        }
        
        try:
            redis_client.setex(CACHE_KEY, 300, json.dumps(stats))
        except Exception: pass
        
        return stats

    def list_products(self):
        # Pas de cache global ici (liste trop volatile)
        return self.repo.list_all()
    
    def search_products(self, term=None, type_filter=None, status_filter=None, page=1, per_page=20):
        if type_filter == 'PHARMA': type_filter = 'pharm'
        elif type_filter == 'NATUREL': type_filter = 'natur'
        elif type_filter == 'MATERIEL': type_filter = 'nat'     
            
        return self.repo.search(term, type_filter, status_filter, page, per_page)

    def get_product(self, medication_id: int):
        prod = self.repo.get_by_id(medication_id)
        if not prod:
            raise ValueError(f"Aucun produit trouvé pour l'ID {medication_id}")
        return prod

    # --- ÉCRITURE AVEC CELERY ET INVALIDATION ---

    def _invalidate_stats(self):
        """Helper pour supprimer le cache des stats."""
        try:
            redis_client.delete("pharmacy:stats:dashboard")
        except Exception: pass

    def _trigger_stock_alert(self, product):
        """Helper pour lancer la tâche Celery."""
        if task_check_low_stock_alert:
            try:
                # On récupère les attributs de l'objet ORM ou dict
                pid = getattr(product, 'medication_id', None) or getattr(product, 'id', None)
                name = getattr(product, 'drug_name', 'Inconnu')
                qty = getattr(product, 'quantity', 0)
                min_qty = getattr(product, 'min_quantity', 5) # Valeur par défaut si non définie
                
                if pid:
                    task_check_low_stock_alert.delay(
                        product_id=pid,
                        product_name=name,
                        current_qty=qty,
                        min_qty=min_qty
                    )
            except Exception as e:
                print(f"⚠️ [CELERY] Erreur tâche alerte stock: {e}")

    def create_product(self, data: dict):
        prod = self.repo.create(data, self.user)
        self._invalidate_stats()
        self._trigger_stock_alert(prod) # Vérifier si on crée avec stock bas
        self._audit("CREATE", getattr(prod, 'medication_id', None), f"Produit: {data.get('drug_name')}")
        return prod

    def update_product(self, medication_id: int, data: dict):
        prod = self.repo.update(medication_id, data, self.user)
        self._invalidate_stats()
        self._trigger_stock_alert(prod)
        self._audit("UPDATE", medication_id, new_values=data)
        return prod

    def delete_product(self, medication_id: int):
        res = self.repo.delete(medication_id)
        if res:
            self._invalidate_stats()
            self._audit("DELETE", medication_id)
        return res

    def renew_stock(self, medication_id: int, added_quantity: int):
        res = self.repo.renew_stock(medication_id, added_quantity, self.user)
        self._invalidate_stats()
        
        # Récupérer l'objet mis à jour pour vérifier le niveau de stock
        # (renew_stock retourne souvent un bool ou l'objet, à adapter selon votre repo)
        updated_prod = self.repo.get_by_id(medication_id)
        if updated_prod:
            self._trigger_stock_alert(updated_prod)

        self._audit("RESTOCK", medication_id, f"Ajout de {added_quantity} unités.")
        return res

    # --- MÉTHODES KPI (Délèguent au dashboard stats ou direct repo si besoin spécifique) ---

    def list_critical_or_empty(self):
        return self.repo.get_critical_or_empty()
    
    def get_critical_stock_count_kpi(self) -> int:
        return self.repo.count_low_stock()
    
    def get_expiring_product_count_kpi(self, days: int = 30) -> int:
        expiring_items = self.repo.get_expiring_soon(days=days)
        return len(expiring_items)

    def get_total_stock_value_kpi(self) -> float:
        return self.repo.get_total_valuation()

    def get_pharma_count_kpi(self) -> int:
        return self.repo.count_by_category('pharm')

    def get_natural_count_kpi(self) -> int:
        return self.repo.count_by_category('natur')

    def get_expired_count_kpi(self) -> int:
        return self.repo.count_expired()

    # --- ALIAS POUR DASHBOARD ---

    def get_dashboard_critical_stock_kpi(self) -> int:
        return self.get_critical_stock_count_kpi()

    def get_dashboard_expiring_stock_kpi(self, days: int = 30) -> int:
        return self.get_expiring_product_count_kpi(days=days)
        
    def list_dashboard_critical_products(self):
        return self.list_critical_or_empty()
        
    def get_dashboard_total_stock_value_kpi(self) -> float:
        return self.get_total_stock_value_kpi()
    
    # --- HELPER AUDIT ---
    def _audit(self, action, resource_id, details=None, new_values=None):
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed=action,
                    resource_id=resource_id,
                    details=details,
                    new_values=new_values
                )
            except Exception:
                logger.exception("Échec de l'écriture d'audit")