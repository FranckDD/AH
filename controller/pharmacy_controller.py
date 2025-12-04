# controllers/pharmacy_controller.py
from decimal import Decimal
from repositories.audit_repo import AuditRepository
from typing import Optional

class PharmacyController:
    def __init__(self, repo, current_user, audit_repo: Optional[AuditRepository] = None):
        self.repo = repo
        self.user = current_user  
        self.audit_repo = audit_repo

    def list_products(self):
        return self.repo.list_all()
    
    def search_products(self, term=None, type_filter=None, status_filter=None, page=1, per_page=20):
        # Mapping optionnel : si le front envoie 'PHARMA', on convertit en 'pharmaceutique' pour la BD
        if type_filter == 'PHARMA':
            type_filter = 'pharm'
        elif type_filter == 'NATUREL': # Attention à la casse du front vs BD
            type_filter = 'natur'
        elif type_filter == 'MATERIEL':
            type_filter = 'nat'    
            
        return self.repo.search(term, type_filter, status_filter, page, per_page)

    def get_product(self, medication_id: int):
        prod = self.repo.get_by_id(medication_id)
        if not prod:
            raise ValueError(f"Aucun produit trouvé pour l'ID {medication_id}")
        return prod

    def create_product(self, data: dict):
        prod = self.repo.create(data, self.user)
        
        if self.audit_repo and self.user:
            try:
                prod_id = getattr(prod, 'id', None) or getattr(prod, 'medication_id', None)
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed="CREATE",
                    resource_id=prod_id,
                    details=f"Produit: {data.get('drug_name')} (Qté: {data.get('quantity')})" # type: ignore
                )
            except Exception: pass
        return prod

    def update_product(self, medication_id: int, data: dict):
        prod = self.repo.update(medication_id, data, self.user)
        
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed="UPDATE",
                    resource_id=medication_id,
                    new_values=data
                )
            except Exception: pass
        return prod

    def delete_product(self, medication_id: int):
        res = self.repo.delete(medication_id)
        if res and self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed="DELETE",
                    resource_id=medication_id
                )
            except Exception: pass
        return res

    def renew_stock(self, medication_id: int, added_quantity: int):
        res = self.repo.renew_stock(medication_id, added_quantity, self.user)
        
        if self.audit_repo and self.user:
            try:
                self.audit_repo.log_user_action(
                    current_user=self.user,
                    resource_type="PharmacyProduct",
                    action_performed="RESTOCK", # Action spécifique
                    resource_id=medication_id,
                    details=f"Ajout de {added_quantity} unités." # type: ignore
                )
            except Exception: pass
        return res

    def list_critical_or_empty(self):
        return self.repo.get_critical_or_empty()
    
    # NOUVELLE MÉTHODE POUR LE KPI DASHBOARD
    def get_critical_stock_count_kpi(self) -> int:
        """KPI: Nombre de produits en alerte (critique ou épuisé)"""
        return self.repo.count_low_stock()
    
    # NOUVELLE MÉTHODE KPI 2 : Compte des produits expirant bientôt
    def get_expiring_product_count_kpi(self, days: int = 30) -> int:
        """
        Retourne le nombre total de produits qui expireront dans les {days} prochains jours (par défaut 30).
        """
        expiring_items = self.repo.get_expiring_soon(days=days)
        return len(expiring_items) # Retourne le compte (int)

    # NOUVELLE MÉTHODE KPI 3 : Valeur Monétaire Totale du Stock
    
    
    # --- NOUVEAUX ALIAS POUR LE DASHBOARD (À AJOUTER) ---

    def get_dashboard_critical_stock_kpi(self) -> int:
        """Alias pour le Dashboard, utilisant la méthode existante du contrôleur."""
        return self.get_critical_stock_count_kpi()

    def get_dashboard_expiring_stock_kpi(self, days: int = 30) -> int:
        """Alias pour le Dashboard, utilisant la méthode existante du contrôleur."""
        return self.get_expiring_product_count_kpi(days=days)
        
    def list_dashboard_critical_products(self):
        """Alias pour l'affichage du tableau des produits critiques sur le Dashboard."""
        return self.list_critical_or_empty()
        
    def get_dashboard_total_stock_value_kpi(self) -> float:
        """Alias pour le KPI de la valeur totale du stock."""
        return self.get_total_stock_value_kpi()
    
    # --- MÉTHODES KPI POUR LA VUE STOCK (CORRIGÉES) ---

    def get_pharma_count_kpi(self) -> int:
        """KPI: Nombre de produits de type 'pharmaceutique'"""
        return self.repo.count_by_category('pharm')

    def get_natural_count_kpi(self) -> int:
        """KPI: Nombre de produits de type 'Naturel'"""
        return self.repo.count_by_category('natur')

    def get_expired_count_kpi(self) -> int:
        """KPI: Nombre total de produits périmés"""
        return self.repo.count_expired()



    def get_total_stock_value_kpi(self) -> float:
        """KPI: Valeur financière totale du stock"""
        return self.repo.get_total_valuation()

    def get_stock_dashboard_stats(self) -> dict:
        """
        Aggregateur pour le dashboard.
        Retourne toutes les stats en un seul appel pour optimiser le chargement de la vue.
        """
        return {
            "totalValue": self.get_total_stock_value_kpi(),
            "countPharma": self.get_pharma_count_kpi(),
            "countNatural": self.get_natural_count_kpi(),
            "lowStockAlerts": self.get_critical_stock_count_kpi(),
            "expiredCount": self.get_expired_count_kpi()
        }
    
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
                pass
