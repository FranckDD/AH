# view_pyqt6/fallback_controlle.py

from datetime import datetime, date
from typing import Optional, Union, Dict, List, Any

# --- GESTION DES IMPORTS AVEC FALLBACK ---

# 1. Pharmacy Controller Fallback
try:
    from .fallback_pharmacy_controller import FallbackPharmacyController
except ImportError:
    # On définit une classe locale avec un nom différent pour éviter la confusion de type
    class _MockPharmacyController:
        def get_critical_stock_count_kpi(self) -> Dict: return {"stock_alerts_count": 0}
        def list_products(self, **kwargs) -> Dict: return {'data': [], 'total': 0}
        def get_expiring_product_count_kpi(self, days: int = 30) -> Dict: return {"expiring_alerts_count": 0}
        def get_total_stock_value_kpi(self) -> Dict: return {"total_stock_value": 0.0}
        # IMPORTANT: Il faut que cette méthode existe pour que le resolver fonctionne
        def pharmacy_controller(self): return self 

    # On assigne l'alias en ignorant l'erreur de type
    FallbackPharmacyController = _MockPharmacyController # type: ignore

# 2. Patient Controller Fallback
try:
    from .fallback_patient_controller import FallbackPatientController
except ImportError:
    class _MockPatientController:
        def get_spiritual_new_patients_count_kpi(self, period: str = "week") -> Dict: return {"new_patients_count": 0}
        def get_spiritual_patient_status_kpi(self) -> Dict: return {"active_patients_count": 0, "inactive_patients_count": 0, "total_patients_count": 0}
        def get_spiritual_assurance_distribution_kpi(self) -> Dict: return {"assurance_distribution": {}}
        def list_patients(self, **kwargs) -> Dict: return {'data': [], 'total': 0}
        def get_by_id(self, patient_id: int) -> Optional[Dict]: return None
        def find_by_code(self, code: str) -> Optional[Dict]: return None
        # IMPORTANT
        def patient_controller(self): return self

    FallbackPatientController = _MockPatientController # type: ignore

try:
    # Assurez-vous que le chemin d'import est correct (par exemple, .fallback_caisse_controller)
    from .fallback_caisse_controller import CaisseFallbackController 
except ImportError:
    class _MockCaisseController:
        # Les signatures des méthodes KPI doivent correspondre à celles du contrôleur principal
        def get_financial_kpis(self, date_from: date, date_to: date) -> Dict: 
            return {
                "total_paid": 0.0, "total_factured": 0.0, "remaining_due": 0.0, 
                "recouvrement_rate": 0.0, "total_transactions": 0,
            }
        def get_unpaid_action_list(self, date_from: date, date_to: date) -> List[Dict]: return []
        def get_payment_distribution_kpi(self, date_from: date, date_to: date) -> Dict[str, float]: return {}
        # IMPORTANT: Doit exister pour la résolution
        def caisse_controller(self): return self

    CaisseFallbackController = _MockCaisseController # type: ignore    

try:
    from .fallback_caisse_retrait import CaisseRetraitFallbackController 
except ImportError:
    class _MockCaisseRetraitController:
        # Assurez-vous d'avoir les méthodes CRUD essentielles ici en cas d'échec d'import
        def list_retraits(self, **kwargs) -> Dict: return {'data': [], 'total': 0}
        def effectuer_retrait(self, amount: float, justification: str) -> Dict[str, Any]: 
            return {'id': -1, 'amount': amount, 'justification': justification, 'status': 'mocked'}
        def annuler_retrait(self, retrait_id: int, cancel_justification: str) -> bool: return True
        # IMPORTANT: Doit exister pour la résolution
        def caisse_retrait_controller(self): return self

    CaisseRetraitFallbackController = _MockCaisseRetraitController # type: ignore    


class _FallbackResolver:
    """Fallback minimal qui expose les controllers en mode hors ligne."""
    
    def __init__(self, controllers):
        self.controllers = controllers
        self.gateway = getattr(controllers, "gateway", None)
        self.primary_controller = getattr(controllers, "controller", None)
        self.fallback_controller = getattr(controllers, "fallback_controller", None)
        self.network_manager = getattr(controllers, "network_manager", None)

    def _offline_mode(self):
        nm = self.network_manager
        return bool(getattr(nm, "offline_mode", False))

    # ----------------------------------------------------------------
    # RESOLUTION DES CONTROLLERS (Priorité: Primary > Fallback > Gateway)
    # ----------------------------------------------------------------

    def appointment_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "appointment_controller"):
            return self.primary_controller.appointment_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "appointment_controller"):
            return self.fallback_controller.appointment_controller
        return getattr(self.controllers, "appointment_controller", None) or getattr(self.gateway, "appointment_controller", None)

    def patient_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "patient_controller"):
            return self.primary_controller.patient_controller
        
        # UTILISATION DU FALLBACK DÉDIÉ
        if self._offline_mode():
            return FallbackPatientController()
            
        return getattr(self.controllers, "patient_controller", None) or getattr(self.gateway, "patient_controller", None)

    def pharmacy_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "pharmacy_controller"):
            return self.primary_controller.pharmacy_controller
        
        # UTILISATION DU FALLBACK DÉDIÉ
        if self._offline_mode():
            return FallbackPharmacyController()

        return getattr(self.controllers, "pharmacy_controller", None) or getattr(self.gateway, "pharmacy_controller", None)

    def medical_record_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "medical_record_controller"):
            return self.primary_controller.medical_record_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "medical_record_controller"):
            return self.fallback_controller.medical_record_controller
        return getattr(self.controllers, "medical_record_controller", None) or getattr(self.gateway, "medical_record_controller", None)
    
    def prescription_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "prescription_controller"):
            return self.primary_controller.prescription_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "prescription_controller"):
            return self.fallback_controller.prescription_controller
        return getattr(self.controllers, "prescription_controller", None) or getattr(self.gateway, "prescription_controller", None)

    def lab_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "lab_controller"):
            return self.primary_controller.lab_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "lab_controller"):
            return self.fallback_controller.lab_controller
        return getattr(self.controllers, "lab_controller", None) or getattr(self.gateway, "lab_controller", None)
    
    def user_controller(self):
        if self.primary_controller and hasattr(self.primary_controller, "user_controller"):
            return self.primary_controller.user_controller
        if self._offline_mode() and self.fallback_controller and hasattr(self.fallback_controller, "user_controller"):
            return self.fallback_controller.user_controller
        return getattr(self.controllers, "user_controller", None) or getattr(self.gateway, "user_controller", None)
    
    def caisse_controller(self):
        # 1. Tentez le contrôleur Principal (mode en ligne)
        if self.primary_controller and hasattr(self.primary_controller, "caisse_controller"):
            return self.primary_controller.caisse_controller
        
        # 2. Si hors ligne, utilisez le Fallback dédié
        if self._offline_mode():
            # Nécessite d'injecter le repo local et l'utilisateur comme dans votre FallbackController
            # Nous supposons ici que le repo et l'utilisateur sont disponibles via self.controllers
            local_repo = getattr(self.controllers, "caisse_repo", None)
            current_user = getattr(self.controllers, "current_user", {})
            
            if local_repo:
                 # Assurez-vous que CaisseFallbackController accepte ces arguments
                return CaisseFallbackController(repo=local_repo, current_user=current_user) # type: ignore
            
            # Si le repo local n'est pas dispo (cas rare), on retourne un mock simple
            return CaisseFallbackController(repo=None, current_user={})  # type: ignore

        # 3. Par défaut (en ligne mais pas de contrôleur principal), utilisez le Gateway
        return getattr(self.controllers, "caisse_controller", None) or getattr(self.gateway, "caisse_controller", None)
    
    def caisse_retrait_controller(self):
        """
        Résout et retourne le contrôleur de Retrait de Caisse.
        Priorité : Primary Controller > Fallback Controller > Gateway/None.
        """
        # 1. Tentez le contrôleur Principal (mode en ligne)
        # Nous supposons que le contrôleur principal a aussi cette méthode
        if self.primary_controller and hasattr(self.primary_controller, "caisse_retrait_controller"):
            return self.primary_controller.caisse_retrait_controller
        
        # 2. Si hors ligne, utilisez le Fallback dédié
        if self._offline_mode():
            local_retrait_repo = getattr(self.controllers, "caisse_retrait_repo", None)
            current_user = getattr(self.controllers, "current_user", {})
            
            if local_retrait_repo:
                # Retourne l'instance du Fallback Controller local
                return CaisseRetraitFallbackController(
                    repo=local_retrait_repo,  # type: ignore
                    current_user=current_user # type: ignore
                ) # type: ignore
            
            # Si le repo local n'est pas dispo, on retourne un mock simple
            return CaisseRetraitFallbackController(repo=None, current_user={}) # type: ignore

        # 3. Par défaut (en ligne mais pas de contrôleur principal), utilisez le Gateway
        return getattr(self.controllers, "caisse_retrait_controller", None) or getattr(self.gateway, "caisse_retrait_controller", None)

    